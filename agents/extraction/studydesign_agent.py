"""
StudyDesignAgent - Extracts study design structure from protocol.

Wraps extraction/studydesign/extractor.py with the agent framework.
"""

import logging
from typing import Any, Dict, List, Optional

from agents.base import AgentCapabilities, AgentTask
from agents.extraction.base_extraction_agent import BaseExtractionAgent

logger = logging.getLogger(__name__)


class StudyDesignAgent(BaseExtractionAgent):
    """
    Extracts study design structure: arms, cohorts, cells, epochs,
    blinding, randomization, and control type.

    Depends on SoA data (epochs/arms from Context Store) when available.
    """

    def __init__(self, agent_id: str = "studydesign_agent", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id=agent_id, config=config)

    def get_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            agent_type="studydesign_extraction",
            input_types=["pdf", "protocol_text"],
            output_types=[
                "study_design", "study_arm", "study_cohort",
                "study_cell", "study_element",
            ],
            dependencies=["metadata_extraction"],
            supports_parallel=True,
            timeout_seconds=420,
        )

    def extract(self, pdf_path: str, protocol_text: str, model: str,
                output_dir: str, task: AgentTask) -> Optional[Dict[str, Any]]:
        from extraction.studydesign.extractor import extract_study_design

        pages = task.input_data.get("pages")

        # Pull existing epochs/arms from Context Store for reference
        existing_epochs = task.input_data.get("existing_epochs")
        existing_arms = task.input_data.get("existing_arms")

        if self._context_store:
            if not existing_epochs:
                epoch_entities = self._context_store.query_entities("epoch")
                existing_epochs = [e.data for e in epoch_entities]
            if not existing_arms:
                arm_entities = self._context_store.query_entities("study_arm")
                existing_arms = [e.data for e in arm_entities]

        result = extract_study_design(
            pdf_path=pdf_path,
            model_name=model,
            pages=pages,
            protocol_text=protocol_text or None,
            existing_epochs=existing_epochs,
            existing_arms=existing_arms,
        )

        if not result.success or not result.data:
            return None

        data = result.data
        entities = []

        # Study design
        if data.study_design:
            entities.append({
                "id": data.study_design.id,
                "entity_type": "study_design",
                "data": data.study_design.to_dict(),
                "confidence": 0.85,
                "source_pages": result.pages_used,
            })

        # Arms
        for arm in data.arms:
            entities.append({
                "id": arm.id,
                "entity_type": "study_arm",
                "data": arm.to_dict(),
                "confidence": 0.85,
                "source_pages": result.pages_used,
            })

        # Cohorts
        for cohort in data.cohorts:
            entities.append({
                "id": cohort.id,
                "entity_type": "study_cohort",
                "data": cohort.to_dict(),
                "confidence": 0.8,
                "source_pages": result.pages_used,
            })

        # Cells
        for cell in data.cells:
            entities.append({
                "id": cell.id,
                "entity_type": "study_cell",
                "data": cell.to_dict(),
                "confidence": 0.8,
                "source_pages": result.pages_used,
            })

        # Elements
        for elem in data.elements:
            entities.append({
                "id": elem.id,
                "entity_type": "study_element",
                "data": elem.to_dict(),
                "confidence": 0.8,
                "source_pages": result.pages_used,
            })

        return {
            "entities": entities,
            "confidence": 0.85,
            "design_summary": {
                "arm_count": len(data.arms),
                "cohort_count": len(data.cohorts),
                "cell_count": len(data.cells),
            },
            "raw_response": result.raw_response,
        }
