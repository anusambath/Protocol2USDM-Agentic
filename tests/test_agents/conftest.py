"""
Shared fixtures for agent tests.
"""

import pytest
from agents.base import (
    AgentCapabilities,
    AgentResult,
    AgentState,
    AgentTask,
    BaseAgent,
)
from agents.context_store import ContextEntity, ContextStore, EntityProvenance
from agents.message_queue import MessageQueue
from agents.orchestrator import OrchestratorAgent
from agents.registry import AgentRegistry
from datetime import datetime


class MockAgent(BaseAgent):
    """A simple mock agent for testing."""

    def __init__(self, agent_id: str = "mock_agent",
                 agent_type: str = "mock",
                 output_types: list = None,
                 dependencies: list = None,
                 should_fail: bool = False,
                 config: dict = None):
        super().__init__(agent_id=agent_id, config=config or {})
        self._agent_type = agent_type
        self._output_types = output_types or ["mock_output"]
        self._dependencies = dependencies or []
        self._should_fail = should_fail
        self._execute_count = 0

    def initialize(self) -> None:
        self.set_state(AgentState.READY)

    def execute(self, task: AgentTask) -> AgentResult:
        self._execute_count += 1
        if self._should_fail:
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=False,
                error="Mock failure",
            )
        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            success=True,
            data={"extracted": f"data_from_{self.agent_id}"},
            confidence_score=0.95,
        )

    def terminate(self) -> None:
        self.set_state(AgentState.TERMINATED)

    def get_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            agent_type=self._agent_type,
            input_types=["pdf", "context_data"],
            output_types=self._output_types,
            dependencies=self._dependencies,
        )


@pytest.fixture
def mock_agent():
    return MockAgent()


@pytest.fixture
def registry():
    return AgentRegistry()


@pytest.fixture
def context_store():
    return ContextStore()


@pytest.fixture
def message_queue():
    return MessageQueue()


@pytest.fixture
def orchestrator():
    return OrchestratorAgent(config={"checkpoints_dir": "test_checkpoints"})


@pytest.fixture
def sample_entity():
    return ContextEntity(
        id="entity_1",
        entity_type="epoch",
        data={"name": "Screening", "description": "Screening period"},
        provenance=EntityProvenance(
            entity_id="entity_1",
            source_agent_id="metadata_agent",
            confidence_score=0.9,
            source_pages=[1, 2],
            model_used="gpt-4",
        ),
    )


@pytest.fixture
def sample_task():
    return AgentTask(
        task_id="task_1",
        agent_id="mock_agent",
        task_type="extract_metadata",
        input_data={"protocol_id": "NCT12345"},
    )
