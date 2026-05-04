"""Unit tests for converter/mapper.py — consolidation, relationships, SoA, domain modules."""

from __future__ import annotations

from converter.mapper import (
    consolidate_top_level_entities,
    map_domain_modules,
    map_schedule_of_activity,
    map_to_usdm,
    resolve_relationships,
)
from converter.models import ProdigyDocument, USDMDocument, ConversionStats


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_prodigy_doc(**overrides) -> ProdigyDocument:
    """Build a minimal ProdigyDocument with sensible defaults."""
    defaults = dict(
        study={
            "id": "study_1",
            "name": "Test Study",
            "instanceType": "Study",
            "versions": [
                {
                    "id": "ver_1",
                    "instanceType": "StudyVersion",
                    "studyIdentifiers": [],
                    "studyDesigns": [
                        {"id": "design_1", "instanceType": "InterventionalStudyDesign"}
                    ],
                }
            ],
            "documentedBy": [],
        },
        identifiers=[],
        population_definition=None,
        scheduled_instances=[],
        syntax_templates=[],
        metadata={},
        relationships=[],
        domain_modules={},
        auxiliary={},
        raw_keys=["Study"],
    )
    defaults.update(overrides)
    return ProdigyDocument(**defaults)


def _minimal_usdm_doc() -> USDMDocument:
    """Build a minimal USDMDocument for relationship testing."""
    return USDMDocument(
        study={
            "id": "study_1",
            "name": "Test",
            "versions": [
                {
                    "id": "ver_1",
                    "studyDesigns": [
                        {
                            "id": "design_1",
                            "epochs": [{"id": "epoch_1"}],
                            "arms": [{"id": "arm_1"}],
                        }
                    ],
                }
            ],
            "instanceType": "Study",
        },
        warnings=[],
        stats=ConversionStats(),
    )


# ===================================================================
# consolidate_top_level_entities tests
# ===================================================================


class TestConsolidateTopLevelEntities:
    """Tests for consolidate_top_level_entities."""

    def test_identifiers_merged_into_study_identifiers(self):
        """Identifier entities are appended to studyIdentifiers."""
        doc = _minimal_prodigy_doc(
            identifiers=[
                {"id": "ident_1", "text": "NCT12345"},
                {"id": "ident_2", "text": "EudraCT-001"},
            ]
        )
        study_version = {
            "id": "ver_1",
            "studyIdentifiers": [{"id": "existing"}],
            "studyDesigns": [],
        }
        consolidate_top_level_entities(doc, study_version)
        assert len(study_version["studyIdentifiers"]) == 3
        ids = [si["id"] for si in study_version["studyIdentifiers"]]
        assert "ident_1" in ids
        assert "ident_2" in ids

    def test_identifiers_creates_array_when_none(self):
        """studyIdentifiers is created when it was None."""
        doc = _minimal_prodigy_doc(identifiers=[{"id": "ident_1"}])
        study_version = {"id": "ver_1", "studyIdentifiers": None, "studyDesigns": []}
        consolidate_top_level_entities(doc, study_version)
        assert len(study_version["studyIdentifiers"]) == 1

    def test_population_definition_merged_into_study_design(self):
        """PopulationDefinition is set on studyDesigns[0].population."""
        pop = {"id": "pop_1", "name": "Adults"}
        doc = _minimal_prodigy_doc(population_definition=pop)
        study_version = {
            "id": "ver_1",
            "studyIdentifiers": [],
            "studyDesigns": [{"id": "design_1"}],
        }
        consolidate_top_level_entities(doc, study_version)
        assert study_version["studyDesigns"][0]["population"] == pop

    def test_population_definition_no_study_designs(self):
        """PopulationDefinition is skipped when no studyDesigns exist."""
        pop = {"id": "pop_1"}
        doc = _minimal_prodigy_doc(population_definition=pop)
        study_version = {"id": "ver_1", "studyIdentifiers": [], "studyDesigns": []}
        # Should not raise
        consolidate_top_level_entities(doc, study_version)

    def test_scheduled_instances_merged_into_schedule_timelines(self):
        """ScheduledInstance entities are appended to scheduleTimelines."""
        instances = [{"id": "si_1", "name": "Visit 1"}]
        doc = _minimal_prodigy_doc(scheduled_instances=instances)
        study_version = {
            "id": "ver_1",
            "studyIdentifiers": [],
            "studyDesigns": [{"id": "design_1", "scheduleTimelines": []}],
        }
        consolidate_top_level_entities(doc, study_version)
        assert len(study_version["studyDesigns"][0]["scheduleTimelines"]) == 1

    def test_syntax_template_discarded(self):
        """SyntaxTemplate entities are discarded (no crash)."""
        doc = _minimal_prodigy_doc(
            syntax_templates=[{"id": "st_1", "name": "Template"}]
        )
        study_version = {"id": "ver_1", "studyIdentifiers": [], "studyDesigns": []}
        # Should not raise, just log warning
        consolidate_top_level_entities(doc, study_version)

    def test_metadata_dates_merged(self):
        """Metadata protocol_date is merged into dateValues."""
        doc = _minimal_prodigy_doc(
            metadata={
                "id": "meta_1",
                "protocol_date": "2022-03-18",
                "extraction_timestamp": "2026-04-25T01:12:28Z",
            }
        )
        study_version = {"id": "ver_1", "studyIdentifiers": [], "studyDesigns": [], "dateValues": []}
        consolidate_top_level_entities(doc, study_version)
        assert len(study_version["dateValues"]) == 2
        types = [dv["type"] for dv in study_version["dateValues"]]
        assert "protocol_date" in types
        assert "extraction_date" in types

    def test_empty_doc_no_changes(self):
        """An empty ProdigyDocument causes no changes to study_version."""
        doc = _minimal_prodigy_doc()
        study_version = {"id": "ver_1", "studyIdentifiers": [], "studyDesigns": []}
        consolidate_top_level_entities(doc, study_version)
        assert study_version["studyIdentifiers"] == []


# ===================================================================
# resolve_relationships tests
# ===================================================================


class TestResolveRelationships:
    """Tests for resolve_relationships."""

    def test_epoch_relationship_resolved(self):
        """A relationship of type 'epoch' populates epochId on the source entity."""
        usdm_doc = _minimal_usdm_doc()
        relationships = [
            {
                "id": "rel_1",
                "type": "epoch",
                "startNodeId": "design_1",
                "endNodeId": "epoch_1",
                "properties": {},
            }
        ]
        resolve_relationships(relationships, usdm_doc)
        design = usdm_doc.study["versions"][0]["studyDesigns"][0]
        assert design.get("epochId") == "epoch_1"
        assert usdm_doc.stats.relationships_processed == 1
        assert usdm_doc.stats.relationships_discarded == 0

    def test_unmappable_relationship_discarded(self):
        """A relationship with unknown type is discarded."""
        usdm_doc = _minimal_usdm_doc()
        relationships = [
            {
                "id": "rel_1",
                "type": "intercurrentEvents",
                "startNodeId": "design_1",
                "endNodeId": "some_id",
                "properties": {},
            }
        ]
        resolve_relationships(relationships, usdm_doc)
        assert usdm_doc.stats.relationships_discarded == 1
        assert usdm_doc.stats.relationships_processed == 0

    def test_missing_source_entity_discarded(self):
        """A relationship referencing a non-existent source entity is discarded."""
        usdm_doc = _minimal_usdm_doc()
        relationships = [
            {
                "id": "rel_1",
                "type": "epoch",
                "startNodeId": "nonexistent_id",
                "endNodeId": "epoch_1",
                "properties": {},
            }
        ]
        resolve_relationships(relationships, usdm_doc)
        assert usdm_doc.stats.relationships_discarded == 1

    def test_array_reference_field(self):
        """A relationship type mapping to an array field appends the ID."""
        usdm_doc = _minimal_usdm_doc()
        relationships = [
            {
                "id": "rel_1",
                "type": "activities",
                "startNodeId": "design_1",
                "endNodeId": "act_1",
                "properties": {},
            },
            {
                "id": "rel_2",
                "type": "activities",
                "startNodeId": "design_1",
                "endNodeId": "act_2",
                "properties": {},
            },
        ]
        resolve_relationships(relationships, usdm_doc)
        design = usdm_doc.study["versions"][0]["studyDesigns"][0]
        assert design.get("activityIds") == ["act_1", "act_2"]
        assert usdm_doc.stats.relationships_processed == 2

    def test_empty_relationships(self):
        """Empty relationships array results in zero counts."""
        usdm_doc = _minimal_usdm_doc()
        resolve_relationships([], usdm_doc)
        assert usdm_doc.stats.relationships_processed == 0
        assert usdm_doc.stats.relationships_discarded == 0


# ===================================================================
# map_schedule_of_activity tests
# ===================================================================


class TestMapScheduleOfActivity:
    """Tests for map_schedule_of_activity."""

    def _make_soa_data(self):
        return [
            {
                "title": "Table 1: Schedule of Activities",
                "id": "soa_1",
                "table_reference": "TBL-001",
                "page_number": 14,
                "span_hash": "abc123",
                "structure": {
                    "periods": [
                        {"id": "period_1", "name": "Screening", "period_order": 1, "encounter_ids": ["enc_1"]},
                        {"id": "period_2", "name": "Treatment", "period_order": 2, "encounter_ids": ["enc_2"]},
                    ],
                    "encounter": [
                        {"id": "enc_1", "name": "Visit 1", "column_index": 1, "period_id": "period_1"},
                        {"id": "enc_2", "name": "Visit 2", "column_index": 2, "period_id": "period_2"},
                    ],
                    "activity": [
                        {"id": "act_1", "name": "Informed Consent", "activity_category": "Eligibility", "row_index": 1},
                    ],
                    "cells": [
                        {"id": "cell_1", "value": "X", "activity_id": "act_1", "encounter_id": "enc_1", "row_index": 1, "column_index": 1, "is_required": True},
                    ],
                    "footnotes": [],
                    "table_metadata": {},
                },
            }
        ]

    def test_epochs_created_from_periods(self):
        """Periods are mapped to StudyEpoch entities."""
        study_design: dict = {"id": "design_1"}
        map_schedule_of_activity(self._make_soa_data(), study_design)
        epochs = study_design.get("epochs", [])
        assert len(epochs) == 2
        assert epochs[0]["instanceType"] == "StudyEpoch"
        assert epochs[0]["name"] == "Screening"

    def test_encounters_created(self):
        """Encounters are mapped with epochId from period_id."""
        study_design: dict = {"id": "design_1"}
        map_schedule_of_activity(self._make_soa_data(), study_design)
        encounters = study_design.get("encounters", [])
        assert len(encounters) == 2
        assert encounters[0]["instanceType"] == "Encounter"
        assert encounters[0]["epochId"] == "period_1"

    def test_activities_created(self):
        """Activities are mapped from the activity array."""
        study_design: dict = {"id": "design_1"}
        map_schedule_of_activity(self._make_soa_data(), study_design)
        activities = study_design.get("activities", [])
        assert len(activities) == 1
        assert activities[0]["instanceType"] == "Activity"

    def test_scheduled_instances_from_cells(self):
        """Cells with values create ScheduledActivityInstance entries."""
        study_design: dict = {"id": "design_1"}
        map_schedule_of_activity(self._make_soa_data(), study_design)
        timelines = study_design.get("scheduleTimelines", [])
        assert len(timelines) == 1
        instances = timelines[0].get("instances", [])
        assert len(instances) == 1
        assert instances[0]["instanceType"] == "ScheduledActivityInstance"
        assert instances[0]["activityIds"] == ["act_1"]
        assert instances[0]["encounterId"] == "enc_1"

    def test_empty_soa_data(self):
        """Empty SoA list causes no changes."""
        study_design: dict = {"id": "design_1"}
        map_schedule_of_activity([], study_design)
        assert "epochs" not in study_design

    def test_dict_soa_data_normalized(self):
        """A dict SoA (instead of list) is normalized to a list."""
        soa_dict = self._make_soa_data()[0]
        study_design: dict = {"id": "design_1"}
        map_schedule_of_activity(soa_dict, study_design)
        assert len(study_design.get("epochs", [])) == 2


# ===================================================================
# map_domain_modules tests
# ===================================================================


class TestMapDomainModules:
    """Tests for map_domain_modules."""

    def test_all_modules_discarded_with_warnings(self):
        """All domain modules are discarded since none have USDM 4.0 mappings."""
        modules = {
            "biomarker_driven_design_module": {"summary": "data"},
            "adverse_event_analysis_module": {"summary": "data"},
        }
        mapped, warnings = map_domain_modules(modules)
        assert mapped == {}
        assert len(warnings) == 2
        assert "biomarker_driven_design_module" in warnings[0]
        assert "adverse_event_analysis_module" in warnings[1]

    def test_empty_modules(self):
        """Empty modules dict returns empty results."""
        mapped, warnings = map_domain_modules({})
        assert mapped == {}
        assert warnings == []

    def test_warning_message_format(self):
        """Warning messages include the module name."""
        modules = {"phase_ii_clinical_trial_module": {"data": "x"}}
        _, warnings = map_domain_modules(modules)
        assert len(warnings) == 1
        assert "phase_ii_clinical_trial_module" in warnings[0]
        assert "no USDM 4.0 mapping" in warnings[0]


# ===================================================================
# map_to_usdm integration test
# ===================================================================


class TestMapToUsdmIntegration:
    """Test that map_to_usdm calls the new functions."""

    def test_full_pipeline_with_all_sections(self):
        """map_to_usdm processes identifiers, SoA, domain modules, and relationships."""
        doc = _minimal_prodigy_doc(
            identifiers=[{"id": "ident_1", "text": "NCT12345"}],
            population_definition={"id": "pop_1", "name": "Adults"},
            syntax_templates=[{"id": "st_1"}],
            domain_modules={"test_module": {"data": "x"}},
            relationships=[
                {
                    "id": "rel_1",
                    "type": "epoch",
                    "startNodeId": "design_1",
                    "endNodeId": "epoch_1",
                    "properties": {},
                }
            ],
            auxiliary={
                "schedule_of_activity": [
                    {
                        "title": "SoA",
                        "id": "soa_1",
                        "table_reference": "T1",
                        "page_number": 1,
                        "span_hash": "h",
                        "structure": {
                            "periods": [{"id": "p1", "name": "Screening"}],
                            "encounter": [],
                            "activity": [],
                            "cells": [],
                            "footnotes": [],
                            "table_metadata": {},
                        },
                    }
                ]
            },
        )
        result = map_to_usdm(doc)

        # Identifiers consolidated
        version = result.study["versions"][0]
        ident_ids = [si["id"] for si in version.get("studyIdentifiers", [])]
        assert "ident_1" in ident_ids

        # Population consolidated
        design = version["studyDesigns"][0]
        assert design.get("population", {}).get("id") == "pop_1"

        # SoA mapped
        assert len(design.get("epochs", [])) >= 1

        # Domain modules discarded
        assert result.stats.domain_modules_skipped == 1
        assert any("test_module" in w for w in result.warnings)
