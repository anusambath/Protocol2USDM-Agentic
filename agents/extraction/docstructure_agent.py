"""
DocStructureAgent - Extracts document structure references, annotations, and versions.

Wraps extraction/document_structure/extractor.py with the agent framework.
"""

import logging
from typing import Any, Dict, List, Optional

from agents.base import AgentCapabilities, AgentTask
from agents.extraction.base_extraction_agent import BaseExtractionAgent

logger = logging.getLogger(__name__)


class DocStructureAgent(BaseExtractionAgent):
    """
    Extracts document structure: content references (TOC entries),
    comment annotations (footnotes), and document version history.

    Wave 1 agent - no dependencies on other extraction agents.
    """

    def __init__(self, agent_id: str = "docstructure_agent", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id=agent_id, config=config)

    def get_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            agent_type="docstructure_extraction",
            input_types=["pdf"],
            output_types=[
                "document_content_reference", "comment_annotation",
                "document_version",
            ],
            dependencies=[],
            supports_parallel=True,
            timeout_seconds=420,
        )

    def extract(self, pdf_path: str, protocol_text: str, model: str,
                output_dir: str, task: AgentTask) -> Optional[Dict[str, Any]]:
        from extraction.document_structure.extractor import extract_document_structure

        result = extract_document_structure(
            pdf_path=pdf_path,
            model=model,
            output_dir=output_dir or None,
        )

        if not result.success or not result.data:
            return None

        data = result.data
        entities = []

        for ref in data.content_references:
            entities.append({
                "id": ref.id,
                "entity_type": "document_content_reference",
                "data": ref.to_dict(),
                "confidence": result.confidence,
                "source_pages": result.pages_used,
            })

        for annot in data.annotations:
            entities.append({
                "id": annot.id,
                "entity_type": "comment_annotation",
                "data": annot.to_dict(),
                "confidence": result.confidence,
                "source_pages": result.pages_used,
            })

        for ver in data.document_versions:
            entities.append({
                "id": ver.id,
                "entity_type": "document_version",
                "data": ver.to_dict(),
                "confidence": result.confidence,
                "source_pages": result.pages_used,
            })

        return {
            "entities": entities,
            "confidence": result.confidence,
            "docstructure_summary": {
                "reference_count": len(data.content_references),
                "annotation_count": len(data.annotations),
                "version_count": len(data.document_versions),
            },
        }
