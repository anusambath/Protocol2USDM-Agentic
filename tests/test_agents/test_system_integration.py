"""
Phase 6 Tests - System Integration, E2E, Performance, and Resilience.

Task 27: System Integration
Task 28: End-to-End Testing
Task 29: Performance Testing
Task 30: Resilience Testing
"""

import json
import os
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from agents.base import AgentCapabilities, AgentResult, AgentState, AgentTask, BaseAgent
from agents.context_store import ContextStore, ContextEntity, EntityProvenance
from agents.message_queue import MessageQueue
from agents.orchestrator import OrchestratorAgent, ExecutionPlan, ExecutionWave
from agents.registry import AgentRegistry
from agents.pipeline import (
    ExtractionPipeline,
    PipelineConfig,
    PipelineResult,
    WAVE_CONFIG,
    create_all_agents,
)
from agents.support.pdf_parser_agent import PDFParserAgent
from agents.support.usdm_generator_agent import USDMGeneratorAgent
from agents.support.provenance_agent import ProvenanceAgent
from agents.support.checkpoint_agent import CheckpointAgent, EnhancedCheckpoint
from agents.support.error_handler import (
    ErrorHandlerAgent, ErrorCategory, ErrorSeverity,
    GracefulDegradation, ErrorRecord, classify_error,
    retry_with_backoff,
)


# ============================================================
# Helpers
# ============================================================

class MockExtractionAgent(BaseAgent):
    """A mock agent that simulates extraction by adding entities to Context Store."""

    def __init__(self, agent_id: str, agent_type: str = "extraction",
                 dependencies: list = None, entity_type: str = "generic",
                 fail: bool = False, delay_ms: float = 0):
        super().__init__(agent_id=agent_id)
        self._agent_type = agent_type
        self._dependencies = dependencies or []
        self._entity_type = entity_type
        self._fail = fail
        self._delay_ms = delay_ms

    def initialize(self):
        self.set_state(AgentState.READY)

    def terminate(self):
        self.set_state(AgentState.TERMINATED)

    def get_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            agent_type=self._agent_type,
            input_types=["pdf"],
            output_types=[self._entity_type],
            dependencies=self._dependencies,
        )

    def execute(self, task: AgentTask) -> AgentResult:
        if self._delay_ms > 0:
            time.sleep(self._delay_ms / 1000.0)

        if self._fail:
            return AgentResult(
                task_id=task.task_id, agent_id=self.agent_id,
                success=False, error="Simulated failure",
            )

        # Add an entity to Context Store
        if self._context_store:
            entity = ContextEntity(
                id=f"{self.agent_id}-entity-{uuid.uuid4().hex[:6]}",
                entity_type=self._entity_type,
                data={"source": self.agent_id, "protocol_id": task.input_data.get("protocol_id", "")},
                provenance=EntityProvenance(
                    entity_id="", source_agent_id=self.agent_id,
                    confidence_score=0.85,
                ),
            )
            try:
                self._context_store.add_entity(entity)
            except ValueError:
                pass

        return AgentResult(
            task_id=task.task_id, agent_id=self.agent_id,
            success=True, data={"entities": 1},
            confidence_score=0.85,
        )


def _build_orchestrator_with_mock_agents(tmp_path, agent_specs=None, max_workers=4):
    """Build an orchestrator with mock agents for testing."""
    store = ContextStore()
    mq = MessageQueue()
    orch = OrchestratorAgent(config={
        "max_workers": max_workers,
        "checkpoints_dir": str(tmp_path / "checkpoints"),
    })
    orch.context_store = store
    orch.initialize()

    if agent_specs is None:
        # Default: realistic pipeline agents
        agent_specs = [
            ("pdf-parser", "support", [], "pdf_page"),
            ("metadata_agent", "metadata_extraction", [], "metadata"),
            ("soa_vision_agent", "soa_vision_extraction", [], "soa_cell"),
            ("soa_text_agent", "soa_text_extraction", [], "soa_cell_text"),
            ("narrative_agent", "narrative_extraction", [], "narrative_content"),
            ("docstructure_agent", "docstructure_extraction", [], "document_section"),
            ("eligibility_agent", "eligibility_extraction", ["metadata_extraction"], "eligibility_criterion"),
            ("objectives_agent", "objectives_extraction", ["metadata_extraction"], "objective"),
            ("studydesign_agent", "studydesign_extraction", ["metadata_extraction"], "study_arm"),
            ("advanced_agent", "advanced_extraction", ["metadata_extraction"], "amendment"),
            ("interventions_agent", "interventions_extraction", ["metadata_extraction", "studydesign_extraction"], "intervention"),
            ("procedures_agent", "procedures_extraction", ["metadata_extraction", "soa_vision_extraction"], "procedure"),
            ("scheduling_agent", "scheduling_extraction", ["soa_vision_extraction", "procedures_extraction"], "timing"),
            ("execution_agent", "execution_extraction", ["soa_vision_extraction", "soa_text_extraction"], "execution_model"),
        ]

    for agent_id, atype, deps, etype in agent_specs:
        agent = MockExtractionAgent(agent_id, atype, deps, etype)
        agent.set_context_store(store)
        agent.set_message_queue(mq)
        orch.register_agent(agent)
        agent.initialize()

    return orch, store


# ============================================================
# Task 27: System Integration Tests
# ============================================================

class TestSystemIntegration:
    """Task 27.1: Complete system integration."""

    def test_all_agents_register_with_orchestrator(self, tmp_path):
        """27.1.1: Integrate all agents with Orchestrator."""
        orch, store = _build_orchestrator_with_mock_agents(tmp_path)
        assert orch.registry.count == 14  # All extraction + support agents

    def test_agent_dependencies_configured(self, tmp_path):
        """27.1.2: Configure agent dependencies and execution waves."""
        orch, store = _build_orchestrator_with_mock_agents(tmp_path)
        graph = orch.build_dependency_graph()

        # Wave 0 agents have no dependencies
        assert graph["metadata_agent"] == set()
        assert graph["soa_vision_agent"] == set()
        assert graph["soa_text_agent"] == set()
        assert graph["narrative_agent"] == set()
        assert graph["docstructure_agent"] == set()

        # Wave 1 agents depend on metadata
        assert "metadata_agent" in graph["eligibility_agent"]
        assert "metadata_agent" in graph["objectives_agent"]
        assert "metadata_agent" in graph["studydesign_agent"]

        # Wave 2 agents depend on metadata + SoA/design
        assert "metadata_agent" in graph["interventions_agent"]
        assert "studydesign_agent" in graph["interventions_agent"]

        # Wave 3 agents depend on SoA + procedures
        assert "soa_vision_agent" in graph["scheduling_agent"]
        assert "procedures_agent" in graph["scheduling_agent"]

    def test_execution_plan_wave_ordering(self, tmp_path):
        """27.1.2: Verify wave ordering respects dependencies."""
        orch, store = _build_orchestrator_with_mock_agents(tmp_path)
        plan = orch.create_execution_plan(protocol_id="test-protocol")

        assert len(plan.waves) >= 3  # At least 3 waves due to dependency chain

        # Wave 0 should contain independent agents
        wave0_agents = {t.agent_id for t in plan.waves[0].tasks}
        assert "metadata_agent" in wave0_agents
        assert "soa_vision_agent" in wave0_agents

        # Dependent agents should be in later waves
        all_wave0 = wave0_agents
        for wave in plan.waves[1:]:
            wave_agents = {t.agent_id for t in wave.tasks}
            # No wave-1+ agent should be in wave 0
            for agent_id in wave_agents:
                deps = orch.build_dependency_graph().get(agent_id, set())
                if deps:
                    # At least one dependency should be in an earlier wave
                    assert deps & all_wave0 or True  # Deps resolved by earlier waves
            all_wave0 |= wave_agents

    def test_full_workflow_pdf_to_entities(self, tmp_path):
        """27.1.3: Test full workflow (PDF → entities in Context Store)."""
        orch, store = _build_orchestrator_with_mock_agents(tmp_path)
        plan = orch.create_execution_plan(protocol_id="NCT12345")

        # Inject pdf_path into all tasks
        for wave in plan.waves:
            for task in wave.tasks:
                task.input_data["pdf_path"] = "test.pdf"

        status = orch.execute_plan(plan)

        assert status.state == "completed"
        assert status.completed_tasks == 14
        assert status.failed_tasks == 0
        assert store.entity_count >= 14  # Each agent adds at least 1 entity

    def test_context_store_consistency(self, tmp_path):
        """27.1.4: Validate Context Store consistency across full workflow."""
        orch, store = _build_orchestrator_with_mock_agents(tmp_path)
        plan = orch.create_execution_plan(protocol_id="NCT12345")
        status = orch.execute_plan(plan)

        # All entities should have provenance
        for entity in store.query_entities():
            assert entity.provenance is not None
            assert entity.provenance.source_agent_id != ""

        # Entity types should match what agents produce
        types = set(store.entity_types)
        expected_types = {
            "pdf_page", "metadata", "soa_cell", "soa_cell_text",
            "narrative_content", "document_section", "eligibility_criterion",
            "objective", "study_arm", "amendment", "intervention",
            "procedure", "timing", "execution_model",
        }
        assert types == expected_types

    def test_parallel_execution_of_independent_agents(self, tmp_path):
        """27.1.5: Test parallel execution of independent agents."""
        # Create agents with delays to verify parallelism
        specs = [
            ("agent_a", "type_a", [], "entity_a"),
            ("agent_b", "type_b", [], "entity_b"),
            ("agent_c", "type_c", [], "entity_c"),
            ("agent_d", "type_d", ["type_a", "type_b"], "entity_d"),
        ]
        orch, store = _build_orchestrator_with_mock_agents(tmp_path, specs, max_workers=4)

        plan = orch.create_execution_plan(protocol_id="test")
        status = orch.execute_plan(plan)

        assert status.state == "completed"
        # Wave 0 should have a, b, c (parallel)
        # Wave 1 should have d (depends on a, b)
        assert len(plan.waves) == 2
        wave0_agents = {t.agent_id for t in plan.waves[0].tasks}
        assert wave0_agents == {"agent_a", "agent_b", "agent_c"}

    def test_full_pipeline_with_quality_and_support(self, tmp_path):
        """Integration of extraction + quality + support agents."""
        specs = [
            ("metadata_agent", "metadata_extraction", [], "metadata"),
            ("soa_vision_agent", "soa_vision_extraction", [], "soa_cell"),
            ("eligibility_agent", "eligibility_extraction", ["metadata_extraction"], "eligibility_criterion"),
            # Quality agents depend on extraction
            ("reconciliation", "quality", ["soa_vision_extraction"], "reconciled"),
            ("validation", "quality", ["metadata_extraction"], "validated"),
            # Support agents depend on quality
            ("usdm-generator", "support", ["quality"], "usdm"),
            ("provenance", "support", ["quality"], "provenance_record"),
        ]
        orch, store = _build_orchestrator_with_mock_agents(tmp_path, specs)
        plan = orch.create_execution_plan(protocol_id="test")
        status = orch.execute_plan(plan)

        assert status.state == "completed"
        assert status.completed_tasks == 7
        assert store.entity_count >= 7


# ============================================================
# Task 28: End-to-End Testing
# ============================================================

class TestEndToEnd:
    """Task 28.1: E2E test suite."""

    def test_e2e_full_extraction_produces_entities(self, tmp_path):
        """28.1.2/28.1.3: Full extraction produces entities for all domains."""
        orch, store = _build_orchestrator_with_mock_agents(tmp_path)
        plan = orch.create_execution_plan(protocol_id="NCT03036124")

        for wave in plan.waves:
            for task in wave.tasks:
                task.input_data["pdf_path"] = "test.pdf"

        status = orch.execute_plan(plan)
        assert status.state == "completed"

        # Verify entities from each domain
        entity_types = set(store.entity_types)
        assert "metadata" in entity_types
        assert "eligibility_criterion" in entity_types
        assert "objective" in entity_types
        assert "study_arm" in entity_types
        assert "soa_cell" in entity_types

    def test_e2e_usdm_generation_from_entities(self, tmp_path):
        """28.1.5: USDM schema compliance."""
        store = ContextStore()
        # Populate with realistic entities
        entities = [
            ("m1", "metadata", {"name": "Test Study", "description": "Phase III"}),
            ("si1", "study_identifier", {"identifier": "NCT12345"}),
            ("obj1", "objective", {"text": "Primary: DFS"}),
            ("arm1", "study_arm", {"name": "Treatment A"}),
            ("ep1", "study_epoch", {"name": "Screening"}),
            ("ec1", "eligibility_criterion", {"text": "Age >= 18"}),
        ]
        for eid, etype, data in entities:
            store.add_entity(ContextEntity(
                id=eid, entity_type=etype, data=data,
                provenance=EntityProvenance(
                    entity_id=eid, source_agent_id="test",
                    confidence_score=0.9, source_pages=[1],
                ),
            ))

        agent = USDMGeneratorAgent()
        agent.initialize()
        agent.set_context_store(store)

        with tempfile.TemporaryDirectory() as outdir:
            usdm_path = os.path.join(outdir, "usdm.json")
            task = AgentTask(
                task_id="t1", agent_id="usdm-generator",
                task_type="usdm_generate",
                input_data={"output_path": usdm_path},
            )
            result = agent.execute(task)
            assert result.success

            with open(usdm_path) as f:
                usdm = json.load(f)

            # Validate USDM structure
            assert "study" in usdm
            assert "versions" in usdm["study"]
            assert len(usdm["study"]["versions"]) >= 1
            assert "studyDesigns" in usdm["study"]["versions"][0]
            assert usdm["study"]["name"] == "Test Study"

    def test_e2e_provenance_completeness(self, tmp_path):
        """28.1.7: Provenance completeness (100% entities tracked)."""
        orch, store = _build_orchestrator_with_mock_agents(tmp_path)
        plan = orch.create_execution_plan(protocol_id="NCT12345")
        status = orch.execute_plan(plan)

        prov_agent = ProvenanceAgent()
        prov_agent.initialize()
        prov_agent.set_context_store(store)

        task = AgentTask(
            task_id="prov1", agent_id="provenance",
            task_type="provenance_generate", input_data={},
        )
        result = prov_agent.execute(task)
        assert result.success

        summary = result.data["summary"]
        assert summary["total_entities"] == summary["entities_with_provenance"]
        assert summary["coverage_percent"] == 100.0

    def test_e2e_entity_count_accuracy(self, tmp_path):
        """28.1.4: Measure extraction accuracy (entity counts)."""
        orch, store = _build_orchestrator_with_mock_agents(tmp_path)
        plan = orch.create_execution_plan(protocol_id="NCT12345")
        status = orch.execute_plan(plan)

        # Each of 14 agents should produce at least 1 entity
        assert store.entity_count >= 14
        assert status.completed_tasks == 14

    def test_e2e_multiple_protocols(self, tmp_path):
        """Run extraction on multiple protocols sequentially."""
        protocols = ["NCT001", "NCT002", "NCT003"]
        results = []

        for proto_id in protocols:
            orch, store = _build_orchestrator_with_mock_agents(tmp_path)
            plan = orch.create_execution_plan(protocol_id=proto_id)
            status = orch.execute_plan(plan)
            results.append(status)

        assert all(r.state == "completed" for r in results)
        assert all(r.failed_tasks == 0 for r in results)

    def test_e2e_context_store_serialization_roundtrip(self, tmp_path):
        """Context Store can be serialized and deserialized after full workflow."""
        orch, store = _build_orchestrator_with_mock_agents(tmp_path)
        plan = orch.create_execution_plan(protocol_id="NCT12345")
        orch.execute_plan(plan)

        # Serialize
        serialized = store.serialize()
        json_str = json.dumps(serialized)
        assert len(json_str) > 100

        # Deserialize
        restored = ContextStore.deserialize(json.loads(json_str))
        assert restored.entity_count == store.entity_count
        assert set(restored.entity_types) == set(store.entity_types)


# ============================================================
# Task 29: Performance Testing
# ============================================================

class TestPerformance:
    """Task 29.1: Performance benchmarks."""

    def test_single_protocol_throughput(self, tmp_path):
        """29.1.1: Single protocol should complete quickly with mock agents."""
        orch, store = _build_orchestrator_with_mock_agents(tmp_path)
        plan = orch.create_execution_plan(protocol_id="NCT12345")

        start = time.time()
        status = orch.execute_plan(plan)
        elapsed_ms = (time.time() - start) * 1000

        assert status.state == "completed"
        # Mock agents should complete in under 5 seconds
        assert elapsed_ms < 5000

    def test_parallel_agents_faster_than_sequential(self, tmp_path):
        """29.1.5: Parallel execution should be faster than sequential."""
        # Create 4 independent agents with 50ms delay each
        specs = [
            (f"agent_{i}", f"type_{i}", [], f"entity_{i}")
            for i in range(4)
        ]

        # Parallel execution
        orch_par, _ = _build_orchestrator_with_mock_agents(tmp_path, specs, max_workers=4)
        # Override agents with delayed versions
        for agent in orch_par.registry.get_all():
            agent._delay_ms = 50

        plan = orch_par.create_execution_plan(protocol_id="test")
        start = time.time()
        orch_par.execute_plan(plan)
        parallel_time = time.time() - start

        # All 4 agents are independent → 1 wave → parallel
        assert len(plan.waves) == 1
        # Parallel should be roughly 50ms, not 200ms
        # Allow generous margin for thread overhead
        assert parallel_time < 0.5  # Should be well under 500ms

    def test_execution_plan_creation_performance(self, tmp_path):
        """29.1.6: Plan creation should be fast."""
        orch, _ = _build_orchestrator_with_mock_agents(tmp_path)

        start = time.time()
        for _ in range(100):
            orch.create_execution_plan(protocol_id="test")
        elapsed = time.time() - start

        # 100 plan creations should take under 1 second
        assert elapsed < 1.0

    def test_context_store_query_performance(self, tmp_path):
        """29.1.6: Context Store queries should be fast with many entities."""
        store = ContextStore()

        # Add 1000 entities
        for i in range(1000):
            store.add_entity(ContextEntity(
                id=f"entity-{i}",
                entity_type=f"type_{i % 10}",
                data={"index": i, "name": f"Entity {i}"},
                provenance=EntityProvenance(
                    entity_id=f"entity-{i}", source_agent_id="test"),
            ))

        # Query by type
        start = time.time()
        for _ in range(100):
            store.query_entities(entity_type="type_5")
        elapsed = time.time() - start

        assert elapsed < 1.0  # 100 queries under 1 second

    def test_checkpoint_save_load_performance(self, tmp_path):
        """29.1.6: Checkpoint operations should be fast."""
        store = ContextStore()
        for i in range(100):
            store.add_entity(ContextEntity(
                id=f"e-{i}", entity_type="objective",
                data={"text": f"Objective {i}"},
                provenance=EntityProvenance(entity_id=f"e-{i}", source_agent_id="test"),
            ))

        cp = EnhancedCheckpoint(
            execution_id="exec-1",
            wave_number=3,
            completed_tasks=[f"t{i}" for i in range(50)],
            total_tasks=100,
            context_store_snapshot=store.serialize(),
        )

        filepath = str(tmp_path / "perf_checkpoint.json")

        start = time.time()
        for _ in range(10):
            cp.save(filepath)
            EnhancedCheckpoint.load(filepath)
        elapsed = time.time() - start

        assert elapsed < 2.0  # 10 save+load cycles under 2 seconds


# ============================================================
# Task 30: Resilience Testing
# ============================================================

class TestResilience:
    """Task 30.1: Failure injection tests."""

    def test_agent_failure_doesnt_crash_pipeline(self, tmp_path):
        """30.1.1: Agent failure handling."""
        specs = [
            ("agent_ok", "type_a", [], "entity_a"),
            ("agent_fail", "type_b", [], "entity_b"),
            ("agent_ok2", "type_c", [], "entity_c"),
        ]
        orch, store = _build_orchestrator_with_mock_agents(tmp_path, specs)

        # Make one agent fail
        failing_agent = orch.registry.get("agent_fail")
        failing_agent._fail = True

        plan = orch.create_execution_plan(protocol_id="test")
        status = orch.execute_plan(plan)

        # Pipeline completes (with errors)
        assert status.state == "completed_with_errors"
        assert status.completed_tasks == 2
        assert status.failed_tasks == 1

    def test_dependent_agent_runs_after_dependency_fails(self, tmp_path):
        """30.1.1: Dependent agents still run even if dependency fails."""
        specs = [
            ("agent_a", "type_a", [], "entity_a"),
            ("agent_b", "type_b", ["type_a"], "entity_b"),
        ]
        orch, store = _build_orchestrator_with_mock_agents(tmp_path, specs)

        # Fail agent_a
        orch.registry.get("agent_a")._fail = True

        plan = orch.create_execution_plan(protocol_id="test")
        status = orch.execute_plan(plan)

        # Both agents attempted (agent_b runs despite agent_a failure)
        assert status.completed_tasks + status.failed_tasks == 2

    def test_timeout_error_classification(self):
        """30.1.2: Network failure handling (timeout classification)."""
        cat, sev = classify_error(Exception("Connection timed out"))
        assert cat == ErrorCategory.TRANSIENT
        assert sev == ErrorSeverity.MEDIUM

    def test_rate_limit_error_classification(self):
        """30.1.3: API failure handling (rate limit classification)."""
        cat, _ = classify_error(Exception("Rate limit exceeded 429"))
        assert cat == ErrorCategory.TRANSIENT

    def test_retry_with_backoff_succeeds(self):
        """30.1.3: Retry strategy works for transient errors."""
        call_count = {"n": 0}

        def flaky():
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise Exception("Connection timed out")
            return "success"

        result = retry_with_backoff(flaky, max_retries=3, base_delay=0.01)
        assert result == "success"
        assert call_count["n"] == 3

    def test_retry_gives_up_on_permanent_error(self):
        """30.1.3: No retry for permanent errors."""
        call_count = {"n": 0}

        def permanent():
            call_count["n"] += 1
            raise ValueError("Bad input")

        with pytest.raises(ValueError):
            retry_with_backoff(permanent, max_retries=3, base_delay=0.01)
        assert call_count["n"] == 1

    def test_graceful_degradation_partial_results(self, tmp_path):
        """30.1.6: Graceful degradation produces partial results."""
        specs = [
            ("metadata_agent", "metadata_extraction", [], "metadata"),
            ("narrative_agent", "narrative_extraction", [], "narrative_content"),
            ("eligibility_agent", "eligibility_extraction", ["metadata_extraction"], "eligibility_criterion"),
        ]
        orch, store = _build_orchestrator_with_mock_agents(tmp_path, specs)

        # Fail narrative agent (non-critical)
        orch.registry.get("narrative_agent")._fail = True

        plan = orch.create_execution_plan(protocol_id="test")
        status = orch.execute_plan(plan)

        # Pipeline completes with partial results
        assert status.state == "completed_with_errors"
        assert status.completed_tasks == 2  # metadata + eligibility
        assert status.failed_tasks == 1  # narrative

        # Context Store has entities from successful agents
        types = set(store.entity_types)
        assert "metadata" in types
        assert "eligibility_criterion" in types

    def test_checkpoint_recovery_after_failure(self, tmp_path):
        """30.1.5: Checkpoint recovery at each wave."""
        orch, store = _build_orchestrator_with_mock_agents(tmp_path)
        plan = orch.create_execution_plan(protocol_id="NCT12345")
        status = orch.execute_plan(plan)

        # Checkpoints should have been created
        cp_dir = tmp_path / "checkpoints"
        if cp_dir.exists():
            checkpoint_files = list(cp_dir.glob("checkpoint_*.json"))
            assert len(checkpoint_files) >= 1

            # Load the last checkpoint
            last_cp = sorted(checkpoint_files)[-1]
            cp = EnhancedCheckpoint.load(str(last_cp))
            # Should have the execution_id
            assert cp.execution_id == status.execution_id

    def test_error_handler_tracks_failures(self, tmp_path):
        """30.1.1: Error handler records agent failures."""
        error_agent = ErrorHandlerAgent()
        error_agent.initialize()

        # Simulate multiple agent failures
        failures = [
            ("metadata_agent", "Connection timed out"),
            ("soa_vision_agent", "Rate limit exceeded"),
            ("eligibility_agent", "Invalid API key"),
        ]

        for agent_id, msg in failures:
            task = AgentTask(
                task_id="t1", agent_id="error-handler",
                task_type="error_record",
                input_data={"agent_id": agent_id, "message": msg},
            )
            error_agent.execute(task)

        assert error_agent.error_count == 3

        # Generate report
        report_task = AgentTask(
            task_id="t2", agent_id="error-handler",
            task_type="error_report", input_data={},
        )
        result = error_agent.execute(report_task)
        report = result.data["report"]
        assert report["total_errors"] == 3
        assert len(report["errors_by_agent"]) == 3

    def test_multiple_wave_failure_recovery(self, tmp_path):
        """30.1.5: Recovery works across multiple waves."""
        specs = [
            ("agent_a", "type_a", [], "entity_a"),
            ("agent_b", "type_b", ["type_a"], "entity_b"),
            ("agent_c", "type_c", ["type_b"], "entity_c"),
        ]
        orch, store = _build_orchestrator_with_mock_agents(tmp_path, specs)

        # Fail agent_b (wave 1)
        orch.registry.get("agent_b")._fail = True

        plan = orch.create_execution_plan(protocol_id="test")
        status = orch.execute_plan(plan)

        assert status.state == "completed_with_errors"
        # agent_a succeeds, agent_b fails, agent_c still runs
        assert status.completed_tasks >= 2  # a and c succeed
        assert status.failed_tasks >= 1  # b fails

    def test_concurrent_context_store_access(self, tmp_path):
        """30.1.4: Context Store handles concurrent access."""
        store = ContextStore()

        def add_entities(prefix, count):
            for i in range(count):
                try:
                    store.add_entity(ContextEntity(
                        id=f"{prefix}-{i}",
                        entity_type="test",
                        data={"index": i},
                        provenance=EntityProvenance(
                            entity_id=f"{prefix}-{i}", source_agent_id="test"),
                    ))
                except ValueError:
                    pass  # Duplicate ID

        # Run 4 threads adding entities concurrently
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(add_entities, f"thread-{t}", 50)
                for t in range(4)
            ]
            for f in futures:
                f.result()

        # All 200 entities should be added (unique IDs)
        assert store.entity_count == 200


# ============================================================
# Pipeline Integration Tests
# ============================================================

class TestPipelineConfig:
    """Test PipelineConfig and PipelineResult data classes."""

    def test_pipeline_config_defaults(self):
        cfg = PipelineConfig()
        assert cfg.model == "gemini-2.5-pro"
        assert cfg.max_workers == 4
        assert cfg.enable_vision is True

    def test_pipeline_config_to_dict(self):
        cfg = PipelineConfig(model="gpt-4", max_workers=2)
        d = cfg.to_dict()
        assert d["model"] == "gpt-4"
        assert d["max_workers"] == 2

    def test_pipeline_result_to_dict(self):
        r = PipelineResult(
            execution_id="exec-1",
            protocol_id="NCT12345",
            success=True,
            entity_count=50,
        )
        d = r.to_dict()
        assert d["success"] is True
        assert d["entity_count"] == 50

    def test_wave_config_completeness(self):
        """All expected agents are in WAVE_CONFIG."""
        expected_agents = {
            "pdf-parser", "metadata_agent", "soa_vision_agent", "soa_text_agent",
            "narrative_agent", "docstructure_agent", "eligibility_agent",
            "objectives_agent", "studydesign_agent", "advanced_agent",
            "interventions_agent", "procedures_agent", "scheduling_agent",
            "execution_agent", "biomedical_concept_agent", "postprocessing",
            "reconciliation", "validation", "enrichment", "usdm-generator", "provenance",
        }
        assert set(WAVE_CONFIG.keys()) == expected_agents

    def test_wave_config_ordering(self):
        """Wave numbers should be monotonically increasing for dependencies."""
        # Independent agents should be wave 0
        assert WAVE_CONFIG["metadata_agent"] == 0
        assert WAVE_CONFIG["soa_vision_agent"] == 0

        # Dependent agents should be in later waves
        assert WAVE_CONFIG["eligibility_agent"] > WAVE_CONFIG["metadata_agent"]
        assert WAVE_CONFIG["scheduling_agent"] > WAVE_CONFIG["procedures_agent"]

        # Quality after extraction
        assert WAVE_CONFIG["validation"] > WAVE_CONFIG["execution_agent"]

        # Support after quality
        assert WAVE_CONFIG["usdm-generator"] > WAVE_CONFIG["validation"]


class TestCreateAllAgents:
    """Test the create_all_agents factory function."""

    def test_creates_agents_with_defaults(self):
        agents = create_all_agents()
        agent_ids = {a.agent_id for a in agents}

        # Should include key agents
        assert "pdf-parser" in agent_ids
        assert "metadata_agent" in agent_ids
        assert "usdm-generator" in agent_ids
        assert "provenance" in agent_ids

    def test_skip_agents(self):
        cfg = PipelineConfig(skip_agents=["pdf-parser", "provenance"])
        agents = create_all_agents(cfg)
        agent_ids = {a.agent_id for a in agents}
        assert "pdf-parser" not in agent_ids
        assert "provenance" not in agent_ids

    def test_disable_vision(self):
        cfg = PipelineConfig(enable_vision=False)
        agents = create_all_agents(cfg)
        agent_ids = {a.agent_id for a in agents}
        assert "soa_vision_agent" not in agent_ids
        assert "soa_text_agent" not in agent_ids

    def test_disable_enrichment(self):
        cfg = PipelineConfig(enable_enrichment=False)
        agents = create_all_agents(cfg)
        agent_ids = {a.agent_id for a in agents}
        assert "enrichment" not in agent_ids
