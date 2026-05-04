"""Integration tests comparing converter pipeline output against golden files.

Validates Requirements 19.1, 19.2, 19.3 — the converter produces structurally
consistent USDM 4.0 output for both Alexion and EliLilly Prodigy inputs.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from converter.constants import PRODIGY_METADATA_FIELDS, USDM_VERSION
from converter.enricher import enrich, normalize_codes
from converter.mapper import map_to_usdm
from converter.parser import parse_prodigy
from converter.serializer import serialize
from converter.stripper import strip_metadata


# ---------------------------------------------------------------------------
# Helper: run the full conversion pipeline on a raw Prodigy dict
# ---------------------------------------------------------------------------


def _run_pipeline(raw: dict) -> dict:
    """Run the full converter pipeline and return the parsed output dict."""
    doc = parse_prodigy(raw)

    # Strip metadata from all sections
    doc.study = strip_metadata(doc.study)
    doc.identifiers = strip_metadata(doc.identifiers)
    doc.population_definition = strip_metadata(doc.population_definition)
    doc.scheduled_instances = strip_metadata(doc.scheduled_instances)
    doc.syntax_templates = strip_metadata(doc.syntax_templates)
    doc.metadata = strip_metadata(doc.metadata)
    doc.relationships = strip_metadata(doc.relationships)
    doc.domain_modules = strip_metadata(doc.domain_modules)
    doc.auxiliary = strip_metadata(doc.auxiliary)

    usdm_doc = map_to_usdm(doc)
    enrich(usdm_doc.study)
    normalize_codes(usdm_doc.study)

    output_json = serialize(usdm_doc)
    return json.loads(output_json)


# ---------------------------------------------------------------------------
# Helper: recursively check that no Prodigy metadata fields exist
# ---------------------------------------------------------------------------

# Metadata fields that must never appear in the output
_BANNED_FIELDS = PRODIGY_METADATA_FIELDS - {"scopeId"}


def _assert_no_prodigy_metadata(obj: Any, path: str = "$") -> None:
    """Recursively assert no banned Prodigy metadata fields exist anywhere."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in _BANNED_FIELDS:
                pytest.fail(
                    f"Prodigy metadata field '{key}' found at {path}.{key}"
                )
            # scopeId is only allowed on StudyIdentifier entities
            if key == "scopeId" and obj.get("instanceType") != "StudyIdentifier":
                pytest.fail(
                    f"scopeId found on non-StudyIdentifier entity at {path}.{key} "
                    f"(instanceType={obj.get('instanceType')})"
                )
            _assert_no_prodigy_metadata(value, f"{path}.{key}")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _assert_no_prodigy_metadata(item, f"{path}[{i}]")


# ---------------------------------------------------------------------------
# Helper: recursively check enrichment invariants
# ---------------------------------------------------------------------------


def _assert_enrichment_invariants(obj: Any, path: str = "$") -> None:
    """Assert all entities with instanceType have extensionAttributes."""
    if isinstance(obj, dict):
        if "instanceType" in obj:
            assert "extensionAttributes" in obj, (
                f"Entity at {path} has instanceType={obj['instanceType']} "
                f"but missing extensionAttributes"
            )
            assert isinstance(obj["extensionAttributes"], list), (
                f"extensionAttributes at {path} is not a list"
            )
        for key, value in obj.items():
            _assert_enrichment_invariants(value, f"{path}.{key}")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _assert_enrichment_invariants(item, f"{path}[{i}]")


# ---------------------------------------------------------------------------
# Helper: recursively check Code entity completeness
# ---------------------------------------------------------------------------


def _assert_code_entities_valid(obj: Any, path: str = "$") -> None:
    """Assert all Code entities have required fields and normalized codeSystem."""
    if isinstance(obj, dict):
        if obj.get("instanceType") == "Code":
            for field in ("id", "extensionAttributes", "code", "codeSystem",
                          "codeSystemVersion", "decode", "instanceType"):
                assert field in obj, (
                    f"Code entity at {path} missing required field '{field}'"
                )
            assert obj["codeSystem"] != "NCI Thesaurus", (
                f"Code entity at {path} has un-normalized codeSystem 'NCI Thesaurus'"
            )
        for key, value in obj.items():
            _assert_code_entities_valid(value, f"{path}.{key}")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _assert_code_entities_valid(item, f"{path}[{i}]")


# ---------------------------------------------------------------------------
# Expected USDM 4.0 StudyVersion keys (from golden files)
# ---------------------------------------------------------------------------

_EXPECTED_VERSION_KEYS = {
    "id",
    "instanceType",
    "extensionAttributes",
    "versionIdentifier",
    "rationale",
    "documentVersionIds",
    "dateValues",
    "amendments",
    "businessTherapeuticAreas",
    "studyIdentifiers",
    "referenceIdentifiers",
    "studyDesigns",
    "titles",
    "eligibilityCriterionItems",
    "narrativeContentItems",
    "abbreviations",
    "roles",
    "organizations",
    "studyInterventions",
    "administrableProducts",
    "medicalDevices",
    "productOrganizationRoles",
    "biomedicalConcepts",
    "bcCategories",
    "bcSurrogates",
    "dictionaries",
    "conditions",
    "notes",
}


# ===================================================================
# Alexion integration tests
# ===================================================================


class TestAlexionIntegration:
    """Integration tests for Alexion Prodigy → USDM conversion."""

    @pytest.fixture(scope="class")
    def alexion_output(self, alexion_prodigy: dict) -> dict:
        """Run the full pipeline on the Alexion Prodigy input."""
        return _run_pipeline(alexion_prodigy)

    def test_top_level_keys(self, alexion_output: dict, alexion_golden: dict):
        """Output has the same top-level keys as the golden file."""
        assert set(alexion_output.keys()) == {"study", "usdmVersion", "systemName", "systemVersion"}
        assert set(alexion_output.keys()) == set(alexion_golden.keys())

    def test_usdm_version(self, alexion_output: dict):
        """usdmVersion is 4.0.0."""
        assert alexion_output["usdmVersion"] == USDM_VERSION

    def test_study_instance_type(self, alexion_output: dict):
        """study.instanceType is Study."""
        assert alexion_output["study"]["instanceType"] == "Study"

    def test_study_name_preserved(self, alexion_output: dict, alexion_prodigy: dict):
        """study.name is preserved from the Prodigy input."""
        assert alexion_output["study"]["name"] == alexion_prodigy["Study"]["name"]

    def test_study_version_keys(self, alexion_output: dict):
        """study.versions[0] has all expected USDM 4.0 keys."""
        versions = alexion_output["study"]["versions"]
        assert len(versions) >= 1
        actual_keys = set(versions[0].keys())
        assert _EXPECTED_VERSION_KEYS.issubset(actual_keys), (
            f"Missing keys: {_EXPECTED_VERSION_KEYS - actual_keys}"
        )

    def test_no_prodigy_metadata(self, alexion_output: dict):
        """No Prodigy metadata fields exist anywhere in the output."""
        _assert_no_prodigy_metadata(alexion_output)

    def test_enrichment_invariants(self, alexion_output: dict):
        """All entities with instanceType have extensionAttributes."""
        _assert_enrichment_invariants(alexion_output)

    def test_code_entities_valid(self, alexion_output: dict):
        """All Code entities have required fields and normalized codeSystem."""
        _assert_code_entities_valid(alexion_output)

    def test_structural_consistency_with_golden(self, alexion_output: dict, alexion_golden: dict):
        """Output study structure is consistent with the golden file."""
        out_study = alexion_output["study"]
        gold_study = alexion_golden["study"]

        # Golden file keys should be a subset of output keys (converter may
        # add enrichment fields like extensionAttributes on the Study root)
        golden_keys = set(gold_study.keys())
        output_keys = set(out_study.keys())
        assert golden_keys.issubset(output_keys), (
            f"Golden file has keys not in output: {golden_keys - output_keys}"
        )

        # Same instanceType
        assert out_study["instanceType"] == gold_study["instanceType"]

        # Both have versions
        assert len(out_study["versions"]) >= 1
        assert len(gold_study["versions"]) >= 1


# ===================================================================
# EliLilly integration tests
# ===================================================================


class TestEliLillyIntegration:
    """Integration tests for EliLilly Prodigy → USDM conversion."""

    @pytest.fixture(scope="class")
    def elililly_output(self, elililly_prodigy: dict) -> dict:
        """Run the full pipeline on the EliLilly Prodigy input."""
        return _run_pipeline(elililly_prodigy)

    def test_top_level_keys(self, elililly_output: dict, elililly_golden: dict):
        """Output has the same top-level keys as the golden file."""
        assert set(elililly_output.keys()) == {"study", "usdmVersion", "systemName", "systemVersion"}
        assert set(elililly_output.keys()) == set(elililly_golden.keys())

    def test_usdm_version(self, elililly_output: dict):
        """usdmVersion is 4.0.0."""
        assert elililly_output["usdmVersion"] == USDM_VERSION

    def test_study_instance_type(self, elililly_output: dict):
        """study.instanceType is Study."""
        assert elililly_output["study"]["instanceType"] == "Study"

    def test_study_name_preserved(self, elililly_output: dict, elililly_prodigy: dict):
        """study.name is preserved from the Prodigy input."""
        assert elililly_output["study"]["name"] == elililly_prodigy["Study"]["name"]

    def test_study_version_keys(self, elililly_output: dict):
        """study.versions[0] has all expected USDM 4.0 keys."""
        versions = elililly_output["study"]["versions"]
        assert len(versions) >= 1
        actual_keys = set(versions[0].keys())
        assert _EXPECTED_VERSION_KEYS.issubset(actual_keys), (
            f"Missing keys: {_EXPECTED_VERSION_KEYS - actual_keys}"
        )

    def test_no_prodigy_metadata(self, elililly_output: dict):
        """No Prodigy metadata fields exist anywhere in the output."""
        _assert_no_prodigy_metadata(elililly_output)

    def test_enrichment_invariants(self, elililly_output: dict):
        """All entities with instanceType have extensionAttributes."""
        _assert_enrichment_invariants(elililly_output)

    def test_code_entities_valid(self, elililly_output: dict):
        """All Code entities have required fields and normalized codeSystem."""
        _assert_code_entities_valid(elililly_output)

    def test_structural_consistency_with_golden(self, elililly_output: dict, elililly_golden: dict):
        """Output study structure is consistent with the golden file."""
        out_study = elililly_output["study"]
        gold_study = elililly_golden["study"]

        # Golden file keys should be a subset of output keys (converter may
        # add enrichment fields like extensionAttributes on the Study root)
        golden_keys = set(gold_study.keys())
        output_keys = set(out_study.keys())
        assert golden_keys.issubset(output_keys), (
            f"Golden file has keys not in output: {golden_keys - output_keys}"
        )

        # Same instanceType
        assert out_study["instanceType"] == gold_study["instanceType"]

        # Both have versions
        assert len(out_study["versions"]) >= 1
        assert len(gold_study["versions"]) >= 1
