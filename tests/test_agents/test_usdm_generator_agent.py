"""
Tests for USDMGeneratorAgent.
"""

import json
import os
import tempfile
import pytest

from agents.base import AgentTask, AgentState
from agents.context_store import ContextStore, ContextEntity, EntityProvenance
from agents.support.usdm_generator_agent import (
    USDMGeneratorAgent,
    USDMValidationIssue,
    USDMGenerationResult,
    _build_empty_usdm_skeleton,
    _place_entity,
    _place_metadata,
    _resolve_list_container,
    _validate_usdm_structure,
    ENTITY_TYPE_PLACEMENT,
    LIST_ENTITY_TYPES,
)


# --- Helper Functions ---

def _make_store_with_entities(entities):
    """Create a ContextStore populated with entities."""
    store = ContextStore()
    for etype, data in entities:
        entity = ContextEntity(
            id=data.get("id", f"ent-{etype}-{store.entity_count}"),
            entity_type=etype,
            data=data,
            provenance=EntityProvenance(
                entity_id=data.get("id", ""),
                source_agent_id="test-agent",
                confidence_score=0.9,
            ),
        )
        store.add_entity(entity)
    return store


# --- Skeleton Tests ---

class TestBuildEmptySkeleton:
    def test_has_study(self):
        usdm = _build_empty_usdm_skeleton()
        assert "study" in usdm
        assert "id" in usdm["study"]

    def test_has_version(self):
        usdm = _build_empty_usdm_skeleton()
        versions = usdm["study"]["versions"]
        assert len(versions) == 1
        assert "studyIdentifiers" in versions[0]

    def test_has_design(self):
        usdm = _build_empty_usdm_skeleton()
        designs = usdm["study"]["versions"][0]["studyDesigns"]
        assert len(designs) == 1
        assert "arms" in designs[0]
        assert "epochs" in designs[0]
        assert "objectives" in designs[0]

    def test_has_population(self):
        usdm = _build_empty_usdm_skeleton()
        pop = usdm["study"]["versions"][0]["studyDesigns"][0]["population"]
        assert "criteria" in pop

    def test_has_document_versions(self):
        usdm = _build_empty_usdm_skeleton()
        assert "documentVersions" in usdm["study"]
        assert len(usdm["study"]["documentVersions"]) == 1


# --- Entity Placement Tests ---

class TestPlaceEntity:
    def test_place_metadata(self):
        usdm = _build_empty_usdm_skeleton()
        placed = _place_entity(usdm, "metadata", {"name": "Test Study", "label": "TS"})
        assert placed
        assert usdm["study"]["name"] == "Test Study"
        assert usdm["study"]["label"] == "TS"

    def test_place_study_phase(self):
        usdm = _build_empty_usdm_skeleton()
        phase_data = {"id": "p1", "standardCode": {"code": "C49686"}}
        placed = _place_entity(usdm, "study_phase", phase_data)
        assert placed
        assert usdm["study"]["versions"][0]["studyPhase"] == phase_data

    def test_place_study_identifier(self):
        usdm = _build_empty_usdm_skeleton()
        placed = _place_entity(usdm, "study_identifier",
                               {"id": "si1", "identifier": "NCT12345"})
        assert placed
        assert len(usdm["study"]["versions"][0]["studyIdentifiers"]) == 1

    def test_place_objective(self):
        usdm = _build_empty_usdm_skeleton()
        placed = _place_entity(usdm, "objective",
                               {"id": "obj1", "text": "Primary objective"})
        assert placed
        assert len(usdm["study"]["versions"][0]["studyDesigns"][0]["objectives"]) == 1

    def test_place_eligibility_criterion(self):
        usdm = _build_empty_usdm_skeleton()
        placed = _place_entity(usdm, "eligibility_criterion",
                               {"id": "ec1", "text": "Age >= 18"})
        assert placed
        criteria = usdm["study"]["versions"][0]["studyDesigns"][0]["eligibilityCriteria"]
        assert len(criteria) == 1

    def test_place_criterion_item(self):
        usdm = _build_empty_usdm_skeleton()
        placed = _place_entity(usdm, "criterion_item",
                               {"id": "eci1", "text": "Age >= 18", "instanceType": "EligibilityCriterionItem"})
        assert placed
        items = usdm["study"]["versions"][0]["eligibilityCriterionItems"]
        assert len(items) == 1

    def test_place_study_arm(self):
        usdm = _build_empty_usdm_skeleton()
        placed = _place_entity(usdm, "study_arm",
                               {"id": "arm1", "name": "Treatment A"})
        assert placed
        assert len(usdm["study"]["versions"][0]["studyDesigns"][0]["arms"]) == 1

    def test_place_study_population(self):
        usdm = _build_empty_usdm_skeleton()
        placed = _place_entity(usdm, "study_population",
                               {"name": "ITT Population", "description": "All randomized"})
        assert placed
        pop = usdm["study"]["versions"][0]["studyDesigns"][0]["population"]
        assert pop["name"] == "ITT Population"

    def test_place_unknown_type_returns_false(self):
        usdm = _build_empty_usdm_skeleton()
        placed = _place_entity(usdm, "unknown_type", {"id": "x"})
        assert not placed

    def test_place_multiple_entities(self):
        usdm = _build_empty_usdm_skeleton()
        for i in range(3):
            _place_entity(usdm, "study_arm", {"id": f"arm{i}", "name": f"Arm {i}"})
        assert len(usdm["study"]["versions"][0]["studyDesigns"][0]["arms"]) == 3

    def test_place_document_section(self):
        usdm = _build_empty_usdm_skeleton()
        placed = _place_entity(usdm, "document_section",
                               {"id": "sec1", "title": "Introduction"})
        assert placed
        assert len(usdm["study"]["documentVersions"][0]["sections"]) == 1

    def test_place_narrative_content(self):
        usdm = _build_empty_usdm_skeleton()
        placed = _place_entity(usdm, "narrative_content",
                               {"id": "nc1", "text": "Study narrative"})
        assert placed
        assert len(usdm["study"]["versions"][0]["narrativeContentItems"]) == 1


# --- Validation Tests ---

class TestValidateUSDMStructure:
    def test_empty_skeleton_has_warnings(self):
        usdm = _build_empty_usdm_skeleton()
        issues = _validate_usdm_structure(usdm)
        assert len(issues) > 0
        assert any(i.severity == "warning" for i in issues)

    def test_populated_has_fewer_warnings(self):
        usdm = _build_empty_usdm_skeleton()
        usdm["study"]["name"] = "Test Study"
        _place_entity(usdm, "study_identifier", {"id": "si1", "identifier": "NCT123"})
        _place_entity(usdm, "study_arm", {"id": "a1", "name": "Arm 1"})
        _place_entity(usdm, "study_epoch", {"id": "e1", "name": "Screening"})
        _place_entity(usdm, "objective", {"id": "o1", "text": "Primary"})
        issues = _validate_usdm_structure(usdm)
        # Should have no warnings about missing arms/epochs/objectives/identifiers
        warning_paths = [i.path for i in issues if i.severity == "warning"]
        assert "studyDesigns[0].arms" not in warning_paths
        assert "studyDesigns[0].epochs" not in warning_paths

    def test_no_versions_is_error(self):
        usdm = {"study": {"versions": []}}
        issues = _validate_usdm_structure(usdm)
        assert any(i.severity == "error" for i in issues)

    def test_no_designs_is_error(self):
        usdm = {"study": {"versions": [{"studyDesigns": []}]}}
        issues = _validate_usdm_structure(usdm)
        assert any(i.severity == "error" for i in issues)


class TestUSDMValidationIssue:
    def test_to_dict(self):
        issue = USDMValidationIssue("error", "study.name", "Missing name")
        d = issue.to_dict()
        assert d["severity"] == "error"
        assert d["path"] == "study.name"
        assert d["message"] == "Missing name"


class TestUSDMGenerationResult:
    def test_to_dict(self):
        r = USDMGenerationResult(
            entity_count=5,
            entity_types_included=["objective", "study_arm"],
            output_path="/tmp/usdm.json",
        )
        d = r.to_dict()
        assert d["entity_count"] == 5
        assert d["output_path"] == "/tmp/usdm.json"


# --- USDMGeneratorAgent Tests ---

class TestUSDMGeneratorAgent:
    def setup_method(self):
        self.agent = USDMGeneratorAgent()
        self.agent.initialize()

    def test_init(self):
        assert self.agent.agent_id == "usdm-generator"
        assert self.agent.state == AgentState.READY

    def test_get_capabilities(self):
        caps = self.agent.get_capabilities()
        assert caps.agent_type == "support"
        assert "usdm_json" in caps.output_types

    def test_terminate(self):
        self.agent.terminate()
        assert self.agent.state == AgentState.TERMINATED

    def test_execute_no_context_store(self):
        task = AgentTask(task_id="t1", agent_id="usdm-generator",
                         task_type="usdm_generate", input_data={})
        result = self.agent.execute(task)
        assert not result.success
        assert "Context Store" in result.error

    def test_execute_empty_store(self):
        store = ContextStore()
        self.agent.set_context_store(store)
        task = AgentTask(task_id="t1", agent_id="usdm-generator",
                         task_type="usdm_generate", input_data={})
        result = self.agent.execute(task)
        assert result.success
        assert result.data["entity_count"] == 0
        assert "usdm" in result.data

    def test_execute_with_entities(self):
        store = _make_store_with_entities([
            ("metadata", {"id": "m1", "name": "Test Study"}),
            ("study_identifier", {"id": "si1", "identifier": "NCT12345"}),
            ("objective", {"id": "obj1", "text": "Primary objective"}),
            ("study_arm", {"id": "arm1", "name": "Treatment A"}),
            ("study_epoch", {"id": "ep1", "name": "Screening"}),
        ])
        self.agent.set_context_store(store)

        task = AgentTask(task_id="t1", agent_id="usdm-generator",
                         task_type="usdm_generate", input_data={})
        result = self.agent.execute(task)
        assert result.success
        assert result.data["entity_count"] == 5
        usdm = result.data["usdm"]
        assert usdm["study"]["name"] == "Test Study"
        assert len(usdm["study"]["versions"][0]["studyIdentifiers"]) == 1

    def test_execute_skips_infrastructure_types(self):
        store = _make_store_with_entities([
            ("metadata", {"id": "m1", "name": "Study"}),
            ("pdf_page", {"id": "pp1", "page_number": 0}),
            ("checkpoint", {"id": "cp1", "wave": 1}),
        ])
        self.agent.set_context_store(store)

        task = AgentTask(task_id="t1", agent_id="usdm-generator",
                         task_type="usdm_generate", input_data={})
        result = self.agent.execute(task)
        assert result.success
        assert result.data["entity_count"] == 1  # Only metadata

    def test_execute_with_include_filter(self):
        store = _make_store_with_entities([
            ("metadata", {"id": "m1", "name": "Study"}),
            ("objective", {"id": "obj1", "text": "Primary"}),
            ("study_arm", {"id": "arm1", "name": "Arm 1"}),
        ])
        self.agent.set_context_store(store)

        task = AgentTask(task_id="t1", agent_id="usdm-generator",
                         task_type="usdm_generate",
                         input_data={"include_types": ["objective"]})
        result = self.agent.execute(task)
        assert result.success
        assert result.data["entity_count"] == 1
        assert "objective" in result.data["entity_types_included"]

    def test_execute_with_exclude_filter(self):
        store = _make_store_with_entities([
            ("metadata", {"id": "m1", "name": "Study"}),
            ("objective", {"id": "obj1", "text": "Primary"}),
            ("study_arm", {"id": "arm1", "name": "Arm 1"}),
        ])
        self.agent.set_context_store(store)

        task = AgentTask(task_id="t1", agent_id="usdm-generator",
                         task_type="usdm_generate",
                         input_data={"exclude_types": ["objective"]})
        result = self.agent.execute(task)
        assert result.success
        assert "objective" not in result.data["entity_types_included"]

    def test_execute_writes_to_file(self):
        store = _make_store_with_entities([
            ("metadata", {"id": "m1", "name": "Study"}),
        ])
        self.agent.set_context_store(store)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "usdm_output.json")
            task = AgentTask(task_id="t1", agent_id="usdm-generator",
                             task_type="usdm_generate",
                             input_data={"output_path": output_path})
            result = self.agent.execute(task)
            assert result.success
            assert os.path.exists(output_path)

            with open(output_path, "r") as f:
                written = json.load(f)
            assert written["study"]["name"] == "Study"

    def test_execute_provenance(self):
        store = _make_store_with_entities([
            ("metadata", {"id": "m1", "name": "Study"}),
        ])
        self.agent.set_context_store(store)

        task = AgentTask(task_id="t1", agent_id="usdm-generator",
                         task_type="usdm_generate", input_data={})
        result = self.agent.execute(task)
        assert result.provenance is not None
        assert result.provenance["agent_id"] == "usdm-generator"

    def test_execute_confidence_with_issues(self):
        store = ContextStore()  # Empty store → validation warnings
        self.agent.set_context_store(store)

        task = AgentTask(task_id="t1", agent_id="usdm-generator",
                         task_type="usdm_generate", input_data={})
        result = self.agent.execute(task)
        assert result.success
        # Empty store produces validation issues → confidence < 1.0
        assert result.confidence_score == 0.8

    def test_all_list_entity_types_have_placement(self):
        """Every LIST_ENTITY_TYPE should have a placement mapping."""
        for etype in LIST_ENTITY_TYPES:
            assert etype in ENTITY_TYPE_PLACEMENT, f"{etype} missing from ENTITY_TYPE_PLACEMENT"

    def test_entity_id_added_if_missing(self):
        store = _make_store_with_entities([
            ("study_arm", {"name": "Arm 1"}),  # No "id" in data
        ])
        self.agent.set_context_store(store)

        task = AgentTask(task_id="t1", agent_id="usdm-generator",
                         task_type="usdm_generate", input_data={})
        result = self.agent.execute(task)
        assert result.success
        arms = result.data["usdm"]["study"]["versions"][0]["studyDesigns"][0]["arms"]
        assert len(arms) == 1
        assert "id" in arms[0]
