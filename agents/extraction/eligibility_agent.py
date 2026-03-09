"""
EligibilityAgent - Extracts inclusion/exclusion criteria from protocol.

Wraps extraction/eligibility/extractor.py with the agent framework.
"""

import logging
from typing import Any, Dict, List, Optional

from agents.base import AgentCapabilities, AgentTask
from agents.extraction.base_extraction_agent import BaseExtractionAgent

logger = logging.getLogger(__name__)


class EligibilityAgent(BaseExtractionAgent):
    """
    Extracts eligibility criteria: inclusion criteria, exclusion criteria,
    and study population definitions.

    Depends on MetadataAgent for study indication and phase context.
    """

    def __init__(self, agent_id: str = "eligibility_agent", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id=agent_id, config=config)

    def get_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            agent_type="eligibility_extraction",
            input_types=["pdf", "protocol_text"],
            output_types=[
                "eligibility_criterion", "criterion_item", "study_population",
            ],
            dependencies=["metadata_extraction"],
            supports_parallel=True,
            timeout_seconds=420,
        )

    def extract(self, pdf_path: str, protocol_text: str, model: str,
                output_dir: str, task: AgentTask) -> Optional[Dict[str, Any]]:
        from extraction.eligibility.extractor import extract_eligibility_criteria

        pages = task.input_data.get("pages")

        # Pull context from prior metadata extraction
        study_indication = task.input_data.get("study_indication")
        study_phase = task.input_data.get("study_phase")

        if self._context_store and not study_indication:
            indications = self._context_store.query_entities("indication")
            if indications:
                study_indication = indications[0].data.get("name", "")
            phases = self._context_store.query_entities("study_phase")
            if phases:
                study_phase = phases[0].data.get("code", "")

        result = extract_eligibility_criteria(
            pdf_path=pdf_path,
            model_name=model,
            pages=pages,
            protocol_text=protocol_text or None,
            study_indication=study_indication,
            study_phase=study_phase,
        )

        if not result.success or not result.data:
            return None

        data = result.data
        entities = []

        # Criterion items
        for item in data.criterion_items:
            entities.append({
                "id": item.id,
                "entity_type": "criterion_item",
                "data": item.to_dict(),
                "confidence": 0.85,
                "source_pages": result.pages_used,
            })

        # Criteria
        for crit in data.criteria:
            entities.append({
                "id": crit.id,
                "entity_type": "eligibility_criterion",
                "data": crit.to_dict(),
                "confidence": 0.85,
                "source_pages": result.pages_used,
            })

        # Population
        if data.population:
            entities.append({
                "id": data.population.id,
                "entity_type": "study_population",
                "data": data.population.to_dict(),
                "confidence": 0.8,
                "source_pages": result.pages_used,
            })

        return {
            "entities": entities,
            "confidence": 0.85,
            "eligibility_summary": {
                "inclusion_count": data.inclusion_count,
                "exclusion_count": data.exclusion_count,
            },
            "raw_response": result.raw_response,
        }
