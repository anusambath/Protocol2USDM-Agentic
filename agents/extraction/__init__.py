"""
Extraction agents for the AI Agent Architecture.

Each agent wraps existing extraction modules and integrates them
with the agent framework (BaseAgent, ContextStore, MessageQueue).
"""

from .base_extraction_agent import BaseExtractionAgent
from .metadata_agent import MetadataAgent
from .eligibility_agent import EligibilityAgent
from .objectives_agent import ObjectivesAgent
from .studydesign_agent import StudyDesignAgent
from .interventions_agent import InterventionsAgent
from .soa_vision_agent import SoAVisionAgent
from .soa_text_agent import SoATextAgent
# Phase 3 agents
from .procedures_agent import ProceduresAgent
from .scheduling_agent import SchedulingAgent
from .execution_agent import ExecutionAgent
from .narrative_agent import NarrativeAgent
from .advanced_agent import AdvancedAgent
from .docstructure_agent import DocStructureAgent

__all__ = [
    "BaseExtractionAgent",
    # Phase 2
    "MetadataAgent",
    "EligibilityAgent",
    "ObjectivesAgent",
    "StudyDesignAgent",
    "InterventionsAgent",
    "SoAVisionAgent",
    "SoATextAgent",
    # Phase 3
    "ProceduresAgent",
    "SchedulingAgent",
    "ExecutionAgent",
    "NarrativeAgent",
    "AdvancedAgent",
    "DocStructureAgent",
]
