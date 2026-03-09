"""
Unit tests for AgentRegistry.

Covers: registration, discovery, lifecycle, health checks.
"""

import pytest
from agents.base import AgentState
from agents.registry import AgentRegistry
from .conftest import MockAgent


class TestRegistration:
    def test_register_agent(self, registry):
        agent = MockAgent(agent_id="agent_1")
        agent_id = registry.register(agent)
        assert agent_id == "agent_1"
        assert registry.count == 1

    def test_register_duplicate_raises(self, registry):
        agent = MockAgent(agent_id="agent_1")
        registry.register(agent)
        with pytest.raises(ValueError, match="already registered"):
            registry.register(MockAgent(agent_id="agent_1"))

    def test_unregister_agent(self, registry):
        agent = MockAgent(agent_id="agent_1")
        agent.initialize()
        registry.register(agent)
        assert registry.unregister("agent_1") is True
        assert registry.count == 0

    def test_unregister_nonexistent(self, registry):
        assert registry.unregister("nonexistent") is False


class TestDiscovery:
    def test_get_by_id(self, registry):
        agent = MockAgent(agent_id="agent_1")
        registry.register(agent)
        found = registry.get("agent_1")
        assert found is agent

    def test_get_nonexistent(self, registry):
        assert registry.get("nonexistent") is None

    def test_get_all(self, registry):
        for i in range(3):
            registry.register(MockAgent(agent_id=f"agent_{i}"))
        assert len(registry.get_all()) == 3

    def test_get_by_type(self, registry):
        registry.register(MockAgent(agent_id="meta_1", agent_type="metadata"))
        registry.register(MockAgent(agent_id="elig_1", agent_type="eligibility"))
        registry.register(MockAgent(agent_id="meta_2", agent_type="metadata"))
        assert len(registry.get_by_type("metadata")) == 2
        assert len(registry.get_by_type("eligibility")) == 1

    def test_get_by_capability(self, registry):
        registry.register(MockAgent(agent_id="a1", output_types=["metadata"]))
        registry.register(MockAgent(agent_id="a2", output_types=["eligibility"]))
        found = registry.get_by_capability("metadata")
        assert len(found) == 1
        assert found[0].agent_id == "a1"

    def test_has(self, registry):
        registry.register(MockAgent(agent_id="agent_1"))
        assert registry.has("agent_1") is True
        assert registry.has("nonexistent") is False


class TestLifecycle:
    def test_initialize_all(self, registry):
        for i in range(3):
            registry.register(MockAgent(agent_id=f"agent_{i}"))
        results = registry.initialize_all()
        assert all(results.values())
        for agent in registry.get_all():
            assert agent.state == AgentState.READY

    def test_terminate_all(self, registry):
        for i in range(3):
            agent = MockAgent(agent_id=f"agent_{i}")
            agent.initialize()
            registry.register(agent)
        registry.terminate_all()
        for agent in registry.get_all():
            assert agent.state == AgentState.TERMINATED

    def test_health_check(self, registry):
        a1 = MockAgent(agent_id="a1")
        a1.initialize()
        a2 = MockAgent(agent_id="a2")
        registry.register(a1)
        registry.register(a2)
        health = registry.health_check()
        assert health["a1"] == "ready"
        assert health["a2"] == "initializing"

    def test_get_ready_agents(self, registry):
        a1 = MockAgent(agent_id="a1")
        a1.initialize()
        a2 = MockAgent(agent_id="a2")
        registry.register(a1)
        registry.register(a2)
        ready = registry.get_ready_agents()
        assert len(ready) == 1
        assert ready[0].agent_id == "a1"

    def test_dependency_map(self, registry):
        registry.register(MockAgent(agent_id="a1", dependencies=[]))
        registry.register(MockAgent(agent_id="a2", dependencies=["a1"]))
        dep_map = registry.get_dependency_map()
        assert dep_map["a1"] == []
        assert dep_map["a2"] == ["a1"]

    def test_serialization(self, registry):
        a = MockAgent(agent_id="a1", agent_type="metadata")
        a.initialize()
        registry.register(a)
        d = registry.to_dict()
        assert d["agent_count"] == 1
        assert "a1" in d["agents"]
        assert d["agents"]["a1"]["type"] == "metadata"
