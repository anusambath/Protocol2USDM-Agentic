"""
ProceduresAgent - Extracts clinical procedures and medical devices from protocol.

Wraps extraction/procedures/extractor.py with the agent framework.
"""

import logging
from typing import Any, Dict, List, Optional

from agents.base import AgentCapabilities, AgentTask
from agents.extraction.base_extraction_agent import BaseExtractionAgent

logger = logging.getLogger(__name__)


class ProceduresAgent(BaseExtractionAgent):
    """
    Extracts clinical procedures, medical devices, ingredients,
    and strengths from the protocol.

    Depends on MetadataAgent and SoA agents for activity context.
    """

    def __init__(self, agent_id: str = "procedures_agent", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id=agent_id, config=config)

    def get_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            agent_type="procedures_extraction",
            input_types=["pdf"],
            output_types=[
                "procedure", "medical_device", "ingredient", "strength",
            ],
            dependencies=["metadata_extraction", "soa_vision_extraction"],
            supports_parallel=True,
            timeout_seconds=420,
        )

    def extract(self, pdf_path: str, protocol_text: str, model: str,
                output_dir: str, task: AgentTask) -> Optional[Dict[str, Any]]:
        from extraction.procedures.extractor import extract_procedures_devices

        result = extract_procedures_devices(
            pdf_path=pdf_path,
            model=model,
            output_dir=output_dir or None,
        )

        if not result.success or not result.data:
            return None

        data = result.data
        entities = []

        for proc in data.procedures:
            entities.append({
                "id": proc.id,
                "entity_type": "procedure",
                "data": proc.to_dict(),
                "confidence": result.confidence,
                "source_pages": result.pages_used,
            })

        for dev in data.devices:
            entities.append({
                "id": dev.id,
                "entity_type": "medical_device",
                "data": dev.to_dict(),
                "confidence": result.confidence,
                "source_pages": result.pages_used,
            })

        for ing in data.ingredients:
            entities.append({
                "id": ing.id,
                "entity_type": "ingredient",
                "data": ing.to_dict(),
                "confidence": result.confidence,
                "source_pages": result.pages_used,
            })

        for s in data.strengths:
            entities.append({
                "id": s.id,
                "entity_type": "strength",
                "data": s.to_dict(),
                "confidence": result.confidence,
                "source_pages": result.pages_used,
            })

        return {
            "entities": entities,
            "confidence": result.confidence,
            "procedures_summary": {
                "procedure_count": len(data.procedures),
                "device_count": len(data.devices),
                "ingredient_count": len(data.ingredients),
                "strength_count": len(data.strengths),
            },
        }
