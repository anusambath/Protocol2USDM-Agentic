"""
SoAVisionAgent - Extracts Schedule of Assessments using vision models.

Wraps extraction/soa_finder.py and extraction/header_analyzer.py
for vision-based SoA table extraction.
"""

import logging
from typing import Any, Dict, List, Optional

from agents.base import AgentCapabilities, AgentTask
from agents.extraction.base_extraction_agent import BaseExtractionAgent

logger = logging.getLogger(__name__)


class SoAVisionAgent(BaseExtractionAgent):
    """
    Extracts SoA table structure from PDF page images using vision models.
    Detects epochs, encounters, activities, and cell content from images.

    Wave 1 agent - independent, runs in parallel with MetadataAgent.
    """

    def __init__(self, agent_id: str = "soa_vision_agent", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id=agent_id, config=config)

    def get_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            agent_type="soa_vision_extraction",
            input_types=["pdf", "page_images"],
            output_types=[
                "epoch", "encounter", "activity", "soa_cell",
                "header_structure", "footnote",
            ],
            dependencies=[],
            supports_parallel=True,
            timeout_seconds=600,
        )

    def extract(self, pdf_path: str, protocol_text: str, model: str,
                output_dir: str, task: AgentTask) -> Optional[Dict[str, Any]]:
        from extraction.soa_finder import find_soa_pages, extract_soa_images
        from extraction.header_analyzer import analyze_soa_headers

        soa_pages = task.input_data.get("soa_pages")
        image_paths = task.input_data.get("soa_images")

        # Step 1: Find SoA pages if not provided
        if not soa_pages:
            soa_pages = find_soa_pages(pdf_path)
            if not soa_pages:
                self._logger.warning("No SoA pages detected")
                return None

        # Cap pages to keep vision API fast (increased to 10 to handle multi-page SOA tables)
        if len(soa_pages) > 10:
            self._logger.info(f"Capping SoA pages from {len(soa_pages)} to 10 for vision")
            soa_pages = soa_pages[:10]

        # Step 2: Extract images if not provided
        if not image_paths:
            image_paths = extract_soa_images(
                pdf_path=pdf_path,
                page_numbers=soa_pages,
                output_dir=output_dir or ".",
            )
            if not image_paths:
                self._logger.warning("Failed to extract SoA images")
                return None

        # Step 3: Analyze headers using vision model
        header_result = analyze_soa_headers(
            image_paths=image_paths,
            model_name=model,
        )

        if not header_result or not header_result.structure:
            err = getattr(header_result, 'error', None) if header_result else None
            self._logger.warning(f"Header analysis returned no structure with {model}: {err}")
            # Fallback: retry with the pipeline's main model (e.g. Claude)
            fallback_model = task.input_data.get("model", "")
            if fallback_model and fallback_model != model:
                self._logger.info(f"Retrying header analysis with fallback model: {fallback_model}")
                header_result = analyze_soa_headers(
                    image_paths=image_paths,
                    model_name=fallback_model,
                )
            if not header_result or not header_result.structure:
                err2 = getattr(header_result, 'error', None) if header_result else None
                self._logger.warning(f"Header analysis failed with fallback model: {err2}")
                return None

        structure = header_result.structure
        entities = []

        # Store header structure as entity
        entities.append({
            "id": "soa_header_structure",
            "entity_type": "header_structure",
            "data": {
                "source": "vision",
                "page_numbers": soa_pages,
                "image_count": len(image_paths),
                "structure": structure.to_dict() if hasattr(structure, 'to_dict') else str(structure),
            },
            "confidence": header_result.confidence if hasattr(header_result, 'confidence') else 0.8,
            "source_pages": soa_pages,
        })

        # Extract epochs from header structure
        if hasattr(structure, 'epochs'):
            for i, epoch in enumerate(structure.epochs):
                epoch_name = epoch.name if hasattr(epoch, 'name') else str(epoch)
                entities.append({
                    "id": f"epoch_v_{i+1}",
                    "entity_type": "epoch",
                    "data": {"name": epoch_name, "source": "vision", "order": i},
                    "confidence": 0.85,
                    "source_pages": soa_pages,
                })

        # Extract encounters from header structure
        if hasattr(structure, 'encounters'):
            for i, enc in enumerate(structure.encounters):
                enc_name = enc.name if hasattr(enc, 'name') else str(enc)
                epoch_id = enc.epochId if hasattr(enc, 'epochId') else ""
                entities.append({
                    "id": f"encounter_v_{i+1}",
                    "entity_type": "encounter",
                    "data": {"name": enc_name, "epochId": epoch_id, "source": "vision", "order": i},
                    "confidence": 0.85,
                    "source_pages": soa_pages,
                })

        return {
            "entities": entities,
            "confidence": 0.8,
            "vision_summary": {
                "soa_pages": soa_pages,
                "image_count": len(image_paths),
                "epoch_count": len([e for e in entities if e["entity_type"] == "epoch"]),
                "encounter_count": len([e for e in entities if e["entity_type"] == "encounter"]),
            },
        }
