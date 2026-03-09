"""
SchedulingAgent - Extracts timing rules, conditions, and transitions from protocol.

Wraps extraction/scheduling/extractor.py with the agent framework.
"""

import logging
from typing import Any, Dict, List, Optional

from agents.base import AgentCapabilities, AgentTask
from agents.extraction.base_extraction_agent import BaseExtractionAgent

logger = logging.getLogger(__name__)


class SchedulingAgent(BaseExtractionAgent):
    """
    Extracts scheduling logic: timings (ISO 8601), conditions,
    transition rules, schedule exits, and decision instances.

    Depends on SoA and Procedures agents for activity/encounter context.
    """

    def __init__(self, agent_id: str = "scheduling_agent", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id=agent_id, config=config)

    def get_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            agent_type="scheduling_extraction",
            input_types=["pdf"],
            output_types=[
                "timing", "condition", "transition_rule",
                "schedule_exit", "decision_instance",
            ],
            dependencies=["soa_vision_extraction", "procedures_extraction"],
            supports_parallel=True,
            timeout_seconds=420,
        )

    def extract(self, pdf_path: str, protocol_text: str, model: str,
                output_dir: str, task: AgentTask) -> Optional[Dict[str, Any]]:
        from extraction.scheduling.extractor import extract_scheduling

        result = extract_scheduling(
            pdf_path=pdf_path,
            model=model,
            output_dir=output_dir or None,
        )

        if not result.success or not result.data:
            return None

        data = result.data
        entities = []

        for t in data.timings:
            entities.append({
                "id": t.id,
                "entity_type": "timing",
                "data": t.to_dict(),
                "confidence": result.confidence,
                "source_pages": result.pages_used,
            })

        for c in data.conditions:
            entities.append({
                "id": c.id,
                "entity_type": "condition",
                "data": c.to_dict(),
                "confidence": result.confidence,
                "source_pages": result.pages_used,
            })

        for tr in data.transition_rules:
            entities.append({
                "id": tr.id,
                "entity_type": "transition_rule",
                "data": tr.to_dict(),
                "confidence": result.confidence,
                "source_pages": result.pages_used,
            })

        for ex in data.schedule_exits:
            entities.append({
                "id": ex.id,
                "entity_type": "schedule_exit",
                "data": ex.to_dict(),
                "confidence": result.confidence,
                "source_pages": result.pages_used,
            })

        for d in data.decision_instances:
            entities.append({
                "id": d.id,
                "entity_type": "decision_instance",
                "data": d.to_dict(),
                "confidence": result.confidence,
                "source_pages": result.pages_used,
            })

        return {
            "entities": entities,
            "confidence": result.confidence,
            "scheduling_summary": {
                "timing_count": len(data.timings),
                "condition_count": len(data.conditions),
                "transition_rule_count": len(data.transition_rules),
                "exit_count": len(data.schedule_exits),
                "decision_count": len(data.decision_instances),
            },
        }
