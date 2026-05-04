"""Unit tests for converter.enricher module."""

from __future__ import annotations

import copy
from typing import Any

import pytest

from converter.enricher import (
    enrich,
    inject_extension_attributes,
    normalize_codes,
    validate_id_references,
    validate_instance_type,
)
from converter.models import ConversionStats, USDMDocument


# ---------------------------------------------------------------------------
# inject_extension_attributes
# ---------------------------------------------------------------------------


class TestInjectExtensionAttributes:
    def test_adds_when_missing(self):
        entity = {"id": "e1", "instanceType": "Study"}
        inject_extension_attributes(entity)
        assert entity["extensionAttributes"] == []

    def test_preserves_when_present(self):
        existing = [{"id": "ext1"}]
        entity = {"id": "e1", "instanceType": "Study", "extensionAttributes": existing}
        inject_extension_attributes(entity)
        assert entity["extensionAttributes"] is existing


# ---------------------------------------------------------------------------
# validate_instance_type
# ---------------------------------------------------------------------------


class TestValidateInstanceType:
    def test_preserves_existing(self):
        entity = {"id": "e1", "instanceType": "Study"}
        validate_instance_type(entity, context="")
        assert entity["instanceType"] == "Study"

    def test_infers_from_context(self):
        entity = {"id": "e1"}
        validate_instance_type(entity, context="encounters")
        assert entity["instanceType"] == "Encounter"

    def test_sets_unknown_when_no_context(self):
        entity = {"id": "e1"}
        validate_instance_type(entity, context="")
        assert entity["instanceType"] == "Unknown"

    def test_handles_empty_string_instance_type(self):
        entity = {"id": "e1", "instanceType": ""}
        validate_instance_type(entity, context="titles")
        assert entity["instanceType"] == "StudyTitle"


# ---------------------------------------------------------------------------
# enrich
# ---------------------------------------------------------------------------


class TestEnrich:
    def test_injects_extension_attributes_on_entities(self):
        obj = {
            "id": "s1",
            "instanceType": "Study",
            "versions": [
                {"id": "v1", "instanceType": "StudyVersion"},
            ],
        }
        enrich(obj)
        assert obj["extensionAttributes"] == []
        assert obj["versions"][0]["extensionAttributes"] == []

    def test_does_not_inject_on_plain_dicts(self):
        """Dicts without instanceType should not get extensionAttributes."""
        obj = {"key": "value", "nested": {"a": 1}}
        enrich(obj)
        assert "extensionAttributes" not in obj
        assert "extensionAttributes" not in obj["nested"]

    def test_generates_id_when_missing(self):
        obj = {"instanceType": "Code"}
        enrich(obj)
        assert obj["id"]  # non-empty
        assert isinstance(obj["id"], str)

    def test_preserves_existing_id(self):
        obj = {"id": "my-id", "instanceType": "Study"}
        enrich(obj)
        assert obj["id"] == "my-id"

    def test_deeply_nested_enrichment(self):
        obj = {
            "id": "root",
            "instanceType": "Study",
            "versions": [
                {
                    "id": "v1",
                    "instanceType": "StudyVersion",
                    "studyDesigns": [
                        {
                            "id": "d1",
                            "instanceType": "InterventionalStudyDesign",
                            "encounters": [
                                {"id": "enc1", "instanceType": "Encounter"},
                            ],
                        }
                    ],
                }
            ],
        }
        enrich(obj)
        enc = obj["versions"][0]["studyDesigns"][0]["encounters"][0]
        assert "extensionAttributes" in enc
        assert enc["extensionAttributes"] == []


# ---------------------------------------------------------------------------
# normalize_codes
# ---------------------------------------------------------------------------


class TestNormalizeCodes:
    def test_replaces_nci_thesaurus(self):
        obj = {
            "id": "c1",
            "instanceType": "Code",
            "code": "C123",
            "codeSystem": "NCI Thesaurus",
            "decode": "Test",
        }
        normalize_codes(obj)
        assert obj["codeSystem"] == "http://www.cdisc.org"

    def test_sets_default_code_system_version(self):
        obj = {
            "id": "c1",
            "instanceType": "Code",
            "code": "C123",
            "codeSystem": "SNOMED",
            "decode": "Test",
        }
        normalize_codes(obj)
        assert obj["codeSystemVersion"] == "2024-09-27"

    def test_preserves_existing_code_system_version(self):
        obj = {
            "id": "c1",
            "instanceType": "Code",
            "code": "C123",
            "codeSystem": "SNOMED",
            "codeSystemVersion": "2023-01-01",
            "decode": "Test",
        }
        normalize_codes(obj)
        assert obj["codeSystemVersion"] == "2023-01-01"

    def test_ensures_all_required_fields(self):
        obj = {"instanceType": "Code"}
        normalize_codes(obj)
        assert obj["id"]  # generated
        assert obj["extensionAttributes"] == []
        assert "code" in obj
        assert "codeSystem" in obj
        assert "codeSystemVersion" in obj
        assert "decode" in obj
        assert obj["instanceType"] == "Code"

    def test_normalizes_nested_codes(self):
        obj = {
            "id": "s1",
            "instanceType": "Study",
            "type": {
                "id": "c1",
                "instanceType": "Code",
                "code": "C123",
                "codeSystem": "NCI Thesaurus",
                "decode": "Test",
            },
        }
        normalize_codes(obj)
        assert obj["type"]["codeSystem"] == "http://www.cdisc.org"

    def test_normalizes_codes_in_arrays(self):
        obj = {
            "id": "s1",
            "instanceType": "Study",
            "codes": [
                {
                    "id": "c1",
                    "instanceType": "Code",
                    "code": "A",
                    "codeSystem": "NCI Thesaurus",
                    "decode": "Alpha",
                },
                {
                    "id": "c2",
                    "instanceType": "Code",
                    "code": "B",
                    "codeSystem": "LOINC",
                    "codeSystemVersion": "2.0",
                    "decode": "Beta",
                },
            ],
        }
        normalize_codes(obj)
        assert obj["codes"][0]["codeSystem"] == "http://www.cdisc.org"
        assert obj["codes"][1]["codeSystem"] == "LOINC"
        assert obj["codes"][1]["codeSystemVersion"] == "2.0"


# ---------------------------------------------------------------------------
# validate_id_references
# ---------------------------------------------------------------------------


class TestValidateIdReferences:
    def _make_doc(self, study: dict) -> USDMDocument:
        return USDMDocument(study=study, warnings=[], stats=ConversionStats())

    def test_no_warnings_for_valid_refs(self):
        study = {
            "id": "s1",
            "instanceType": "Study",
            "versions": [
                {
                    "id": "v1",
                    "instanceType": "StudyVersion",
                    "studyDesigns": [
                        {
                            "id": "d1",
                            "instanceType": "InterventionalStudyDesign",
                            "epochs": [
                                {"id": "ep1", "instanceType": "StudyEpoch"},
                            ],
                            "encounters": [
                                {
                                    "id": "enc1",
                                    "instanceType": "Encounter",
                                    "epochId": "ep1",
                                },
                            ],
                        }
                    ],
                }
            ],
        }
        warnings = validate_id_references(self._make_doc(study))
        assert warnings == []

    def test_warns_on_dangling_scalar_ref(self):
        study = {
            "id": "s1",
            "instanceType": "Study",
            "versions": [
                {
                    "id": "v1",
                    "instanceType": "StudyVersion",
                    "studyDesigns": [
                        {
                            "id": "d1",
                            "instanceType": "InterventionalStudyDesign",
                            "encounters": [
                                {
                                    "id": "enc1",
                                    "instanceType": "Encounter",
                                    "epochId": "nonexistent_epoch",
                                },
                            ],
                        }
                    ],
                }
            ],
        }
        warnings = validate_id_references(self._make_doc(study))
        assert len(warnings) == 1
        assert "nonexistent_epoch" in warnings[0]

    def test_warns_on_dangling_list_ref(self):
        study = {
            "id": "s1",
            "instanceType": "Study",
            "versions": [
                {
                    "id": "v1",
                    "instanceType": "StudyVersion",
                    "studyDesigns": [
                        {
                            "id": "d1",
                            "instanceType": "InterventionalStudyDesign",
                            "activities": [
                                {
                                    "id": "act1",
                                    "instanceType": "Activity",
                                },
                            ],
                            "scheduleTimelines": [
                                {
                                    "id": "tl1",
                                    "instanceType": "ScheduleTimeline",
                                    "instances": [
                                        {
                                            "id": "sai1",
                                            "instanceType": "ScheduledActivityInstance",
                                            "activityIds": ["act1", "missing_act"],
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        warnings = validate_id_references(self._make_doc(study))
        assert len(warnings) == 1
        assert "missing_act" in warnings[0]

    def test_empty_study_no_warnings(self):
        study = {"id": "s1", "instanceType": "Study"}
        warnings = validate_id_references(self._make_doc(study))
        assert warnings == []
