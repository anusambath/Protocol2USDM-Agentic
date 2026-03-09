"""
BiomedicalConceptAgent — derives BiomedicalConcept entities from SoA activities.

Wave 3 agent: depends on SoA + procedures agents completing first so that
all Activity entities are available in the ContextStore.

Output entity types:
  "biomedical_concept"          → study.versions[0].biomedicalConcepts[]
  "biomedical_concept_category" → study.versions[0].bcCategories[]

Each Activity entity in ContextStore is updated with biomedicalConceptIds
so USDM Activity.biomedicalConceptIds references the generated BCs.
"""

import logging
import re
from typing import Any, Dict, List, Optional

from agents.base import AgentCapabilities, AgentTask
from agents.extraction.base_extraction_agent import BaseExtractionAgent

logger = logging.getLogger(__name__)


class BiomedicalConceptAgent(BaseExtractionAgent):
    """
    Generates BiomedicalConcept entities for every unique SoA activity.

    Reads Activity entities from ContextStore (stored by soa_vision_agent,
    soa_text_agent, and procedures_agent), calls an LLM to produce formal
    BiomedicalConcept + BiomedicalConceptCategory objects, and backfills
    biomedicalConceptIds on each Activity entity.
    """

    def __init__(self, agent_id: str = "biomedical_concept_agent",
                 config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id=agent_id, config=config)

    def get_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            agent_type="biomedical_concept_extraction",
            input_types=["activity"],
            output_types=["biomedical_concept", "biomedical_concept_category"],
            dependencies=[
                "soa_vision_extraction",  # provides activity entities (Wave 1)
                "soa_text_extraction",    # provides additional activity entities (Wave 2)
                "procedures_extraction",  # provides additional activity context (Wave 2)
            ],
            supports_parallel=False,   # reads and writes shared Activity entities
            timeout_seconds=600,
        )

    def extract(self, pdf_path: str, protocol_text: str, model: str,
                output_dir: str, task: AgentTask) -> Optional[Dict[str, Any]]:
        from extraction.biomedical_concepts.extractor import extract_biomedical_concepts

        # Collect activity names from ContextStore
        activity_names = self._collect_activity_names(task)
        if not activity_names:
            logger.warning("No activity names found in ContextStore — skipping BC extraction")
            return None

        logger.info(f"BiomedicalConceptAgent: found {len(activity_names)} activity names")

        result = extract_biomedical_concepts(
            activity_names=activity_names,
            model_name=model,
        )

        if not result.success:
            logger.error(f"BC extraction failed: {result.error}")
            return None

        # Build entity list for the base class to store in ContextStore
        entities = []

        for bc in result.biomedical_concepts:
            entities.append({
                "id": bc.id,
                "entity_type": "biomedical_concept",
                "data": bc.to_dict(),
                "confidence": 0.75,
                "source_pages": [],
            })

        for cat in result.categories:
            entities.append({
                "id": cat.id,
                "entity_type": "biomedical_concept_category",
                "data": cat.to_dict(),
                "confidence": 0.75,
                "source_pages": [],
            })

        # Backfill biomedicalConceptIds on existing Activity entities
        self._backfill_activity_bc_ids(result.biomedical_concepts)

        return {
            "entities": entities,
            "confidence": 0.75,
            "bc_summary": {
                "biomedical_concept_count": len(result.biomedical_concepts),
                "category_count": len(result.categories),
                "activity_count": len(activity_names),
            },
            "raw_response": result.raw_response,
        }

    def _collect_activity_names(self, task: AgentTask) -> List[str]:
        """
        Gather unique activity names from the ContextStore.

        Looks for entities of type 'activity' (stored by soa_vision_agent,
        soa_text_agent, postprocessing, and procedures_agent).
        """
        names: List[str] = []

        if not self._context_store:
            return names

        activity_entities = self._context_store.query_entities("activity")
        for entity in activity_entities:
            data = entity.data or {}
            name = data.get("name") or data.get("activityName") or ""
            if name and name.strip():
                names.append(name.strip())

        return names

    def _backfill_activity_bc_ids(self, bcs: list) -> None:
        """
        Update Activity entities in ContextStore to reference their BiomedicalConcept.

        Matches by normalised activity name (case-insensitive, whitespace-collapsed).
        Each Activity gets the ID of the BiomedicalConcept whose name matches.
        """
        if not self._context_store or not bcs:
            return

        def _norm(s: str) -> str:
            return re.sub(r'\s+', ' ', s.strip().lower())

        # Build normalised name → bc_id lookup
        name_to_bc_id: Dict[str, str] = {_norm(bc.name): bc.id for bc in bcs}
        # Also index synonyms
        for bc in bcs:
            for syn in bc.synonyms:
                name_to_bc_id.setdefault(_norm(syn), bc.id)

        activity_entities = self._context_store.query_entities("activity")
        updated = 0
        for entity in activity_entities:
            data = entity.data or {}
            act_name = data.get("name") or data.get("activityName") or ""
            norm_name = _norm(act_name)
            bc_id = name_to_bc_id.get(norm_name)
            if bc_id:
                existing_ids = data.get("biomedicalConceptIds") or []
                if bc_id not in existing_ids:
                    data["biomedicalConceptIds"] = existing_ids + [bc_id]
                    entity.data = data
                    updated += 1

        if updated:
            logger.info(f"Backfilled biomedicalConceptIds on {updated} Activity entities")
