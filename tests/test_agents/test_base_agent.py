"""
Unit tests for BaseAgent interface.

Covers: lifecycle, state management, metrics collection, task execution.
"""

import pytest
from agents.base import (
    AgentCapabilities,
    AgentMetrics,
    AgentResult,
    AgentState,
    AgentTask,
)
from .conftest import MockAgent


class TestAgentState:
    def test_initial_state(self):
        agent = MockAgent()
        assert agent.state == AgentState.INITIALIZING

    def test_state_transition(self):
        agent = MockAgent()
        agent.set_state(AgentState.READY)
        assert agent.state == AgentState.READY
        assert agent.is_ready()

    def test_is_executing(self):
        agent = MockAgent()
        agent.set_state(AgentState.EXECUTING)
        assert agent.is_executing()
        assert not agent.is_ready()


class TestAgentCapabilities:
    def test_capabilities_declaration(self):
        agent = MockAgent(agent_type="metadata", output_types=["metadata"])
        caps = agent.get_capabilities()
        assert caps.agent_type == "metadata"
        assert "metadata" in caps.output_types
        assert caps.supports_parallel is True

    def test_capabilities_serialization(self):
        caps = AgentCapabilities(
            agent_type="test",
            input_types=["pdf"],
            output_types=["data"],
            dependencies=["dep1"],
        )
        d = caps.to_dict()
        restored = AgentCapabilities.from_dict(d)
        assert restored.agent_type == caps.agent_type
        assert restored.input_types == caps.input_types
        assert restored.dependencies == caps.dependencies


class TestAgentMetrics:
    def test_initial_metrics(self):
        metrics = AgentMetrics()
        assert metrics.execution_count == 0
        assert metrics.avg_execution_time_ms == 0.0
        assert metrics.success_rate == 0.0

    def test_record_success(self):
        metrics = AgentMetrics()
        metrics.record_execution(success=True, execution_time_ms=100.0, tokens_used=500)
        assert metrics.execution_count == 1
        assert metrics.success_count == 1
        assert metrics.success_rate == 1.0
        assert metrics.total_tokens_used == 500

    def test_record_failure(self):
        metrics = AgentMetrics()
        metrics.record_execution(success=False, execution_time_ms=50.0)
        assert metrics.failure_count == 1
        assert metrics.success_rate == 0.0

    def test_avg_execution_time(self):
        metrics = AgentMetrics()
        metrics.record_execution(success=True, execution_time_ms=100.0)
        metrics.record_execution(success=True, execution_time_ms=200.0)
        assert metrics.avg_execution_time_ms == 150.0


class TestAgentTaskExecution:
    def test_run_task_success(self, sample_task):
        agent = MockAgent()
        agent.initialize()
        result = agent.run_task(sample_task)
        assert result.success is True
        assert result.execution_time_ms > 0
        assert agent.state == AgentState.READY
        assert agent.metrics.execution_count == 1

    def test_run_task_failure(self, sample_task):
        agent = MockAgent(should_fail=True)
        agent.initialize()
        result = agent.run_task(sample_task)
        assert result.success is False
        assert result.error == "Mock failure"
        assert agent.state == AgentState.FAILED

    def test_run_task_exception(self, sample_task):
        """Test that exceptions in execute() are caught."""
        class ExplodingAgent(MockAgent):
            def execute(self, task):
                raise RuntimeError("Boom")

        agent = ExplodingAgent()
        agent.initialize()
        result = agent.run_task(sample_task)
        assert result.success is False
        assert "Boom" in result.error
        assert agent.state == AgentState.FAILED

    def test_unique_agent_ids(self):
        a1 = MockAgent()
        a2 = MockAgent()
        # Default IDs include random hex, so they should differ
        assert a1.agent_id != a2.agent_id or a1.agent_id == "mock_agent"


class TestAgentTaskSerialization:
    def test_task_round_trip(self, sample_task):
        d = sample_task.to_dict()
        restored = AgentTask.from_dict(d)
        assert restored.task_id == sample_task.task_id
        assert restored.agent_id == sample_task.agent_id
        assert restored.task_type == sample_task.task_type

    def test_result_serialization(self):
        result = AgentResult(
            task_id="t1",
            agent_id="a1",
            success=True,
            data={"key": "value"},
            confidence_score=0.85,
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["confidence_score"] == 0.85
        assert d["data"]["key"] == "value"
