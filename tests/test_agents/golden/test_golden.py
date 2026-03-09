"""
Golden file tests for extraction agents.

These tests run real extraction agents against protocol PDFs and compare
entity counts AND key content to golden reference files generated from
existing pipeline output.

Skipped by default. Run with:
    pytest tests/test_agents/golden/ -m golden --run-golden -v

Requires:
    - Protocol PDFs in input/test_trials/
    - Golden reference files in tests/test_agents/golden/references/
    - LLM API access (GOOGLE_API_KEY or equivalent)
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import pytest

from agents.base import AgentTask
from agents.extraction import (
    AdvancedAgent,
    DocStructureAgent,
    EligibilityAgent,
    ExecutionAgent,
    InterventionsAgent,
    MetadataAgent,
    NarrativeAgent,
    ObjectivesAgent,
    ProceduresAgent,
    SchedulingAgent,
    SoATextAgent,
    SoAVisionAgent,
    StudyDesignAgent,
)

from .conftest import GOLDEN_DIR, GOLDEN_PROTOCOLS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Agent ↔ domain mapping
# ---------------------------------------------------------------------------

AGENT_DOMAIN_MAP = {
    "metadata": MetadataAgent,
    "eligibility": EligibilityAgent,
    "objectives": ObjectivesAgent,
    "studydesign": StudyDesignAgent,
    "interventions": InterventionsAgent,
    "soa_vision": SoAVisionAgent,
    "soa_text": SoATextAgent,
    "procedures": ProceduresAgent,
    "scheduling": SchedulingAgent,
    "execution": ExecutionAgent,
    "narrative": NarrativeAgent,
    "advanced": AdvancedAgent,
    "docstructure": DocStructureAgent,
}

# Default tolerance: allow entity counts to differ by up to this fraction
# e.g. 0.20 means ±20% of the golden count (minimum ±1)
DEFAULT_TOLERANCE = 0.20

# Minimum overlap ratio for content matching (fuzzy name matching)
CONTENT_OVERLAP_THRESHOLD = 0.60


def _load_golden(trial_name: str, domain: str) -> Optional[Dict[str, Any]]:
    """Load a golden reference file for a trial/domain pair."""
    path = GOLDEN_DIR / trial_name / f"{domain}.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _within_tolerance(actual: int, expected: int,
                      tolerance: float = DEFAULT_TOLERANCE) -> bool:
    """Check if actual count is within tolerance of expected."""
    if expected == 0:
        return actual == 0
    margin = max(1, int(expected * tolerance))
    return abs(actual - expected) <= margin


def _normalize_name(name: str) -> str:
    """Normalize a name for fuzzy comparison."""
    return name.strip().lower().replace("_", " ").replace("-", " ")


def _name_overlap(golden_names: List[str], actual_names: List[str]) -> float:
    """
    Compute the fraction of golden names found (fuzzy) in actual names.
    Returns a ratio between 0.0 and 1.0.
    """
    if not golden_names:
        return 1.0
    norm_actual = {_normalize_name(n) for n in actual_names}
    matched = 0
    for gn in golden_names:
        norm_gn = _normalize_name(gn)
        # Exact match or substring containment
        if norm_gn in norm_actual:
            matched += 1
        elif any(norm_gn in a or a in norm_gn for a in norm_actual):
            matched += 1
    return matched / len(golden_names)


def _build_test_params():
    """Build parametrized test cases from available golden files."""
    params = []
    for trial_name in GOLDEN_PROTOCOLS:
        for domain in AGENT_DOMAIN_MAP:
            golden_path = GOLDEN_DIR / trial_name / f"{domain}.json"
            if golden_path.exists():
                params.append(
                    pytest.param(
                        trial_name, domain,
                        id=f"{trial_name}-{domain}",
                    )
                )
    return params


# ---------------------------------------------------------------------------
# Content extraction helpers — pull names from agent result_data
# ---------------------------------------------------------------------------

def _get_actual_names(result_data: Dict[str, Any], domain: str, content_key: str) -> List[str]:
    """
    Extract entity names from agent result_data for content matching.
    Returns a list of name strings.
    """
    if not result_data:
        return []

    entities = result_data.get("entities", [])

    if domain == "metadata":
        if content_key == "identifiers":
            return [e.get("data", {}).get("text", "") for e in entities
                    if e.get("entity_type") == "study_identifier"]
        if content_key == "titles":
            return [e.get("data", {}).get("text", "") for e in entities
                    if e.get("entity_type") == "study_title"]
        if content_key == "organizations":
            return [e.get("data", {}).get("name", "") for e in entities
                    if e.get("entity_type") == "organization"]
        return []

    if domain == "eligibility":
        if content_key == "criterion_items":
            return [e.get("data", {}).get("name", "") for e in entities
                    if e.get("entity_type") in ("eligibility_criterion", "eligibility_criterion_item")]
        return []

    if domain == "objectives":
        if content_key == "objectives":
            return [e.get("data", {}).get("name", "") for e in entities
                    if e.get("entity_type") == "objective"]
        if content_key == "endpoints":
            return [e.get("data", {}).get("name", "") for e in entities
                    if e.get("entity_type") == "endpoint"]
        return []

    if domain == "studydesign":
        if content_key == "arms":
            return [e.get("data", {}).get("name", "") for e in entities
                    if e.get("entity_type") == "study_arm"]
        if content_key == "elements":
            return [e.get("data", {}).get("name", "") for e in entities
                    if e.get("entity_type") == "study_element"]
        return []

    if domain == "interventions":
        if content_key == "interventions":
            return [e.get("data", {}).get("name", "") for e in entities
                    if e.get("entity_type") == "study_intervention"]
        if content_key == "products":
            return [e.get("data", {}).get("name", "") for e in entities
                    if e.get("entity_type") == "investigational_product"]
        return []

    if domain == "narrative":
        if content_key == "sections":
            return [e.get("data", {}).get("name", e.get("data", {}).get("sectionTitle", ""))
                    for e in entities if e.get("entity_type") == "narrative_content"]
        if content_key == "abbreviations":
            return [e.get("data", {}).get("abbreviatedText", e.get("data", {}).get("term", ""))
                    for e in entities if e.get("entity_type") == "abbreviation"]
        return []

    if domain == "advanced":
        if content_key == "amendments":
            return [e.get("data", {}).get("name", "") for e in entities
                    if e.get("entity_type") == "study_amendment"]
        if content_key == "countries":
            return [e.get("data", {}).get("name", e.get("data", {}).get("countryName", ""))
                    for e in entities if e.get("entity_type") == "country"]
        return []

    if domain == "procedures":
        if content_key == "procedures":
            return [e.get("data", {}).get("name", "") for e in entities
                    if e.get("entity_type") == "procedure"]
        if content_key == "devices":
            return [e.get("data", {}).get("name", "") for e in entities
                    if e.get("entity_type") == "medical_device"]
        return []

    if domain == "scheduling":
        if content_key == "timings":
            return [e.get("data", {}).get("name", "") for e in entities
                    if e.get("entity_type") == "timing"]
        return []

    if domain == "execution":
        if content_key == "time_anchors":
            return [e.get("data", {}).get("definition", "") for e in entities
                    if e.get("entity_type") == "time_anchor"]
        return []

    if domain == "docstructure":
        if content_key == "references":
            return [e.get("data", {}).get("name", "") for e in entities
                    if e.get("entity_type") == "document_content_reference"]
        return []

    if domain == "soa_vision":
        raw = result_data.get("raw_result", result_data)
        ch = raw.get("columnHierarchy", {})
        if content_key == "epochs":
            return [e.get("name", "") for e in ch.get("epochs", [])]
        if content_key == "encounters":
            return [e.get("name", "") for e in ch.get("encounters", [])]
        return []

    if domain == "soa_text":
        raw = result_data.get("raw_result", result_data)
        if content_key == "activities":
            try:
                study = raw.get("study", {})
                versions = study.get("versions", [])
                if versions:
                    designs = versions[0].get("studyDesigns", [])
                    if designs:
                        return [a.get("name", a.get("activityName", ""))
                                for a in designs[0].get("activities", [])]
            except (IndexError, AttributeError):
                pass
            # Fallback: entity list
            return [e.get("data", {}).get("name", "") for e in entities
                    if e.get("entity_type") == "activity"]
        return []

    return []


# ---------------------------------------------------------------------------
# Count extraction helpers — pull counts from agent result_data
# ---------------------------------------------------------------------------

def _get_actual_count(result_data: Dict[str, Any], domain: str, key: str) -> int:
    """
    Extract the actual entity count from agent result_data.

    Each agent returns data in a slightly different structure, so we need
    domain-specific logic to find the right count.
    """
    if not result_data:
        return 0

    if domain == "metadata":
        summary = result_data.get("metadata_summary", {})
        mapping = {
            "titles": "title_count",
            "identifiers": "identifier_count",
            "organizations": "organization_count",
            "indications": "indication_count",
        }
        if key in mapping:
            return summary.get(mapping[key], 0)
        entities = result_data.get("entities", [])
        type_map = {
            "titles": "study_title",
            "identifiers": "study_identifier",
            "organizations": "organization",
            "indications": "indication",
        }
        if key in type_map:
            return sum(1 for e in entities if e.get("entity_type") == type_map[key])
        return 0

    entities = result_data.get("entities", [])

    if domain == "eligibility":
        if key == "inclusion":
            return sum(1 for e in entities
                       if e.get("entity_type") == "eligibility_criterion"
                       and e.get("data", {}).get("category") == "inclusion")
        if key == "exclusion":
            return sum(1 for e in entities
                       if e.get("entity_type") == "eligibility_criterion"
                       and e.get("data", {}).get("category") == "exclusion")
        if key in ("criteria", "items"):
            return len([e for e in entities
                        if e.get("entity_type") in ("eligibility_criterion", "eligibility_criterion_item")])
        return 0

    if domain == "objectives":
        type_map = {"objectives": "objective", "endpoints": "endpoint", "estimands": "estimand"}
        return sum(1 for e in entities if e.get("entity_type") == type_map.get(key, "")) if key in type_map else 0

    if domain == "studydesign":
        type_map = {"arms": "study_arm", "cohorts": "study_cohort", "cells": "study_cell", "elements": "study_element"}
        return sum(1 for e in entities if e.get("entity_type") == type_map.get(key, "")) if key in type_map else 0

    if domain == "interventions":
        type_map = {"interventions": "study_intervention", "products": "investigational_product", "administrations": "administration"}
        return sum(1 for e in entities if e.get("entity_type") == type_map.get(key, "")) if key in type_map else 0

    if domain == "narrative":
        type_map = {"sections": "narrative_content", "items": "narrative_content_item", "abbreviations": "abbreviation"}
        return sum(1 for e in entities if e.get("entity_type") == type_map.get(key, "")) if key in type_map else 0

    if domain == "advanced":
        type_map = {"amendments": "study_amendment", "countries": "country", "sites": "study_site"}
        return sum(1 for e in entities if e.get("entity_type") == type_map.get(key, "")) if key in type_map else 0

    if domain == "procedures":
        type_map = {"procedures": "procedure", "devices": "medical_device"}
        return sum(1 for e in entities if e.get("entity_type") == type_map.get(key, "")) if key in type_map else 0

    if domain == "scheduling":
        type_map = {"timings": "timing", "conditions": "condition", "transition_rules": "transition_rule", "exits": "schedule_timeline_exit"}
        return sum(1 for e in entities if e.get("entity_type") == type_map.get(key, "")) if key in type_map else 0

    if domain == "execution":
        type_map = {
            "time_anchors": "time_anchor", "repetitions": "repetition",
            "execution_types": "execution_type", "traversal_constraints": "traversal_constraint",
            "visit_windows": "visit_window", "dosing_regimens": "dosing_regimen",
        }
        return sum(1 for e in entities if e.get("entity_type") == type_map.get(key, "")) if key in type_map else 0

    if domain == "docstructure":
        type_map = {"references": "document_content_reference", "annotations": "comment_annotation", "versions": "document_version"}
        return sum(1 for e in entities if e.get("entity_type") == type_map.get(key, "")) if key in type_map else 0

    if domain == "soa_vision":
        raw = result_data.get("raw_result", result_data)
        if key == "epochs":
            return len(raw.get("columnHierarchy", {}).get("epochs", []))
        if key == "encounters":
            return len(raw.get("columnHierarchy", {}).get("encounters", []))
        return 0

    if domain == "soa_text":
        raw = result_data.get("raw_result", result_data)
        if key == "activities":
            try:
                study = raw.get("study", {})
                versions = study.get("versions", [])
                if versions:
                    designs = versions[0].get("studyDesigns", [])
                    if designs:
                        return len(designs[0].get("activities", []))
            except (IndexError, AttributeError):
                pass
            return sum(1 for e in entities if e.get("entity_type") == "activity")
        return 0

    return 0


# ---------------------------------------------------------------------------
# Content keys per domain — which golden keys contain entity name lists
# ---------------------------------------------------------------------------

CONTENT_KEYS = {
    "metadata": ["identifiers", "titles", "organizations"],
    "eligibility": ["criterion_items"],
    "objectives": ["objectives", "endpoints"],
    "studydesign": ["arms", "elements"],
    "interventions": ["interventions", "products"],
    "narrative": ["sections", "abbreviations"],
    "advanced": ["amendments", "countries"],
    "procedures": ["procedures", "devices"],
    "scheduling": ["timings"],
    "execution": ["time_anchors"],
    "docstructure": ["references"],
    "soa_vision": ["epochs", "encounters"],
    "soa_text": ["activities"],
}


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

@pytest.mark.golden
class TestGoldenExtraction:
    """Compare extraction agent output against golden reference files."""

    @pytest.fixture(autouse=True)
    def _setup(self, protocol_info):
        """Store protocol info for use in tests."""
        self.trial_name = protocol_info["trial_name"]
        self.pdf_path = protocol_info["pdf_path"]

    def _run_agent(self, domain: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Instantiate and run an extraction agent for the given domain.

        Returns (success, result_data) where result_data is the raw dict
        returned by agent.extract().
        """
        agent_cls = AGENT_DOMAIN_MAP[domain]
        agent = agent_cls()
        agent.initialize()

        task = AgentTask(
            task_id=f"golden_{domain}_{self.trial_name}",
            agent_id=agent.agent_id,
            input_data={
                "pdf_path": self.pdf_path,
                "protocol_text": "",
                "model": "gemini-2.5-pro",
                "output_dir": "",
            },
        )

        result = agent.execute(task)
        return result.success, result.data or {}

    # --- Parametrized golden comparison test ---

    @pytest.mark.parametrize("domain", list(AGENT_DOMAIN_MAP.keys()))
    def test_entity_counts(self, domain: str):
        """
        Run extraction agent and compare entity counts to golden reference.

        Allows a tolerance window since LLM outputs can vary between runs.
        """
        golden = _load_golden(self.trial_name, domain)
        if golden is None:
            pytest.skip(f"No golden file for {self.trial_name}/{domain}")

        golden_counts = golden.get("entity_counts", {})
        golden_success = golden.get("success", False)

        success, result_data = self._run_agent(domain)

        if not golden_success:
            logger.info(
                f"[{self.trial_name}/{domain}] Golden was success=False, "
                f"agent success={success}"
            )
            return

        assert success, (
            f"[{self.trial_name}/{domain}] Agent failed but golden was successful"
        )

        # --- Count comparison ---
        count_mismatches = []
        for key, expected in golden_counts.items():
            actual = _get_actual_count(result_data, domain, key)
            if not _within_tolerance(actual, expected):
                count_mismatches.append(
                    f"  {key}: expected ~{expected} (±{max(1, int(expected * DEFAULT_TOLERANCE))}), "
                    f"got {actual}"
                )

        # --- Content comparison ---
        content_mismatches = []
        for content_key in CONTENT_KEYS.get(domain, []):
            golden_items = golden.get(content_key, [])
            if not golden_items:
                continue

            # Extract names from golden
            golden_names = []
            for item in golden_items:
                if isinstance(item, dict):
                    golden_names.append(
                        item.get("name", item.get("text", item.get("term", "")))
                    )
                elif isinstance(item, str):
                    golden_names.append(item)

            if not golden_names:
                continue

            actual_names = _get_actual_names(result_data, domain, content_key)
            overlap = _name_overlap(golden_names, actual_names)

            if overlap < CONTENT_OVERLAP_THRESHOLD:
                content_mismatches.append(
                    f"  {content_key}: name overlap {overlap:.0%} < {CONTENT_OVERLAP_THRESHOLD:.0%} threshold "
                    f"(golden={len(golden_names)}, actual={len(actual_names)})"
                )

        all_mismatches = count_mismatches + content_mismatches
        if all_mismatches:
            mismatch_str = "\n".join(all_mismatches)
            pytest.fail(
                f"[{self.trial_name}/{domain}] Mismatches:\n{mismatch_str}"
            )
