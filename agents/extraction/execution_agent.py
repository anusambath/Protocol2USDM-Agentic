"""
ExecutionAgent - Extracts execution model from protocol.

Wraps extraction/execution/pipeline_integration.py with the agent framework.
The execution module has multiple sub-extractors (time anchors, repetitions,
state machines, dosing, etc.) orchestrated by extract_execution_model().
"""

import logging
from typing import Any, Dict, List, Optional

from agents.base import AgentCapabilities, AgentTask
from agents.extraction.base_extraction_agent import BaseExtractionAgent

logger = logging.getLogger(__name__)


class ExecutionAgent(BaseExtractionAgent):
    """
    Extracts the full execution model: time anchors, repetitions,
    execution type classifications, crossover design, traversal
    constraints, footnote conditions, endpoint algorithms, derived
    variables, state machines, dosing regimens, visit windows,
    and stratification.

    Depends on SoA agents for encounter/activity context.
    """

    def __init__(self, agent_id: str = "execution_agent", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id=agent_id, config=config)

    def get_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            agent_type="execution_extraction",
            input_types=["pdf"],
            output_types=[
                "time_anchor", "repetition", "execution_type",
                "traversal_constraint", "footnote_condition",
                "state_machine", "dosing_regimen", "visit_window",
            ],
            dependencies=["soa_vision_extraction", "soa_text_extraction"],
            supports_parallel=True,
            timeout_seconds=600,
        )

    def extract(self, pdf_path: str, protocol_text: str, model: str,
                output_dir: str, task: AgentTask) -> Optional[Dict[str, Any]]:
        from extraction.execution.pipeline_integration import extract_execution_model

        # Pull SoA data from Context Store if available
        soa_data = task.input_data.get("soa_data")
        activities = task.input_data.get("activities")
        sap_path = task.input_data.get("sap_path")

        if self._context_store and not soa_data:
            soa_entities = self._context_store.query_entities("soa_table")
            if soa_entities:
                soa_data = soa_entities[0].data

        result = extract_execution_model(
            pdf_path=pdf_path,
            model=model,
            activities=activities,
            soa_data=soa_data,
            sap_path=sap_path,
            output_dir=output_dir or None,
        )

        if not result.success or not result.data:
            return None

        data = result.data
        entities = []

        for anchor in data.time_anchors:
            entities.append({
                "id": anchor.id,
                "entity_type": "time_anchor",
                "data": anchor.to_dict(),
                "confidence": 0.8,
                "source_pages": result.pages_used,
            })

        for rep in data.repetitions:
            entities.append({
                "id": rep.id,
                "entity_type": "repetition",
                "data": rep.to_dict(),
                "confidence": 0.8,
                "source_pages": result.pages_used,
            })

        for i, et in enumerate(data.execution_types):
            entities.append({
                "id": f"et_{et.activity_id}" if hasattr(et, 'activity_id') else f"et_{i+1}",
                "entity_type": "execution_type",
                "data": et.to_dict(),
                "confidence": 0.75,
                "source_pages": result.pages_used,
            })

        for tc in data.traversal_constraints:
            entities.append({
                "id": tc.id,
                "entity_type": "traversal_constraint",
                "data": tc.to_dict(),
                "confidence": 0.8,
                "source_pages": result.pages_used,
            })

        for fc in data.footnote_conditions:
            entities.append({
                "id": fc.id,
                "entity_type": "footnote_condition",
                "data": fc.to_dict(),
                "confidence": 0.75,
                "source_pages": result.pages_used,
            })

        if data.state_machine:
            entities.append({
                "id": data.state_machine.id,
                "entity_type": "state_machine",
                "data": data.state_machine.to_dict(),
                "confidence": 0.8,
                "source_pages": result.pages_used,
            })

        for dr in data.dosing_regimens:
            entities.append({
                "id": dr.id,
                "entity_type": "dosing_regimen",
                "data": dr.to_dict(),
                "confidence": 0.8,
                "source_pages": result.pages_used,
            })

        for vw in data.visit_windows:
            entities.append({
                "id": vw.id,
                "entity_type": "visit_window",
                "data": vw.to_dict(),
                "confidence": 0.8,
                "source_pages": result.pages_used,
            })

        return {
            "entities": entities,
            "confidence": 0.8,
            "execution_summary": {
                "time_anchor_count": len(data.time_anchors),
                "repetition_count": len(data.repetitions),
                "execution_type_count": len(data.execution_types),
                "traversal_count": len(data.traversal_constraints),
                "footnote_condition_count": len(data.footnote_conditions),
                "has_state_machine": data.state_machine is not None,
                "dosing_regimen_count": len(data.dosing_regimens),
                "visit_window_count": len(data.visit_windows),
            },
        }
