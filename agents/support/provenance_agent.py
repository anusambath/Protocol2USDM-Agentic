"""
Provenance Agent - Generates provenance metadata and confidence tracking.

Collects provenance from all entities in the Context Store, links them
to USDM entity IDs, computes aggregate confidence, and generates
provenance JSON for the web UI.
"""

import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from agents.base import AgentCapabilities, AgentResult, AgentState, AgentTask, BaseAgent

logger = logging.getLogger(__name__)


@dataclass
class ProvenanceRecord:
    """Provenance record for a single USDM entity."""
    entity_id: str
    entity_type: str
    source_agent_id: str
    confidence_score: float = 0.0
    source_pages: List[int] = field(default_factory=list)
    model_used: str = ""
    source_type: str = "text"  # "text", "vision", "both", "derived"
    extraction_timestamp: str = ""
    parent_entity_id: Optional[str] = None
    contributing_agents: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "source_agent_id": self.source_agent_id,
            "confidence_score": self.confidence_score,
            "source_pages": self.source_pages,
            "model_used": self.model_used,
            "source_type": self.source_type,
            "extraction_timestamp": self.extraction_timestamp,
            "parent_entity_id": self.parent_entity_id,
            "contributing_agents": self.contributing_agents,
        }


@dataclass
class ProvenanceSummary:
    """Summary statistics for provenance across all entities."""
    total_entities: int = 0
    entities_with_provenance: int = 0
    avg_confidence: float = 0.0
    min_confidence: float = 1.0
    max_confidence: float = 0.0
    source_type_counts: Dict[str, int] = field(default_factory=dict)
    agent_contribution_counts: Dict[str, int] = field(default_factory=dict)
    low_confidence_entities: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_entities": self.total_entities,
            "entities_with_provenance": self.entities_with_provenance,
            "coverage_percent": (self.entities_with_provenance / self.total_entities * 100
                                 if self.total_entities > 0 else 0.0),
            "avg_confidence": round(self.avg_confidence, 4),
            "min_confidence": round(self.min_confidence, 4),
            "max_confidence": round(self.max_confidence, 4),
            "source_type_counts": self.source_type_counts,
            "agent_contribution_counts": self.agent_contribution_counts,
            "low_confidence_count": len(self.low_confidence_entities),
        }


# Confidence calculation weights
CONFIDENCE_WEIGHTS = {
    "both": 1.0,       # Vision + text agreement → highest confidence
    "vision": 0.85,    # Vision-only extraction
    "text": 0.80,      # Text-only extraction
    "derived": 0.70,   # Derived from other entities
}

LOW_CONFIDENCE_THRESHOLD = 0.5


def determine_source_type(agent_id: str) -> str:
    """Determine source type from agent ID."""
    if "vision" in agent_id.lower():
        return "vision"
    elif "reconcil" in agent_id.lower():
        return "both"
    elif "enrich" in agent_id.lower() or "valid" in agent_id.lower():
        return "derived"
    return "text"


def compute_aggregate_confidence(
    base_confidence: float,
    source_type: str,
    contributing_agent_count: int,
) -> float:
    """
    Compute aggregate confidence score.

    Formula:
    - Start with base confidence from extraction
    - Apply source type weight
    - Boost slightly for multiple contributing agents (max +0.1)
    """
    weight = CONFIDENCE_WEIGHTS.get(source_type, 0.75)
    weighted = base_confidence * weight

    # Multi-agent boost: +0.02 per additional agent, max +0.1
    if contributing_agent_count > 1:
        boost = min(0.1, 0.02 * (contributing_agent_count - 1))
        weighted = min(1.0, weighted + boost)

    return round(min(1.0, max(0.0, weighted)), 4)


class ProvenanceAgent(BaseAgent):
    """
    Agent that generates provenance metadata for all extracted entities.

    Collects provenance from Context Store entities, computes aggregate
    confidence, determines source types, and generates provenance JSON.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id="provenance", config=config or {})
        self._low_confidence_threshold = (config or {}).get(
            "low_confidence_threshold", LOW_CONFIDENCE_THRESHOLD)

    def initialize(self) -> None:
        self.set_state(AgentState.READY)
        self._logger.info(f"[{self.agent_id}] Initialized")

    def terminate(self) -> None:
        self.set_state(AgentState.TERMINATED)

    def get_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            agent_type="support",
            input_types=["context_store"],
            output_types=["provenance_json"],
        )

    def execute(self, task: AgentTask) -> AgentResult:
        """
        Generate or query provenance.

        Task types:
        - "provenance_generate": Generate full provenance JSON
        - "provenance_query": Query provenance for specific entities

        Input data:
        - output_path (str, optional): Path to write provenance JSON
        - entity_ids (list[str], optional): Specific entity IDs to query
        - entity_types (list[str], optional): Filter by entity types
        """
        if not self._context_store:
            return AgentResult(
                task_id=task.task_id, agent_id=self.agent_id,
                success=False, error="No Context Store available",
            )

        try:
            if task.task_type == "provenance_query":
                return self._handle_query(task)
            return self._handle_generate(task)
        except Exception as e:
            self._logger.error(f"[{self.agent_id}] Provenance generation failed: {e}")
            return AgentResult(
                task_id=task.task_id, agent_id=self.agent_id,
                success=False, error=str(e),
            )

    def _handle_generate(self, task: AgentTask) -> AgentResult:
        """Generate full provenance for all entities."""
        entity_types_filter = set(task.input_data.get("entity_types", []))
        records = self._collect_provenance(entity_types_filter)
        summary = self._compute_summary(records)

        provenance_json = {
            "generated_at": datetime.now().isoformat(),
            "summary": summary.to_dict(),
            "records": [r.to_dict() for r in records],
        }

        # Write to file if requested
        output_path = task.input_data.get("output_path")
        if output_path:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            
            # Check if SOA cell provenance file exists (created by validation.py)
            # If it exists, merge the cells field into our output
            output_dir = os.path.dirname(output_path)
            soa_prov_path = os.path.join(output_dir, "9_final_soa_provenance.json")
            if os.path.exists(soa_prov_path):
                try:
                    with open(soa_prov_path, 'r', encoding='utf-8') as f:
                        soa_prov = json.load(f)
                    
                    # Load id_mapping to convert cell keys to UUIDs
                    id_map_path = os.path.join(output_dir, "id_mapping.json")
                    if os.path.exists(id_map_path):
                        with open(id_map_path, 'r', encoding='utf-8') as f:
                            id_map = json.load(f)
                        
                        # Convert SOA provenance to UUIDs
                        from core.validation import convert_provenance_to_uuids
                        converted_soa_prov = convert_provenance_to_uuids(soa_prov, id_map)
                        
                        # Merge cells and cellFootnotes into our output
                        if 'cells' in converted_soa_prov:
                            provenance_json['cells'] = converted_soa_prov['cells']
                        if 'cellFootnotes' in converted_soa_prov:
                            provenance_json['cellFootnotes'] = converted_soa_prov['cellFootnotes']
                        
                        self._logger.info(f"Merged {len(provenance_json.get('cells', {}))} SOA cells into provenance")
                except Exception as e:
                    self._logger.warning(f"Failed to merge SOA cell provenance: {e}")
            
            # Populate entities section with encounter/activity name mappings
            # The web UI needs {uuid: name} to resolve cell IDs to display names
            self._populate_entities(provenance_json, output_dir)
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(provenance_json, f, indent=2, ensure_ascii=False)

        return AgentResult(
            task_id=task.task_id, agent_id=self.agent_id,
            success=True,
            data={
                "provenance": provenance_json,
                "output_path": output_path,
                "record_count": len(records),
                "summary": summary.to_dict(),
            },
            confidence_score=1.0,
            provenance={
                "agent_id": self.agent_id,
                "entities_tracked": len(records),
                "timestamp": datetime.now().isoformat(),
            },
        )

    def _populate_entities(self, provenance_json: dict, output_dir: str) -> None:
        """Populate entities section with {uuid: name} mappings from USDM data.
        
        The web UI needs this to resolve cell UUIDs to display names for
        encounters and activities in the SOA table.
        """
        try:
            # Find the USDM JSON file
            usdm_files = [f for f in os.listdir(output_dir) 
                         if f.endswith('_usdm.json')]
            if not usdm_files:
                self._logger.warning("No USDM file found for entity population")
                return
            
            usdm_path = os.path.join(output_dir, usdm_files[0])
            with open(usdm_path, 'r', encoding='utf-8') as f:
                usdm_data = json.load(f)
            
            sd = (usdm_data.get('study', {})
                  .get('versions', [{}])[0]
                  .get('studyDesigns', [{}])[0])
            
            entities = {
                'encounters': {
                    enc.get('id'): enc.get('name', 'Unknown')
                    for enc in sd.get('encounters', []) if enc.get('id')
                },
                'activities': {
                    act.get('id'): act.get('name') or act.get('label', 'Unknown')
                    for act in sd.get('activities', []) if act.get('id')
                },
                'epochs': {
                    epoch.get('id'): epoch.get('name', 'Unknown')
                    for epoch in sd.get('epochs', []) if epoch.get('id')
                },
            }
            
            provenance_json['entities'] = entities
            self._logger.info(
                f"Populated entities: {len(entities['encounters'])} encounters, "
                f"{len(entities['activities'])} activities, "
                f"{len(entities['epochs'])} epochs"
            )
        except Exception as e:
            self._logger.warning(f"Failed to populate entities: {e}")

    def _handle_query(self, task: AgentTask) -> AgentResult:
        """Query provenance for specific entities."""
        entity_ids = set(task.input_data.get("entity_ids", []))
        entity_types_filter = set(task.input_data.get("entity_types", []))

        all_records = self._collect_provenance(entity_types_filter)

        if entity_ids:
            records = [r for r in all_records if r.entity_id in entity_ids]
        else:
            records = all_records

        return AgentResult(
            task_id=task.task_id, agent_id=self.agent_id,
            success=True,
            data={
                "records": [r.to_dict() for r in records],
                "record_count": len(records),
            },
        )

    def _collect_provenance(self,
                             entity_types_filter: Set[str] = None) -> List[ProvenanceRecord]:
        """Collect provenance records from all Context Store entities."""
        entities = self._context_store.query_entities()
        records = []

        for entity in entities:
            # Skip infrastructure types
            if entity.entity_type in ("pdf_page", "checkpoint", "error_record"):
                continue

            if entity_types_filter and entity.entity_type not in entity_types_filter:
                continue

            prov = entity.provenance
            source_type = determine_source_type(prov.source_agent_id) if prov else "text"

            # Find contributing agents via relationships
            contributing = self._find_contributing_agents(entity.id)

            base_confidence = prov.confidence_score if prov else 0.0
            agg_confidence = compute_aggregate_confidence(
                base_confidence, source_type, len(contributing))

            record = ProvenanceRecord(
                entity_id=entity.id,
                entity_type=entity.entity_type,
                source_agent_id=prov.source_agent_id if prov else "unknown",
                confidence_score=agg_confidence,
                source_pages=prov.source_pages if prov else [],
                model_used=prov.model_used if prov else "",
                source_type=source_type,
                extraction_timestamp=prov.extraction_timestamp.isoformat() if prov else "",
                parent_entity_id=prov.parent_entity_id if prov else None,
                contributing_agents=contributing,
            )
            records.append(record)

        return records

    def _find_contributing_agents(self, entity_id: str) -> List[str]:
        """Find all agents that contributed to an entity."""
        agents = set()
        entity = self._context_store.get_entity(entity_id)
        if entity and entity.provenance:
            agents.add(entity.provenance.source_agent_id)

        # Check related entities for additional contributors
        try:
            related = self._context_store.get_related_entities(entity_id)
            for rel_entity in related:
                if rel_entity.provenance:
                    agents.add(rel_entity.provenance.source_agent_id)
        except (KeyError, ValueError):
            pass

        return sorted(agents)

    def _compute_summary(self, records: List[ProvenanceRecord]) -> ProvenanceSummary:
        """Compute summary statistics from provenance records."""
        summary = ProvenanceSummary()
        summary.total_entities = len(records)

        if not records:
            summary.min_confidence = 0.0
            return summary

        confidences = []
        for r in records:
            if r.source_agent_id != "unknown":
                summary.entities_with_provenance += 1

            confidences.append(r.confidence_score)

            # Source type counts
            summary.source_type_counts[r.source_type] = (
                summary.source_type_counts.get(r.source_type, 0) + 1)

            # Agent contribution counts
            for agent in r.contributing_agents:
                summary.agent_contribution_counts[agent] = (
                    summary.agent_contribution_counts.get(agent, 0) + 1)

            # Low confidence tracking
            if r.confidence_score < self._low_confidence_threshold:
                summary.low_confidence_entities.append(r.entity_id)

        summary.avg_confidence = sum(confidences) / len(confidences)
        summary.min_confidence = min(confidences)
        summary.max_confidence = max(confidences)

        return summary
