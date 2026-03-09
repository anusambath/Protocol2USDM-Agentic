"""
NarrativeAgent - Extracts document narrative structure and abbreviations from protocol.

Wraps extraction/narrative/extractor.py with the agent framework.
"""

import logging
from typing import Any, Dict, List, Optional

from agents.base import AgentCapabilities, AgentTask
from agents.extraction.base_extraction_agent import BaseExtractionAgent

logger = logging.getLogger(__name__)


class NarrativeAgent(BaseExtractionAgent):
    """
    Extracts narrative structure: document sections, narrative content
    items, and abbreviations.

    Wave 1 agent - no dependencies on other extraction agents.
    """

    def __init__(self, agent_id: str = "narrative_agent", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id=agent_id, config=config)

    def get_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            agent_type="narrative_extraction",
            input_types=["pdf", "protocol_text"],
            output_types=[
                "narrative_content", "narrative_content_item", "abbreviation",
            ],
            dependencies=[],
            supports_parallel=True,
            timeout_seconds=600,
        )

    def extract(self, pdf_path: str, protocol_text: str, model: str,
                output_dir: str, task: AgentTask) -> Optional[Dict[str, Any]]:
        from extraction.narrative.extractor import extract_narrative_structure

        pages = task.input_data.get("pages")

        result = extract_narrative_structure(
            pdf_path=pdf_path,
            model_name=model,
            pages=pages,
            protocol_text=protocol_text or None,
        )

        if not result.success or not result.data:
            return None

        data = result.data
        entities = []

        for section in data.sections:
            entities.append({
                "id": section.id,
                "entity_type": "narrative_content",
                "data": section.to_dict(),
                "confidence": 0.85,
                "source_pages": result.pages_used,
            })

        for item in data.items:
            entities.append({
                "id": item.id,
                "entity_type": "narrative_content_item",
                "data": item.to_dict(),
                "confidence": 0.85,
                "source_pages": result.pages_used,
            })

        for abbrev in data.abbreviations:
            entities.append({
                "id": abbrev.id,
                "entity_type": "abbreviation",
                "data": abbrev.to_dict(),
                "confidence": 0.9,
                "source_pages": result.pages_used,
            })

        if data.document:
            entities.append({
                "id": data.document.id,
                "entity_type": "study_definition_document",
                "data": data.document.to_dict(),
                "confidence": 0.85,
                "source_pages": result.pages_used,
            })

        return {
            "entities": entities,
            "confidence": 0.85,
            "narrative_summary": {
                "section_count": len(data.sections),
                "item_count": len(data.items),
                "abbreviation_count": len(data.abbreviations),
                "has_document": data.document is not None,
            },
            "raw_response": result.raw_response,
        }
