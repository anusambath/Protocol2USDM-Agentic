"""
Tests for CheckpointAgent and EnhancedCheckpoint.
"""

import json
import os
import tempfile
import pytest

from agents.base import AgentTask, AgentState
from agents.context_store import ContextStore, ContextEntity, EntityProvenance
from agents.support.checkpoint_agent import (
    CheckpointAgent,
    CheckpointMetadata,
    EnhancedCheckpoint,
)


# --- EnhancedCheckpoint Tests ---

class TestEnhancedCheckpoint:
    def test_defaults(self):
        cp = EnhancedCheckpoint()
        assert cp.checkpoint_id != ""
        assert cp.wave_number == 0
        assert cp.completed_tasks == []
        assert cp.failed_tasks == []

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test_checkpoint.json")
            cp = EnhancedCheckpoint(
                execution_id="exec-1",
                wave_number=3,
                completed_tasks=["t1", "t2", "t3"],
                failed_tasks=["t4"],
                total_tasks=5,
                agent_states={"agent-a": "READY", "agent-b": "EXECUTING"},
                execution_plan_id="plan-1",
                metadata={"protocol": "NCT12345"},
            )
            cp.save(filepath)

            loaded = EnhancedCheckpoint.load(filepath)
            assert loaded.execution_id == "exec-1"
            assert loaded.wave_number == 3
            assert loaded.completed_tasks == ["t1", "t2", "t3"]
            assert loaded.failed_tasks == ["t4"]
            assert loaded.total_tasks == 5
            assert loaded.agent_states["agent-a"] == "READY"
            assert loaded.execution_plan_id == "plan-1"
            assert loaded.metadata["protocol"] == "NCT12345"

    def test_save_creates_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "subdir", "checkpoint.json")
            cp = EnhancedCheckpoint(execution_id="exec-1")
            cp.save(filepath)
            assert os.path.exists(filepath)

    def test_save_with_context_store_snapshot(self):
        store = ContextStore()
        store.add_entity(ContextEntity(
            id="e1", entity_type="objective",
            data={"text": "Primary"},
            provenance=EntityProvenance(entity_id="e1", source_agent_id="test"),
        ))

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "checkpoint.json")
            cp = EnhancedCheckpoint(
                execution_id="exec-1",
                context_store_snapshot=store.serialize(),
            )
            cp.save(filepath)

            loaded = EnhancedCheckpoint.load(filepath)
            assert "entities" in loaded.context_store_snapshot

    def test_to_dict(self):
        cp = EnhancedCheckpoint(
            execution_id="exec-1",
            wave_number=2,
            completed_tasks=["t1"],
            total_tasks=5,
        )
        d = cp.to_dict()
        assert d["execution_id"] == "exec-1"
        assert d["wave_number"] == 2
        assert d["total_tasks"] == 5
        assert "context_store_snapshot" not in d  # Not in to_dict (too large)


class TestCheckpointMetadata:
    def test_to_dict(self):
        m = CheckpointMetadata(
            checkpoint_id="cp1",
            execution_id="exec-1",
            wave_number=2,
            completed_task_count=3,
            total_task_count=10,
            timestamp="2026-02-28T10:00:00",
            filepath="/tmp/cp.json",
            size_bytes=1024,
        )
        d = m.to_dict()
        assert d["checkpoint_id"] == "cp1"
        assert d["wave_number"] == 2
        assert d["size_bytes"] == 1024


# --- CheckpointAgent Tests ---

class TestCheckpointAgent:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.agent = CheckpointAgent(config={"checkpoints_dir": self.tmpdir})
        self.agent.initialize()

    def test_init(self):
        assert self.agent.agent_id == "checkpoint"
        assert self.agent.state == AgentState.READY

    def test_get_capabilities(self):
        caps = self.agent.get_capabilities()
        assert caps.agent_type == "support"
        assert "checkpoint" in caps.output_types

    def test_terminate(self):
        self.agent.terminate()
        assert self.agent.state == AgentState.TERMINATED

    def test_create_checkpoint(self):
        task = AgentTask(
            task_id="t1", agent_id="checkpoint",
            task_type="checkpoint_create",
            input_data={
                "execution_id": "exec-1",
                "wave_number": 2,
                "completed_tasks": ["t1", "t2"],
                "total_tasks": 5,
            },
        )
        result = self.agent.execute(task)
        assert result.success
        assert result.data["wave_number"] == 2
        assert result.data["completed_tasks"] == 2
        assert os.path.exists(result.data["filepath"])

    def test_create_checkpoint_with_context_store(self):
        store = ContextStore()
        store.add_entity(ContextEntity(
            id="e1", entity_type="objective",
            data={"text": "Primary"},
            provenance=EntityProvenance(entity_id="e1", source_agent_id="test"),
        ))
        self.agent.set_context_store(store)

        task = AgentTask(
            task_id="t1", agent_id="checkpoint",
            task_type="checkpoint_create",
            input_data={
                "execution_id": "exec-1",
                "wave_number": 1,
                "completed_tasks": ["t1"],
                "total_tasks": 3,
            },
        )
        result = self.agent.execute(task)
        assert result.success

        # Verify the checkpoint file contains context store data
        with open(result.data["filepath"], "r") as f:
            data = json.load(f)
        assert "entities" in data["context_store_snapshot"]

    def test_load_checkpoint(self):
        # First create a checkpoint
        create_task = AgentTask(
            task_id="t1", agent_id="checkpoint",
            task_type="checkpoint_create",
            input_data={
                "execution_id": "exec-1",
                "wave_number": 2,
                "completed_tasks": ["t1", "t2"],
                "total_tasks": 5,
            },
        )
        create_result = self.agent.execute(create_task)
        filepath = create_result.data["filepath"]

        # Now load it
        load_task = AgentTask(
            task_id="t2", agent_id="checkpoint",
            task_type="checkpoint_load",
            input_data={"checkpoint_path": filepath},
        )
        load_result = self.agent.execute(load_task)
        assert load_result.success
        assert load_result.data["checkpoint"]["execution_id"] == "exec-1"
        assert load_result.data["checkpoint"]["wave_number"] == 2
        assert load_result.data["remaining_tasks"] == 3

    def test_load_checkpoint_not_found(self):
        task = AgentTask(
            task_id="t1", agent_id="checkpoint",
            task_type="checkpoint_load",
            input_data={"checkpoint_path": "/nonexistent/path.json"},
        )
        result = self.agent.execute(task)
        assert not result.success
        assert "not found" in result.error

    def test_load_checkpoint_by_id(self):
        # Create a checkpoint
        create_task = AgentTask(
            task_id="t1", agent_id="checkpoint",
            task_type="checkpoint_create",
            input_data={
                "execution_id": "exec-1",
                "wave_number": 1,
                "completed_tasks": ["t1"],
                "total_tasks": 3,
            },
        )
        create_result = self.agent.execute(create_task)
        cp_id = create_result.data["checkpoint_id"]

        # Load by ID
        load_task = AgentTask(
            task_id="t2", agent_id="checkpoint",
            task_type="checkpoint_load",
            input_data={"checkpoint_id": cp_id},
        )
        load_result = self.agent.execute(load_task)
        assert load_result.success

    def test_load_restores_context_store(self):
        # Create store with entity
        store = ContextStore()
        store.add_entity(ContextEntity(
            id="e1", entity_type="objective",
            data={"text": "Primary"},
            provenance=EntityProvenance(entity_id="e1", source_agent_id="test"),
        ))
        self.agent.set_context_store(store)

        # Create checkpoint
        create_task = AgentTask(
            task_id="t1", agent_id="checkpoint",
            task_type="checkpoint_create",
            input_data={
                "execution_id": "exec-1",
                "wave_number": 1,
                "completed_tasks": ["t1"],
                "total_tasks": 3,
            },
        )
        create_result = self.agent.execute(create_task)

        # Clear the store
        new_store = ContextStore()
        self.agent.set_context_store(new_store)
        assert new_store.entity_count == 0

        # Load checkpoint - should restore entities
        load_task = AgentTask(
            task_id="t2", agent_id="checkpoint",
            task_type="checkpoint_load",
            input_data={"checkpoint_path": create_result.data["filepath"]},
        )
        load_result = self.agent.execute(load_task)
        assert load_result.success
        assert load_result.data["context_store_restored"] is True
        assert new_store.entity_count >= 1

    def test_list_checkpoints_empty(self):
        with tempfile.TemporaryDirectory() as empty_dir:
            agent = CheckpointAgent(config={"checkpoints_dir": empty_dir})
            agent.initialize()
            task = AgentTask(task_id="t1", agent_id="checkpoint",
                             task_type="checkpoint_list", input_data={})
            result = agent.execute(task)
            assert result.success
            assert result.data["count"] == 0

    def test_list_checkpoints(self):
        # Create multiple checkpoints
        for i in range(3):
            task = AgentTask(
                task_id=f"t{i}", agent_id="checkpoint",
                task_type="checkpoint_create",
                input_data={
                    "execution_id": f"exec-{i}",
                    "wave_number": i,
                    "completed_tasks": [f"t{j}" for j in range(i)],
                    "total_tasks": 5,
                },
            )
            self.agent.execute(task)

        list_task = AgentTask(task_id="tl", agent_id="checkpoint",
                              task_type="checkpoint_list", input_data={})
        result = self.agent.execute(list_task)
        assert result.success
        assert result.data["count"] == 3

    def test_cleanup_checkpoints(self):
        # Create 5 checkpoints
        for i in range(5):
            task = AgentTask(
                task_id=f"t{i}", agent_id="checkpoint",
                task_type="checkpoint_create",
                input_data={
                    "execution_id": f"exec-{i}",
                    "wave_number": i,
                    "completed_tasks": [],
                    "total_tasks": 5,
                },
            )
            self.agent.execute(task)

        # Cleanup, keep only 2
        cleanup_task = AgentTask(
            task_id="tc", agent_id="checkpoint",
            task_type="checkpoint_cleanup",
            input_data={"keep_count": 2},
        )
        result = self.agent.execute(cleanup_task)
        assert result.success
        assert result.data["removed"] == 3
        assert result.data["remaining"] == 2

    def test_unknown_task_type(self):
        task = AgentTask(task_id="t1", agent_id="checkpoint",
                         task_type="unknown_op", input_data={})
        result = self.agent.execute(task)
        assert not result.success
        assert "Unknown task type" in result.error

    def test_list_nonexistent_dir(self):
        agent = CheckpointAgent(config={"checkpoints_dir": "/nonexistent/dir"})
        agent.initialize()
        task = AgentTask(task_id="t1", agent_id="checkpoint",
                         task_type="checkpoint_list", input_data={})
        result = agent.execute(task)
        assert result.success
        assert result.data["count"] == 0
