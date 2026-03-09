#!/usr/bin/env python3
"""
Generate golden reference files from agent pipeline extraction output.

This script reads the most recent extraction output for each golden protocol
and saves a normalized subset as golden reference files for comparison testing.

Golden files include:
  - Entity counts per domain
  - Key identifying content (names, text snippets) for content matching

Usage:
    python tests/test_agents/golden/generate_golden.py
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Resolve paths relative to project root
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Protocols in input/test_trials/ (flat PDFs, no subdirectories)
GOLDEN_PROTOCOLS = [
    "NCT02864992",
    "NCT03019588",
    "NCT03155997",
    "NCT03235752",
    "NCT03421431",
    "NCT03961204",
    "NCT04205812",
    "NCT04573972",
    "NCT04649359",
    "NCT04972110",
    "NCT05327491",
    "NCT05499130",
    "NCT05592275",
    "NCT05763147",
    "NCT05999994",
]

TRIAL_DIR = PROJECT_ROOT / "input" / "test_trials"
GOLDEN_DIR = PROJECT_ROOT / "tests" / "test_agents" / "golden" / "references"
OUTPUT_BASE = PROJECT_ROOT / "output"


# Agent pipeline output filenames (new naming convention)
PHASE_OUTPUT_FILES = {
    "metadata": "01_extraction_metadata.json",
    "soa_vision": "02_extraction_soa_vision.json",
    "soa_text": "03_extraction_soa_text.json",
    "narrative": "04_extraction_narrative.json",
    "docstructure": "05_extraction_document_structure.json",
    "eligibility": "06_extraction_eligibility.json",
    "objectives": "07_extraction_objectives.json",
    "studydesign": "08_extraction_study_design.json",
    "procedures": "09_extraction_procedures_devices.json",
    "interventions": "10_extraction_interventions.json",
    "scheduling": "11_extraction_scheduling_logic.json",
    "execution": "12_extraction_execution_model.json",
    "advanced": "13_extraction_advanced_entities.json",
}


def _find_protocol_pdf(nct_id: str) -> Optional[Path]:
    """Find the protocol PDF for a given NCT ID in the flat test_trials dir."""
    matches = list(TRIAL_DIR.glob(f"{nct_id}_*.pdf"))
    return matches[0] if matches else None


def _find_latest_output(nct_id: str) -> Optional[Path]:
    """Find the most recent timestamped output directory for a protocol."""
    # Agent pipeline outputs: output/{stem}_{timestamp}/
    # Match any directory starting with the NCT ID
    matches = sorted(OUTPUT_BASE.glob(f"{nct_id}_*"), reverse=True)
    # Filter to directories only
    matches = [m for m in matches if m.is_dir()]
    return matches[0] if matches else None


def _truncate(text: str, max_len: int = 120) -> str:
    """Truncate text for golden storage."""
    if not text:
        return ""
    text = text.strip().replace("\n", " ")
    return text[:max_len] if len(text) > max_len else text


# ---------------------------------------------------------------------------
# Entity extraction from agent output format
# Agent output: {"entities": [{"entity_type": "...", "data": {...}}, ...]}
# ---------------------------------------------------------------------------

def _get_entities(data: dict) -> List[dict]:
    """Get the entities list from agent output."""
    return data.get("entities", [])


def _entities_by_type(data: dict, entity_type: str) -> List[dict]:
    """Filter entities by type, returning the data dict for each."""
    return [
        e.get("data", {})
        for e in _get_entities(data)
        if e.get("entity_type") == entity_type
    ]


def _extract_metadata(data: dict) -> Dict[str, Any]:
    titles = _entities_by_type(data, "study_title")
    identifiers = _entities_by_type(data, "study_identifier")
    organizations = _entities_by_type(data, "organization")
    indications = _entities_by_type(data, "indication")

    return {
        "entity_counts": {
            "titles": len(titles),
            "identifiers": len(identifiers),
            "organizations": len(organizations),
            "indications": len(indications),
        },
        "identifiers": [
            {"text": _truncate(i.get("text", "")),
             "type": i.get("identifierType", {}).get("code", "")}
            for i in identifiers
        ],
        "titles": [
            {"text": _truncate(t.get("text", "")),
             "type": t.get("type", {}).get("decode", "")}
            for t in titles
        ],
        "organizations": [
            {"name": _truncate(o.get("name", "")),
             "type": o.get("type", {}).get("decode", "")}
            for o in organizations
        ],
    }


def _extract_eligibility(data: dict) -> Dict[str, Any]:
    criteria = _entities_by_type(data, "eligibility_criterion")
    items = _entities_by_type(data, "eligibility_criterion_item")

    inclusion = [c for c in criteria if c.get("category") == "inclusion"]
    exclusion = [c for c in criteria if c.get("category") == "exclusion"]

    return {
        "entity_counts": {
            "inclusion": len(inclusion),
            "exclusion": len(exclusion),
            "criteria": len(criteria),
            "items": len(items),
        },
        "criterion_items": [
            {"name": _truncate(it.get("name", ""), 80),
             "text": _truncate(it.get("text", ""))}
            for it in (items if items else criteria)
        ],
    }


def _extract_objectives(data: dict) -> Dict[str, Any]:
    objectives = _entities_by_type(data, "objective")
    endpoints = _entities_by_type(data, "endpoint")
    estimands = _entities_by_type(data, "estimand")

    return {
        "entity_counts": {
            "objectives": len(objectives),
            "endpoints": len(endpoints),
            "estimands": len(estimands),
        },
        "objectives": [
            {"name": _truncate(o.get("name", ""), 80),
             "level": o.get("level", {}).get("decode", "") if isinstance(o.get("level"), dict) else str(o.get("level", ""))}
            for o in objectives
        ],
        "endpoints": [
            {"name": _truncate(e.get("name", ""), 80)}
            for e in endpoints
        ],
    }


def _extract_studydesign(data: dict) -> Dict[str, Any]:
    arms = _entities_by_type(data, "study_arm")
    cohorts = _entities_by_type(data, "study_cohort")
    cells = _entities_by_type(data, "study_cell")
    elements = _entities_by_type(data, "study_element")

    return {
        "entity_counts": {
            "arms": len(arms),
            "cohorts": len(cohorts),
            "cells": len(cells),
            "elements": len(elements),
        },
        "arms": [
            {"name": _truncate(a.get("name", ""), 80),
             "type": a.get("type", {}).get("decode", "") if isinstance(a.get("type"), dict) else str(a.get("type", ""))}
            for a in arms
        ],
        "elements": [
            {"name": _truncate(e.get("name", ""), 80)}
            for e in elements
        ],
    }


def _extract_interventions(data: dict) -> Dict[str, Any]:
    interventions = _entities_by_type(data, "study_intervention")
    products = _entities_by_type(data, "investigational_product")
    administrations = _entities_by_type(data, "administration")

    return {
        "entity_counts": {
            "interventions": len(interventions),
            "products": len(products),
            "administrations": len(administrations),
        },
        "interventions": [
            {"name": _truncate(i.get("name", ""), 80),
             "description": _truncate(i.get("description", ""))}
            for i in interventions
        ],
        "products": [
            {"name": _truncate(p.get("name", ""), 80)}
            for p in products
        ],
    }


def _extract_narrative(data: dict) -> Dict[str, Any]:
    sections = _entities_by_type(data, "narrative_content")
    items = _entities_by_type(data, "narrative_content_item")
    abbreviations = _entities_by_type(data, "abbreviation")

    return {
        "entity_counts": {
            "sections": len(sections),
            "items": len(items),
            "abbreviations": len(abbreviations),
        },
        "sections": [
            {"name": _truncate(s.get("name", s.get("sectionTitle", "")), 80),
             "section_number": s.get("sectionNumber", "")}
            for s in sections
        ],
        "abbreviations": [
            {"term": _truncate(a.get("abbreviatedText", a.get("term", "")), 40),
             "expansion": _truncate(a.get("expandedText", a.get("expansion", "")), 80)}
            for a in abbreviations[:20]
        ],
    }


def _extract_advanced(data: dict) -> Dict[str, Any]:
    amendments = _entities_by_type(data, "study_amendment")
    countries = _entities_by_type(data, "country")
    sites = _entities_by_type(data, "study_site")

    return {
        "entity_counts": {
            "amendments": len(amendments),
            "countries": len(countries),
            "sites": len(sites),
        },
        "amendments": [
            {"name": _truncate(a.get("name", ""), 80),
             "number": a.get("number", ""),
             "summary": _truncate(a.get("summary", ""))}
            for a in amendments
        ],
        "countries": [
            {"name": c.get("name", c.get("countryName", ""))}
            for c in countries
        ],
    }


def _extract_procedures(data: dict) -> Dict[str, Any]:
    procedures = _entities_by_type(data, "procedure")
    devices = _entities_by_type(data, "medical_device")

    return {
        "entity_counts": {
            "procedures": len(procedures),
            "devices": len(devices),
        },
        "procedures": [
            {"name": _truncate(p.get("name", ""), 80),
             "type": p.get("procedureType", "")}
            for p in procedures
        ],
        "devices": [
            {"name": _truncate(d.get("name", ""), 80)}
            for d in devices
        ],
    }


def _extract_scheduling(data: dict) -> Dict[str, Any]:
    timings = _entities_by_type(data, "timing")
    conditions = _entities_by_type(data, "condition")
    transition_rules = _entities_by_type(data, "transition_rule")
    exits = _entities_by_type(data, "schedule_timeline_exit")

    return {
        "entity_counts": {
            "timings": len(timings),
            "conditions": len(conditions),
            "transition_rules": len(transition_rules),
            "exits": len(exits),
        },
        "timings": [
            {"name": _truncate(t.get("name", ""), 80),
             "value": t.get("value", "")}
            for t in timings
        ],
    }


def _extract_execution(data: dict) -> Dict[str, Any]:
    time_anchors = _entities_by_type(data, "time_anchor")
    repetitions = _entities_by_type(data, "repetition")
    execution_types = _entities_by_type(data, "execution_type")
    traversal_constraints = _entities_by_type(data, "traversal_constraint")
    visit_windows = _entities_by_type(data, "visit_window")
    dosing_regimens = _entities_by_type(data, "dosing_regimen")

    return {
        "entity_counts": {
            "time_anchors": len(time_anchors),
            "repetitions": len(repetitions),
            "execution_types": len(execution_types),
            "traversal_constraints": len(traversal_constraints),
            "visit_windows": len(visit_windows),
            "dosing_regimens": len(dosing_regimens),
        },
        "time_anchors": [
            {"definition": _truncate(a.get("definition", "")),
             "anchor_type": a.get("anchorType", "")}
            for a in time_anchors
        ],
    }


def _extract_docstructure(data: dict) -> Dict[str, Any]:
    references = _entities_by_type(data, "document_content_reference")
    annotations = _entities_by_type(data, "comment_annotation")
    versions = _entities_by_type(data, "document_version")

    return {
        "entity_counts": {
            "references": len(references),
            "annotations": len(annotations),
            "versions": len(versions),
        },
        "references": [
            {"name": _truncate(r.get("name", ""), 80),
             "section_number": r.get("sectionNumber", "")}
            for r in references
        ],
    }


def _extract_soa_vision(data: dict) -> Dict[str, Any]:
    """Extract SoA vision data from agent output.

    Agent wraps it as: entities[0].data.structure.columnHierarchy
    """
    entities = _get_entities(data)
    epochs = []
    encounters = []
    row_groups = 0
    footnotes = 0

    for e in entities:
        if e.get("entity_type") == "header_structure":
            structure = e.get("data", {}).get("structure", {})
            ch = structure.get("columnHierarchy", {})
            epochs = ch.get("epochs", [])
            encounters = ch.get("encounters", [])
            row_groups = len(structure.get("rowGroups", []))
            footnotes = len(structure.get("footnotes", []))
            break

    return {
        "entity_counts": {
            "epochs": len(epochs),
            "encounters": len(encounters),
        },
        "row_groups": row_groups,
        "footnotes": footnotes,
        "epochs": [
            {"name": _truncate(ep.get("name", ""), 80)}
            for ep in epochs
        ],
        "encounters": [
            {"name": _truncate(enc.get("name", ""), 80)}
            for enc in encounters
        ],
    }


def _extract_soa_text(data: dict) -> Dict[str, Any]:
    """Extract SoA text data from agent output.

    Agent stores result as a string repr or nested structure in
    entities[0].data.result. We parse activity names from it.
    """
    entities = _get_entities(data)
    activities = []

    for e in entities:
        if e.get("entity_type") == "soa_text_extraction":
            result = e.get("data", {}).get("result", "")
            # result may be a string repr of TextExtractionResult
            if isinstance(result, str) and "Activity(" in result:
                # Parse activity names from the string representation
                names = re.findall(r"name='([^']*)'", result)
                # Deduplicate while preserving order (activities appear first)
                seen = set()
                for name in names:
                    if name not in seen:
                        activities.append({"name": _truncate(name, 80)})
                        seen.add(name)
            elif isinstance(result, dict):
                # Structured result
                acts = result.get("activities", [])
                activities = [
                    {"name": _truncate(a.get("name", a.get("activityName", "")), 80)}
                    for a in acts
                ]
            break

    # Fallback: check for activity entities directly
    if not activities:
        for e in entities:
            if e.get("entity_type") == "activity":
                activities.append(
                    {"name": _truncate(e.get("data", {}).get("name", ""), 80)}
                )

    return {
        "entity_counts": {
            "activities": len(activities),
        },
        "activities": activities,
    }


# Dispatch table
_DOMAIN_EXTRACTORS = {
    "metadata": _extract_metadata,
    "eligibility": _extract_eligibility,
    "objectives": _extract_objectives,
    "studydesign": _extract_studydesign,
    "interventions": _extract_interventions,
    "narrative": _extract_narrative,
    "advanced": _extract_advanced,
    "procedures": _extract_procedures,
    "scheduling": _extract_scheduling,
    "execution": _extract_execution,
    "docstructure": _extract_docstructure,
    "soa_vision": _extract_soa_vision,
    "soa_text": _extract_soa_text,
}


def generate():
    """Generate golden reference files for all protocols with available output."""
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)

    generated = 0
    skipped = 0

    for nct_id in GOLDEN_PROTOCOLS:
        output_dir = _find_latest_output(nct_id)
        pdf_path = _find_protocol_pdf(nct_id)

        if not output_dir:
            print(f"  SKIP {nct_id}: no output directory found")
            skipped += 1
            continue

        if not pdf_path:
            print(f"  SKIP {nct_id}: no protocol PDF found")
            skipped += 1
            continue

        trial_golden_dir = GOLDEN_DIR / nct_id
        trial_golden_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n{nct_id}:")
        print(f"  Output: {output_dir.name}")
        print(f"  PDF:    {pdf_path.name}")

        for domain, filename in PHASE_OUTPUT_FILES.items():
            output_file = output_dir / filename
            if not output_file.exists():
                print(f"  SKIP {domain}: {filename} not found")
                continue

            with open(output_file, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            extractor = _DOMAIN_EXTRACTORS.get(domain)
            if not extractor:
                print(f"  SKIP {domain}: no extractor defined")
                continue

            golden = {
                "success": True,
                "domain": domain,
                "source_protocol": nct_id,
                "source_pdf": pdf_path.name,
            }
            golden.update(extractor(raw_data))

            golden_file = trial_golden_dir / f"{domain}.json"
            with open(golden_file, "w", encoding="utf-8") as f:
                json.dump(golden, f, indent=2, ensure_ascii=False)

            counts = golden.get("entity_counts", {})
            count_str = ", ".join(f"{k}={v}" for k, v in counts.items())
            content_keys = [k for k in golden if isinstance(golden[k], list)]
            content_count = sum(len(golden[k]) for k in content_keys)
            print(f"  OK   {domain}: {count_str} | {content_count} content items")
            generated += 1

    print(f"\nDone: {generated} golden files generated, {skipped} protocols skipped")


if __name__ == "__main__":
    generate()
