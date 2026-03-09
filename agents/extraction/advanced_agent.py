"""
AdvancedAgent - Extracts amendments, geographic scope, and countries from protocol.

Wraps extraction/advanced/extractor.py with the agent framework.
"""

import logging
from typing import Any, Dict, List, Optional

from agents.base import AgentCapabilities, AgentTask
from agents.extraction.base_extraction_agent import BaseExtractionAgent

logger = logging.getLogger(__name__)


class AdvancedAgent(BaseExtractionAgent):
    """
    Extracts advanced entities: protocol amendments, amendment reasons,
    geographic scope, countries, and study sites.

    Depends on MetadataAgent for study context.
    """

    def __init__(self, agent_id: str = "advanced_agent", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id=agent_id, config=config)

    def get_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            agent_type="advanced_extraction",
            input_types=["pdf", "protocol_text"],
            output_types=[
                "study_amendment", "amendment_reason",
                "geographic_scope", "country", "study_site",
            ],
            dependencies=["metadata_extraction"],
            supports_parallel=True,
            timeout_seconds=420,
        )

    def extract(self, pdf_path: str, protocol_text: str, model: str,
                output_dir: str, task: AgentTask) -> Optional[Dict[str, Any]]:
        from extraction.advanced.extractor import extract_advanced_entities

        pages = task.input_data.get("pages")

        result = extract_advanced_entities(
            pdf_path=pdf_path,
            model_name=model,
            pages=pages,
            protocol_text=protocol_text or None,
        )

        if not result.success or not result.data:
            return None

        data = result.data
        entities = []

        for amendment in data.amendments:
            entities.append({
                "id": amendment.id,
                "entity_type": "study_amendment",
                "data": amendment.to_dict(),
                "confidence": 0.85,
                "source_pages": result.pages_used,
            })

        for reason in data.amendment_reasons:
            entities.append({
                "id": reason.id,
                "entity_type": "amendment_reason",
                "data": reason.to_dict(),
                "confidence": 0.85,
                "source_pages": result.pages_used,
            })

        if data.geographic_scope:
            entities.append({
                "id": data.geographic_scope.id,
                "entity_type": "geographic_scope",
                "data": data.geographic_scope.to_dict(),
                "confidence": 0.8,
                "source_pages": result.pages_used,
            })

        for country in data.countries:
            entities.append({
                "id": country.id,
                "entity_type": "country",
                "data": country.to_dict(),
                "confidence": 0.85,
                "source_pages": result.pages_used,
            })

        for site in data.sites:
            entities.append({
                "id": site.id,
                "entity_type": "study_site",
                "data": site.to_dict(),
                "confidence": 0.8,
                "source_pages": result.pages_used,
            })

        return {
            "entities": entities,
            "confidence": 0.85,
            "advanced_summary": {
                "amendment_count": len(data.amendments),
                "country_count": len(data.countries),
                "site_count": len(data.sites),
                "has_geographic_scope": data.geographic_scope is not None,
            },
            "raw_response": result.raw_response,
        }
