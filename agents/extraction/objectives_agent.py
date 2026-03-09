"""
ObjectivesAgent - Extracts study objectives, endpoints, and estimands.

Wraps extraction/objectives/extractor.py with the agent framework.
"""

import logging
from typing import Any, Dict, List, Optional

from agents.base import AgentCapabilities, AgentTask
from agents.extraction.base_extraction_agent import BaseExtractionAgent

logger = logging.getLogger(__name__)


class ObjectivesAgent(BaseExtractionAgent):
    """
    Extracts study objectives (primary, secondary, exploratory),
    endpoints, and estimand components (ICH E9 R1).

    Depends on MetadataAgent for study indication and phase context.
    """

    def __init__(self, agent_id: str = "objectives_agent", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id=agent_id, config=config)

    def get_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            agent_type="objectives_extraction",
            input_types=["pdf", "protocol_text"],
            output_types=["objective", "endpoint", "estimand", "analysis_population"],
            dependencies=["metadata_extraction"],
            supports_parallel=True,
            timeout_seconds=420,
        )

    def extract(self, pdf_path: str, protocol_text: str, model: str,
                output_dir: str, task: AgentTask) -> Optional[Dict[str, Any]]:
        from extraction.objectives.extractor import extract_objectives_endpoints

        pages = task.input_data.get("pages")
        extract_estimands = task.input_data.get("extract_estimands", True)

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

        result = extract_objectives_endpoints(
            pdf_path=pdf_path,
            model_name=model,
            pages=pages,
            protocol_text=protocol_text or None,
            study_indication=study_indication,
            study_phase=study_phase,
            extract_estimands=extract_estimands,
        )

        if not result.success or not result.data:
            return None

        data = result.data
        entities = []

        for obj in data.objectives:
            entities.append({
                "id": obj.id,
                "entity_type": "objective",
                "data": obj.to_dict(),
                "confidence": 0.85,
                "source_pages": result.pages_used,
            })

        for ep in data.endpoints:
            entities.append({
                "id": ep.id,
                "entity_type": "endpoint",
                "data": ep.to_dict(),
                "confidence": 0.85,
                "source_pages": result.pages_used,
            })

        for est in data.estimands:
            entities.append({
                "id": est.id,
                "entity_type": "estimand",
                "data": est.to_dict(),
                "confidence": 0.75,
                "source_pages": result.pages_used,
            })

        for ap in data.analysis_populations:
            entities.append({
                "id": ap.id,
                "entity_type": "analysis_population",
                "data": ap.to_dict(),
                "confidence": 0.8,
                "source_pages": result.pages_used,
            })

        return {
            "entities": entities,
            "confidence": 0.85,
            "objectives_summary": {
                "primary_count": data.primary_objectives_count,
                "secondary_count": data.secondary_objectives_count,
                "exploratory_count": data.exploratory_objectives_count,
                "endpoint_count": len(data.endpoints),
                "estimand_count": len(data.estimands),
            },
            "raw_response": result.raw_response,
        }
