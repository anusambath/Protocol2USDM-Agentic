"""
Unit tests for OrchestratorAgent.

Covers: registration, dependency graph, execution plans, task dispatch,
progress monitoring, checkpoints.
"""

import os
import pytest
import tempfile
from agents.base import AgentState
from agents.orchestrator import OrchestratorAgent, ExecutionPlan, Checkpoint
from .conftest import MockAgent


class TestAgentRegistration:
    def test_register_agent(self, orchestrator):
        agent = MockAgent(agent_id="meta_agent", agent_type="metadata")
        agent_id = orchestrator.register_agent(agent)
        assert agent_id == "meta_agent"
        assert orchestrator.registry.count == 1
        # Agent should have context store and message queue attached
        assert agent.context_store is orchestrator.context_store
        assert agent._message_queue is orchestrator.message_queue

    def test_unregister_agent(self, orchestrator):
        agent = MockAgent(agent_id="meta_agent")
        agent.initialize()
        orchestrator.register_agent(agent)
        assert orchestrator.unregister_agent("meta_agent") is True
        assert orchestrator.registry.count == 0


class TestDependencyGraph:
    def test_no_dependencies(self, orchestrator):
        orchestrator.register_agent(MockAgent(agent_id="a1", dependencies=[]))
        orchestrator.register_agent(MockAgent(agent_id="a2", dependencies=[]))
        graph = orchestrator.build_dependency_graph()
        assert graph["a1"] == set()
        assert graph["a2"] == set()

    def test_with_dependencies(self, orchestrator):
        orchestrator.register_agent(MockAgent(agent_id="a1", dependencies=[]))
        orchestrator.register_agent(MockAgent(agent_id="a2", dependencies=["a1"]))
        orchestrator.register_agent(MockAgent(agent_id="a3", dependencies=["a1", "a2"]))
        graph = orchestrator.build_dependency_graph()
        assert "a1" in graph["a2"]
        assert "a1" in graph["a3"]
        assert "a2" in graph["a3"]


class TestExecutionPlan:
    def test_create_plan_single_wave(self, orchestrator):
        orchestrator.register_agent(MockAgent(agent_id="a1", dependencies=[]))
        orchestrator.register_agent(MockAgent(agent_id="a2", dependencies=[]))
        plan = orchestrator.create_execution_plan("test_protocol")
        assert len(plan.waves) == 1
        assert plan.total_tasks == 2

    def test_create_plan_multiple_waves(self, orchestrator):
        orchestrator.register_agent(MockAgent(agent_id="a1", dependencies=[]))
        orchestrator.register_agent(MockAgent(agent_id="a2", dependencies=["a1"]))
        orchestrator.register_agent(MockAgent(agent_id="a3", dependencies=["a2"]))
        plan = orchestrator.create_execution_plan("test_protocol")
        assert len(plan.waves) == 3
        # Wave 0: a1, Wave 1: a2, Wave 2: a3
        wave_agents = [[t.agent_id for t in w.tasks] for w in plan.waves]
        assert "a1" in wave_agents[0]
        assert "a2" in wave_agents[1]
        assert "a3" in wave_agents[2]

    def test_create_plan_parallel_and_sequential(self, orchestrator):
        orchestrator.register_agent(MockAgent(agent_id="a1", dependencies=[]))
        orchestrator.register_agent(MockAgent(agent_id="a2", dependencies=[]))
        orchestrator.register_agent(MockAgent(agent_id="a3", dependencies=["a1", "a2"]))
        plan = orchestrator.create_execution_plan("test_protocol")
        assert len(plan.waves) == 2
        # Wave 0: a1, a2 (parallel), Wave 1: a3
        assert len(plan.waves[0].tasks) == 2
        assert len(plan.waves[1].tasks) == 1

    def test_plan_serialization(self, orchestrator):
        orchestrator.register_agent(MockAgent(agent_id="a1", dependencies=[]))
        plan = orchestrator.create_execution_plan("test")
        d = plan.to_dict()
        assert d["total_tasks"] == 1
        assert len(d["waves"]) == 1


class TestExecution:
    def test_execute_plan_success(self, orchestrator):
        orchestrator.register_agent(MockAgent(agent_id="a1", dependencies=[]))
        orchestrator.register_agent(MockAgent(agent_id="a2", dependencies=["a1"]))
        plan = orchestrator.create_execution_plan("test")
        status = orchestrator.execute_plan(plan)
        assert status.state == "completed"
        assert status.completed_tasks == 2
        assert status.failed_tasks == 0
        assert status.progress_percent == 100.0

    def test_execute_plan_with_failure(self, orchestrator):
        orchestrator.register_agent(MockAgent(agent_id="a1", dependencies=[], should_fail=True))
        orchestrator.register_agent(MockAgent(agent_id="a2", dependencies=[]))
        plan = orchestrator.create_execution_plan("test")
        status = orchestrator.execute_plan(plan)
        assert status.state == "completed_with_errors"
        assert status.failed_tasks > 0

    def test_execute_nonexistent_agent(self, orchestrator):
        """Plan with a task for an unregistered agent."""
        orchestrator.register_agent(MockAgent(agent_id="a1", dependencies=[]))
        plan = orchestrator.create_execution_plan("test")
        # Manually add a task for a nonexistent agent
        from agents.base import AgentTask
        plan.waves[0].tasks.append(AgentTask(
            task_id="bad_task", agent_id="nonexistent", task_type="test"))
        status = orchestrator.execute_plan(plan)
        assert status.failed_tasks >= 1

    def test_execution_status_tracking(self, orchestrator):
        orchestrator.register_agent(MockAgent(agent_id="a1", dependencies=[]))
        plan = orchestrator.create_execution_plan("test")
        status = orchestrator.execute_plan(plan)
        retrieved = orchestrator.get_execution_status(status.execution_id)
        assert retrieved is not None
        assert retrieved.execution_id == status.execution_id


class TestCheckpoints:
    def test_checkpoint_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint = Checkpoint(
                execution_id="exec_1",
                wave_number=2,
                completed_tasks=["task_1", "task_2"],
                context_store_snapshot={"entities": {}},
            )
            filepath = os.path.join(tmpdir, "checkpoint.json")
            checkpoint.save(filepath)

            loaded = Checkpoint.load(filepath)
            assert loaded.execution_id == "exec_1"
            assert loaded.wave_number == 2
            assert len(loaded.completed_tasks) == 2

    def test_resume_from_checkpoint(self, orchestrator):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Add an entity to context store
            from agents.context_store import ContextEntity, EntityProvenance
            orchestrator.context_store.add_entity(ContextEntity(
                id="e1", entity_type="epoch", data={"name": "Test"},
                provenance=EntityProvenance(entity_id="e1", source_agent_id="a1"),
            ))

            # Save checkpoint
            checkpoint = Checkpoint(
                execution_id="exec_1",
                wave_number=1,
                completed_tasks=["task_1"],
                context_store_snapshot=orchestrator.context_store.serialize(),
            )
            filepath = os.path.join(tmpdir, "checkpoint.json")
            checkpoint.save(filepath)

            # Clear and resume
            orchestrator.context_store = None
            status = orchestrator.resume_from_checkpoint(filepath)
            assert status.state == "resumed"
            assert orchestrator.context_store.entity_count == 1


class TestOrchestratorLifecycle:
    def test_initialize(self, orchestrator):
        orchestrator.initialize()
        assert orchestrator.state == AgentState.READY

    def test_terminate(self, orchestrator):
        orchestrator.initialize()
        agent = MockAgent(agent_id="a1")
        agent.initialize()
        orchestrator.register_agent(agent)
        orchestrator.terminate()
        assert orchestrator.state == AgentState.TERMINATED

    def test_capabilities(self, orchestrator):
        caps = orchestrator.get_capabilities()
        assert caps.agent_type == "orchestrator"
        assert "execution_status" in caps.output_types
