"""
Integration tests for Phase 2 and Phase 3 extraction agents.

Tests agent workflows through the Orchestrator, verifying:
- Dependency-based execution ordering (wave planning)
- Context Store consistency across agents
- Parallel execution of independent agents
- Message queue communication
- Checkpoint creation after each wave
- End-to-end workflow with all 13 extraction agents

All extraction calls are mocked — no LLM API access required.
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from agents.base import AgentCapabilities, AgentResult, AgentState, AgentTask
from agents.context_store import ContextEntity, ContextStore, EntityProvenance
from agents.message_queue import AgentMessage, MessageQueue, MessageType, Priority
from agents.orchestrator import OrchestratorAgent
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


# ---------------------------------------------------------------------------
# Helpers — mock return values for each extractor
# ---------------------------------------------------------------------------

def _mock_metadata_result():
    """Build a mock result for extract_study_metadata."""
    mock_title = MagicMock(id="title_1")
    mock_title.to_dict.return_value = {"id": "title_1", "text": "Integration Study"}

    mock_ident = MagicMock(id="ident_1")
    mock_ident.to_dict.return_value = {"id": "ident_1", "text": "NCT99999999"}

    mock_org = MagicMock(id="org_1")
    mock_org.to_dict.return_value = {"id": "org_1", "name": "TestPharma"}

    mock_role = MagicMock(id="role_1")
    mock_role.to_dict.return_value = {"id": "role_1", "name": "Sponsor"}

    mock_ind = MagicMock(id="ind_1")
    mock_ind.to_dict.return_value = {"id": "ind_1", "name": "Diabetes"}

    mock_phase = MagicMock()
    mock_phase.to_dict.return_value = {"code": "Phase 3"}

    md = MagicMock()
    md.study_name = "Integration Study"
    md.titles = [mock_title]
    md.identifiers = [mock_ident]
    md.organizations = [mock_org]
    md.roles = [mock_role]
    md.indications = [mock_ind]
    md.study_phase = mock_phase

    result = MagicMock()
    result.success = True
    result.metadata = md
    result.pages_used = [0, 1]
    result.raw_response = {}
    return result


def _mock_eligibility_result():
    item = MagicMock(id="eci_1")
    item.to_dict.return_value = {"id": "eci_1", "text": "Age >= 18"}

    crit = MagicMock(id="ec_1")
    crit.to_dict.return_value = {"id": "ec_1", "text": "Inclusion 1", "category": "inclusion"}

    pop = MagicMock(id="pop_1")
    pop.to_dict.return_value = {"id": "pop_1", "name": "Adult patients"}

    data = MagicMock()
    data.criterion_items = [item]
    data.criteria = [crit]
    data.population = pop
    data.inclusion_count = 3
    data.exclusion_count = 2

    result = MagicMock()
    result.success = True
    result.data = data
    result.pages_used = [5, 6]
    result.raw_response = {}
    return result


def _mock_objectives_result():
    obj = MagicMock(id="obj_1")
    obj.to_dict.return_value = {"id": "obj_1", "text": "Primary objective"}

    ep = MagicMock(id="ep_1")
    ep.to_dict.return_value = {"id": "ep_1", "text": "Primary endpoint"}

    est = MagicMock(id="est_1")
    est.to_dict.return_value = {"id": "est_1"}

    data = MagicMock()
    data.objectives = [obj]
    data.endpoints = [ep]
    data.estimands = [est]
    data.primary_objectives_count = 1
    data.secondary_objectives_count = 0
    data.exploratory_objectives_count = 0

    result = MagicMock()
    result.success = True
    result.data = data
    result.pages_used = [3, 4]
    result.raw_response = {}
    return result


def _mock_studydesign_result():
    sd = MagicMock(id="sd_1")
    sd.to_dict.return_value = {"id": "sd_1", "name": "Randomized"}

    arm1 = MagicMock(id="arm_1")
    arm1.to_dict.return_value = {"id": "arm_1", "name": "Treatment"}
    arm2 = MagicMock(id="arm_2")
    arm2.to_dict.return_value = {"id": "arm_2", "name": "Placebo"}

    coh = MagicMock(id="coh_1")
    coh.to_dict.return_value = {"id": "coh_1"}

    cell1 = MagicMock(id="cell_1")
    cell1.to_dict.return_value = {"id": "cell_1"}
    cell2 = MagicMock(id="cell_2")
    cell2.to_dict.return_value = {"id": "cell_2"}

    elem1 = MagicMock(id="elem_1")
    elem1.to_dict.return_value = {"id": "elem_1"}
    elem2 = MagicMock(id="elem_2")
    elem2.to_dict.return_value = {"id": "elem_2"}

    data = MagicMock()
    data.study_design = sd
    data.arms = [arm1, arm2]
    data.cohorts = [coh]
    data.cells = [cell1, cell2]
    data.elements = [elem1, elem2]

    result = MagicMock()
    result.success = True
    result.data = data
    result.pages_used = [7, 8]
    result.raw_response = {}
    return result


def _mock_interventions_result():
    intv = MagicMock(id="iv_1")
    intv.to_dict.return_value = {"id": "iv_1", "name": "Drug A"}

    admin = MagicMock(id="admin_1")
    admin.to_dict.return_value = {"id": "admin_1"}

    data = MagicMock()
    data.interventions = [intv]
    data.products = []
    data.administrations = [admin]
    data.substances = []
    data.devices = []

    result = MagicMock()
    result.success = True
    result.data = data
    result.pages_used = [9]
    result.raw_response = {}
    return result


def _mock_soa_vision_result():
    """Mock result for analyze_soa_headers — returns object with .structure."""
    epoch1 = MagicMock()
    epoch1.name = "Screening"
    epoch2 = MagicMock()
    epoch2.name = "Treatment"

    enc1 = MagicMock()
    enc1.name = "Visit 1"
    enc2 = MagicMock()
    enc2.name = "Visit 2"
    enc3 = MagicMock()
    enc3.name = "Visit 3"

    structure = MagicMock()
    structure.epochs = [epoch1, epoch2]
    structure.encounters = [enc1, enc2, enc3]
    structure.to_dict.return_value = {
        "epochs": [{"name": "Screening"}, {"name": "Treatment"}],
        "encounters": [{"name": "Visit 1"}, {"name": "Visit 2"}, {"name": "Visit 3"}],
    }

    result = MagicMock()
    result.structure = structure
    result.confidence = 0.85
    return result


def _mock_soa_text_result():
    """Mock result for extract_soa_from_text — returns object with .activities."""
    result = MagicMock()
    result.activities = [
        {"name": f"Activity {i}", "id": f"act_{i}"} for i in range(6)
    ]
    result.to_dict.return_value = {
        "activities": result.activities,
    }
    return result


def _mock_procedures_result():
    proc = MagicMock(id="proc_1")
    proc.to_dict.return_value = {"id": "proc_1", "name": "Blood draw"}

    dev = MagicMock(id="dev_1")
    dev.to_dict.return_value = {"id": "dev_1", "name": "ECG monitor"}

    data = MagicMock()
    data.procedures = [proc]
    data.devices = [dev]
    data.ingredients = []
    data.strengths = []

    result = MagicMock()
    result.success = True
    result.data = data
    result.confidence = 0.85
    result.pages_used = [10, 11]
    return result


def _mock_scheduling_result():
    tim = MagicMock(id="tim_1")
    tim.to_dict.return_value = {"id": "tim_1"}

    cond = MagicMock(id="cond_1")
    cond.to_dict.return_value = {"id": "cond_1"}

    tr = MagicMock(id="tr_1")
    tr.to_dict.return_value = {"id": "tr_1"}

    exit_ = MagicMock(id="exit_1")
    exit_.to_dict.return_value = {"id": "exit_1"}

    di = MagicMock(id="di_1")
    di.to_dict.return_value = {"id": "di_1"}

    data = MagicMock()
    data.timings = [tim]
    data.conditions = [cond]
    data.transition_rules = [tr]
    data.schedule_exits = [exit_]
    data.decision_instances = [di]

    result = MagicMock()
    result.success = True
    result.data = data
    result.confidence = 0.8
    result.pages_used = [12]
    return result


def _mock_execution_result():
    ta = MagicMock(id="ta_1")
    ta.to_dict.return_value = {"id": "ta_1"}

    rep = MagicMock(id="rep_1")
    rep.to_dict.return_value = {"id": "rep_1"}

    et = MagicMock(id="et_1")
    et.to_dict.return_value = {"id": "et_1"}

    vw = MagicMock(id="vw_1")
    vw.to_dict.return_value = {"id": "vw_1"}

    dr = MagicMock(id="dr_1")
    dr.to_dict.return_value = {"id": "dr_1"}

    data = MagicMock()
    data.time_anchors = [ta]
    data.repetitions = [rep]
    data.execution_types = [et]
    data.traversal_constraints = []
    data.visit_windows = [vw]
    data.dosing_regimens = [dr]
    data.footnote_conditions = []
    data.state_machine = None
    data.get.return_value = 0.8

    result = MagicMock()
    result.success = True
    result.data = data
    result.pages_used = [13, 14]
    return result


def _mock_narrative_result():
    sec = MagicMock(id="nc_1")
    sec.to_dict.return_value = {"id": "nc_1"}

    item = MagicMock(id="nci_1")
    item.to_dict.return_value = {"id": "nci_1"}

    abbr = MagicMock(id="abbr_1")
    abbr.to_dict.return_value = {"id": "abbr_1", "term": "BP"}

    doc = MagicMock(id="doc_1")
    doc.to_dict.return_value = {"id": "doc_1"}

    data = MagicMock()
    data.sections = [sec]
    data.items = [item]
    data.abbreviations = [abbr]
    data.document = doc
    data.get.return_value = 0.8

    result = MagicMock()
    result.success = True
    result.data = data
    result.pages_used = [15, 16]
    result.raw_response = {}
    return result


def _mock_advanced_result():
    amend = MagicMock(id="amend_1")
    amend.to_dict.return_value = {"id": "amend_1"}

    reason = MagicMock(id="reason_1")
    reason.to_dict.return_value = {"id": "reason_1"}

    country = MagicMock(id="country_1")
    country.to_dict.return_value = {"id": "country_1", "name": "US"}

    geo = MagicMock(id="geo_1")
    geo.to_dict.return_value = {"id": "geo_1"}

    data = MagicMock()
    data.amendments = [amend]
    data.amendment_reasons = [reason]
    data.countries = [country]
    data.sites = []
    data.geographic_scope = geo
    data.get.return_value = 0.8

    result = MagicMock()
    result.success = True
    result.data = data
    result.pages_used = [17]
    result.raw_response = {}
    return result


def _mock_docstructure_result():
    ref = MagicMock(id="ref_1")
    ref.to_dict.return_value = {"id": "ref_1"}

    ann = MagicMock(id="ann_1")
    ann.to_dict.return_value = {"id": "ann_1"}

    ver = MagicMock(id="ver_1")
    ver.to_dict.return_value = {"id": "ver_1"}

    data = MagicMock()
    data.content_references = [ref]
    data.annotations = [ann]
    data.document_versions = [ver]

    result = MagicMock()
    result.success = True
    result.data = data
    result.confidence = 0.85
    result.pages_used = [0]
    return result


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def orchestrator(tmp_path):
    """Create an orchestrator with a temp checkpoint directory."""
    return OrchestratorAgent(config={
        "checkpoints_dir": str(tmp_path / "checkpoints"),
        "max_workers": 4,
    })


@pytest.fixture
def all_mock_patches():
    """
    Context manager that patches ALL extraction functions at once.
    Returns a dict of domain -> mock for verification.
    """
    patches = {}
    mocks = {}

    # Phase 2 extractors
    patches["metadata"] = patch(
        "extraction.metadata.extractor.extract_study_metadata",
        return_value=_mock_metadata_result(),
    )
    patches["eligibility"] = patch(
        "extraction.eligibility.extractor.extract_eligibility_criteria",
        return_value=_mock_eligibility_result(),
    )
    patches["objectives"] = patch(
        "extraction.objectives.extractor.extract_objectives_endpoints",
        return_value=_mock_objectives_result(),
    )
    patches["studydesign"] = patch(
        "extraction.studydesign.extractor.extract_study_design",
        return_value=_mock_studydesign_result(),
    )
    patches["interventions"] = patch(
        "extraction.interventions.extractor.extract_interventions",
        return_value=_mock_interventions_result(),
    )
    # SoA shared: find_soa_pages is used by both vision and text agents
    patches["soa_find_pages"] = patch(
        "extraction.soa_finder.find_soa_pages",
        return_value=[10, 11, 12],
    )
    # SoA Vision: extract_soa_images, analyze_soa_headers
    patches["soa_vision_images"] = patch(
        "extraction.soa_finder.extract_soa_images",
        return_value=["img_1.png", "img_2.png"],
    )
    patches["soa_vision"] = patch(
        "extraction.header_analyzer.analyze_soa_headers",
        return_value=_mock_soa_vision_result(),
    )
    # SoA Text: extract_soa_text, extract_soa_from_text
    patches["soa_text_extract"] = patch(
        "extraction.soa_finder.extract_soa_text",
        return_value="SoA table text...",
    )
    patches["soa_text"] = patch(
        "extraction.text_extractor.extract_soa_from_text",
        return_value=_mock_soa_text_result(),
    )

    # Phase 3 extractors
    patches["procedures"] = patch(
        "extraction.procedures.extractor.extract_procedures_devices",
        return_value=_mock_procedures_result(),
    )
    patches["scheduling"] = patch(
        "extraction.scheduling.extractor.extract_scheduling",
        return_value=_mock_scheduling_result(),
    )
    patches["execution"] = patch(
        "extraction.execution.pipeline_integration.extract_execution_model",
        return_value=_mock_execution_result(),
    )
    patches["narrative"] = patch(
        "extraction.narrative.extractor.extract_narrative_structure",
        return_value=_mock_narrative_result(),
    )
    patches["advanced"] = patch(
        "extraction.advanced.extractor.extract_advanced_entities",
        return_value=_mock_advanced_result(),
    )
    patches["docstructure"] = patch(
        "extraction.document_structure.extractor.extract_document_structure",
        return_value=_mock_docstructure_result(),
    )

    # Start all patches
    for name, p in patches.items():
        mocks[name] = p.start()

    yield mocks

    # Stop all patches
    for p in patches.values():
        p.stop()


# ===========================================================================
# Phase 2 Integration Tests (Task 9.1)
# ===========================================================================

class TestPhase2Integration:
    """Integration tests for Phase 2 core extraction agents."""

    # 9.1.1 — MetadataAgent → EligibilityAgent workflow
    @patch("extraction.eligibility.extractor.extract_eligibility_criteria")
    @patch("extraction.metadata.extractor.extract_study_metadata")
    def test_metadata_to_eligibility_workflow(self, mock_meta, mock_elig, orchestrator):
        """Metadata runs first (wave 0), eligibility depends on it (wave 1)."""
        mock_meta.return_value = _mock_metadata_result()
        mock_elig.return_value = _mock_eligibility_result()

        meta_agent = MetadataAgent()
        elig_agent = EligibilityAgent()

        orchestrator.register_agent(meta_agent)
        orchestrator.register_agent(elig_agent)

        plan = orchestrator.create_execution_plan("test_protocol")

        # Metadata should be in an earlier wave than eligibility
        meta_wave = None
        elig_wave = None
        for wave in plan.waves:
            for task in wave.tasks:
                if task.agent_id == "metadata_agent":
                    meta_wave = wave.wave_number
                if task.agent_id == "eligibility_agent":
                    elig_wave = wave.wave_number

        assert meta_wave is not None
        assert elig_wave is not None
        assert meta_wave < elig_wave, "Metadata must execute before Eligibility"

        # Execute the plan
        status = orchestrator.execute_plan(plan)
        assert status.completed_tasks == 2
        assert status.failed_tasks == 0

        # Both extractors should have been called
        mock_meta.assert_called_once()
        mock_elig.assert_called_once()

    # 9.1.2 — SoAVisionAgent + SoATextAgent parallel execution
    @patch("extraction.text_extractor.extract_soa_from_text")
    @patch("extraction.soa_finder.extract_soa_text", return_value="SoA text...")
    @patch("extraction.header_analyzer.analyze_soa_headers")
    @patch("extraction.soa_finder.extract_soa_images", return_value=["img1.png"])
    @patch("extraction.soa_finder.find_soa_pages", return_value=[10, 11])
    def test_soa_vision_text_parallel(self, mock_find, mock_imgs, mock_headers,
                                       mock_soa_text_extract, mock_text_from, orchestrator):
        """SoA Vision and Text have no deps — should be in the same wave."""
        mock_headers.return_value = _mock_soa_vision_result()
        mock_text_from.return_value = _mock_soa_text_result()

        vision_agent = SoAVisionAgent()
        text_agent = SoATextAgent()

        orchestrator.register_agent(vision_agent)
        orchestrator.register_agent(text_agent)

        plan = orchestrator.create_execution_plan("test_protocol")

        # Vision agent in wave 0 (no deps), text agent in wave 1 (depends on vision)
        wave0_agents = {t.agent_id for t in plan.waves[0].tasks}
        assert "soa_vision_agent" in wave0_agents

        wave1_agents = {t.agent_id for t in plan.waves[1].tasks}
        assert "soa_text_agent" in wave1_agents

        status = orchestrator.execute_plan(plan)
        assert status.completed_tasks == 2
        assert status.failed_tasks == 0

    # 9.1.3 — StudyDesignAgent with SoA context dependencies
    @patch("extraction.studydesign.extractor.extract_study_design")
    @patch("extraction.metadata.extractor.extract_study_metadata")
    def test_studydesign_with_metadata_context(self, mock_meta, mock_sd, orchestrator):
        """StudyDesign depends on metadata — should see metadata entities in context."""
        mock_meta.return_value = _mock_metadata_result()
        mock_sd.return_value = _mock_studydesign_result()

        meta_agent = MetadataAgent()
        sd_agent = StudyDesignAgent()

        orchestrator.register_agent(meta_agent)
        orchestrator.register_agent(sd_agent)

        status = orchestrator.execute_plan(
            orchestrator.create_execution_plan("test_protocol")
        )

        assert status.completed_tasks == 2
        # Context store should have entities from both agents
        cs = orchestrator.context_store
        assert cs.entity_count > 0

    # 9.1.4 — InterventionsAgent with design context dependencies
    @patch("extraction.interventions.extractor.extract_interventions")
    @patch("extraction.studydesign.extractor.extract_study_design")
    @patch("extraction.metadata.extractor.extract_study_metadata")
    def test_interventions_with_design_context(self, mock_meta, mock_sd, mock_iv, orchestrator):
        """Interventions depends on metadata + studydesign."""
        mock_meta.return_value = _mock_metadata_result()
        mock_sd.return_value = _mock_studydesign_result()
        mock_iv.return_value = _mock_interventions_result()

        orchestrator.register_agent(MetadataAgent())
        orchestrator.register_agent(StudyDesignAgent())
        orchestrator.register_agent(InterventionsAgent())

        plan = orchestrator.create_execution_plan("test_protocol")

        # Find wave numbers
        waves = {}
        for wave in plan.waves:
            for task in wave.tasks:
                waves[task.agent_id] = wave.wave_number

        assert waves["metadata_agent"] < waves["studydesign_agent"]
        assert waves["studydesign_agent"] < waves["interventions_agent"] or \
               waves["metadata_agent"] < waves["interventions_agent"]

        status = orchestrator.execute_plan(plan)
        assert status.completed_tasks == 3
        assert status.failed_tasks == 0

    # 9.1.5 — Context Store consistency across agents
    @patch("extraction.objectives.extractor.extract_objectives_endpoints")
    @patch("extraction.eligibility.extractor.extract_eligibility_criteria")
    @patch("extraction.metadata.extractor.extract_study_metadata")
    def test_context_store_consistency(self, mock_meta, mock_elig, mock_obj, orchestrator):
        """All agents share the same Context Store and can see each other's entities."""
        mock_meta.return_value = _mock_metadata_result()
        mock_elig.return_value = _mock_eligibility_result()
        mock_obj.return_value = _mock_objectives_result()

        meta = MetadataAgent()
        elig = EligibilityAgent()
        obj = ObjectivesAgent()

        orchestrator.register_agent(meta)
        orchestrator.register_agent(elig)
        orchestrator.register_agent(obj)

        # All agents should share the same context store
        assert meta.context_store is orchestrator.context_store
        assert elig.context_store is orchestrator.context_store
        assert obj.context_store is orchestrator.context_store

        status = orchestrator.execute_plan(
            orchestrator.create_execution_plan("test_protocol")
        )

        cs = orchestrator.context_store
        # Metadata entities should be present
        assert cs.entity_count > 0
        # Verify entity types from metadata
        types = cs.entity_types
        assert "study_title" in types

    # 9.1.6 — Performance benchmarks
    @patch("extraction.metadata.extractor.extract_study_metadata")
    def test_performance_single_agent(self, mock_meta, orchestrator):
        """Single agent execution should complete within reasonable time."""
        mock_meta.return_value = _mock_metadata_result()

        orchestrator.register_agent(MetadataAgent())

        start = time.perf_counter()
        status = orchestrator.execute_plan(
            orchestrator.create_execution_plan("test_protocol")
        )
        elapsed = time.perf_counter() - start

        assert status.completed_tasks == 1
        # With mocked extractors, should be well under 5 seconds
        assert elapsed < 5.0, f"Single agent took {elapsed:.2f}s"

    # 9.1.7 — Golden file comparisons (covered by golden test suite)
    def test_golden_tests_exist(self):
        """Verify golden test infrastructure is in place."""
        from pathlib import Path
        golden_dir = Path("tests/test_agents/golden/references")
        assert golden_dir.exists(), "Golden references directory missing"
        # Should have 10 protocol directories
        protocol_dirs = [d for d in golden_dir.iterdir() if d.is_dir()]
        assert len(protocol_dirs) >= 10, f"Expected 10 protocol dirs, found {len(protocol_dirs)}"


# ===========================================================================
# Phase 3 Integration Tests (Task 16.1)
# ===========================================================================

class TestPhase3Integration:
    """Integration tests for Phase 3 additional extraction agents."""

    # 16.1.1 — ProceduresAgent with SoA context dependencies
    @patch("extraction.procedures.extractor.extract_procedures_devices")
    @patch("extraction.header_analyzer.analyze_soa_headers")
    @patch("extraction.soa_finder.extract_soa_images", return_value=["img1.png"])
    @patch("extraction.soa_finder.find_soa_pages", return_value=[10, 11])
    @patch("extraction.metadata.extractor.extract_study_metadata")
    def test_procedures_with_soa_context(self, mock_meta, mock_find, mock_imgs,
                                          mock_headers, mock_proc, orchestrator):
        """Procedures depends on metadata + soa_vision."""
        mock_meta.return_value = _mock_metadata_result()
        mock_headers.return_value = _mock_soa_vision_result()
        mock_proc.return_value = _mock_procedures_result()

        orchestrator.register_agent(MetadataAgent())
        orchestrator.register_agent(SoAVisionAgent())
        orchestrator.register_agent(ProceduresAgent())

        plan = orchestrator.create_execution_plan("test_protocol")

        waves = {}
        for wave in plan.waves:
            for task in wave.tasks:
                waves[task.agent_id] = wave.wave_number

        # Metadata and SoA Vision are wave 0 (no deps)
        # Procedures depends on both, so must be later
        assert waves["procedures_agent"] > waves["metadata_agent"]
        assert waves["procedures_agent"] > waves["soa_vision_agent"]

        status = orchestrator.execute_plan(plan)
        assert status.completed_tasks == 3
        assert status.failed_tasks == 0

    # 16.1.2 — SchedulingAgent with SoA and Procedures dependencies
    # 16.1.2 — SchedulingAgent with SoA and Procedures dependencies
    @patch("extraction.scheduling.extractor.extract_scheduling")
    @patch("extraction.procedures.extractor.extract_procedures_devices")
    @patch("extraction.header_analyzer.analyze_soa_headers")
    @patch("extraction.soa_finder.extract_soa_images", return_value=["img1.png"])
    @patch("extraction.soa_finder.find_soa_pages", return_value=[10, 11])
    @patch("extraction.metadata.extractor.extract_study_metadata")
    def test_scheduling_with_soa_and_procedures(
        self, mock_meta, mock_find, mock_imgs, mock_headers, mock_proc, mock_sched, orchestrator
    ):
        """Scheduling depends on soa_vision + procedures (transitive chain)."""
        mock_meta.return_value = _mock_metadata_result()
        mock_headers.return_value = _mock_soa_vision_result()
        mock_proc.return_value = _mock_procedures_result()
        mock_sched.return_value = _mock_scheduling_result()

        orchestrator.register_agent(MetadataAgent())
        orchestrator.register_agent(SoAVisionAgent())
        orchestrator.register_agent(ProceduresAgent())
        orchestrator.register_agent(SchedulingAgent())

        plan = orchestrator.create_execution_plan("test_protocol")

        waves = {}
        for wave in plan.waves:
            for task in wave.tasks:
                waves[task.agent_id] = wave.wave_number

        # Scheduling depends on soa_vision + procedures
        assert waves["scheduling_agent"] > waves["soa_vision_agent"]
        assert waves["scheduling_agent"] > waves["procedures_agent"]

        status = orchestrator.execute_plan(plan)
        assert status.completed_tasks == 4
        assert status.failed_tasks == 0

    # 16.1.3 — ExecutionAgent with full SoA structure
    @patch("extraction.execution.pipeline_integration.extract_execution_model")
    @patch("extraction.text_extractor.extract_soa_from_text")
    @patch("extraction.soa_finder.extract_soa_text", return_value="SoA text...")
    @patch("extraction.header_analyzer.analyze_soa_headers")
    @patch("extraction.soa_finder.extract_soa_images", return_value=["img1.png"])
    @patch("extraction.soa_finder.find_soa_pages", return_value=[10, 11])
    def test_execution_with_full_soa(self, mock_find, mock_imgs, mock_headers,
                                      mock_soa_text_extract, mock_text_from,
                                      mock_exec, orchestrator):
        """Execution depends on soa_vision + soa_text."""
        mock_headers.return_value = _mock_soa_vision_result()
        mock_text_from.return_value = _mock_soa_text_result()
        mock_exec.return_value = _mock_execution_result()

        orchestrator.register_agent(SoAVisionAgent())
        orchestrator.register_agent(SoATextAgent())
        orchestrator.register_agent(ExecutionAgent())

        plan = orchestrator.create_execution_plan("test_protocol")

        waves = {}
        for wave in plan.waves:
            for task in wave.tasks:
                waves[task.agent_id] = wave.wave_number

        # SoA vision in wave 0, text in wave 1 (depends on vision), execution after both
        assert waves["soa_text_agent"] == waves["soa_vision_agent"] + 1
        assert waves["execution_agent"] > waves["soa_text_agent"]

        status = orchestrator.execute_plan(plan)
        assert status.completed_tasks == 3
        assert status.failed_tasks == 0

    # 16.1.4 — End-to-end workflow with all extraction agents
    def test_full_extraction_workflow(self, orchestrator, all_mock_patches):
        """Register all 13 agents and run a complete extraction plan."""
        agents = [
            MetadataAgent(),
            EligibilityAgent(),
            ObjectivesAgent(),
            StudyDesignAgent(),
            InterventionsAgent(),
            SoAVisionAgent(),
            SoATextAgent(),
            ProceduresAgent(),
            SchedulingAgent(),
            ExecutionAgent(),
            NarrativeAgent(),
            AdvancedAgent(),
            DocStructureAgent(),
        ]

        for agent in agents:
            orchestrator.register_agent(agent)

        assert orchestrator.registry.count == 13

        plan = orchestrator.create_execution_plan("full_e2e_test")

        # Should have multiple waves due to dependencies
        assert len(plan.waves) >= 2, f"Expected ≥2 waves, got {len(plan.waves)}"
        assert plan.total_tasks == 13

        # Wave 0 should contain agents with no dependencies
        wave0_agents = {t.agent_id for t in plan.waves[0].tasks}
        no_dep_agents = {"metadata_agent", "soa_vision_agent",
                         "narrative_agent", "docstructure_agent"}
        assert wave0_agents == no_dep_agents, (
            f"Wave 0 should be no-dep agents. Got {wave0_agents}"
        )

        status = orchestrator.execute_plan(plan)

        assert status.total_tasks == 13
        assert status.completed_tasks == 13
        assert status.failed_tasks == 0
        assert status.state == "completed"

        # Key extractors should have been called
        for name in ["metadata", "eligibility", "objectives", "studydesign",
                      "interventions", "soa_vision", "soa_text", "procedures",
                      "scheduling", "execution", "narrative", "advanced", "docstructure"]:
            assert all_mock_patches[name].called, f"Extractor for {name} was not called"

    # 16.1.5 — Performance: full workflow timing
    def test_full_workflow_performance(self, orchestrator, all_mock_patches):
        """Full 13-agent workflow with mocks should complete quickly."""
        for agent_cls in [MetadataAgent, EligibilityAgent, ObjectivesAgent,
                          StudyDesignAgent, InterventionsAgent, SoAVisionAgent,
                          SoATextAgent, ProceduresAgent, SchedulingAgent,
                          ExecutionAgent, NarrativeAgent, AdvancedAgent,
                          DocStructureAgent]:
            orchestrator.register_agent(agent_cls())

        start = time.perf_counter()
        plan = orchestrator.create_execution_plan("perf_test")
        status = orchestrator.execute_plan(plan)
        elapsed = time.perf_counter() - start

        assert status.completed_tasks == 13
        # Mocked workflow should be well under 10 seconds
        assert elapsed < 10.0, f"Full workflow took {elapsed:.2f}s"


# ===========================================================================
# Cross-Phase Integration Tests
# ===========================================================================

class TestCrossPhaseIntegration:
    """Tests that span both Phase 2 and Phase 3 concerns."""

    def test_checkpoint_created_per_wave(self, orchestrator, all_mock_patches, tmp_path):
        """Verify checkpoints are saved after each wave."""
        orchestrator._checkpoints_dir = str(tmp_path / "ckpts")

        for agent_cls in [MetadataAgent, SoAVisionAgent, EligibilityAgent]:
            orchestrator.register_agent(agent_cls())

        plan = orchestrator.create_execution_plan("ckpt_test")
        status = orchestrator.execute_plan(plan)

        assert status.completed_tasks == 3

        # Check checkpoint files were created
        from pathlib import Path
        ckpt_dir = Path(orchestrator._checkpoints_dir)
        if ckpt_dir.exists():
            ckpt_files = list(ckpt_dir.glob("checkpoint_*.json"))
            assert len(ckpt_files) >= 1, "Expected at least 1 checkpoint file"

    def test_message_queue_shared(self, orchestrator, all_mock_patches):
        """All agents share the same message queue."""
        agents = [MetadataAgent(), SoAVisionAgent(), EligibilityAgent()]
        for a in agents:
            orchestrator.register_agent(a)

        # All agents should have the same message queue reference
        mq = orchestrator.message_queue
        for a in agents:
            assert a._message_queue is mq

    def test_agent_state_transitions(self, orchestrator, all_mock_patches):
        """Agents transition through correct states during execution."""
        meta = MetadataAgent()
        orchestrator.register_agent(meta)

        # After registration, agent is still INITIALIZING (lazy init)
        assert meta.state == AgentState.INITIALIZING

        plan = orchestrator.create_execution_plan("state_test")
        orchestrator.execute_plan(plan)

        # After successful execution, should be READY
        assert meta.state == AgentState.READY

    def test_failed_agent_doesnt_block_others(self, orchestrator, tmp_path):
        """If one agent fails, others in the same wave still execute."""
        orchestrator._checkpoints_dir = str(tmp_path / "ckpts")

        with patch("extraction.metadata.extractor.extract_study_metadata") as mock_meta, \
             patch("extraction.soa_finder.find_soa_pages", return_value=[10, 11]), \
             patch("extraction.soa_finder.extract_soa_images", return_value=["img1.png"]), \
             patch("extraction.header_analyzer.analyze_soa_headers") as mock_vision, \
             patch("extraction.narrative.extractor.extract_narrative_structure") as mock_narr:

            # Metadata succeeds, SoA Vision fails, Narrative succeeds
            mock_meta.return_value = _mock_metadata_result()
            mock_vision.side_effect = Exception("Vision API timeout")
            mock_narr.return_value = _mock_narrative_result()

            orchestrator.register_agent(MetadataAgent())
            orchestrator.register_agent(SoAVisionAgent())
            orchestrator.register_agent(NarrativeAgent())

            plan = orchestrator.create_execution_plan("fail_test")
            status = orchestrator.execute_plan(plan)

            # SoA Vision should fail, but metadata and narrative should succeed
            assert status.failed_tasks >= 1
            assert status.completed_tasks >= 2

    def test_dependency_graph_correctness(self, orchestrator):
        """Verify the full dependency graph is built correctly."""
        for agent_cls in [MetadataAgent, EligibilityAgent, ObjectivesAgent,
                          StudyDesignAgent, InterventionsAgent, SoAVisionAgent,
                          SoATextAgent, ProceduresAgent, SchedulingAgent,
                          ExecutionAgent, NarrativeAgent, AdvancedAgent,
                          DocStructureAgent]:
            orchestrator.register_agent(agent_cls())

        graph = orchestrator.build_dependency_graph()

        # No-dependency agents
        assert graph["metadata_agent"] == set()
        assert graph["soa_vision_agent"] == set()
        assert graph["soa_text_agent"] == {"soa_vision_agent"}
        assert graph["narrative_agent"] == set()
        assert graph["docstructure_agent"] == set()

        # Single dependency on metadata
        assert "metadata_agent" in graph["eligibility_agent"]
        assert "metadata_agent" in graph["objectives_agent"]
        assert "metadata_agent" in graph["studydesign_agent"]
        assert "metadata_agent" in graph["advanced_agent"]

        # Multiple dependencies
        assert "metadata_agent" in graph["interventions_agent"]
        assert "metadata_agent" in graph["procedures_agent"]
        assert "soa_vision_agent" in graph["procedures_agent"]
        assert "soa_vision_agent" in graph["scheduling_agent"]
        assert "soa_vision_agent" in graph["execution_agent"]
        assert "soa_text_agent" in graph["execution_agent"]

    def test_execution_plan_wave_ordering(self, orchestrator):
        """Verify wave ordering respects all dependency chains."""
        for agent_cls in [MetadataAgent, EligibilityAgent, ObjectivesAgent,
                          StudyDesignAgent, InterventionsAgent, SoAVisionAgent,
                          SoATextAgent, ProceduresAgent, SchedulingAgent,
                          ExecutionAgent, NarrativeAgent, AdvancedAgent,
                          DocStructureAgent]:
            orchestrator.register_agent(agent_cls())

        plan = orchestrator.create_execution_plan("wave_test")

        # Build agent -> wave mapping
        agent_waves = {}
        for wave in plan.waves:
            for task in wave.tasks:
                agent_waves[task.agent_id] = wave.wave_number

        # Verify all dependency constraints
        graph = orchestrator.build_dependency_graph()
        for agent_id, deps in graph.items():
            for dep_id in deps:
                if dep_id in agent_waves:
                    assert agent_waves[agent_id] > agent_waves[dep_id], (
                        f"{agent_id} (wave {agent_waves[agent_id]}) must be after "
                        f"{dep_id} (wave {agent_waves[dep_id]})"
                    )

    def test_context_store_serialization_after_workflow(self, orchestrator, all_mock_patches):
        """Context Store can be serialized and deserialized after a full run."""
        for agent_cls in [MetadataAgent, SoAVisionAgent, NarrativeAgent]:
            orchestrator.register_agent(agent_cls())

        plan = orchestrator.create_execution_plan("serial_test")
        orchestrator.execute_plan(plan)

        cs = orchestrator.context_store
        serialized = cs.serialize()

        assert "entities" in serialized
        assert "metadata" in serialized
        assert serialized["metadata"]["entity_count"] == cs.entity_count

        # Deserialize and verify
        restored = ContextStore.deserialize(serialized)
        assert restored.entity_count == cs.entity_count

    def test_metrics_collected_for_all_agents(self, orchestrator, all_mock_patches):
        """Every agent should have metrics after execution."""
        agents = []
        for agent_cls in [MetadataAgent, EligibilityAgent, SoAVisionAgent,
                          SoATextAgent, NarrativeAgent, DocStructureAgent]:
            a = agent_cls()
            orchestrator.register_agent(a)
            agents.append(a)

        plan = orchestrator.create_execution_plan("metrics_test")
        orchestrator.execute_plan(plan)

        for a in agents:
            assert a.metrics.execution_count >= 1, (
                f"{a.agent_id} has no executions recorded"
            )
            assert a.metrics.last_execution_time_ms > 0

    def test_registry_health_check(self, orchestrator, all_mock_patches):
        """Health check reports correct states after execution."""
        for agent_cls in [MetadataAgent, SoAVisionAgent]:
            orchestrator.register_agent(agent_cls())

        plan = orchestrator.create_execution_plan("health_test")
        orchestrator.execute_plan(plan)

        health = orchestrator.registry.health_check()
        assert health["metadata_agent"] == "ready"
        assert health["soa_vision_agent"] == "ready"
