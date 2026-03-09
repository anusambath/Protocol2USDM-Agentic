"""
Agent Registry for dynamic agent registration and discovery.

Provides capability-based lookup, lifecycle management, and health checks.
"""

import logging
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from .base import AgentCapabilities, AgentState, BaseAgent

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Registry for agent registration, discovery, and lifecycle management.

    Thread-safe. Supports:
    - Register/unregister agents
    - Capability-based lookup
    - Health checks
    - Agent lifecycle tracking
    """

    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._capabilities: Dict[str, AgentCapabilities] = {}
        self._registered_at: Dict[str, datetime] = {}
        self._lock = threading.RLock()

    # --- Registration ---

    def register(self, agent: BaseAgent) -> str:
        """
        Register an agent with the registry.

        Returns the agent's unique ID. Raises ValueError if an agent
        with the same ID is already registered.
        """
        with self._lock:
            if agent.agent_id in self._agents:
                raise ValueError(f"Agent '{agent.agent_id}' is already registered")

            self._agents[agent.agent_id] = agent
            self._capabilities[agent.agent_id] = agent.get_capabilities()
            self._registered_at[agent.agent_id] = datetime.now()

            logger.info(f"Registered agent: {agent.agent_id} "
                        f"(type={self._capabilities[agent.agent_id].agent_type})")
            return agent.agent_id

    def unregister(self, agent_id: str) -> bool:
        """
        Unregister an agent. Returns True if found and removed.
        """
        with self._lock:
            if agent_id not in self._agents:
                return False

            agent = self._agents.pop(agent_id)
            self._capabilities.pop(agent_id, None)
            self._registered_at.pop(agent_id, None)

            # Terminate if still active
            if agent.state not in (AgentState.TERMINATED, AgentState.FAILED):
                try:
                    agent.terminate()
                    agent.set_state(AgentState.TERMINATED)
                except Exception as e:
                    logger.warning(f"Error terminating agent {agent_id}: {e}")

            logger.info(f"Unregistered agent: {agent_id}")
            return True

    # --- Discovery ---

    def get(self, agent_id: str) -> Optional[BaseAgent]:
        """Get an agent by ID."""
        with self._lock:
            return self._agents.get(agent_id)

    def get_all(self) -> List[BaseAgent]:
        """Get all registered agents."""
        with self._lock:
            return list(self._agents.values())

    def get_by_type(self, agent_type: str) -> List[BaseAgent]:
        """Get all agents of a specific type."""
        with self._lock:
            return [
                agent for agent_id, agent in self._agents.items()
                if self._capabilities.get(agent_id, AgentCapabilities(agent_type="")).agent_type == agent_type
            ]

    def get_by_capability(self, output_type: str) -> List[BaseAgent]:
        """Find agents that produce a specific output type."""
        with self._lock:
            return [
                agent for agent_id, agent in self._agents.items()
                if output_type in self._capabilities.get(agent_id, AgentCapabilities(agent_type="")).output_types
            ]

    def get_capabilities(self, agent_id: str) -> Optional[AgentCapabilities]:
        """Get capabilities for a specific agent."""
        with self._lock:
            return self._capabilities.get(agent_id)

    def has(self, agent_id: str) -> bool:
        """Check if an agent is registered."""
        with self._lock:
            return agent_id in self._agents

    @property
    def count(self) -> int:
        """Number of registered agents."""
        with self._lock:
            return len(self._agents)

    # --- Lifecycle ---

    def health_check(self) -> Dict[str, str]:
        """
        Check health of all registered agents.
        Returns dict of agent_id -> state.
        """
        with self._lock:
            return {
                agent_id: agent.state.value
                for agent_id, agent in self._agents.items()
            }

    def get_ready_agents(self) -> List[BaseAgent]:
        """Get all agents in READY state."""
        with self._lock:
            return [a for a in self._agents.values() if a.state == AgentState.READY]

    def get_failed_agents(self) -> List[BaseAgent]:
        """Get all agents in FAILED state."""
        with self._lock:
            return [a for a in self._agents.values() if a.state == AgentState.FAILED]

    def initialize_all(self) -> Dict[str, bool]:
        """
        Initialize all registered agents.
        Returns dict of agent_id -> success.
        """
        results = {}
        with self._lock:
            agents = list(self._agents.items())

        for agent_id, agent in agents:
            try:
                agent.initialize()
                agent.set_state(AgentState.READY)
                results[agent_id] = True
            except Exception as e:
                logger.error(f"Failed to initialize agent {agent_id}: {e}")
                agent.set_state(AgentState.FAILED)
                results[agent_id] = False

        return results

    def terminate_all(self) -> None:
        """Terminate all registered agents."""
        with self._lock:
            agents = list(self._agents.items())

        for agent_id, agent in agents:
            try:
                agent.terminate()
                agent.set_state(AgentState.TERMINATED)
            except Exception as e:
                logger.warning(f"Error terminating agent {agent_id}: {e}")

    def get_dependency_map(self) -> Dict[str, List[str]]:
        """
        Build a dependency map from agent capabilities.
        Returns dict of agent_id -> list of agent_ids it depends on.
        """
        with self._lock:
            dep_map = {}
            for agent_id, caps in self._capabilities.items():
                dep_map[agent_id] = list(caps.dependencies)
            return dep_map

    def to_dict(self) -> Dict[str, Any]:
        """Serialize registry state for debugging/monitoring."""
        with self._lock:
            return {
                "agent_count": len(self._agents),
                "agents": {
                    agent_id: {
                        "type": self._capabilities.get(agent_id, AgentCapabilities(agent_type="unknown")).agent_type,
                        "state": agent.state.value,
                        "registered_at": self._registered_at.get(agent_id, datetime.now()).isoformat(),
                        "metrics": agent.metrics.to_dict(),
                    }
                    for agent_id, agent in self._agents.items()
                },
            }

    def __repr__(self) -> str:
        return f"<AgentRegistry agents={self.count}>"
