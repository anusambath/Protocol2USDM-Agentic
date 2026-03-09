"""
Base Agent interface for the AI Agent Architecture.

Defines the abstract base class that all agents must implement,
along with supporting data models for capabilities, metrics, tasks, and results.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import logging
import time
import uuid

logger = logging.getLogger(__name__)


class AgentState(Enum):
    """Agent lifecycle states."""
    INITIALIZING = "initializing"
    READY = "ready"
    EXECUTING = "executing"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINATED = "terminated"


@dataclass
class AgentCapabilities:
    """Declares what an agent can process and produce."""
    agent_type: str
    input_types: List[str] = field(default_factory=list)
    output_types: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    supports_parallel: bool = True
    max_retries: int = 3
    timeout_seconds: int = 300

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_type": self.agent_type,
            "input_types": self.input_types,
            "output_types": self.output_types,
            "dependencies": self.dependencies,
            "supports_parallel": self.supports_parallel,
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentCapabilities":
        return cls(
            agent_type=data["agent_type"],
            input_types=data.get("input_types", []),
            output_types=data.get("output_types", []),
            dependencies=data.get("dependencies", []),
            supports_parallel=data.get("supports_parallel", True),
            max_retries=data.get("max_retries", 3),
            timeout_seconds=data.get("timeout_seconds", 300),
        )


@dataclass
class AgentMetrics:
    """Performance and quality metrics for an agent."""
    execution_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_execution_time_ms: float = 0.0
    total_tokens_used: int = 0
    total_api_calls: int = 0
    last_execution_time_ms: float = 0.0
    last_confidence_score: float = 0.0

    @property
    def avg_execution_time_ms(self) -> float:
        if self.execution_count == 0:
            return 0.0
        return self.total_execution_time_ms / self.execution_count

    @property
    def success_rate(self) -> float:
        if self.execution_count == 0:
            return 0.0
        return self.success_count / self.execution_count

    def record_execution(self, success: bool, execution_time_ms: float,
                         tokens_used: int = 0, api_calls: int = 0,
                         confidence_score: float = 0.0) -> None:
        """Record metrics from a single execution."""
        self.execution_count += 1
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        self.total_execution_time_ms += execution_time_ms
        self.last_execution_time_ms = execution_time_ms
        self.total_tokens_used += tokens_used
        self.total_api_calls += api_calls
        self.last_confidence_score = confidence_score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "avg_execution_time_ms": self.avg_execution_time_ms,
            "success_rate": self.success_rate,
            "total_tokens_used": self.total_tokens_used,
            "total_api_calls": self.total_api_calls,
        }


@dataclass
class AgentTask:
    """Task assigned to an agent by the orchestrator."""
    task_id: str
    agent_id: str
    task_type: str
    input_data: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    priority: int = 1  # 0=HIGH, 1=NORMAL, 2=LOW
    timeout_seconds: int = 300
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "task_type": self.task_type,
            "input_data": self.input_data,
            "dependencies": self.dependencies,
            "priority": self.priority,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentTask":
        return cls(
            task_id=data["task_id"],
            agent_id=data["agent_id"],
            task_type=data["task_type"],
            input_data=data.get("input_data", {}),
            dependencies=data.get("dependencies", []),
            priority=data.get("priority", 1),
            timeout_seconds=data.get("timeout_seconds", 300),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
        )


@dataclass
class AgentResult:
    """Result from agent task execution."""
    task_id: str
    agent_id: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    confidence_score: Optional[float] = None
    execution_time_ms: float = 0.0
    tokens_used: int = 0
    api_calls: int = 0
    provenance: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "success": self.success,
            "execution_time_ms": self.execution_time_ms,
            "tokens_used": self.tokens_used,
            "api_calls": self.api_calls,
        }
        if self.data is not None:
            result["data"] = self.data
        if self.error is not None:
            result["error"] = self.error
        if self.confidence_score is not None:
            result["confidence_score"] = self.confidence_score
        if self.provenance is not None:
            result["provenance"] = self.provenance
        return result


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the system.

    Subclasses must implement:
    - initialize(): Set up agent resources
    - execute(task): Execute an assigned task
    - terminate(): Clean up resources
    - get_capabilities(): Declare agent capabilities
    """

    def __init__(self, agent_id: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        self.agent_id = agent_id or f"{self.__class__.__name__}_{uuid.uuid4().hex[:8]}"
        self.config = config or {}
        self.state = AgentState.INITIALIZING
        self.metrics = AgentMetrics()
        self._context_store = None
        self._message_queue = None
        self._logger = logging.getLogger(f"agents.{self.__class__.__name__}")

    # --- Lifecycle ---

    @abstractmethod
    def initialize(self) -> None:
        """Initialize agent resources. Called once before first execution."""
        pass

    @abstractmethod
    def execute(self, task: AgentTask) -> AgentResult:
        """Execute an assigned task and return the result."""
        pass

    @abstractmethod
    def terminate(self) -> None:
        """Clean up agent resources. Called when agent is being removed."""
        pass

    @abstractmethod
    def get_capabilities(self) -> AgentCapabilities:
        """Return this agent's capability declaration."""
        pass

    # --- State Management ---

    def set_state(self, new_state: AgentState) -> None:
        """Transition to a new state with logging."""
        old_state = self.state
        self.state = new_state
        self._logger.debug(f"[{self.agent_id}] {old_state.value} -> {new_state.value}")

    def is_ready(self) -> bool:
        return self.state == AgentState.READY

    def is_executing(self) -> bool:
        return self.state == AgentState.EXECUTING

    # --- Context Store ---

    def set_context_store(self, context_store) -> None:
        """Attach a context store to this agent."""
        self._context_store = context_store

    @property
    def context_store(self):
        return self._context_store

    # --- Message Queue ---

    def set_message_queue(self, message_queue) -> None:
        """Attach a message queue to this agent."""
        self._message_queue = message_queue

    def send_message(self, message) -> None:
        """Send a message via the attached message queue."""
        if self._message_queue:
            self._message_queue.publish(message)
        else:
            self._logger.warning(f"[{self.agent_id}] No message queue attached, cannot send message")

    def receive_message(self, timeout_ms: int = 1000):
        """Receive a message from the queue."""
        if self._message_queue:
            return self._message_queue.poll(self.agent_id, timeout_ms)
        return None

    # --- Execution Wrapper ---

    def run_task(self, task: AgentTask) -> AgentResult:
        """
        Execute a task with metrics collection and state management.

        This is the main entry point called by the orchestrator.
        Wraps execute() with timing, error handling, and metrics.
        """
        self.set_state(AgentState.EXECUTING)
        task.started_at = datetime.now()
        start_time = time.perf_counter()

        try:
            result = self.execute(task)
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            result.execution_time_ms = elapsed_ms

            self.metrics.record_execution(
                success=result.success,
                execution_time_ms=elapsed_ms,
                tokens_used=result.tokens_used,
                api_calls=result.api_calls,
                confidence_score=result.confidence_score or 0.0,
            )

            task.completed_at = datetime.now()
            self.set_state(AgentState.READY if result.success else AgentState.FAILED)
            return result

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            self._logger.error(f"[{self.agent_id}] Task {task.task_id} failed: {e}")

            self.metrics.record_execution(
                success=False,
                execution_time_ms=elapsed_ms,
            )

            task.completed_at = datetime.now()
            self.set_state(AgentState.FAILED)

            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=False,
                error=str(e),
                execution_time_ms=elapsed_ms,
            )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.agent_id} state={self.state.value}>"
