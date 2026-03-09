"""
InterventionsAgent - Extracts study interventions and products from protocol.

Wraps extraction/interventions/extractor.py with the agent framework.
"""

import logging
from typing import Any, Dict, List, Optional

from agents.base import AgentCapabilities, AgentTask
from agents.extraction.base_extraction_agent import BaseExtractionAgent

logger = logging.getLogger(__name__)


class InterventionsAgent(BaseExtractionAgent):
    """
    Extracts study interventions, administrable products, substances,
    administration regimens, and medical devices.

    Depends on MetadataAgent (indication) and StudyDesignAgent (arms).
    """

    def __init__(self, agent_id: str = "interventions_agent", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id=agent_id, config=config)

    def get_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            agent_type="interventions_extraction",
            input_types=["pdf", "protocol_text"],
            output_types=[
                "study_intervention", "administrable_product",
                "administration", "substance", "medical_device",
            ],
            dependencies=["metadata_extraction", "studydesign_extraction"],
            supports_parallel=True,
            timeout_seconds=420,
        )

    def extract(self, pdf_path: str, protocol_text: str, model: str,
                output_dir: str, task: AgentTask) -> Optional[Dict[str, Any]]:
        from extraction.interventions.extractor import extract_interventions

        pages = task.input_data.get("pages")

        # Pull context from prior extractions
        existing_arms = task.input_data.get("existing_arms")
        study_indication = task.input_data.get("study_indication")

        if self._context_store:
            if not existing_arms:
                arm_entities = self._context_store.query_entities("study_arm")
                existing_arms = [e.data for e in arm_entities]
            if not study_indication:
                indications = self._context_store.query_entities("indication")
                if indications:
                    study_indication = indications[0].data.get("name", "")

        result = extract_interventions(
            pdf_path=pdf_path,
            model_name=model,
            pages=pages,
            protocol_text=protocol_text or None,
            existing_arms=existing_arms,
            study_indication=study_indication,
        )

        if not result.success or not result.data:
            return None

        data = result.data
        entities = []

        for intv in data.interventions:
            entities.append({
                "id": intv.id,
                "entity_type": "study_intervention",
                "data": intv.to_dict(),
                "confidence": 0.85,
                "source_pages": result.pages_used,
            })

        for prod in data.products:
            entities.append({
                "id": prod.id,
                "entity_type": "administrable_product",
                "data": prod.to_dict(),
                "confidence": 0.8,
                "source_pages": result.pages_used,
            })

        for admin in data.administrations:
            entities.append({
                "id": admin.id,
                "entity_type": "administration",
                "data": admin.to_dict(),
                "confidence": 0.8,
                "source_pages": result.pages_used,
            })

        for sub in data.substances:
            entities.append({
                "id": sub.id,
                "entity_type": "substance",
                "data": sub.to_dict(),
                "confidence": 0.8,
                "source_pages": result.pages_used,
            })

        for dev in data.devices:
            entities.append({
                "id": dev.id,
                "entity_type": "medical_device",
                "data": dev.to_dict(),
                "confidence": 0.75,
                "source_pages": result.pages_used,
            })

        return {
            "entities": entities,
            "confidence": 0.85,
            "interventions_summary": {
                "intervention_count": len(data.interventions),
                "product_count": len(data.products),
                "administration_count": len(data.administrations),
            },
            "raw_response": result.raw_response,
        }
