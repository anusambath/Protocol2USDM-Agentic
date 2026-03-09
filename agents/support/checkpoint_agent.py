"""
Checkpoint Agent - Enhanced checkpoint and recovery system.

Extends the existing Checkpoint dataclass in agents/orchestrator.py with:
- Automatic checkpoint creation after each wave
- Full execution state persistence (agent states, message queue)
- Recovery process that identifies completed tasks and resumes
- Checkpoint listing and management
"""

import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from agents.base import AgentCapabilities, AgentResult, AgentState, AgentTask, BaseAgent

logger = logging.getLogger(__name__)


@dataclass
class CheckpointMetadata:
    """Metadata about a saved checkpoint."""
    checkpoint_id: str
    execution_id: str
    wave_number: int
    completed_task_count: int
    total_task_count: int
    timestamp: str
    filepath: str
    size_bytes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "execution_id": self.execution_id,
            "wave_number": self.wave_number,
            "completed_task_count": self.completed_task_count,
            "total_task_count": self.total_task_count,
            "timestamp": self.timestamp,
            "filepath": self.filepath,
            "size_bytes": self.size_bytes,
        }


@dataclass
class EnhancedCheckpoint:
    """
    Enhanced checkpoint with full execution state.

    Extends the basic Checkpoint from orchestrator.py with:
    - Agent states snapshot
    - Message queue snapshot
    - Execution plan reference
    - Recovery metadata
    """
    checkpoint_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    execution_id: str = ""
    wave_number: int = 0
    completed_tasks: List[str] = field(default_factory=list)
    failed_tasks: List[str] = field(default_factory=list)
    total_tasks: int = 0
    context_store_snapshot: Dict[str, Any] = field(default_factory=dict)
    agent_states: Dict[str, str] = field(default_factory=dict)
    message_queue_snapshot: List[Dict[str, Any]] = field(default_factory=list)
    execution_plan_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def save(self, filepath: str) -> None:
        """Save checkpoint to JSON file."""
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        data = {
            "checkpoint_id": self.checkpoint_id,
            "execution_id": self.execution_id,
            "wave_number": self.wave_number,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "total_tasks": self.total_tasks,
            "context_store_snapshot": self.context_store_snapshot,
            "agent_states": self.agent_states,
            "message_queue_snapshot": self.message_queue_snapshot,
            "execution_plan_id": self.execution_plan_id,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> "EnhancedCheckpoint":
        """Load checkpoint from JSON file."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(
            checkpoint_id=data["checkpoint_id"],
            execution_id=data["execution_id"],
            wave_number=data["wave_number"],
            completed_tasks=data.get("completed_tasks", []),
            failed_tasks=data.get("failed_tasks", []),
            total_tasks=data.get("total_tasks", 0),
            context_store_snapshot=data.get("context_store_snapshot", {}),
            agent_states=data.get("agent_states", {}),
            message_queue_snapshot=data.get("message_queue_snapshot", []),
            execution_plan_id=data.get("execution_plan_id", ""),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "execution_id": self.execution_id,
            "wave_number": self.wave_number,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "total_tasks": self.total_tasks,
            "execution_plan_id": self.execution_plan_id,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class CheckpointAgent(BaseAgent):
    """
    Agent for managing checkpoints and recovery.

    Provides:
    - Checkpoint creation with full state capture
    - Checkpoint listing and management
    - Recovery from any checkpoint
    - Automatic cleanup of old checkpoints
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id="checkpoint", config=config or {})
        self._checkpoints_dir = (config or {}).get("checkpoints_dir", "checkpoints")
        self._max_checkpoints = (config or {}).get("max_checkpoints", 50)

    def initialize(self) -> None:
        self.set_state(AgentState.READY)
        self._logger.info(f"[{self.agent_id}] Initialized (dir={self._checkpoints_dir})")

    def terminate(self) -> None:
        self.set_state(AgentState.TERMINATED)

    def get_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            agent_type="support",
            input_types=["execution_state"],
            output_types=["checkpoint"],
        )

    def execute(self, task: AgentTask) -> AgentResult:
        """
        Execute checkpoint operations.

        Task types:
        - "checkpoint_create": Create a new checkpoint
        - "checkpoint_load": Load a checkpoint for recovery
        - "checkpoint_list": List available checkpoints
        - "checkpoint_cleanup": Remove old checkpoints

        Input data for create:
        - execution_id (str): Current execution ID
        - wave_number (int): Current wave number
        - completed_tasks (list[str]): Completed task IDs
        - failed_tasks (list[str], optional): Failed task IDs
        - total_tasks (int): Total task count
        - agent_states (dict, optional): Agent state snapshot
        - execution_plan_id (str, optional): Plan ID

        Input data for load:
        - checkpoint_path (str): Path to checkpoint file
        - OR checkpoint_id (str): Checkpoint ID to find

        Input data for cleanup:
        - keep_count (int, optional): Number of recent checkpoints to keep
        """
        try:
            task_type = task.task_type
            if task_type == "checkpoint_create":
                return self._handle_create(task)
            elif task_type == "checkpoint_load":
                return self._handle_load(task)
            elif task_type == "checkpoint_list":
                return self._handle_list(task)
            elif task_type == "checkpoint_cleanup":
                return self._handle_cleanup(task)
            else:
                return AgentResult(
                    task_id=task.task_id, agent_id=self.agent_id,
                    success=False, error=f"Unknown task type: {task_type}",
                )
        except Exception as e:
            self._logger.error(f"[{self.agent_id}] Checkpoint operation failed: {e}")
            return AgentResult(
                task_id=task.task_id, agent_id=self.agent_id,
                success=False, error=str(e),
            )

    def _handle_create(self, task: AgentTask) -> AgentResult:
        """Create a new checkpoint."""
        data = task.input_data
        checkpoint = EnhancedCheckpoint(
            execution_id=data.get("execution_id", ""),
            wave_number=data.get("wave_number", 0),
            completed_tasks=data.get("completed_tasks", []),
            failed_tasks=data.get("failed_tasks", []),
            total_tasks=data.get("total_tasks", 0),
            agent_states=data.get("agent_states", {}),
            execution_plan_id=data.get("execution_plan_id", ""),
            metadata=data.get("metadata", {}),
        )

        # Capture Context Store snapshot
        if self._context_store:
            checkpoint.context_store_snapshot = self._context_store.serialize()

        # Save to file
        filename = f"checkpoint_{checkpoint.execution_id}_{checkpoint.wave_number}.json"
        filepath = os.path.join(self._checkpoints_dir, filename)
        checkpoint.save(filepath)

        return AgentResult(
            task_id=task.task_id, agent_id=self.agent_id,
            success=True,
            data={
                "checkpoint_id": checkpoint.checkpoint_id,
                "filepath": filepath,
                "wave_number": checkpoint.wave_number,
                "completed_tasks": len(checkpoint.completed_tasks),
            },
        )

    def _handle_load(self, task: AgentTask) -> AgentResult:
        """Load a checkpoint for recovery."""
        checkpoint_path = task.input_data.get("checkpoint_path")
        checkpoint_id = task.input_data.get("checkpoint_id")

        if not checkpoint_path and checkpoint_id:
            # Find by ID
            checkpoint_path = self._find_checkpoint_by_id(checkpoint_id)

        if not checkpoint_path or not os.path.exists(checkpoint_path):
            return AgentResult(
                task_id=task.task_id, agent_id=self.agent_id,
                success=False, error=f"Checkpoint not found: {checkpoint_path or checkpoint_id}",
            )

        checkpoint = EnhancedCheckpoint.load(checkpoint_path)

        # Restore Context Store if available
        if self._context_store and checkpoint.context_store_snapshot:
            from agents.context_store import ContextStore
            restored = ContextStore.deserialize(checkpoint.context_store_snapshot)
            # Copy restored data into existing store
            for entity in restored.query_entities():
                try:
                    self._context_store.add_entity(entity)
                except ValueError:
                    self._context_store.update_entity(
                        entity.id, entity.data, agent_id=self.agent_id)

        return AgentResult(
            task_id=task.task_id, agent_id=self.agent_id,
            success=True,
            data={
                "checkpoint": checkpoint.to_dict(),
                "context_store_restored": bool(checkpoint.context_store_snapshot),
                "remaining_tasks": checkpoint.total_tasks - len(checkpoint.completed_tasks),
            },
        )

    def _handle_list(self, task: AgentTask) -> AgentResult:
        """List available checkpoints."""
        checkpoints = self._list_checkpoints()
        return AgentResult(
            task_id=task.task_id, agent_id=self.agent_id,
            success=True,
            data={
                "checkpoints": [c.to_dict() for c in checkpoints],
                "count": len(checkpoints),
            },
        )

    def _handle_cleanup(self, task: AgentTask) -> AgentResult:
        """Remove old checkpoints, keeping the most recent ones."""
        keep_count = task.input_data.get("keep_count", self._max_checkpoints)
        checkpoints = self._list_checkpoints()

        removed = 0
        if len(checkpoints) > keep_count:
            # Sort by timestamp (oldest first) and remove excess
            to_remove = checkpoints[:-keep_count] if keep_count > 0 else checkpoints
            for cp in to_remove:
                try:
                    os.remove(cp.filepath)
                    removed += 1
                except OSError:
                    pass

        return AgentResult(
            task_id=task.task_id, agent_id=self.agent_id,
            success=True,
            data={"removed": removed, "remaining": max(0, len(checkpoints) - removed)},
        )

    def _list_checkpoints(self) -> List[CheckpointMetadata]:
        """List all checkpoint files in the checkpoints directory."""
        checkpoints = []
        cp_dir = Path(self._checkpoints_dir)
        if not cp_dir.exists():
            return checkpoints

        for filepath in sorted(cp_dir.glob("checkpoint_*.json")):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                checkpoints.append(CheckpointMetadata(
                    checkpoint_id=data.get("checkpoint_id", ""),
                    execution_id=data.get("execution_id", ""),
                    wave_number=data.get("wave_number", 0),
                    completed_task_count=len(data.get("completed_tasks", [])),
                    total_task_count=data.get("total_tasks", 0),
                    timestamp=data.get("timestamp", ""),
                    filepath=str(filepath),
                    size_bytes=filepath.stat().st_size,
                ))
            except (json.JSONDecodeError, KeyError):
                continue

        # Sort by timestamp
        checkpoints.sort(key=lambda c: c.timestamp)
        return checkpoints

    def _find_checkpoint_by_id(self, checkpoint_id: str) -> Optional[str]:
        """Find a checkpoint file by its ID."""
        for cp in self._list_checkpoints():
            if cp.checkpoint_id == checkpoint_id:
                return cp.filepath
        return None
