"""
AI Agent Architecture for Protocol2USDM.

This package implements the agent-based architecture for clinical protocol
extraction, replacing the monolithic pipeline with autonomous, collaborative agents.

Core Components:
- BaseAgent: Abstract base class for all agents
- AgentRegistry: Dynamic agent registration and discovery
- ContextStore: Shared knowledge repository
- MessageQueue: Inter-agent communication
- OrchestratorAgent: Central coordination
"""

from .base import (
    BaseAgent,
    AgentState,
    AgentCapabilities,
    AgentMetrics,
    AgentTask,
    AgentResult,
)
from .registry import AgentRegistry
from .context_store import ContextStore, ContextEntity, EntityProvenance
from .message_queue import MessageQueue, AgentMessage, MessageType, Priority
from .orchestrator import OrchestratorAgent

__all__ = [
    # Base Agent
    "BaseAgent",
    "AgentState",
    "AgentCapabilities",
    "AgentMetrics",
    "AgentTask",
    "AgentResult",
    # Registry
    "AgentRegistry",
    # Context Store
    "ContextStore",
    "ContextEntity",
    "EntityProvenance",
    # Message Queue
    "MessageQueue",
    "AgentMessage",
    "MessageType",
    "Priority",
    # Orchestrator
    "OrchestratorAgent",
]
