"""Shared Hypothesis strategies and pytest fixtures for converter tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from hypothesis import strategies as st

from converter.constants import PRODIGY_METADATA_FIELDS

# ---------------------------------------------------------------------------
# Paths to reference files
# ---------------------------------------------------------------------------
_PRODIGY_DIR = Path(__file__).resolve().parents[2] / "ProdigyJSON"

ALEXION_PRODIGY_PATH = _PRODIGY_DIR / "Alexion_Prodigy.json"
ELILILLY_PRODIGY_PATH = _PRODIGY_DIR / "EliLily_Prodigy.json"
ALEXION_GOLDEN_PATH = _PRODIGY_DIR / "Alexion_NCT04573309_Wilsons_golden.json"
ELILILLY_GOLDEN_PATH = _PRODIGY_DIR / "EliLilly_NCT03421379_Diabetes_golden.json"

# ---------------------------------------------------------------------------
# Primitive strategies
# ---------------------------------------------------------------------------
_safe_text = st.text(
    alphabet=st.characters(categories=("L", "N", "P", "Z")),
    min_size=1,
    max_size=60,
)
_entity_id = st.text(
    alphabet=st.characters(categories=("L", "N"), whitelist_characters="_-"),
    min_size=4,
    max_size=30,
)

# ---------------------------------------------------------------------------
# Hypothesis strategies – Prodigy metadata fields
# ---------------------------------------------------------------------------


@st.composite
def prodigy_metadata_block(draw: st.DrawFn) -> dict[str, Any]:
    """Generate a dict containing a random subset of Prodigy metadata fields."""
    block: dict[str, Any] = {}
    for field in PRODIGY_METADATA_FIELDS:
        if draw(st.booleans()):
            if field == "provenance":
                block[field] = {
                    "document_id": draw(_safe_text),
                    "evidence": [],
                    "hash": draw(_safe_text),
                    "id": draw(_entity_id),
                }
            elif field == "confidenceScoring":
                block[field] = draw(st.floats(min_value=0.0, max_value=1.0))
            elif field == "hash":
                block[field] = "sha256:" + draw(
                    st.text(alphabet="0123456789abcdef", min_size=16, max_size=16)
                )
            elif field == "unmapped":
                block[field] = draw(st.booleans())
            elif field in ("kgLabel", "scopeId"):
                block[field] = draw(_safe_text)
            elif field == "complexityScoring":
                block[field] = draw(st.floats(min_value=0.0, max_value=10.0))
    return block


def _inject_metadata(base: dict, metadata: dict) -> dict:
    """Merge metadata fields into a base dict."""
    return {**base, **metadata}


# ---------------------------------------------------------------------------
# Hypothesis strategies – Code entities
# ---------------------------------------------------------------------------

_CODE_SYSTEMS = [
    "NCI Thesaurus",
    "http://www.cdisc.org",
    "SNOMED",
    "MedDRA",
    "LOINC",
]


@st.composite
def code_entity(draw: st.DrawFn) -> dict[str, Any]:
    """Generate a random Code entity (Prodigy-style, may have metadata)."""
    base: dict[str, Any] = {
        "id": draw(_entity_id),
        "code": draw(_safe_text),
        "codeSystem": draw(st.sampled_from(_CODE_SYSTEMS)),
        "decode": draw(_safe_text),
        "instanceType": "Code",
    }
    # Optionally include codeSystemVersion
    if draw(st.booleans()):
        base["codeSystemVersion"] = draw(_safe_text)
    # Optionally inject Prodigy metadata
    meta = draw(prodigy_metadata_block())
    return _inject_metadata(base, meta)


# ---------------------------------------------------------------------------
# Hypothesis strategies – Study entities
# ---------------------------------------------------------------------------

@st.composite
def study_design(draw: st.DrawFn) -> dict[str, Any]:
    """Generate a minimal Prodigy studyDesign dict."""
    design: dict[str, Any] = {
        "id": draw(_entity_id),
        "instanceType": "InterventionalStudyDesign",
    }
    meta = draw(prodigy_metadata_block())
    return _inject_metadata(design, meta)


@st.composite
def study_version(draw: st.DrawFn) -> dict[str, Any]:
    """Generate a Prodigy Study version dict with varying fields."""
    version: dict[str, Any] = {
        "id": draw(_entity_id),
        "instanceType": "StudyVersion",
    }
    # Optional fields
    if draw(st.booleans()):
        version["versionIdentifier"] = draw(_safe_text)
    if draw(st.booleans()):
        version["rationale"] = draw(_safe_text)
    if draw(st.booleans()):
        version["studyDesigns"] = draw(st.lists(study_design(), max_size=2))
    if draw(st.booleans()):
        version["titles"] = draw(
            st.lists(
                st.fixed_dictionaries(
                    {"id": _entity_id, "text": _safe_text, "instanceType": st.just("StudyTitle")}
                ),
                max_size=2,
            )
        )
    meta = draw(prodigy_metadata_block())
    return _inject_metadata(version, meta)



@st.composite
def study_entity(draw: st.DrawFn) -> dict[str, Any]:
    """Generate a random Prodigy Study entity with varying fields."""
    study: dict[str, Any] = {
        "id": draw(_entity_id),
        "name": draw(_safe_text),
        "instanceType": "Study",
    }
    # Optional fields
    if draw(st.booleans()):
        study["description"] = draw(_safe_text)
    if draw(st.booleans()):
        study["label"] = draw(_safe_text)
    if draw(st.booleans()):
        study["versions"] = draw(st.lists(study_version(), min_size=1, max_size=3))
    if draw(st.booleans()):
        study["documentedBy"] = draw(
            st.lists(
                st.fixed_dictionaries({
                    "id": _entity_id,
                    "name": _safe_text,
                    "instanceType": st.just("StudyDefinitionDocument"),
                }),
                max_size=2,
            )
        )
    meta = draw(prodigy_metadata_block())
    return _inject_metadata(study, meta)


# ---------------------------------------------------------------------------
# Hypothesis strategies – Relationships
# ---------------------------------------------------------------------------

@st.composite
def relationship_entry(draw: st.DrawFn) -> dict[str, Any]:
    """Generate a single Prodigy relationship entry."""
    return {
        "id": draw(_entity_id),
        "type": draw(st.sampled_from(["epochId", "armId", "activityIds", "parentId", "custom"])),
        "sourceId": draw(_entity_id),
        "targetId": draw(_entity_id),
    }


@st.composite
def relationships_array(draw: st.DrawFn) -> list[dict[str, Any]]:
    """Generate a random relationships array."""
    return draw(st.lists(relationship_entry(), max_size=5))


# ---------------------------------------------------------------------------
# Hypothesis strategies – Top-level Prodigy JSON dict
# ---------------------------------------------------------------------------

_KNOWN_TOP_LEVEL = [
    "Identifier",
    "PopulationDefinition",
    "ScheduledInstance",
    "SyntaxTemplate",
]

_DOMAIN_MODULE_NAMES = [
    "biomarker_driven_design_module",
    "adverse_event_analysis_module",
    "phase_ii_clinical_trial_module",
    "dose_optimization_design_module",
    "randomized_controlled_trial_design_module",
]

_AUXILIARY_KEYS = [
    "sdtm_trial_design_views",
    "document_map",
    "schedule_of_activity",
    "table_of_contents",
    "list_of_tables",
    "list_of_figures",
]


@st.composite
def prodigy_top_level_entity(draw: st.DrawFn) -> dict[str, Any]:
    """Generate a generic Prodigy top-level entity (Identifier, PopulationDefinition, etc.)."""
    entity: dict[str, Any] = {
        "id": draw(_entity_id),
        "name": draw(_safe_text),
    }
    meta = draw(prodigy_metadata_block())
    return _inject_metadata(entity, meta)


@st.composite
def prodigy_json_dict(draw: st.DrawFn) -> dict[str, Any]:
    """Generate a complete Prodigy-like JSON dict with Study and optional sections.

    Always includes a ``Study`` key. Randomly includes other top-level keys,
    domain modules, auxiliary data, metadata, and relationships.
    """
    doc: dict[str, Any] = {}

    # Study is always present
    doc["Study"] = draw(study_entity())

    # Random subset of known top-level entity keys
    for key in _KNOWN_TOP_LEVEL:
        if draw(st.booleans()):
            doc[key] = draw(prodigy_top_level_entity())

    # metadata
    if draw(st.booleans()):
        doc["metadata"] = {"created": draw(_safe_text)}

    # relationships
    if draw(st.booleans()):
        doc["relationships"] = draw(relationships_array())

    # Random domain modules
    for mod_name in _DOMAIN_MODULE_NAMES:
        if draw(st.booleans()):
            doc[mod_name] = {"summary": draw(_safe_text)}

    # Random auxiliary keys
    for aux_key in _AUXILIARY_KEYS:
        if draw(st.booleans()):
            doc[aux_key] = {"data": draw(_safe_text)}

    return doc


# ---------------------------------------------------------------------------
# Strategy to inject Prodigy metadata at random nesting depths
# ---------------------------------------------------------------------------

@st.composite
def nested_dict_with_metadata(draw: st.DrawFn, max_depth: int = 4) -> dict[str, Any]:
    """Generate a dict with Prodigy metadata fields injected at random depths."""
    meta = draw(prodigy_metadata_block())
    base: dict[str, Any] = {"id": draw(_entity_id), **meta}

    depth = draw(st.integers(min_value=0, max_value=max_depth))
    current = base
    for _ in range(depth):
        child_meta = draw(prodigy_metadata_block())
        child: dict[str, Any] = {"id": draw(_entity_id), **child_meta}
        current["nested"] = child
        current = child

    return base


# ---------------------------------------------------------------------------
# Pytest fixtures – reference file loading
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def alexion_prodigy() -> dict[str, Any]:
    """Load the Alexion Prodigy reference JSON."""
    with open(ALEXION_PRODIGY_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def elililly_prodigy() -> dict[str, Any]:
    """Load the EliLilly Prodigy reference JSON."""
    with open(ELILILLY_PRODIGY_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def alexion_golden() -> dict[str, Any]:
    """Load the Alexion golden USDM reference JSON."""
    with open(ALEXION_GOLDEN_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def elililly_golden() -> dict[str, Any]:
    """Load the EliLilly golden USDM reference JSON."""
    with open(ELILILLY_GOLDEN_PATH, encoding="utf-8") as f:
        return json.load(f)
