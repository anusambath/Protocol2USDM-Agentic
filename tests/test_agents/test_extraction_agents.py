"""
Unit tests for all Phase 2 extraction agents.

Tests verify that each agent:
- Initializes correctly and reports proper capabilities
- Wraps the underlying extractor correctly
- Stores entities in the Context Store
- Returns proper AgentResult with provenance
- Handles extraction failures gracefully
- Pulls context from Context Store when available
"""

import pytest
from unittest.mock import patch, MagicMock

from agents.base import AgentCapabilities, AgentResult, AgentState, AgentTask
from agents.context_store import ContextStore, ContextEntity, EntityProvenance
from agents.extraction.base_extraction_agent import BaseExtractionAgent
from agents.extraction.metadata_agent import MetadataAgent
from agents.extraction.eligibility_agent import EligibilityAgent
from agents.extraction.objectives_agent import ObjectivesAgent
from agents.extraction.studydesign_agent import StudyDesignAgent
from agents.extraction.interventions_agent import InterventionsAgent
from agents.extraction.soa_vision_agent import SoAVisionAgent
from agents.extraction.soa_text_agent import SoATextAgent
# Phase 3 agents
from agents.extraction.procedures_agent import ProceduresAgent
from agents.extraction.scheduling_agent import SchedulingAgent
from agents.extraction.execution_agent import ExecutionAgent
from agents.extraction.narrative_agent import NarrativeAgent
from agents.extraction.advanced_agent import AdvancedAgent
from agents.extraction.docstructure_agent import DocStructureAgent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def context_store():
    return ContextStore()


@pytest.fixture
def sample_task():
    return AgentTask(
        task_id="test_task",
        agent_id="test_agent",
        task_type="extraction",
        input_data={
            "pdf_path": "/fake/protocol.pdf",
            "protocol_text": "Sample protocol text for testing.",
            "model": "test-model",
            "output_dir": "/fake/output",
        },
    )


def _seed_metadata_context(store: ContextStore):
    """Add metadata entities to context store for downstream agents."""
    store.add_entity(ContextEntity(
        id="indication_1",
        entity_type="indication",
        data={"name": "Type 2 Diabetes", "id": "indication_1"},
        provenance=EntityProvenance(
            entity_id="indication_1", source_agent_id="metadata_agent",
            confidence_score=0.9, model_used="test-model",
        ),
    ))
    store.add_entity(ContextEntity(
        id="study_phase_1",
        entity_type="study_phase",
        data={"code": "Phase 3", "id": "study_phase_1"},
        provenance=EntityProvenance(
            entity_id="study_phase_1", source_agent_id="metadata_agent",
            confidence_score=0.9, model_used="test-model",
        ),
    ))


def _seed_arm_context(store: ContextStore):
    """Add study arm entities to context store."""
    store.add_entity(ContextEntity(
        id="arm_1",
        entity_type="study_arm",
        data={"name": "Treatment A", "id": "arm_1"},
        provenance=EntityProvenance(
            entity_id="arm_1", source_agent_id="studydesign_agent",
            confidence_score=0.85, model_used="test-model",
        ),
    ))


# ===========================================================================
# MetadataAgent Tests
# ===========================================================================

class TestMetadataAgent:

    def test_init_and_capabilities(self):
        agent = MetadataAgent()
        assert agent.agent_id == "metadata_agent"
        caps = agent.get_capabilities()
        assert caps.agent_type == "metadata_extraction"
        assert caps.dependencies == []
        assert "study_title" in caps.output_types

    def test_initialize_sets_ready(self):
        agent = MetadataAgent()
        agent.initialize()
        assert agent.state == AgentState.READY

    def test_terminate_sets_terminated(self):
        agent = MetadataAgent()
        agent.initialize()
        agent.terminate()
        assert agent.state == AgentState.TERMINATED

    @patch("extraction.metadata.extractor.extract_study_metadata")
    def test_extract_success(self, mock_extract, sample_task, context_store):
        mock_title = MagicMock()
        mock_title.id = "title_1"
        mock_title.to_dict.return_value = {"id": "title_1", "text": "Test Study"}

        mock_ident = MagicMock()
        mock_ident.id = "sid_1"
        mock_ident.to_dict.return_value = {"id": "sid_1", "text": "NCT12345678"}

        mock_org = MagicMock()
        mock_org.id = "org_1"
        mock_org.to_dict.return_value = {"id": "org_1", "name": "TestPharma"}

        mock_role = MagicMock()
        mock_role.id = "role_1"
        mock_role.to_dict.return_value = {"id": "role_1", "name": "Sponsor"}

        mock_ind = MagicMock()
        mock_ind.id = "ind_1"
        mock_ind.to_dict.return_value = {"id": "ind_1", "name": "Diabetes"}

        mock_phase = MagicMock()
        mock_phase.to_dict.return_value = {"code": "Phase 3"}

        mock_metadata = MagicMock()
        mock_metadata.study_name = "Test Study"
        mock_metadata.titles = [mock_title]
        mock_metadata.identifiers = [mock_ident]
        mock_metadata.organizations = [mock_org]
        mock_metadata.roles = [mock_role]
        mock_metadata.indications = [mock_ind]
        mock_metadata.study_phase = mock_phase

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.metadata = mock_metadata
        mock_result.pages_used = [0, 1, 2]
        mock_result.raw_response = {"titles": []}
        mock_extract.return_value = mock_result

        agent = MetadataAgent()
        agent.initialize()
        agent.set_context_store(context_store)

        result = agent.run_task(sample_task)

        assert result.success
        assert result.data is not None
        assert len(result.data["entities"]) == 6
        assert context_store.entity_count == 6

    @patch("extraction.metadata.extractor.extract_study_metadata")
    def test_extract_failure(self, mock_extract, sample_task):
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.metadata = None
        mock_extract.return_value = mock_result

        agent = MetadataAgent()
        agent.initialize()

        result = agent.run_task(sample_task)

        assert not result.success


# ===========================================================================
# EligibilityAgent Tests
# ===========================================================================

class TestEligibilityAgent:

    def test_init_and_capabilities(self):
        agent = EligibilityAgent()
        assert agent.agent_id == "eligibility_agent"
        caps = agent.get_capabilities()
        assert caps.agent_type == "eligibility_extraction"
        assert "metadata_extraction" in caps.dependencies
        assert "eligibility_criterion" in caps.output_types

    @patch("extraction.eligibility.extractor.extract_eligibility_criteria")
    def test_extract_success(self, mock_extract, sample_task, context_store):
        mock_item = MagicMock()
        mock_item.id = "eci_1"
        mock_item.to_dict.return_value = {"id": "eci_1", "text": "Age >= 18"}

        mock_crit = MagicMock()
        mock_crit.id = "ec_1"
        mock_crit.to_dict.return_value = {"id": "ec_1", "category": "Inclusion"}

        mock_pop = MagicMock()
        mock_pop.id = "pop_1"
        mock_pop.to_dict.return_value = {"id": "pop_1", "name": "Study Population"}

        mock_data = MagicMock()
        mock_data.criterion_items = [mock_item]
        mock_data.criteria = [mock_crit]
        mock_data.population = mock_pop
        mock_data.inclusion_count = 1
        mock_data.exclusion_count = 0

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.data = mock_data
        mock_result.pages_used = [5, 6, 7]
        mock_result.raw_response = {}
        mock_extract.return_value = mock_result

        agent = EligibilityAgent()
        agent.initialize()
        agent.set_context_store(context_store)

        result = agent.run_task(sample_task)

        assert result.success
        assert len(result.data["entities"]) == 3
        assert context_store.entity_count == 3

    @patch("extraction.eligibility.extractor.extract_eligibility_criteria")
    def test_pulls_context_from_store(self, mock_extract, sample_task, context_store):
        """Verify agent pulls indication/phase from Context Store."""
        _seed_metadata_context(context_store)

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.data = None
        mock_extract.return_value = mock_result

        agent = EligibilityAgent()
        agent.initialize()
        agent.set_context_store(context_store)

        agent.run_task(sample_task)

        call_kwargs = mock_extract.call_args
        assert call_kwargs.kwargs.get("study_indication") == "Type 2 Diabetes"


# ===========================================================================
# ObjectivesAgent Tests
# ===========================================================================

class TestObjectivesAgent:

    def test_init_and_capabilities(self):
        agent = ObjectivesAgent()
        assert agent.agent_id == "objectives_agent"
        caps = agent.get_capabilities()
        assert caps.agent_type == "objectives_extraction"
        assert "metadata_extraction" in caps.dependencies
        assert "objective" in caps.output_types
        assert "endpoint" in caps.output_types
        assert "estimand" in caps.output_types

    @patch("extraction.objectives.extractor.extract_objectives_endpoints")
    def test_extract_success(self, mock_extract, sample_task, context_store):
        mock_obj = MagicMock()
        mock_obj.id = "obj_1"
        mock_obj.to_dict.return_value = {"id": "obj_1", "name": "Primary Objective"}

        mock_ep = MagicMock()
        mock_ep.id = "ep_1"
        mock_ep.to_dict.return_value = {"id": "ep_1", "name": "Primary Endpoint"}

        mock_est = MagicMock()
        mock_est.id = "est_1"
        mock_est.to_dict.return_value = {"id": "est_1", "name": "Estimand 1"}

        mock_data = MagicMock()
        mock_data.objectives = [mock_obj]
        mock_data.endpoints = [mock_ep]
        mock_data.estimands = [mock_est]
        mock_data.primary_objectives_count = 1
        mock_data.secondary_objectives_count = 0
        mock_data.exploratory_objectives_count = 0

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.data = mock_data
        mock_result.pages_used = [3, 4]
        mock_result.raw_response = {}
        mock_extract.return_value = mock_result

        agent = ObjectivesAgent()
        agent.initialize()
        agent.set_context_store(context_store)

        result = agent.run_task(sample_task)

        assert result.success
        assert len(result.data["entities"]) == 3
        assert context_store.entity_count == 3


# ===========================================================================
# StudyDesignAgent Tests
# ===========================================================================

class TestStudyDesignAgent:

    def test_init_and_capabilities(self):
        agent = StudyDesignAgent()
        assert agent.agent_id == "studydesign_agent"
        caps = agent.get_capabilities()
        assert caps.agent_type == "studydesign_extraction"
        assert "study_arm" in caps.output_types
        assert "study_design" in caps.output_types

    @patch("extraction.studydesign.extractor.extract_study_design")
    def test_extract_success(self, mock_extract, sample_task, context_store):
        mock_design = MagicMock()
        mock_design.id = "sd_1"
        mock_design.to_dict.return_value = {"id": "sd_1", "name": "Study Design"}

        mock_arm = MagicMock()
        mock_arm.id = "arm_1"
        mock_arm.to_dict.return_value = {"id": "arm_1", "name": "Treatment A"}

        mock_cohort = MagicMock()
        mock_cohort.id = "cohort_1"
        mock_cohort.to_dict.return_value = {"id": "cohort_1", "name": "Cohort 1"}

        mock_data = MagicMock()
        mock_data.study_design = mock_design
        mock_data.arms = [mock_arm]
        mock_data.cohorts = [mock_cohort]
        mock_data.cells = []
        mock_data.elements = []

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.data = mock_data
        mock_result.pages_used = [2, 3]
        mock_result.raw_response = {}
        mock_extract.return_value = mock_result

        agent = StudyDesignAgent()
        agent.initialize()
        agent.set_context_store(context_store)

        result = agent.run_task(sample_task)

        assert result.success
        assert len(result.data["entities"]) == 3
        assert context_store.entity_count == 3

    @patch("extraction.studydesign.extractor.extract_study_design")
    def test_pulls_epochs_from_context(self, mock_extract, sample_task, context_store):
        """Verify agent pulls existing epochs from Context Store."""
        context_store.add_entity(ContextEntity(
            id="epoch_1",
            entity_type="epoch",
            data={"name": "Screening"},
            provenance=EntityProvenance(
                entity_id="epoch_1", source_agent_id="soa_vision_agent",
                confidence_score=0.85, model_used="test-model",
            ),
        ))

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.data = None
        mock_extract.return_value = mock_result

        agent = StudyDesignAgent()
        agent.initialize()
        agent.set_context_store(context_store)

        agent.run_task(sample_task)

        call_kwargs = mock_extract.call_args
        existing_epochs = call_kwargs.kwargs.get("existing_epochs")
        assert existing_epochs is not None
        assert len(existing_epochs) == 1


# ===========================================================================
# InterventionsAgent Tests
# ===========================================================================

class TestInterventionsAgent:

    def test_init_and_capabilities(self):
        agent = InterventionsAgent()
        assert agent.agent_id == "interventions_agent"
        caps = agent.get_capabilities()
        assert caps.agent_type == "interventions_extraction"
        assert "metadata_extraction" in caps.dependencies
        assert "studydesign_extraction" in caps.dependencies
        assert "study_intervention" in caps.output_types

    @patch("extraction.interventions.extractor.extract_interventions")
    def test_extract_success(self, mock_extract, sample_task, context_store):
        mock_intv = MagicMock()
        mock_intv.id = "int_1"
        mock_intv.to_dict.return_value = {"id": "int_1", "name": "Drug A"}

        mock_prod = MagicMock()
        mock_prod.id = "prod_1"
        mock_prod.to_dict.return_value = {"id": "prod_1", "name": "Tablet"}

        mock_admin = MagicMock()
        mock_admin.id = "admin_1"
        mock_admin.to_dict.return_value = {"id": "admin_1", "dose": "100mg"}

        mock_data = MagicMock()
        mock_data.interventions = [mock_intv]
        mock_data.products = [mock_prod]
        mock_data.administrations = [mock_admin]
        mock_data.substances = []
        mock_data.devices = []

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.data = mock_data
        mock_result.pages_used = [10, 11]
        mock_result.raw_response = {}
        mock_extract.return_value = mock_result

        agent = InterventionsAgent()
        agent.initialize()
        agent.set_context_store(context_store)

        result = agent.run_task(sample_task)

        assert result.success
        assert len(result.data["entities"]) == 3
        assert context_store.entity_count == 3

    @patch("extraction.interventions.extractor.extract_interventions")
    def test_pulls_arms_and_indication(self, mock_extract, sample_task, context_store):
        """Verify agent pulls arms and indication from Context Store."""
        _seed_metadata_context(context_store)
        _seed_arm_context(context_store)

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.data = None
        mock_extract.return_value = mock_result

        agent = InterventionsAgent()
        agent.initialize()
        agent.set_context_store(context_store)

        agent.run_task(sample_task)

        call_kwargs = mock_extract.call_args
        assert call_kwargs.kwargs.get("study_indication") == "Type 2 Diabetes"
        existing_arms = call_kwargs.kwargs.get("existing_arms")
        assert existing_arms is not None
        assert len(existing_arms) == 1


# ===========================================================================
# SoAVisionAgent Tests
# ===========================================================================

class TestSoAVisionAgent:

    def test_init_and_capabilities(self):
        agent = SoAVisionAgent()
        assert agent.agent_id == "soa_vision_agent"
        caps = agent.get_capabilities()
        assert caps.agent_type == "soa_vision_extraction"
        assert caps.dependencies == []
        assert "epoch" in caps.output_types
        assert "encounter" in caps.output_types

    @patch("extraction.header_analyzer.analyze_soa_headers")
    @patch("extraction.soa_finder.extract_soa_images")
    @patch("extraction.soa_finder.find_soa_pages")
    def test_extract_success(self, mock_find, mock_images, mock_analyze,
                             sample_task, context_store):
        mock_find.return_value = [5, 6, 7]
        mock_images.return_value = ["/fake/page5.png", "/fake/page6.png"]

        mock_epoch = MagicMock()
        mock_epoch.name = "Screening"
        mock_enc = MagicMock()
        mock_enc.name = "Visit 1"

        mock_structure = MagicMock()
        mock_structure.epochs = [mock_epoch]
        mock_structure.encounters = [mock_enc]
        mock_structure.to_dict.return_value = {"epochs": ["Screening"], "encounters": ["Visit 1"]}

        mock_header_result = MagicMock()
        mock_header_result.structure = mock_structure
        mock_header_result.confidence = 0.85
        mock_analyze.return_value = mock_header_result

        agent = SoAVisionAgent()
        agent.initialize()
        agent.set_context_store(context_store)

        result = agent.run_task(sample_task)

        assert result.success
        assert len(result.data["entities"]) == 3
        assert context_store.entity_count == 3

    @patch("extraction.soa_finder.find_soa_pages")
    def test_no_soa_pages(self, mock_find, sample_task):
        mock_find.return_value = []

        agent = SoAVisionAgent()
        agent.initialize()

        result = agent.run_task(sample_task)

        assert not result.success

    @patch("extraction.header_analyzer.analyze_soa_headers")
    @patch("extraction.soa_finder.extract_soa_images")
    @patch("extraction.soa_finder.find_soa_pages")
    def test_uses_provided_pages(self, mock_find, mock_images, mock_analyze,
                                  context_store):
        """When soa_pages and soa_images are provided, skip detection."""
        task = AgentTask(
            task_id="test", agent_id="soa_vision_agent", task_type="extraction",
            input_data={
                "pdf_path": "/fake/protocol.pdf",
                "soa_pages": [10, 11],
                "soa_images": ["/fake/img1.png"],
                "output_dir": "/fake/output",
            },
        )

        mock_structure = MagicMock()
        mock_structure.epochs = []
        mock_structure.encounters = []
        mock_structure.to_dict.return_value = {}

        mock_header_result = MagicMock()
        mock_header_result.structure = mock_structure
        mock_header_result.confidence = 0.8
        mock_analyze.return_value = mock_header_result

        agent = SoAVisionAgent()
        agent.initialize()
        agent.set_context_store(context_store)

        result = agent.run_task(task)

        assert result.success
        mock_find.assert_not_called()
        mock_images.assert_not_called()


# ===========================================================================
# SoATextAgent Tests
# ===========================================================================

class TestSoATextAgent:

    def test_init_and_capabilities(self):
        agent = SoATextAgent()
        assert agent.agent_id == "soa_text_agent"
        caps = agent.get_capabilities()
        assert caps.agent_type == "soa_text_extraction"
        assert caps.dependencies == ["soa_vision_extraction"]
        assert "activity" in caps.output_types

    @patch("extraction.text_extractor.extract_soa_from_text")
    @patch("extraction.soa_finder.extract_soa_text")
    @patch("extraction.soa_finder.find_soa_pages")
    def test_extract_success(self, mock_find, mock_text, mock_extract_soa,
                             sample_task, context_store):
        mock_find.return_value = [5, 6]
        mock_text.return_value = "SoA table text content"

        mock_activity = {"name": "Blood Draw", "cells": []}
        mock_text_result = MagicMock()
        mock_text_result.activities = [mock_activity]
        mock_text_result.to_dict.return_value = {"activities": [mock_activity]}
        mock_extract_soa.return_value = mock_text_result

        # Provide header_structure (required since null-check was added)
        sample_task.input_data["header_structure"] = {"activityGroups": []}

        agent = SoATextAgent()
        agent.initialize()
        agent.set_context_store(context_store)

        result = agent.run_task(sample_task)

        assert result.success
        assert len(result.data["entities"]) == 2
        assert context_store.entity_count == 2

    @patch("extraction.soa_finder.find_soa_pages")
    def test_no_soa_pages(self, mock_find, sample_task):
        mock_find.return_value = []

        agent = SoATextAgent()
        agent.initialize()

        result = agent.run_task(sample_task)

        assert not result.success


# ===========================================================================
# Cross-cutting Tests
# ===========================================================================

class TestExtractionAgentCommon:

    @pytest.mark.parametrize("agent_cls,agent_id", [
        (MetadataAgent, "metadata_agent"),
        (EligibilityAgent, "eligibility_agent"),
        (ObjectivesAgent, "objectives_agent"),
        (StudyDesignAgent, "studydesign_agent"),
        (InterventionsAgent, "interventions_agent"),
        (SoAVisionAgent, "soa_vision_agent"),
        (SoATextAgent, "soa_text_agent"),
        # Phase 3
        (ProceduresAgent, "procedures_agent"),
        (SchedulingAgent, "scheduling_agent"),
        (ExecutionAgent, "execution_agent"),
        (NarrativeAgent, "narrative_agent"),
        (AdvancedAgent, "advanced_agent"),
        (DocStructureAgent, "docstructure_agent"),
    ])
    def test_all_agents_extend_base(self, agent_cls, agent_id):
        agent = agent_cls()
        assert isinstance(agent, BaseExtractionAgent)
        assert agent.agent_id == agent_id

    @pytest.mark.parametrize("agent_cls", [
        MetadataAgent, EligibilityAgent, ObjectivesAgent,
        StudyDesignAgent, InterventionsAgent,
        SoAVisionAgent, SoATextAgent,
        ProceduresAgent, SchedulingAgent, ExecutionAgent,
        NarrativeAgent, AdvancedAgent, DocStructureAgent,
    ])
    def test_all_agents_lifecycle(self, agent_cls):
        agent = agent_cls()
        assert agent.state == AgentState.INITIALIZING
        agent.initialize()
        assert agent.state == AgentState.READY
        agent.terminate()
        assert agent.state == AgentState.TERMINATED

    @pytest.mark.parametrize("agent_cls", [
        MetadataAgent, EligibilityAgent, ObjectivesAgent,
        StudyDesignAgent, InterventionsAgent,
        SoAVisionAgent, SoATextAgent,
        ProceduresAgent, SchedulingAgent, ExecutionAgent,
        NarrativeAgent, AdvancedAgent, DocStructureAgent,
    ])
    def test_all_agents_have_valid_capabilities(self, agent_cls):
        agent = agent_cls()
        caps = agent.get_capabilities()
        assert isinstance(caps, AgentCapabilities)
        assert caps.agent_type != ""
        assert len(caps.output_types) > 0
        assert caps.timeout_seconds > 0

    @pytest.mark.parametrize("agent_cls", [
        MetadataAgent, EligibilityAgent, ObjectivesAgent,
        StudyDesignAgent, InterventionsAgent,
        SoAVisionAgent, SoATextAgent,
        ProceduresAgent, SchedulingAgent, ExecutionAgent,
        NarrativeAgent, AdvancedAgent, DocStructureAgent,
    ])
    def test_custom_agent_id(self, agent_cls):
        agent = agent_cls(agent_id="custom_id")
        assert agent.agent_id == "custom_id"

    @pytest.mark.parametrize("agent_cls", [
        MetadataAgent, EligibilityAgent, ObjectivesAgent,
        StudyDesignAgent, InterventionsAgent,
        SoAVisionAgent, SoATextAgent,
        ProceduresAgent, SchedulingAgent, ExecutionAgent,
        NarrativeAgent, AdvancedAgent, DocStructureAgent,
    ])
    def test_context_store_attachment(self, agent_cls, context_store):
        agent = agent_cls()
        assert agent.context_store is None
        agent.set_context_store(context_store)
        assert agent.context_store is context_store



# ===========================================================================
# Phase 3: ProceduresAgent Tests
# ===========================================================================

class TestProceduresAgent:

    def test_init_and_capabilities(self):
        agent = ProceduresAgent()
        assert agent.agent_id == "procedures_agent"
        caps = agent.get_capabilities()
        assert caps.agent_type == "procedures_extraction"
        assert "metadata_extraction" in caps.dependencies
        assert "procedure" in caps.output_types
        assert "medical_device" in caps.output_types

    @patch("extraction.procedures.extractor.extract_procedures_devices")
    def test_extract_success(self, mock_extract, sample_task, context_store):
        mock_proc = MagicMock()
        mock_proc.id = "proc_1"
        mock_proc.to_dict.return_value = {"id": "proc_1", "name": "Blood Draw"}

        mock_dev = MagicMock()
        mock_dev.id = "dev_1"
        mock_dev.to_dict.return_value = {"id": "dev_1", "name": "ECG Monitor"}

        mock_ing = MagicMock()
        mock_ing.id = "ing_1"
        mock_ing.to_dict.return_value = {"id": "ing_1", "name": "Saline"}

        mock_str = MagicMock()
        mock_str.id = "str_1"
        mock_str.to_dict.return_value = {"id": "str_1", "value": 100, "unit": "mg"}

        mock_data = MagicMock()
        mock_data.procedures = [mock_proc]
        mock_data.devices = [mock_dev]
        mock_data.ingredients = [mock_ing]
        mock_data.strengths = [mock_str]

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.data = mock_data
        mock_result.pages_used = [10, 11, 12]
        mock_result.confidence = 0.8
        mock_extract.return_value = mock_result

        agent = ProceduresAgent()
        agent.initialize()
        agent.set_context_store(context_store)

        result = agent.run_task(sample_task)

        assert result.success
        assert len(result.data["entities"]) == 4
        assert context_store.entity_count == 4
        assert result.data["procedures_summary"]["procedure_count"] == 1
        assert result.data["procedures_summary"]["device_count"] == 1

    @patch("extraction.procedures.extractor.extract_procedures_devices")
    def test_extract_failure(self, mock_extract, sample_task):
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.data = None
        mock_extract.return_value = mock_result

        agent = ProceduresAgent()
        agent.initialize()

        result = agent.run_task(sample_task)

        assert not result.success


# ===========================================================================
# Phase 3: SchedulingAgent Tests
# ===========================================================================

class TestSchedulingAgent:

    def test_init_and_capabilities(self):
        agent = SchedulingAgent()
        assert agent.agent_id == "scheduling_agent"
        caps = agent.get_capabilities()
        assert caps.agent_type == "scheduling_extraction"
        assert "soa_vision_extraction" in caps.dependencies
        assert "timing" in caps.output_types
        assert "transition_rule" in caps.output_types

    @patch("extraction.scheduling.extractor.extract_scheduling")
    def test_extract_success(self, mock_extract, sample_task, context_store):
        mock_timing = MagicMock()
        mock_timing.id = "timing_1"
        mock_timing.to_dict.return_value = {"id": "timing_1", "name": "Day 1"}

        mock_cond = MagicMock()
        mock_cond.id = "cond_1"
        mock_cond.to_dict.return_value = {"id": "cond_1", "name": "Screening Pass"}

        mock_rule = MagicMock()
        mock_rule.id = "trans_1"
        mock_rule.to_dict.return_value = {"id": "trans_1", "name": "Screen to Treatment"}

        mock_exit = MagicMock()
        mock_exit.id = "exit_1"
        mock_exit.to_dict.return_value = {"id": "exit_1", "name": "Early Termination"}

        mock_dec = MagicMock()
        mock_dec.id = "dec_1"
        mock_dec.to_dict.return_value = {"id": "dec_1", "name": "Randomization"}

        mock_data = MagicMock()
        mock_data.timings = [mock_timing]
        mock_data.conditions = [mock_cond]
        mock_data.transition_rules = [mock_rule]
        mock_data.schedule_exits = [mock_exit]
        mock_data.decision_instances = [mock_dec]

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.data = mock_data
        mock_result.pages_used = [8, 9]
        mock_result.confidence = 0.7
        mock_extract.return_value = mock_result

        agent = SchedulingAgent()
        agent.initialize()
        agent.set_context_store(context_store)

        result = agent.run_task(sample_task)

        assert result.success
        assert len(result.data["entities"]) == 5
        assert context_store.entity_count == 5
        assert result.data["scheduling_summary"]["timing_count"] == 1
        assert result.data["scheduling_summary"]["transition_rule_count"] == 1

    @patch("extraction.scheduling.extractor.extract_scheduling")
    def test_extract_failure(self, mock_extract, sample_task):
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.data = None
        mock_extract.return_value = mock_result

        agent = SchedulingAgent()
        agent.initialize()

        result = agent.run_task(sample_task)

        assert not result.success


# ===========================================================================
# Phase 3: ExecutionAgent Tests
# ===========================================================================

class TestExecutionAgent:

    def test_init_and_capabilities(self):
        agent = ExecutionAgent()
        assert agent.agent_id == "execution_agent"
        caps = agent.get_capabilities()
        assert caps.agent_type == "execution_extraction"
        assert "soa_vision_extraction" in caps.dependencies
        assert "time_anchor" in caps.output_types
        assert "state_machine" in caps.output_types

    @patch("extraction.execution.pipeline_integration.extract_execution_model")
    def test_extract_success(self, mock_extract, sample_task, context_store):
        mock_anchor = MagicMock()
        mock_anchor.id = "anchor_1"
        mock_anchor.to_dict.return_value = {"id": "anchor_1", "name": "Day 1"}

        mock_rep = MagicMock()
        mock_rep.id = "rep_1"
        mock_rep.to_dict.return_value = {"id": "rep_1", "name": "Weekly Cycle"}

        mock_et = MagicMock()
        mock_et.id = "et_1"
        mock_et.to_dict.return_value = {"id": "et_1", "type": "WINDOW"}

        mock_tc = MagicMock()
        mock_tc.id = "tc_1"
        mock_tc.to_dict.return_value = {"id": "tc_1", "name": "Main Path"}

        mock_fc = MagicMock()
        mock_fc.id = "fc_1"
        mock_fc.to_dict.return_value = {"id": "fc_1", "text": "If applicable"}

        mock_sm = MagicMock()
        mock_sm.id = "sm_1"
        mock_sm.to_dict.return_value = {"id": "sm_1", "states": []}

        mock_dr = MagicMock()
        mock_dr.id = "dr_1"
        mock_dr.to_dict.return_value = {"id": "dr_1", "name": "Dose A"}

        mock_vw = MagicMock()
        mock_vw.id = "vw_1"
        mock_vw.to_dict.return_value = {"id": "vw_1", "name": "Visit 1 Window"}

        mock_data = MagicMock()
        mock_data.time_anchors = [mock_anchor]
        mock_data.repetitions = [mock_rep]
        mock_data.execution_types = [mock_et]
        mock_data.traversal_constraints = [mock_tc]
        mock_data.footnote_conditions = [mock_fc]
        mock_data.state_machine = mock_sm
        mock_data.dosing_regimens = [mock_dr]
        mock_data.visit_windows = [mock_vw]

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.data = mock_data
        mock_result.pages_used = [1, 2, 3, 4, 5]
        mock_extract.return_value = mock_result

        agent = ExecutionAgent()
        agent.initialize()
        agent.set_context_store(context_store)

        result = agent.run_task(sample_task)

        assert result.success
        # 1 anchor + 1 rep + 1 et + 1 tc + 1 fc + 1 sm + 1 dr + 1 vw = 8
        assert len(result.data["entities"]) == 8
        assert context_store.entity_count == 8
        assert result.data["execution_summary"]["has_state_machine"] is True

    @patch("extraction.execution.pipeline_integration.extract_execution_model")
    def test_extract_failure(self, mock_extract, sample_task):
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.data = None
        mock_extract.return_value = mock_result

        agent = ExecutionAgent()
        agent.initialize()

        result = agent.run_task(sample_task)

        assert not result.success

    @patch("extraction.execution.pipeline_integration.extract_execution_model")
    def test_pulls_soa_from_context(self, mock_extract, sample_task, context_store):
        """Verify agent pulls SoA data from Context Store."""
        context_store.add_entity(ContextEntity(
            id="soa_1",
            entity_type="soa_table",
            data={"epochs": ["Screening", "Treatment"]},
            provenance=EntityProvenance(
                entity_id="soa_1", source_agent_id="soa_vision_agent",
                confidence_score=0.9, model_used="test-model",
            ),
        ))

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.data = None
        mock_extract.return_value = mock_result

        agent = ExecutionAgent()
        agent.initialize()
        agent.set_context_store(context_store)

        agent.run_task(sample_task)

        call_kwargs = mock_extract.call_args
        assert call_kwargs.kwargs.get("soa_data") == {"epochs": ["Screening", "Treatment"]}


# ===========================================================================
# Phase 3: NarrativeAgent Tests
# ===========================================================================

class TestNarrativeAgent:

    def test_init_and_capabilities(self):
        agent = NarrativeAgent()
        assert agent.agent_id == "narrative_agent"
        caps = agent.get_capabilities()
        assert caps.agent_type == "narrative_extraction"
        assert caps.dependencies == []
        assert "narrative_content" in caps.output_types
        assert "abbreviation" in caps.output_types

    @patch("extraction.narrative.extractor.extract_narrative_structure")
    def test_extract_success(self, mock_extract, sample_task, context_store):
        mock_section = MagicMock()
        mock_section.id = "sec_1"
        mock_section.to_dict.return_value = {"id": "sec_1", "name": "Introduction"}

        mock_item = MagicMock()
        mock_item.id = "item_1"
        mock_item.to_dict.return_value = {"id": "item_1", "name": "Background"}

        mock_abbrev = MagicMock()
        mock_abbrev.id = "abbr_1"
        mock_abbrev.to_dict.return_value = {"id": "abbr_1", "abbreviatedText": "ECG"}

        mock_doc = MagicMock()
        mock_doc.id = "doc_1"
        mock_doc.to_dict.return_value = {"id": "doc_1", "name": "Protocol v1.0"}

        mock_data = MagicMock()
        mock_data.sections = [mock_section]
        mock_data.items = [mock_item]
        mock_data.abbreviations = [mock_abbrev]
        mock_data.document = mock_doc

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.data = mock_data
        mock_result.pages_used = [0, 1, 2, 3]
        mock_result.raw_response = {}
        mock_extract.return_value = mock_result

        agent = NarrativeAgent()
        agent.initialize()
        agent.set_context_store(context_store)

        result = agent.run_task(sample_task)

        assert result.success
        # 1 section + 1 item + 1 abbrev + 1 doc = 4
        assert len(result.data["entities"]) == 4
        assert context_store.entity_count == 4
        assert result.data["narrative_summary"]["section_count"] == 1
        assert result.data["narrative_summary"]["has_document"] is True

    @patch("extraction.narrative.extractor.extract_narrative_structure")
    def test_extract_no_document(self, mock_extract, sample_task, context_store):
        """Verify agent handles missing document gracefully."""
        mock_data = MagicMock()
        mock_data.sections = []
        mock_data.items = []
        mock_data.abbreviations = []
        mock_data.document = None

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.data = mock_data
        mock_result.pages_used = [0, 1]
        mock_result.raw_response = {}
        mock_extract.return_value = mock_result

        agent = NarrativeAgent()
        agent.initialize()
        agent.set_context_store(context_store)

        result = agent.run_task(sample_task)

        assert result.success
        assert len(result.data["entities"]) == 0
        assert result.data["narrative_summary"]["has_document"] is False

    @patch("extraction.narrative.extractor.extract_narrative_structure")
    def test_extract_failure(self, mock_extract, sample_task):
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.data = None
        mock_extract.return_value = mock_result

        agent = NarrativeAgent()
        agent.initialize()

        result = agent.run_task(sample_task)

        assert not result.success


# ===========================================================================
# Phase 3: AdvancedAgent Tests
# ===========================================================================

class TestAdvancedAgent:

    def test_init_and_capabilities(self):
        agent = AdvancedAgent()
        assert agent.agent_id == "advanced_agent"
        caps = agent.get_capabilities()
        assert caps.agent_type == "advanced_extraction"
        assert "metadata_extraction" in caps.dependencies
        assert "study_amendment" in caps.output_types
        assert "country" in caps.output_types

    @patch("extraction.advanced.extractor.extract_advanced_entities")
    def test_extract_success(self, mock_extract, sample_task, context_store):
        mock_amendment = MagicMock()
        mock_amendment.id = "amend_1"
        mock_amendment.to_dict.return_value = {"id": "amend_1", "number": "1"}

        mock_reason = MagicMock()
        mock_reason.id = "reason_1"
        mock_reason.to_dict.return_value = {"id": "reason_1", "code": "SAFETY"}

        mock_scope = MagicMock()
        mock_scope.id = "scope_1"
        mock_scope.to_dict.return_value = {"id": "scope_1", "name": "Global"}

        mock_country = MagicMock()
        mock_country.id = "country_1"
        mock_country.to_dict.return_value = {"id": "country_1", "name": "United States"}

        mock_site = MagicMock()
        mock_site.id = "site_1"
        mock_site.to_dict.return_value = {"id": "site_1", "name": "Site 001"}

        mock_data = MagicMock()
        mock_data.amendments = [mock_amendment]
        mock_data.amendment_reasons = [mock_reason]
        mock_data.geographic_scope = mock_scope
        mock_data.countries = [mock_country]
        mock_data.sites = [mock_site]

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.data = mock_data
        mock_result.pages_used = [0, 1, 2]
        mock_result.raw_response = {}
        mock_extract.return_value = mock_result

        agent = AdvancedAgent()
        agent.initialize()
        agent.set_context_store(context_store)

        result = agent.run_task(sample_task)

        assert result.success
        # 1 amendment + 1 reason + 1 scope + 1 country + 1 site = 5
        assert len(result.data["entities"]) == 5
        assert context_store.entity_count == 5
        assert result.data["advanced_summary"]["amendment_count"] == 1
        assert result.data["advanced_summary"]["has_geographic_scope"] is True

    @patch("extraction.advanced.extractor.extract_advanced_entities")
    def test_extract_no_scope(self, mock_extract, sample_task, context_store):
        """Verify agent handles missing geographic scope."""
        mock_data = MagicMock()
        mock_data.amendments = []
        mock_data.amendment_reasons = []
        mock_data.geographic_scope = None
        mock_data.countries = []
        mock_data.sites = []

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.data = mock_data
        mock_result.pages_used = [0]
        mock_result.raw_response = {}
        mock_extract.return_value = mock_result

        agent = AdvancedAgent()
        agent.initialize()
        agent.set_context_store(context_store)

        result = agent.run_task(sample_task)

        assert result.success
        assert len(result.data["entities"]) == 0
        assert result.data["advanced_summary"]["has_geographic_scope"] is False

    @patch("extraction.advanced.extractor.extract_advanced_entities")
    def test_extract_failure(self, mock_extract, sample_task):
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.data = None
        mock_extract.return_value = mock_result

        agent = AdvancedAgent()
        agent.initialize()

        result = agent.run_task(sample_task)

        assert not result.success


# ===========================================================================
# Phase 3: DocStructureAgent Tests
# ===========================================================================

class TestDocStructureAgent:

    def test_init_and_capabilities(self):
        agent = DocStructureAgent()
        assert agent.agent_id == "docstructure_agent"
        caps = agent.get_capabilities()
        assert caps.agent_type == "docstructure_extraction"
        assert caps.dependencies == []
        assert "document_content_reference" in caps.output_types
        assert "comment_annotation" in caps.output_types

    @patch("extraction.document_structure.extractor.extract_document_structure")
    def test_extract_success(self, mock_extract, sample_task, context_store):
        mock_ref = MagicMock()
        mock_ref.id = "ref_1"
        mock_ref.to_dict.return_value = {"id": "ref_1", "name": "Section 5.1"}

        mock_annot = MagicMock()
        mock_annot.id = "annot_1"
        mock_annot.to_dict.return_value = {"id": "annot_1", "text": "See appendix"}

        mock_ver = MagicMock()
        mock_ver.id = "ver_1"
        mock_ver.to_dict.return_value = {"id": "ver_1", "versionNumber": "1.0"}

        mock_data = MagicMock()
        mock_data.content_references = [mock_ref]
        mock_data.annotations = [mock_annot]
        mock_data.document_versions = [mock_ver]

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.data = mock_data
        mock_result.pages_used = [0, 1, 2, 3, 4]
        mock_result.confidence = 0.75
        mock_extract.return_value = mock_result

        agent = DocStructureAgent()
        agent.initialize()
        agent.set_context_store(context_store)

        result = agent.run_task(sample_task)

        assert result.success
        assert len(result.data["entities"]) == 3
        assert context_store.entity_count == 3
        assert result.data["docstructure_summary"]["reference_count"] == 1
        assert result.data["docstructure_summary"]["annotation_count"] == 1
        assert result.data["docstructure_summary"]["version_count"] == 1

    @patch("extraction.document_structure.extractor.extract_document_structure")
    def test_extract_failure(self, mock_extract, sample_task):
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.data = None
        mock_extract.return_value = mock_result

        agent = DocStructureAgent()
        agent.initialize()

        result = agent.run_task(sample_task)

        assert not result.success
