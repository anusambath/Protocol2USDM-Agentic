"""
Tests for SoAPostProcessingAgent.

Covers:
- ID standardization (hyphens → underscores)
- Entity name normalization (remove timing text)
- Superscript footnote stripping
- Required field filling
- Epoch/encounter injection from header structure
- Activity-group linking
- Timing code normalization
- Full execute() workflow
"""

import pytest
from agents.quality.postprocessing_agent import (
    SoAPostProcessingAgent,
    PostProcessingFix,
    PostProcessingReport,
    normalize_entity_name,
    strip_superscripts,
    standardize_id,
)
from agents.base import AgentState, AgentTask
from agents.context_store import ContextStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def agent():
    a = SoAPostProcessingAgent()
    a.initialize()
    return a


def _make_entity(entity_type, data, entity_id="test_1"):
    return {"id": entity_id, "entity_type": entity_type, "data": data}


# ---------------------------------------------------------------------------
# Pure function tests
# ---------------------------------------------------------------------------

class TestNormalizeEntityName:
    def test_removes_day_timing(self):
        assert normalize_entity_name("Vital Signs (Day 1)") == "Vital Signs"

    def test_removes_week_timing(self):
        assert normalize_entity_name("Lab Tests (Week -2)") == "Lab Tests"

    def test_preserves_name_without_timing(self):
        assert normalize_entity_name("Physical Exam") == "Physical Exam"

    def test_empty_string(self):
        assert normalize_entity_name("") == ""

    def test_none(self):
        assert normalize_entity_name(None) is None

    def test_strips_whitespace(self):
        assert normalize_entity_name("  ECG  ") == "ECG"


class TestStripSuperscripts:
    def test_removes_superscript_numbers(self):
        assert strip_superscripts("UNS¹ EOS") == "UNS EOS"

    def test_removes_superscript_letters(self):
        assert strip_superscripts("ETᵃ Visit") == "ET Visit"

    def test_preserves_normal_text(self):
        assert strip_superscripts("Normal Text") == "Normal Text"

    def test_empty_string(self):
        assert strip_superscripts("") == ""

    def test_none(self):
        assert strip_superscripts(None) is None


class TestStandardizeId:
    def test_replaces_hyphens(self):
        assert standardize_id("epoch-1") == "epoch_1"

    def test_no_hyphens(self):
        assert standardize_id("epoch_1") == "epoch_1"

    def test_empty(self):
        assert standardize_id("") == ""

    def test_none(self):
        assert standardize_id(None) is None

    def test_multiple_hyphens(self):
        assert standardize_id("act-group-1") == "act_group_1"


# ---------------------------------------------------------------------------
# Agent lifecycle tests
# ---------------------------------------------------------------------------

class TestPostProcessingAgentLifecycle:
    def test_init_default(self):
        a = SoAPostProcessingAgent()
        assert a.agent_id == "postprocessing_agent"

    def test_initialize(self, agent):
        assert agent.state == AgentState.READY

    def test_terminate(self, agent):
        agent.terminate()
        assert agent.state == AgentState.TERMINATED

    def test_capabilities(self, agent):
        caps = agent.get_capabilities()
        assert caps.agent_type == "quality"
        assert "execution_extraction" in caps.dependencies


# ---------------------------------------------------------------------------
# Step 1: ID standardization
# ---------------------------------------------------------------------------

class TestIdStandardization:
    def test_standardizes_entity_id(self, agent):
        entities = [_make_entity("epoch", {"name": "Screening"}, "epoch-1")]
        result, fixes = agent._standardize_all_ids(entities)
        assert result[0]["id"] == "epoch_1"
        assert len(fixes) == 1
        assert fixes[0].fix_type == "id_standardized"

    def test_no_change_needed(self, agent):
        entities = [_make_entity("epoch", {"name": "Screening"}, "epoch_1")]
        result, fixes = agent._standardize_all_ids(entities)
        assert result[0]["id"] == "epoch_1"
        assert len(fixes) == 0

    def test_rewrites_references_in_data(self, agent):
        entities = [_make_entity("activity", {"encounterId": "enc-1"}, "act_1")]
        result, _ = agent._standardize_all_ids(entities)
        assert result[0]["data"]["encounterId"] == "enc_1"


# ---------------------------------------------------------------------------
# Step 2: Name normalization
# ---------------------------------------------------------------------------

class TestNameNormalization:
    def test_removes_timing_from_name(self, agent):
        entities = [_make_entity("activity", {"name": "Vital Signs (Day 1)"}, "act_1")]
        result, fixes = agent._normalize_names(entities)
        assert result[0]["data"]["name"] == "Vital Signs"
        assert len(fixes) == 1

    def test_no_change_for_clean_name(self, agent):
        entities = [_make_entity("activity", {"name": "ECG"}, "act_1")]
        result, fixes = agent._normalize_names(entities)
        assert result[0]["data"]["name"] == "ECG"
        assert len(fixes) == 0


# ---------------------------------------------------------------------------
# Step 3: Superscript stripping
# ---------------------------------------------------------------------------

class TestSuperscriptStripping:
    def test_strips_superscripts(self, agent):
        entities = [_make_entity("encounter", {"name": "Visit 1¹"}, "enc_1")]
        result, fixes = agent._strip_superscripts(entities)
        assert result[0]["data"]["name"] == "Visit 1"
        assert result[0]["data"]["_original_name"] == "Visit 1¹"
        assert len(fixes) == 1

    def test_no_change_for_clean_name(self, agent):
        entities = [_make_entity("encounter", {"name": "Visit 1"}, "enc_1")]
        result, fixes = agent._strip_superscripts(entities)
        assert result[0]["data"]["name"] == "Visit 1"
        assert len(fixes) == 0


# ---------------------------------------------------------------------------
# Step 4: Required field filling
# ---------------------------------------------------------------------------

class TestRequiredFieldFilling:
    def test_fills_missing_instance_type(self, agent):
        entities = [_make_entity("epoch", {"name": "Screening"}, "ep_1")]
        result, fixes = agent._fill_required_fields(entities)
        assert result[0]["data"]["instanceType"] == "Epoch"
        assert len(fixes) == 1

    def test_no_fill_when_present(self, agent):
        entities = [_make_entity("epoch", {"name": "Screening", "instanceType": "Epoch"}, "ep_1")]
        result, fixes = agent._fill_required_fields(entities)
        assert len(fixes) == 0

    def test_fills_encounter_type(self, agent):
        entities = [_make_entity("encounter", {"name": "Visit 1"}, "enc_1")]
        result, fixes = agent._fill_required_fields(entities)
        assert result[0]["data"]["type"] == {"code": "C25426", "decode": "Visit"}


# ---------------------------------------------------------------------------
# Step 5: Header structure injection
# ---------------------------------------------------------------------------

class TestHeaderInjection:
    def test_injects_missing_epochs(self, agent):
        entities = [_make_entity("activity", {"name": "ECG"}, "act_1")]
        header = {
            "epochs": [{"id": "epoch_1", "name": "Screening"}],
            "encounters": [],
        }
        result, ep_count, enc_count, fixes = agent._inject_from_header(entities, header)
        assert ep_count == 1
        assert any(e["id"] == "epoch_1" for e in result)

    def test_injects_missing_encounters(self, agent):
        entities = []
        header = {
            "epochs": [],
            "encounters": [{"id": "enc_1", "name": "Visit 1"}],
        }
        result, ep_count, enc_count, fixes = agent._inject_from_header(entities, header)
        assert enc_count == 1
        assert any(e["id"] == "enc_1" for e in result)

    def test_skips_existing_entities(self, agent):
        entities = [_make_entity("epoch", {"name": "Screening"}, "epoch_1")]
        header = {
            "epochs": [{"id": "epoch_1", "name": "Screening"}],
            "encounters": [],
        }
        result, ep_count, _, _ = agent._inject_from_header(entities, header)
        assert ep_count == 0
        assert len(result) == 1

    def test_empty_header(self, agent):
        entities = [_make_entity("activity", {"name": "ECG"}, "act_1")]
        result, ep_count, enc_count, fixes = agent._inject_from_header(entities, {})
        assert ep_count == 0
        assert enc_count == 0
        assert len(fixes) == 0


# ---------------------------------------------------------------------------
# Step 6: Activity-group linking
# ---------------------------------------------------------------------------

class TestActivityGroupLinking:
    def test_links_activity_to_group(self, agent):
        entities = [_make_entity("activity", {"name": "ECG"}, "act_1")]
        header = {
            "activityGroups": [
                {"id": "ag_1", "activity_names": ["ECG", "Vital Signs"]}
            ],
        }
        result, fixes = agent._resolve_activity_groups(entities, header)
        assert result[0]["data"]["activityGroupId"] == "ag_1"
        assert len(fixes) == 1

    def test_skips_already_assigned(self, agent):
        entities = [_make_entity("activity", {"name": "ECG", "activityGroupId": "ag_2"}, "act_1")]
        header = {
            "activityGroups": [
                {"id": "ag_1", "activity_names": ["ECG"]}
            ],
        }
        result, fixes = agent._resolve_activity_groups(entities, header)
        assert result[0]["data"]["activityGroupId"] == "ag_2"
        assert len(fixes) == 0

    def test_case_insensitive_matching(self, agent):
        entities = [_make_entity("activity", {"name": "ecg"}, "act_1")]
        header = {
            "activityGroups": [
                {"id": "ag_1", "activity_names": ["ECG"]}
            ],
        }
        result, fixes = agent._resolve_activity_groups(entities, header)
        assert result[0]["data"]["activityGroupId"] == "ag_1"

    def test_no_header(self, agent):
        entities = [_make_entity("activity", {"name": "ECG"}, "act_1")]
        result, fixes = agent._resolve_activity_groups(entities, {})
        assert len(fixes) == 0


# ---------------------------------------------------------------------------
# Step 7: Timing code normalization
# ---------------------------------------------------------------------------

class TestTimingCodeNormalization:
    def test_normalizes_encounter_type(self, agent):
        entities = [_make_entity("encounter", {"name": "Visit 1", "type": None}, "enc_1")]
        result, fixes = agent._normalize_timing_codes(entities)
        assert result[0]["data"]["type"] == {"code": "C25426", "decode": "Visit"}

    def test_normalizes_string_pt_type(self, agent):
        entities = [_make_entity("planned_timepoint", {"type": "Fixed Reference"}, "pt_1")]
        result, fixes = agent._normalize_timing_codes(entities)
        assert result[0]["data"]["type"]["code"] == "C99073"
        assert result[0]["data"]["type"]["decode"] == "Fixed Reference"

    def test_no_change_for_correct_codes(self, agent):
        entities = [_make_entity("encounter", {"name": "V1", "type": {"code": "C25426", "decode": "Visit"}}, "enc_1")]
        result, fixes = agent._normalize_timing_codes(entities)
        assert len(fixes) == 0


# ---------------------------------------------------------------------------
# Full execute() tests
# ---------------------------------------------------------------------------

class TestPostProcessingExecute:
    def test_execute_with_entities(self, agent):
        entities = [
            _make_entity("epoch", {"name": "Screening¹"}, "epoch-1"),
            _make_entity("activity", {"name": "Vital Signs (Day 1)"}, "act-1"),
            _make_entity("encounter", {"name": "Visit 1", "type": None}, "enc-1"),
        ]
        task = AgentTask(
            task_id="test_pp",
            agent_id="postprocessing_agent",
            task_type="postprocess",
            input_data={"entities": entities},
        )
        result = agent.execute(task)
        assert result.success
        report = result.data["report"]
        assert report["ids_standardized"] > 0
        assert report["names_normalized"] > 0 or report["superscripts_cleaned"] > 0

    def test_execute_no_entities(self, agent):
        task = AgentTask(
            task_id="test_pp",
            agent_id="postprocessing_agent",
            task_type="postprocess",
            input_data={},
        )
        result = agent.execute(task)
        assert not result.success

    def test_execute_with_header_structure(self, agent):
        entities = [_make_entity("activity", {"name": "ECG"}, "act_1")]
        header = {
            "epochs": [{"id": "epoch_1", "name": "Treatment"}],
            "encounters": [{"id": "enc_1", "name": "Visit 1"}],
            "activityGroups": [{"id": "ag_1", "activity_names": ["ECG"]}],
        }
        task = AgentTask(
            task_id="test_pp",
            agent_id="postprocessing_agent",
            task_type="postprocess",
            input_data={"entities": entities, "header_structure": header},
        )
        result = agent.execute(task)
        assert result.success
        report = result.data["report"]
        assert report["epochs_injected"] == 1
        assert report["encounters_injected"] == 1
        assert report["groups_linked"] == 1

    def test_execute_with_context_store(self, agent):
        store = ContextStore()
        from agents.context_store import ContextEntity, EntityProvenance
        store.add_entity(ContextEntity(
            id="act_1",
            entity_type="activity",
            data={"name": "ECG"},
            provenance=EntityProvenance(
                entity_id="act_1",
                source_agent_id="test",
                confidence_score=0.9,
            ),
        ))
        agent.set_context_store(store)
        task = AgentTask(
            task_id="test_pp",
            agent_id="postprocessing_agent",
            task_type="postprocess",
            input_data={},
        )
        result = agent.execute(task)
        assert result.success


# ---------------------------------------------------------------------------
# Report tests
# ---------------------------------------------------------------------------

class TestPostProcessingReport:
    def test_report_to_dict(self):
        report = PostProcessingReport(
            total_entities=5,
            names_normalized=2,
            fields_filled=1,
        )
        d = report.to_dict()
        assert d["total_entities"] == 5
        assert d["names_normalized"] == 2
        assert d["fields_filled"] == 1
        assert d["fixes_count"] == 0

    def test_fix_to_dict(self):
        fix = PostProcessingFix(
            fix_type="name_normalized",
            entity_id="act_1",
            entity_type="activity",
            field_name="name",
            old_value="ECG (Day 1)",
            new_value="ECG",
            reason="Removed timing text",
        )
        d = fix.to_dict()
        assert d["fix_type"] == "name_normalized"
        assert d["old_value"] == "ECG (Day 1)"
