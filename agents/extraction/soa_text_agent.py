"""
SoATextAgent - Extracts Schedule of Assessments using text-based models.

Wraps extraction/soa_finder.py and extraction/text_extractor.py
for text-based SoA table extraction.
"""

import logging
from typing import Any, Dict, List, Optional

from agents.base import AgentCapabilities, AgentTask
from agents.extraction.base_extraction_agent import BaseExtractionAgent

logger = logging.getLogger(__name__)


class SoATextAgent(BaseExtractionAgent):
    """
    Extracts SoA table structure from PDF text using text-based LLM models.
    Parses table text patterns to detect epochs, encounters, activities, and cells.

    Depends on SoAVisionAgent — requires header_structure from vision extraction.
    """

    def __init__(self, agent_id: str = "soa_text_agent", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id=agent_id, config=config)

    def get_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            agent_type="soa_text_extraction",
            input_types=["pdf", "protocol_text"],
            output_types=[
                "epoch", "encounter", "activity", "soa_cell",
                "header_structure", "footnote",
            ],
            dependencies=["soa_vision_extraction"],
            supports_parallel=True,
            timeout_seconds=600,
        )

    def extract(self, pdf_path: str, protocol_text: str, model: str,
                output_dir: str, task: AgentTask) -> Optional[Dict[str, Any]]:
        from extraction.soa_finder import find_soa_pages, extract_soa_text
        from extraction.text_extractor import extract_soa_from_text

        soa_pages = task.input_data.get("soa_pages")

        # Step 1: Find SoA pages if not provided
        if not soa_pages:
            soa_pages = find_soa_pages(pdf_path)
            if not soa_pages:
                self._logger.warning("No SoA pages detected")
                return None

        # Step 2: Extract text from SoA pages
        soa_text = protocol_text
        if not soa_text:
            soa_text = extract_soa_text(pdf_path, soa_pages)
            if not soa_text:
                self._logger.warning("Failed to extract SoA text")
                return None

        # Step 3: Get header structure (needed for text extraction)
        # The text extractor needs a HeaderStructure; try to get from Context Store
        header_structure = task.input_data.get("header_structure")

        if self._context_store and not header_structure:
            hs_entities = self._context_store.query_entities("header_structure")
            if hs_entities:
                header_structure = hs_entities[0].data.get("structure")

        # Reconstruct HeaderStructure object if we got a dict from context store
        if isinstance(header_structure, dict):
            from core.usdm_types import HeaderStructure as HS
            header_structure = HS.from_dict(header_structure)

        # Step 4: Extract SoA from text (requires header_structure)
        if header_structure is None:
            self._logger.warning("No header structure available — text extraction requires vision results first")
            return None

        text_result = extract_soa_from_text(
            protocol_text=soa_text,
            model_name=model,
            header_structure=header_structure,
        )

        if not text_result:
            self._logger.warning("Text extraction returned no result")
            return None

        # Step 5: Validate text extraction against vision images
        # This marks confirmed cells as "both" (text + vision agree)
        validated_provenance = None
        if hasattr(text_result, 'provenance') and text_result.provenance:
            try:
                from extraction.validator import validate_extraction, apply_validation_fixes
                
                # Get image paths from task input or extract them
                image_paths = task.input_data.get("soa_images")
                if not image_paths:
                    from extraction.soa_finder import extract_soa_images
                    image_paths = extract_soa_images(
                        pdf_path=pdf_path,
                        page_numbers=soa_pages,
                        output_dir=output_dir or ".",
                    )
                
                if image_paths:
                    # Extract activities and ticks for validation
                    text_activities = []
                    if hasattr(text_result, 'activities'):
                        for activity in text_result.activities:
                            act_dict = activity if isinstance(activity, dict) else {}
                            if not act_dict and hasattr(activity, '__dict__'):
                                act_dict = vars(activity)
                            text_activities.append(act_dict)
                    
                    text_ticks = []
                    if hasattr(text_result, 'activity_timepoints'):
                        for atp in text_result.activity_timepoints:
                            atp_dict = atp.to_dict() if hasattr(atp, 'to_dict') else (atp if isinstance(atp, dict) else {})
                            if not atp_dict and hasattr(atp, '__dict__'):
                                atp_dict = vars(atp)
                            text_ticks.append(atp_dict)
                    
                    # Run validation
                    validation = validate_extraction(
                        text_activities=text_activities,
                        text_ticks=text_ticks,
                        header_structure=header_structure,
                        image_paths=image_paths,
                        model_name=model,
                    )
                    
                    if validation.success:
                        # Apply validation fixes to update provenance
                        # Keep all ticks (remove_hallucinations=False) but mark confirmed ones as "both"
                        fixed_ticks, validated_provenance = apply_validation_fixes(
                            text_ticks=text_ticks,
                            validation=validation,
                            remove_hallucinations=False,
                            add_missed=False,
                            confidence_threshold=0.7,
                        )
                        
                        # Merge validated provenance into text result provenance
                        if validated_provenance:
                            text_result.provenance.merge(validated_provenance)
                            self._logger.info(
                                f"Validation complete: {validation.confirmed_ticks}/{validation.total_ticks_checked} "
                                f"cells confirmed by vision (marked as 'both')"
                            )
                    else:
                        self._logger.warning(f"Validation failed: {validation.error}")
                else:
                    self._logger.warning("No images available for validation")
                    
            except Exception as e:
                self._logger.warning(f"Cell validation failed: {e}")
                # Continue without validation - cells will remain as "text"
        
        # Build LLM ID → entity ID mapping for provenance remapping
        llm_act_id_map: dict = {}  # maps LLM-assigned IDs (act_N) → entity IDs (activity_t_N)
        if hasattr(text_result, 'activities'):
            for i, activity in enumerate(text_result.activities):
                act_dict = activity if isinstance(activity, dict) else {}
                if not act_dict and hasattr(activity, '__dict__'):
                    act_dict = vars(activity)
                llm_id = act_dict.get('id', '') or getattr(activity, 'id', '') or f'act_{i+1}'
                entity_id = f'activity_t_{i+1}'
                llm_act_id_map[llm_id] = entity_id
        
        # Remap provenance cell keys from act_N|enc_N to activity_t_N|encounter_v_N
        # This ensures cell keys match the entity IDs used in the final USDM
        if hasattr(text_result, 'provenance') and text_result.provenance:
            import re as _re
            def _map_enc_id(llm_enc_id: str) -> str:
                m = _re.match(r'^enc_(\d+)$', llm_enc_id)
                if m:
                    return f'encounter_v_{m.group(1)}'
                return llm_enc_id
            
            # Remap cells
            if hasattr(text_result.provenance, 'cells') and text_result.provenance.cells:
                remapped_cells = {}
                for cell_key, source in text_result.provenance.cells.items():
                    if '|' in cell_key:
                        act_id, enc_id = cell_key.split('|', 1)
                        new_act_id = llm_act_id_map.get(act_id, act_id)
                        new_enc_id = _map_enc_id(enc_id)
                        new_key = f'{new_act_id}|{new_enc_id}'
                        remapped_cells[new_key] = source
                    else:
                        remapped_cells[cell_key] = source
                text_result.provenance.cells = remapped_cells
            
            # Remap cellFootnotes
            if hasattr(text_result.provenance, 'cellFootnotes') and text_result.provenance.cellFootnotes:
                remapped_footnotes = {}
                for cell_key, footnotes in text_result.provenance.cellFootnotes.items():
                    if '|' in cell_key:
                        act_id, enc_id = cell_key.split('|', 1)
                        new_act_id = llm_act_id_map.get(act_id, act_id)
                        new_enc_id = _map_enc_id(enc_id)
                        new_key = f'{new_act_id}|{new_enc_id}'
                        remapped_footnotes[new_key] = footnotes
                    else:
                        remapped_footnotes[cell_key] = footnotes
                text_result.provenance.cellFootnotes = remapped_footnotes
        
        # Save provenance to 9_final_soa_provenance.json for later use
        if hasattr(text_result, 'provenance') and text_result.provenance:
            import os
            provenance_path = os.path.join(output_dir, "9_final_soa_provenance.json")
            try:
                text_result.provenance.save(provenance_path)
                self._logger.info(f"Saved SOA provenance to {provenance_path}")
            except Exception as e:
                self._logger.warning(f"Failed to save SOA provenance: {e}")

        entities = []

        # Store the text extraction result
        entities.append({
            "id": "soa_text_result",
            "entity_type": "soa_text_extraction",
            "data": {
                "source": "text",
                "page_numbers": soa_pages,
                "result": text_result.to_dict() if hasattr(text_result, 'to_dict') else str(text_result),
            },
            "confidence": 0.75,
            "source_pages": soa_pages,
        })

        # Extract activities if available — also build LLM ID → entity ID map
        llm_act_id_map: dict = {}  # maps LLM-assigned IDs (act_N) → entity IDs (activity_t_N)
        if hasattr(text_result, 'activities'):
            for i, activity in enumerate(text_result.activities):
                act_dict = activity if isinstance(activity, dict) else {}
                if not act_dict and hasattr(activity, '__dict__'):
                    act_dict = vars(activity)
                act_name = act_dict.get('name', '') or getattr(activity, 'name', '') or ''
                llm_id = act_dict.get('id', '') or getattr(activity, 'id', '') or f'act_{i+1}'
                entity_id = f'activity_t_{i+1}'
                llm_act_id_map[llm_id] = entity_id
                entities.append({
                    "id": entity_id,
                    "entity_type": "activity",
                    "data": {
                        "name": act_name,
                        "source": "text",
                        "raw": act_dict if act_dict else {"name": act_name},
                    },
                    "confidence": 0.75,
                    "source_pages": soa_pages,
                })

        # Extract activity_timepoints (SoA tick matrix -> ScheduledActivityInstance)
        # Map LLM IDs (act_N / enc_N) to canonical entity IDs (activity_t_N / encounter_v_N)
        import re as _re
        def _map_enc_id(llm_enc_id: str) -> str:
            m = _re.match(r'^enc_(\d+)$', llm_enc_id)
            if m:
                return f'encounter_v_{m.group(1)}'
            return llm_enc_id

        if hasattr(text_result, 'activity_timepoints'):
            for i, atp in enumerate(text_result.activity_timepoints):
                atp_dict = atp.to_dict() if hasattr(atp, 'to_dict') else (atp if isinstance(atp, dict) else {})
                if not atp_dict and hasattr(atp, '__dict__'):
                    atp_dict = vars(atp)
                raw_act_id = atp_dict.get('activityId', '') or getattr(atp, 'activityId', '')
                raw_enc_id = atp_dict.get('encounterId', '') or getattr(atp, 'encounterId', '')
                # Resolve to canonical entity IDs
                activity_id = llm_act_id_map.get(raw_act_id, raw_act_id)
                encounter_id = _map_enc_id(raw_enc_id)
                if activity_id and encounter_id:
                    # Generate a unique ID for this scheduled instance
                    import uuid
                    instance_id = str(uuid.uuid4()).replace('-', '_')
                    entities.append({
                        "id": instance_id,
                        "entity_type": "scheduled_instance",
                        "data": {
                            "activityId": activity_id,
                            "encounterId": encounter_id,
                            "instanceType": "ScheduledActivityInstance",
                            "footnoteRefs": atp_dict.get('footnoteRefs', []),
                        },
                        "confidence": 0.8,
                        "source_pages": soa_pages,
                    })

        return {
            "entities": entities,
            "confidence": 0.75,
            "text_summary": {
                "soa_pages": soa_pages,
                "activity_count": len([e for e in entities if e["entity_type"] == "activity"]),
                "scheduled_instance_count": len([e for e in entities if e["entity_type"] == "scheduled_instance"]),
            },
        }
