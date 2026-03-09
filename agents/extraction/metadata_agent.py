"""
MetadataAgent - Extracts study identity and metadata from protocol.

Wraps extraction/metadata/extractor.py with the agent framework.
"""

import logging
from typing import Any, Dict, List, Optional

from agents.base import AgentCapabilities, AgentTask
from agents.extraction.base_extraction_agent import BaseExtractionAgent

logger = logging.getLogger(__name__)


class MetadataAgent(BaseExtractionAgent):
    """
    Extracts study metadata: titles, identifiers, organizations,
    study phase, indications, and protocol version info.

    Wave 1 agent - no dependencies on other extraction agents.
    """

    def __init__(self, agent_id: str = "metadata_agent", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id=agent_id, config=config)

    def get_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            agent_type="metadata_extraction",
            input_types=["pdf", "protocol_text"],
            output_types=[
                "study_title", "study_identifier", "organization",
                "study_role", "indication", "study_phase", "governance_date",
            ],
            dependencies=[],
            supports_parallel=True,
            timeout_seconds=600,  # 10 minutes - sufficient for fast models (Gemini)
        )

    def extract(self, pdf_path: str, protocol_text: str, model: str,
                output_dir: str, task: AgentTask) -> Optional[Dict[str, Any]]:
        from extraction.metadata.extractor import extract_study_metadata

        title_page_images = task.input_data.get("title_page_images")
        pages = task.input_data.get("pages")

        result = extract_study_metadata(
            pdf_path=pdf_path,
            model_name=model,
            title_page_images=title_page_images,
            protocol_text=protocol_text or None,
            pages=pages,
        )

        if not result.success or not result.metadata:
            return None

        md = result.metadata
        entities = []

        # Titles
        for title in md.titles:
            entities.append({
                "id": title.id,
                "entity_type": "study_title",
                "data": title.to_dict(),
                "confidence": 0.9,
                "source_pages": result.pages_used,
            })

        # Identifiers
        for ident in md.identifiers:
            entities.append({
                "id": ident.id,
                "entity_type": "study_identifier",
                "data": ident.to_dict(),
                "confidence": 0.85,
                "source_pages": result.pages_used,
            })

        # Organizations
        for org in md.organizations:
            entities.append({
                "id": org.id,
                "entity_type": "organization",
                "data": org.to_dict(),
                "confidence": 0.85,
                "source_pages": result.pages_used,
            })

        # Roles
        for role in md.roles:
            entities.append({
                "id": role.id,
                "entity_type": "study_role",
                "data": role.to_dict(),
                "confidence": 0.8,
                "source_pages": result.pages_used,
            })

        # Indications
        for ind in md.indications:
            entities.append({
                "id": ind.id,
                "entity_type": "indication",
                "data": ind.to_dict(),
                "confidence": 0.85,
                "source_pages": result.pages_used,
            })

        # Study phase
        if md.study_phase:
            entities.append({
                "id": "study_phase_1",
                "entity_type": "study_phase",
                "data": md.study_phase.to_dict(),
                "confidence": 0.9,
                "source_pages": result.pages_used,
            })

        # Governance dates (protocol version/approval/effective dates)
        for gd in md.governance_dates:
            entities.append({
                "id": gd.id,
                "entity_type": "governance_date",
                "data": gd.to_dict(),
                "confidence": 0.85,
                "source_pages": result.pages_used,
            })

        # Emit a metadata entity so the generator can set study.name,
        # versionIdentifier (from amendment/protocol version), and rationale.
        version_id = md.amendment_number or md.protocol_version or "1"
        entities.append({
            "id": "study_metadata_1",
            "entity_type": "metadata",
            "data": {
                "name": md.study_name,
                "description": md.study_description or "",
                "label": "",
                "versionIdentifier": version_id,
            },
            "confidence": 0.9,
            "source_pages": result.pages_used,
        })

        return {
            "entities": entities,
            "confidence": 0.85,
            "metadata_summary": {
                "study_name": md.study_name,
                "title_count": len(md.titles),
                "identifier_count": len(md.identifiers),
                "organization_count": len(md.organizations),
            },
            "raw_response": result.raw_response,
        }
