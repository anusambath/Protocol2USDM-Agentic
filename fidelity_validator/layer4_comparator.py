"""
Layer 4 — Fidelity Comparator

For each section, computes fidelity across five dimensions using LLM-as-judge
and produces the final report.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

from .models import (
    SectionMap,
    SectionSpec,
    SectionReport,
    FidelityReport,
    DimensionScore,
    Finding,
    Dimension,
    Severity,
)
from .layer2_protocol_extractor import ProtocolContent, ExtractedSection
from .layer3_usdm_indexer import USDMIndex, SectionIndex, format_entities_for_llm
from .rubrics import (
    COVERAGE_SYSTEM_PROMPT,
    COVERAGE_USER_TEMPLATE,
    FAITHFULNESS_SYSTEM_PROMPT,
    FAITHFULNESS_USER_TEMPLATE,
    HALLUCINATION_SYSTEM_PROMPT,
    HALLUCINATION_USER_TEMPLATE,
)

logger = logging.getLogger(__name__)


def evaluate_fidelity(
    protocol: ProtocolContent,
    usdm_index: USDMIndex,
    section_map: SectionMap,
    model: str = "claude-sonnet-4",
    output_dir: Optional[str] = None,
) -> FidelityReport:
    """Run full fidelity evaluation across all sections."""
    report = FidelityReport(
        protocol_file=protocol.pdf_path,
        usdm_file=usdm_index.usdm_path,
    )

    for section_spec in section_map.sections:
        sid = section_spec.id

        # Get protocol content for this section
        protocol_section = protocol.sections.get(sid)
        section_index = usdm_index.sections.get(sid, SectionIndex(section_id=sid))

        if not protocol_section:
            # Section not found in protocol — skip but note it
            logger.info(f"Section '{sid}' not found in protocol PDF — skipping")
            continue

        logger.info(f"Evaluating section: {section_spec.name}")

        # Evaluate each dimension
        presence = evaluate_presence(section_index, section_spec)
        coverage = evaluate_coverage(protocol_section, section_index, model)
        faithfulness = evaluate_faithfulness(protocol_section, section_index, model)
        placement = evaluate_placement(section_index, usdm_index, section_spec)
        hallucination = evaluate_hallucination(protocol_section, section_index, model)

        section_report = SectionReport(
            section_id=sid,
            section_name=section_spec.name,
            protocol_pages=list(range(protocol_section.page_start + 1, protocol_section.page_end + 2)),
            usdm_entity_count=section_index.entity_count,
            protocol_item_count=coverage.total_items,
            presence=presence,
            coverage=coverage,
            faithfulness=faithfulness,
            placement=placement,
            hallucination=hallucination,
            overall_score=0.0,
        )
        section_report.compute_overall()
        report.sections.append(section_report)

    report.compute_aggregates()
    return report


def evaluate_presence(
    section_index: SectionIndex,
    section_spec: SectionSpec,
) -> DimensionScore:
    """Check if the USDM target entities are populated at all."""
    findings = []
    total_targets = len(section_spec.usdm_targets)
    populated = 0

    # Check each target entity type
    target_types = {t.entity for t in section_spec.usdm_targets}
    found_types = {e.entity_type for e in section_index.entities}

    for target in section_spec.usdm_targets:
        if target.entity in found_types:
            populated += 1
        else:
            findings.append(Finding(
                dimension=Dimension.PRESENCE,
                severity=Severity.MAJOR,
                section_id=section_spec.id,
                usdm_path=target.path,
                message=f"USDM entity '{target.entity}' is not populated",
            ))

    score = populated / total_targets if total_targets > 0 else 0.0

    return DimensionScore(
        dimension=Dimension.PRESENCE,
        score=score,
        total_items=total_targets,
        passed_items=populated,
        findings=findings,
    )


def evaluate_coverage(
    protocol_section: ExtractedSection,
    section_index: SectionIndex,
    model: str = "claude-sonnet-4",
) -> DimensionScore:
    """Evaluate what fraction of protocol items appear in the USDM."""
    if not section_index.is_populated:
        return DimensionScore(
            dimension=Dimension.COVERAGE,
            score=0.0,
            total_items=0,
            passed_items=0,
            findings=[Finding(
                dimension=Dimension.COVERAGE,
                severity=Severity.CRITICAL,
                section_id=protocol_section.section_id,
                message="No USDM entities found — cannot evaluate coverage",
            )],
        )

    # Prepare LLM prompt
    usdm_text = format_entities_for_llm(section_index, max_chars=8000)
    protocol_text = protocol_section.raw_text[:12000]  # Cap for context window
    pages = f"{protocol_section.page_start + 1}-{protocol_section.page_end + 1}"

    user_prompt = COVERAGE_USER_TEMPLATE.format(
        section_name=protocol_section.section_name,
        pages=pages,
        protocol_text=protocol_text,
        usdm_content=usdm_text,
    )

    # Call LLM
    result = _call_llm_judge(COVERAGE_SYSTEM_PROMPT, user_prompt, model)
    if not result:
        return DimensionScore(
            dimension=Dimension.COVERAGE,
            score=0.5,  # Unknown — default to 50%
            findings=[Finding(
                dimension=Dimension.COVERAGE,
                severity=Severity.MINOR,
                section_id=protocol_section.section_id,
                message="LLM evaluation failed — score defaulted to 0.5",
            )],
        )

    # Parse LLM response
    total_items = result.get("total_items", 0)
    covered_items = result.get("covered_items", 0)
    missing = result.get("missing_items", [])
    score = result.get("coverage_score", covered_items / total_items if total_items > 0 else 0.0)

    findings = []
    for item in missing:
        sev = _parse_severity(item.get("severity", "major"))
        findings.append(Finding(
            dimension=Dimension.COVERAGE,
            severity=sev,
            section_id=protocol_section.section_id,
            protocol_evidence=item.get("item_text", ""),
            message=f"Missing from USDM: {item.get('item_text', '')[:100]}",
            item_id=str(item.get("item_number", "")),
        ))

    return DimensionScore(
        dimension=Dimension.COVERAGE,
        score=score,
        total_items=total_items,
        passed_items=covered_items,
        findings=findings,
    )


def evaluate_faithfulness(
    protocol_section: ExtractedSection,
    section_index: SectionIndex,
    model: str = "claude-sonnet-4",
) -> DimensionScore:
    """Evaluate whether present items preserve clinical meaning."""
    if not section_index.is_populated:
        return DimensionScore(dimension=Dimension.FAITHFULNESS, score=1.0)

    # Build paired items text
    paired_text = _build_paired_items(protocol_section, section_index)
    if not paired_text:
        return DimensionScore(dimension=Dimension.FAITHFULNESS, score=1.0)

    user_prompt = FAITHFULNESS_USER_TEMPLATE.format(
        section_name=protocol_section.section_name,
        paired_items=paired_text,
    )

    result = _call_llm_judge(FAITHFULNESS_SYSTEM_PROMPT, user_prompt, model)
    if not result:
        return DimensionScore(dimension=Dimension.FAITHFULNESS, score=0.5)

    total = result.get("total_paired", 0)
    faithful = result.get("faithful_count", 0)
    unfaithful = result.get("unfaithful_items", [])
    score = result.get("faithfulness_score", faithful / total if total > 0 else 1.0)

    findings = []
    for item in unfaithful:
        sev = _parse_severity(item.get("severity", "major"))
        findings.append(Finding(
            dimension=Dimension.FAITHFULNESS,
            severity=sev,
            section_id=protocol_section.section_id,
            protocol_evidence=item.get("protocol_text", ""),
            usdm_evidence=item.get("usdm_text", ""),
            message=item.get("issue", "Faithfulness issue"),
            item_id=item.get("item_id"),
        ))

    return DimensionScore(
        dimension=Dimension.FAITHFULNESS,
        score=score,
        total_items=total,
        passed_items=faithful,
        findings=findings,
    )


def evaluate_placement(
    section_index: SectionIndex,
    usdm_index: USDMIndex,
    section_spec: SectionSpec,
) -> DimensionScore:
    """Check if content is placed in the correct USDM entity."""
    # Simple heuristic: check if entities are in the expected entity types
    findings = []
    expected_types = {t.entity for t in section_spec.usdm_targets}
    total = section_index.entity_count
    correct = 0

    for entity in section_index.entities:
        if entity.entity_type in expected_types:
            correct += 1
        else:
            findings.append(Finding(
                dimension=Dimension.PLACEMENT,
                severity=Severity.MAJOR,
                section_id=section_spec.id,
                usdm_path=entity.json_path,
                message=f"Entity type '{entity.entity_type}' found but expected one of {expected_types}",
            ))

    score = correct / total if total > 0 else 1.0

    return DimensionScore(
        dimension=Dimension.PLACEMENT,
        score=score,
        total_items=total,
        passed_items=correct,
        findings=findings,
    )


def evaluate_hallucination(
    protocol_section: ExtractedSection,
    section_index: SectionIndex,
    model: str = "claude-sonnet-4",
) -> DimensionScore:
    """Check if USDM entities contain unsupported claims."""
    if not section_index.is_populated:
        return DimensionScore(dimension=Dimension.HALLUCINATION, score=1.0)

    usdm_text = format_entities_for_llm(section_index, max_chars=6000)
    protocol_text = protocol_section.raw_text[:10000]
    pages = f"{protocol_section.page_start + 1}-{protocol_section.page_end + 1}"

    user_prompt = HALLUCINATION_USER_TEMPLATE.format(
        section_name=protocol_section.section_name,
        pages=pages,
        protocol_text=protocol_text,
        usdm_content=usdm_text,
    )

    result = _call_llm_judge(HALLUCINATION_SYSTEM_PROMPT, user_prompt, model)
    if not result:
        return DimensionScore(dimension=Dimension.HALLUCINATION, score=0.5)

    total = result.get("total_entities_checked", 0)
    clean = result.get("clean_count", 0)
    hallucinations = result.get("hallucinations", [])
    score = result.get("hallucination_score", clean / total if total > 0 else 1.0)

    findings = []
    for item in hallucinations:
        sev = _parse_severity(item.get("severity", "major"))
        findings.append(Finding(
            dimension=Dimension.HALLUCINATION,
            severity=sev,
            section_id=protocol_section.section_id,
            usdm_path=item.get("usdm_path"),
            usdm_evidence=item.get("usdm_text"),
            message=item.get("reason", "Unsupported content"),
        ))

    return DimensionScore(
        dimension=Dimension.HALLUCINATION,
        score=score,
        total_items=total,
        passed_items=clean,
        findings=findings,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────────────

def _call_llm_judge(system_prompt: str, user_prompt: str, model: str) -> Optional[Dict]:
    """Call the LLM with a rubric and parse JSON response."""
    try:
        from anthropic import Anthropic, AnthropicBedrock
        import os

        use_bedrock = os.environ.get("CLAUDE_PROVIDER", "").lower() == "bedrock"

        if use_bedrock:
            aws_region = os.environ.get("AWS_REGION", "us-east-1")
            client = AnthropicBedrock(aws_region=aws_region, timeout=120.0)
            # Map model name to Bedrock inference profile
            _BEDROCK_MAP = {
                "claude-sonnet-4": "us.anthropic.claude-sonnet-4-20250514-v1:0",
                "claude-opus-4-7": "us.anthropic.claude-opus-4-7",
                "claude-opus-4-6": "us.anthropic.claude-opus-4-6-v1",
            }
            model_id = _BEDROCK_MAP.get(model, f"us.anthropic.{model}")
        else:
            api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")
            client = Anthropic(api_key=api_key, timeout=120.0)
            model_id = model

        params = {
            "model": model_id,
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        # Skip temperature for models that don't support it
        if "opus-4-7" not in model_id:
            params["temperature"] = 0.1

        response = client.messages.create(**params)

        content = response.content[0].text if response.content else ""

        # Parse JSON from response
        import re
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            content = json_match.group(1)

        return json.loads(content.strip())

    except json.JSONDecodeError as e:
        logger.warning(f"LLM response not valid JSON: {e}")
        return None
    except Exception as e:
        logger.warning(f"LLM judge call failed: {e}")
        return None


def _build_paired_items(
    protocol_section: ExtractedSection,
    section_index: SectionIndex,
) -> str:
    """Build a paired comparison text for faithfulness evaluation."""
    lines = []
    for i, entity in enumerate(section_index.entities[:20]):  # Cap at 20
        name = entity.data.get("name") or entity.data.get("text") or ""
        text = entity.data.get("text") or entity.data.get("description") or name
        if text:
            lines.append(f"Item {i+1}:")
            lines.append(f"  USDM ({entity.entity_type}): {text[:300]}")
            lines.append("")
    
    if not lines:
        return ""

    # Add protocol text for comparison
    header = f"Protocol source text:\n{protocol_section.raw_text[:6000]}\n\n"
    return header + "\n".join(lines)


def _parse_severity(s: str) -> Severity:
    """Parse severity string to enum."""
    s = s.lower().strip()
    if s == "critical":
        return Severity.CRITICAL
    elif s == "minor":
        return Severity.MINOR
    return Severity.MAJOR


# ─────────────────────────────────────────────────────────────────────────────
# Report generation
# ─────────────────────────────────────────────────────────────────────────────

def generate_json_report(report: FidelityReport, output_path: str) -> None:
    """Save the machine-readable fidelity report as JSON."""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report.model_dump_json(indent=2))


def generate_html_report(report: FidelityReport, output_path: str) -> None:
    """Generate a human-readable HTML report."""
    html = _build_html(report)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


def _build_html(report: FidelityReport) -> str:
    """Build the HTML report string."""
    sections_html = ""
    for s in report.sections:
        all_findings = (
            s.presence.findings + s.coverage.findings +
            s.faithfulness.findings + s.placement.findings +
            s.hallucination.findings
        )
        findings_rows = ""
        for f in sorted(all_findings, key=lambda x: (0 if x.severity == Severity.CRITICAL else 1 if x.severity == Severity.MAJOR else 2)):
            sev_class = f"sev-{f.severity.value}"
            findings_rows += f"""
            <tr class="{sev_class}">
                <td>{f.severity.value.upper()}</td>
                <td>{f.dimension.value}</td>
                <td>{f.message[:120]}</td>
                <td><code>{f.usdm_path or '-'}</code></td>
                <td>{f.protocol_evidence[:80] if f.protocol_evidence else '-'}</td>
            </tr>"""

        sections_html += f"""
        <div class="section-card">
            <h3>{s.section_name} <span class="score">{s.overall_score:.0%}</span></h3>
            <div class="scores">
                <span>Presence: {s.presence.score:.0%}</span>
                <span>Coverage: {s.coverage.score:.0%}</span>
                <span>Faithfulness: {s.faithfulness.score:.0%}</span>
                <span>Placement: {s.placement.score:.0%}</span>
                <span>Hallucination: {s.hallucination.score:.0%}</span>
            </div>
            <table class="findings">
                <tr><th>Severity</th><th>Dimension</th><th>Message</th><th>USDM Path</th><th>Protocol Evidence</th></tr>
                {findings_rows}
            </table>
        </div>"""

    return f"""<!DOCTYPE html>
<html>
<head>
    <title>USDM Fidelity Report</title>
    <style>
        body {{ font-family: -apple-system, sans-serif; margin: 2rem; background: #f8f9fa; }}
        h1 {{ color: #1a1a2e; }}
        .dashboard {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; margin: 1rem 0; }}
        .metric {{ background: white; padding: 1rem; border-radius: 8px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .metric .value {{ font-size: 2rem; font-weight: bold; color: #2d6a4f; }}
        .metric .label {{ font-size: 0.8rem; color: #666; }}
        .section-card {{ background: white; padding: 1.5rem; margin: 1rem 0; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .section-card h3 {{ margin-top: 0; }}
        .score {{ float: right; font-size: 1.2rem; color: #2d6a4f; }}
        .scores span {{ margin-right: 1rem; font-size: 0.85rem; color: #555; }}
        .findings {{ width: 100%; border-collapse: collapse; margin-top: 1rem; font-size: 0.85rem; }}
        .findings th {{ background: #e9ecef; padding: 0.5rem; text-align: left; }}
        .findings td {{ padding: 0.5rem; border-bottom: 1px solid #eee; }}
        .sev-critical td:first-child {{ color: #c00; font-weight: bold; }}
        .sev-major td:first-child {{ color: #e26b0a; font-weight: bold; }}
        .sev-minor td:first-child {{ color: #666; }}
        code {{ background: #f1f3f5; padding: 0.1rem 0.3rem; border-radius: 3px; font-size: 0.8rem; }}
    </style>
</head>
<body>
    <h1>USDM 4.0 Fidelity Report</h1>
    <p>Protocol: <code>{report.protocol_file}</code><br>
       USDM: <code>{report.usdm_file}</code></p>

    <div class="dashboard">
        <div class="metric"><div class="value">{report.overall_score:.0%}</div><div class="label">Overall</div></div>
        <div class="metric"><div class="value">{report.critical_findings}</div><div class="label">Critical</div></div>
        <div class="metric"><div class="value">{report.major_findings}</div><div class="label">Major</div></div>
        <div class="metric"><div class="value">{report.minor_findings}</div><div class="label">Minor</div></div>
        <div class="metric"><div class="value">{len(report.sections)}</div><div class="label">Sections</div></div>
    </div>

    <h2>Per-Section Results</h2>
    {sections_html}
</body>
</html>"""
