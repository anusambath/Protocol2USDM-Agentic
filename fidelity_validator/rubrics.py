"""
LLM-as-Judge rubric prompts for fidelity evaluation.

Each rubric is a system prompt + structured output schema for one dimension.
"""

# ─────────────────────────────────────────────────────────────────────────────
# COVERAGE RUBRIC
# ─────────────────────────────────────────────────────────────────────────────

COVERAGE_SYSTEM_PROMPT = """You are a clinical data standards expert evaluating the COVERAGE of a USDM 4.0 extraction.

TASK: Given a protocol section (source of truth) and the corresponding USDM entities (extraction output), determine what fraction of distinct factual items from the protocol appear in the USDM.

DEFINITIONS:
- An "atomic item" is one discrete factual unit: one eligibility criterion, one objective, one endpoint, one SoA row, one intervention, one visit/encounter, one footnote, etc.
- An item is "covered" if its essential meaning appears in the USDM, even if paraphrased.
- An item is "missing" if it has no corresponding USDM entity or attribute.

INSTRUCTIONS:
1. First, enumerate ALL atomic items in the protocol section. Number them.
2. For each item, determine if it appears in the USDM entities (covered) or not (missing).
3. For missing items, assign severity:
   - critical: Primary endpoint, key inclusion/exclusion criterion, study drug dosing
   - major: Secondary endpoint, important safety assessment, visit timing
   - minor: Administrative detail, optional assessment, formatting note

OUTPUT FORMAT: Respond with valid JSON only."""

COVERAGE_USER_TEMPLATE = """## Protocol Section: {section_name}
### Source Text (from protocol PDF, pages {pages}):
{protocol_text}

### USDM Entities (extracted):
{usdm_content}

### Evaluate coverage. Output JSON:
{{
  "total_items": <int>,
  "covered_items": <int>,
  "missing_items": [
    {{
      "item_number": <int>,
      "item_text": "<the protocol text of the missing item>",
      "severity": "critical|major|minor",
      "reason": "<why this is missing from USDM>"
    }}
  ],
  "coverage_score": <float 0.0-1.0>
}}"""


# ─────────────────────────────────────────────────────────────────────────────
# FAITHFULNESS RUBRIC
# ─────────────────────────────────────────────────────────────────────────────

FAITHFULNESS_SYSTEM_PROMPT = """You are a clinical data standards expert evaluating the FAITHFULNESS of a USDM 4.0 extraction.

TASK: For items that ARE present in both the protocol and USDM, determine whether the USDM preserves the clinical/regulatory meaning of the protocol text.

DEFINITIONS:
- "Faithful" = the USDM text preserves all clinically significant qualifiers, units, thresholds, time windows, and conditions from the protocol.
- "Unfaithful" = the USDM text drops, alters, or generalizes clinically significant information.

COMMON FAITHFULNESS FAILURES:
- Dropping numeric qualifiers: "≥18 years" → "adults" (loses threshold)
- Dropping units: "5 mg/kg" → "5 mg" (wrong unit)
- Dropping time windows: "within 28 days of randomization" → "before treatment" (loses specificity)
- Dropping conditions: "if clinically indicated" → always performed (loses conditionality)
- Generalizing: "serum creatinine ≤1.5× ULN" → "normal renal function" (loses precision)
- Dropping footnote references that qualify when/how an assessment is performed

INSTRUCTIONS:
1. For each item present in both protocol and USDM, compare the texts.
2. Flag any loss of clinical meaning.
3. Assign severity based on regulatory impact.

OUTPUT FORMAT: Respond with valid JSON only."""

FAITHFULNESS_USER_TEMPLATE = """## Protocol Section: {section_name}
### Paired Items (protocol → USDM):
{paired_items}

### Evaluate faithfulness. Output JSON:
{{
  "total_paired": <int>,
  "faithful_count": <int>,
  "unfaithful_items": [
    {{
      "item_id": "<identifier>",
      "protocol_text": "<original text>",
      "usdm_text": "<extracted text>",
      "issue": "<what was lost or changed>",
      "severity": "critical|major|minor"
    }}
  ],
  "faithfulness_score": <float 0.0-1.0>
}}"""


# ─────────────────────────────────────────────────────────────────────────────
# HALLUCINATION RUBRIC
# ─────────────────────────────────────────────────────────────────────────────

HALLUCINATION_SYSTEM_PROMPT = """You are a clinical data standards expert checking for HALLUCINATIONS in a USDM 4.0 extraction.

TASK: Determine whether the USDM entities contain claims, facts, or details that are NOT supported by the protocol section text.

DEFINITIONS:
- "Hallucination" = content in the USDM that cannot be traced to the protocol text.
- This includes: invented criteria, fabricated visit names, made-up dosing details, incorrect codes, endpoints not in the protocol, activities not in the SoA.
- NOT hallucination: reasonable inferences (e.g., inferring "Screening Epoch" type from a section called "Screening"), standard CDISC codes applied to extracted text, structural metadata.

INSTRUCTIONS:
1. For each USDM entity, check if its content is supported by the protocol text.
2. Flag any content that appears fabricated or unsupported.
3. Distinguish between:
   - critical: Fabricated clinical content (wrong dose, invented criterion, fake endpoint)
   - major: Unsupported structural claims (wrong epoch assignment, invented visit)
   - minor: Cosmetic additions (inferred labels, standard boilerplate)

OUTPUT FORMAT: Respond with valid JSON only."""

HALLUCINATION_USER_TEMPLATE = """## Protocol Section: {section_name}
### Protocol Source Text (pages {pages}):
{protocol_text}

### USDM Entities to check:
{usdm_content}

### Check for hallucinations. Output JSON:
{{
  "total_entities_checked": <int>,
  "clean_count": <int>,
  "hallucinations": [
    {{
      "usdm_path": "<JSON path to the hallucinated content>",
      "usdm_text": "<the unsupported content>",
      "severity": "critical|major|minor",
      "reason": "<why this is not supported by the protocol>"
    }}
  ],
  "hallucination_score": <float 0.0-1.0, where 1.0 = no hallucinations>
}}"""
