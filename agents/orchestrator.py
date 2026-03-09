"""
Orchestrator Agent - Central coordinator for the agent system.

Manages agent registration, builds dependency graphs, creates execution plans,
dispatches tasks, monitors progress, handles failures, and creates checkpoints.
"""

import json
import logging
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from .base import (
    AgentCapabilities,
    AgentResult,
    AgentState,
    AgentTask,
    BaseAgent,
)
from .context_store import ContextStore
from .message_queue import AgentMessage, MessageQueue, MessageType, Priority
from .registry import AgentRegistry

logger = logging.getLogger(__name__)


@dataclass
class ExecutionWave:
    """Group of tasks that can execute in parallel."""
    wave_number: int
    tasks: List[AgentTask] = field(default_factory=list)
    completed: bool = False
    results: Dict[str, AgentResult] = field(default_factory=dict)


@dataclass
class ExecutionPlan:
    """Complete execution plan for protocol extraction."""
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    protocol_id: str = ""
    waves: List[ExecutionWave] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def total_tasks(self) -> int:
        return sum(len(w.tasks) for w in self.waves)

    def get_next_wave(self) -> Optional[ExecutionWave]:
        for wave in self.waves:
            if not wave.completed:
                return wave
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "protocol_id": self.protocol_id,
            "total_tasks": self.total_tasks,
            "waves": [
                {
                    "wave_number": w.wave_number,
                    "tasks": [t.to_dict() for t in w.tasks],
                    "completed": w.completed,
                }
                for w in self.waves
            ],
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ExecutionStatus:
    """Current status of an execution."""
    execution_id: str
    plan_id: str
    state: str = "pending"  # pending, running, completed, failed, paused
    current_wave: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    total_tasks: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    results: Dict[str, AgentResult] = field(default_factory=dict)

    @property
    def progress_percent(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return (self.completed_tasks / self.total_tasks) * 100.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "plan_id": self.plan_id,
            "state": self.state,
            "current_wave": self.current_wave,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "total_tasks": self.total_tasks,
            "progress_percent": self.progress_percent,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class Checkpoint:
    """Checkpoint for workflow recovery."""
    checkpoint_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    execution_id: str = ""
    wave_number: int = 0
    completed_tasks: List[str] = field(default_factory=list)
    context_store_snapshot: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def save(self, filepath: str) -> None:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({
                "checkpoint_id": self.checkpoint_id,
                "execution_id": self.execution_id,
                "wave_number": self.wave_number,
                "completed_tasks": self.completed_tasks,
                "context_store_snapshot": self.context_store_snapshot,
                "timestamp": self.timestamp.isoformat(),
            }, f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> "Checkpoint":
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(
            checkpoint_id=data["checkpoint_id"],
            execution_id=data["execution_id"],
            wave_number=data["wave_number"],
            completed_tasks=data["completed_tasks"],
            context_store_snapshot=data["context_store_snapshot"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


class OrchestratorAgent(BaseAgent):
    """
    Central coordinator that manages agent lifecycle, task distribution,
    and workflow execution.

    Responsibilities:
    - Agent registration and discovery via AgentRegistry
    - Dependency graph construction from agent capabilities
    - Execution plan generation (wave-based)
    - Task dispatch (sequential and parallel)
    - Progress monitoring and status tracking
    - Failure handling with retry logic
    - Checkpoint creation for recovery
    """

    def __init__(self, agent_id: str = "orchestrator",
                 config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id=agent_id, config=config or {})
        self.registry = AgentRegistry()
        self._context_store = ContextStore()
        self._message_queue = MessageQueue()
        self._executions: Dict[str, ExecutionStatus] = {}
        self._checkpoints_dir = config.get("checkpoints_dir", "checkpoints") if config else "checkpoints"
        self._max_workers = config.get("max_workers", 4) if config else 4

    @property
    def context_store(self) -> ContextStore:
        return self._context_store

    @context_store.setter
    def context_store(self, value: ContextStore) -> None:
        self._context_store = value

    @property
    def message_queue(self) -> MessageQueue:
        return self._message_queue

    # --- BaseAgent Implementation ---

    def initialize(self) -> None:
        self.set_state(AgentState.READY)
        self._logger.info(f"Orchestrator initialized (max_workers={self._max_workers})")

    def execute(self, task: AgentTask) -> AgentResult:
        """Execute an orchestration task (e.g., run a full extraction plan)."""
        protocol_id = task.input_data.get("protocol_id", "unknown")
        plan = self.create_execution_plan(protocol_id)
        status = self.execute_plan(plan)

        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            success=status.state == "completed",
            data={"execution_status": status.to_dict()},
            error=None if status.state == "completed" else f"Execution {status.state}",
        )

    def terminate(self) -> None:
        self.registry.terminate_all()
        self.set_state(AgentState.TERMINATED)
        self._logger.info("Orchestrator terminated")

    def get_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            agent_type="orchestrator",
            input_types=["protocol_id"],
            output_types=["execution_status", "usdm_json"],
            dependencies=[],
            supports_parallel=False,
        )

    # --- Agent Registration ---

    def register_agent(self, agent: BaseAgent) -> str:
        """Register an agent, attach shared resources, and initialize it."""
        agent_id = self.registry.register(agent)
        agent.set_context_store(self.context_store)
        agent.set_message_queue(self.message_queue)
        self.message_queue.subscribe(agent_id)
        return agent_id

    def unregister_agent(self, agent_id: str) -> bool:
        self.message_queue.unsubscribe(agent_id)
        return self.registry.unregister(agent_id)

    # --- Dependency Graph ---

    def build_dependency_graph(self) -> Dict[str, Set[str]]:
        """
        Build a dependency graph from agent capabilities.
        Returns dict of agent_id -> set of agent_ids it depends on.
        """
        dep_map = self.registry.get_dependency_map()
        # Resolve dependency names to agent IDs
        graph: Dict[str, Set[str]] = {}
        all_agents = {a.agent_id: a for a in self.registry.get_all()}

        for agent_id, dep_names in dep_map.items():
            resolved = set()
            for dep_name in dep_names:
                # Try direct ID match first
                if dep_name in all_agents:
                    resolved.add(dep_name)
                else:
                    # Try matching by agent type
                    matching = self.registry.get_by_type(dep_name)
                    for m in matching:
                        resolved.add(m.agent_id)
            graph[agent_id] = resolved

        return graph

    # --- Execution Plan ---

    def create_execution_plan(self, protocol_id: str = "") -> ExecutionPlan:
        """
        Create a wave-based execution plan from the dependency graph.
        Agents with no unresolved dependencies go in the earliest wave.
        """
        graph = self.build_dependency_graph()
        plan = ExecutionPlan(protocol_id=protocol_id)

        remaining = set(graph.keys())
        completed: Set[str] = set()
        wave_number = 0

        while remaining:
            # Find agents whose dependencies are all satisfied
            ready = set()
            for agent_id in remaining:
                deps = graph.get(agent_id, set())
                if deps <= completed:
                    ready.add(agent_id)

            if not ready:
                # Circular dependency - break by running all remaining
                self._logger.warning(
                    f"Breaking dependency cycle, running remaining: {remaining}")
                ready = remaining.copy()

            wave = ExecutionWave(wave_number=wave_number)
            for agent_id in ready:
                task = AgentTask(
                    task_id=f"{protocol_id}_{agent_id}_{uuid.uuid4().hex[:6]}",
                    agent_id=agent_id,
                    task_type=f"extract_{agent_id}",
                    input_data={"protocol_id": protocol_id},
                    dependencies=list(graph.get(agent_id, set())),
                )
                wave.tasks.append(task)

            plan.waves.append(wave)
            completed.update(ready)
            remaining -= ready
            wave_number += 1

        self._logger.info(
            f"Execution plan: {len(plan.waves)} waves, {plan.total_tasks} tasks")
        return plan

    # --- Execution ---

    def execute_plan(self, plan: ExecutionPlan) -> ExecutionStatus:
        """Execute a plan wave by wave, with parallel execution within waves."""
        execution_id = str(uuid.uuid4())
        status = ExecutionStatus(
            execution_id=execution_id,
            plan_id=plan.plan_id,
            state="running",
            total_tasks=plan.total_tasks,
            started_at=datetime.now(),
        )
        self._executions[execution_id] = status

        self._logger.info(f"Starting execution {execution_id}: "
                          f"{plan.total_tasks} tasks in {len(plan.waves)} waves")

        for wave in plan.waves:
            status.current_wave = wave.wave_number
            agent_names = [t.agent_id for t in wave.tasks]
            self._logger.info(
                f"  Wave {wave.wave_number}: {len(wave.tasks)} tasks — {', '.join(agent_names)}")

            if len(wave.tasks) == 1:
                # Single task - run directly
                result = self._execute_task(wave.tasks[0])
                wave.results[wave.tasks[0].task_id] = result
                status.results[wave.tasks[0].agent_id] = result
                if result.success:
                    status.completed_tasks += 1
                    self._logger.info(f"    ✓ {wave.tasks[0].agent_id}")
                else:
                    status.failed_tasks += 1
                    self._logger.warning(f"    ✗ {wave.tasks[0].agent_id}: {result.error}")
            else:
                # Multiple tasks - run in parallel
                with ThreadPoolExecutor(
                    max_workers=min(self._max_workers, len(wave.tasks))
                ) as executor:
                    futures = {
                        executor.submit(self._execute_task, task): task
                        for task in wave.tasks
                    }
                    for future in as_completed(futures):
                        task = futures[future]
                        try:
                            result = future.result()
                        except Exception as e:
                            result = AgentResult(
                                task_id=task.task_id,
                                agent_id=task.agent_id,
                                success=False,
                                error=str(e),
                            )
                        wave.results[task.task_id] = result
                        status.results[task.agent_id] = result
                        if result.success:
                            status.completed_tasks += 1
                            self._logger.info(f"    ✓ {task.agent_id}")
                        else:
                            status.failed_tasks += 1
                            self._logger.warning(f"    ✗ {task.agent_id}: {result.error}")

            wave.completed = True

            # Checkpoint after each wave
            self._create_checkpoint(execution_id, wave.wave_number)

            self._logger.info(
                f"  Wave {wave.wave_number} complete: "
                f"{status.completed_tasks}/{status.total_tasks} done, "
                f"{status.failed_tasks} failed")

        status.state = "completed" if status.failed_tasks == 0 else "completed_with_errors"
        status.completed_at = datetime.now()

        self._logger.info(
            f"Execution {execution_id} {status.state}: "
            f"{status.completed_tasks} succeeded, {status.failed_tasks} failed")

        # Clean up checkpoints if execution was successful
        if status.failed_tasks == 0:
            self._cleanup_checkpoints(execution_id)

        return status

    def _execute_task(self, task: AgentTask) -> AgentResult:
        """Execute a single task with retry logic."""
        agent = self.registry.get(task.agent_id)
        if not agent:
            return AgentResult(
                task_id=task.task_id,
                agent_id=task.agent_id,
                success=False,
                error=f"Agent '{task.agent_id}' not found in registry",
            )

        # Initialize agent if needed
        if agent.state == AgentState.INITIALIZING:
            try:
                agent.initialize()
                agent.set_state(AgentState.READY)
            except Exception as e:
                return AgentResult(
                    task_id=task.task_id,
                    agent_id=task.agent_id,
                    success=False,
                    error=f"Agent initialization failed: {e}",
                )

        # Execute with retries
        caps = self.registry.get_capabilities(task.agent_id)
        max_retries = caps.max_retries if caps else 3
        timeout_s = caps.timeout_seconds if caps and caps.timeout_seconds else 300
        last_error = None

        for attempt in range(max_retries + 1):
            if attempt > 0:
                delay = min(2 ** attempt, 30)
                self._logger.info(
                    f"  Retry {attempt}/{max_retries} for {task.agent_id} "
                    f"(delay={delay}s)")
                time.sleep(delay)

            # Enforce per-agent timeout using a thread future
            from concurrent.futures import ThreadPoolExecutor as _TPE, TimeoutError as _TE
            with _TPE(max_workers=1) as _ex:
                _f = _ex.submit(agent.run_task, task)
                try:
                    result = _f.result(timeout=timeout_s)
                except _TE:
                    self._logger.warning(f"  {task.agent_id} timed out after {timeout_s}s")
                    return AgentResult(
                        task_id=task.task_id,
                        agent_id=task.agent_id,
                        success=False,
                        error=f"Timed out after {timeout_s}s",
                    )

            if result.success:
                return result

            last_error = result.error
            self._logger.warning(
                f"  Task {task.task_id} attempt {attempt + 1} failed: {last_error}")

        return AgentResult(
            task_id=task.task_id,
            agent_id=task.agent_id,
            success=False,
            error=f"Failed after {max_retries + 1} attempts: {last_error}",
        )

    # --- Checkpoints ---

    def _create_checkpoint(self, execution_id: str, wave_number: int) -> str:
        """Create a checkpoint after a wave completes."""
        status = self._executions.get(execution_id)
        if not status:
            return ""

        checkpoint = Checkpoint(
            execution_id=execution_id,
            wave_number=wave_number,
            completed_tasks=[
                tid for tid, r in status.results.items() if r.success
            ],
            context_store_snapshot=self.context_store.serialize(),
        )

        filepath = os.path.join(
            self._checkpoints_dir,
            f"checkpoint_{execution_id}_{wave_number}.json",
        )
        try:
            checkpoint.save(filepath)
            self._logger.debug(f"Checkpoint saved: {filepath}")
        except Exception as e:
            self._logger.warning(f"Failed to save checkpoint: {e}")

        return checkpoint.checkpoint_id

    def _cleanup_checkpoints(self, execution_id: str) -> None:
        """
        Clean up checkpoint files for a successful execution.
        Only deletes checkpoints for the given execution_id.
        """
        import glob
        
        pattern = os.path.join(
            self._checkpoints_dir,
            f"checkpoint_{execution_id}_*.json"
        )
        
        checkpoint_files = glob.glob(pattern)
        deleted_count = 0
        
        for filepath in checkpoint_files:
            try:
                os.remove(filepath)
                deleted_count += 1
                self._logger.debug(f"Deleted checkpoint: {filepath}")
            except Exception as e:
                self._logger.warning(f"Failed to delete checkpoint {filepath}: {e}")
        
        if deleted_count > 0:
            self._logger.info(f"Cleaned up {deleted_count} checkpoint(s) for successful execution {execution_id}")

    def resume_from_checkpoint(self, checkpoint_path: str) -> ExecutionStatus:
        """Resume execution from a checkpoint."""
        checkpoint = Checkpoint.load(checkpoint_path)

        # Restore context store
        self.context_store = ContextStore.deserialize(
            checkpoint.context_store_snapshot)

        # Re-attach context store to all agents
        for agent in self.registry.get_all():
            agent.set_context_store(self.context_store)

        self._logger.info(
            f"Resumed from checkpoint: wave={checkpoint.wave_number}, "
            f"completed={len(checkpoint.completed_tasks)} tasks")

        # Create a new execution status
        status = ExecutionStatus(
            execution_id=str(uuid.uuid4()),
            plan_id=checkpoint.execution_id,
            state="resumed",
            completed_tasks=len(checkpoint.completed_tasks),
            started_at=datetime.now(),
        )
        self._executions[status.execution_id] = status
        return status

    # --- Status ---

    def get_execution_status(self, execution_id: str) -> Optional[ExecutionStatus]:
        return self._executions.get(execution_id)

    def get_all_executions(self) -> Dict[str, ExecutionStatus]:
        return dict(self._executions)

    def __repr__(self) -> str:
        return (f"<OrchestratorAgent agents={self.registry.count} "
                f"executions={len(self._executions)}>")
