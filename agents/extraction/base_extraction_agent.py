"""
Base Extraction Agent - Common functionality for all extraction agents.

Provides shared logic for LLM integration, provenance tracking,
confidence scoring, and Context Store updates.
"""

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.base import AgentCapabilities, AgentResult, AgentState, AgentTask, BaseAgent
from agents.context_store import ContextEntity, EntityProvenance
from llm_providers import usage_tracker

logger = logging.getLogger(__name__)


class BaseExtractionAgent(BaseAgent):
    """
    Base class for all extraction agents.

    Provides:
    - LLM client integration
    - Provenance tracking for extracted entities
    - Confidence scoring
    - Context Store entity creation helpers
    - Standard extraction workflow
    """

    def __init__(self, agent_id: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id=agent_id, config=config or {})
        self._model_from_config = "model" in (config or {})
        self._model_name = (config or {}).get("model", "gemini-2.5-pro")

    def initialize(self) -> None:
        self.set_state(AgentState.READY)
        self._logger.info(f"[{self.agent_id}] Initialized (model={self._model_name})")

    def terminate(self) -> None:
        self.set_state(AgentState.TERMINATED)

    def execute(self, task: AgentTask) -> AgentResult:
        """
        Standard extraction workflow:
        1. Get input data from task
        2. Call extract() (implemented by subclass)
        3. Store entities in Context Store
        4. Return result with provenance
        """
        pdf_path = task.input_data.get("pdf_path", "")
        protocol_text = task.input_data.get("protocol_text", "")
        # Agent-level model override (set via config) takes priority over pipeline default
        if self._model_from_config:
            model = self._model_name
        else:
            model = task.input_data.get("model", self._model_name)
        output_dir = task.input_data.get("output_dir", "")

        # Tag this thread's LLM calls with the agent id, then snapshot current stats
        usage_tracker.set_phase(self.agent_id)
        _before = usage_tracker.get_summary()["by_phase"].get(
            self.agent_id, {"input": 0, "output": 0, "calls": 0}
        )

        try:
            result_data = self.extract(
                pdf_path=pdf_path,
                protocol_text=protocol_text,
                model=model,
                output_dir=output_dir,
                task=task,
            )

            if result_data is None:
                return AgentResult(
                    task_id=task.task_id,
                    agent_id=self.agent_id,
                    success=False,
                    error="Extraction returned no data",
                )

            # Store entities in Context Store
            entities_stored = self._store_entities(result_data, task)

            # Save extraction output to JSON file
            if output_dir:
                self._save_output(result_data, output_dir)

            confidence = result_data.get("confidence", 0.0)

            # Compute token / call delta for this agent's execution
            _after = usage_tracker.get_summary()["by_phase"].get(
                self.agent_id, {"input": 0, "output": 0, "calls": 0}
            )
            tokens_used = (
                (_after["input"] + _after["output"])
                - (_before["input"] + _before["output"])
            )
            api_calls = _after["calls"] - _before["calls"]

            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                data=result_data,
                confidence_score=confidence,
                tokens_used=tokens_used,
                api_calls=api_calls,
                provenance={
                    "agent_id": self.agent_id,
                    "model_used": model,
                    "entities_stored": entities_stored,
                    "timestamp": datetime.now().isoformat(),
                },
            )

        except Exception as e:
            self._logger.error(f"[{self.agent_id}] Extraction failed: {e}")
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=False,
                error=str(e),
            )

    def extract(self, pdf_path: str, protocol_text: str, model: str,
                output_dir: str, task: AgentTask) -> Optional[Dict[str, Any]]:
        """
        Perform the actual extraction. Must be implemented by subclasses.

        Returns a dict with at minimum:
        - "entities": list of dicts to store in Context Store
        - "confidence": float 0.0-1.0
        """
        raise NotImplementedError("Subclasses must implement extract()")

    # --- Context Store Helpers ---

    def _store_entities(self, result_data: Dict[str, Any],
                        task: AgentTask) -> int:
        """Store extracted entities in the Context Store."""
        if not self._context_store:
            return 0

        entities = result_data.get("entities", [])
        count = 0
        for entity_data in entities:
            try:
                entity = ContextEntity(
                    id=entity_data.get("id", str(uuid.uuid4())),
                    entity_type=entity_data.get("entity_type", "unknown"),
                    data=entity_data.get("data", {}),
                    provenance=EntityProvenance(
                        entity_id=entity_data.get("id", ""),
                        source_agent_id=self.agent_id,
                        confidence_score=entity_data.get("confidence", 0.0),
                        source_pages=entity_data.get("source_pages", []),
                        model_used=self._model_name,
                    ),
                )
                self._context_store.add_entity(entity)
                count += 1
            except ValueError:
                # Entity already exists, update it
                try:
                    self._context_store.update_entity(
                        entity_data["id"],
                        entity_data.get("data", {}),
                        agent_id=self.agent_id,
                    )
                    count += 1
                except KeyError:
                    pass
        return count

    # --- Output File Numbering ---
    # Format: <step>_<category>_<name>
    # Categories: extraction, quality, support
    # Step numbers are unique and sequential across the full pipeline
    _AGENT_FILE_PREFIX = {
        "metadata_agent": "01_extraction_metadata",
        "soa_vision_agent": "02_extraction_soa_vision",
        "soa_text_agent": "03_extraction_soa_text",
        "narrative_agent": "04_extraction_narrative",
        "docstructure_agent": "05_extraction_document_structure",
        "eligibility_agent": "06_extraction_eligibility",
        "objectives_agent": "07_extraction_objectives",
        "studydesign_agent": "08_extraction_study_design",
        "procedures_agent": "09_extraction_procedures_devices",
        "interventions_agent": "10_extraction_interventions",
        "scheduling_agent": "11_extraction_scheduling_logic",
        "execution_agent": "12_extraction_execution_model",
        "advanced_agent": "13_extraction_advanced_entities",
        "biomedical_concept_agent": "14_extraction_biomedical_concepts",
    }

    def _save_output(self, result_data: Dict[str, Any], output_dir: str) -> None:
        """Save extraction result to a JSON file in the output directory."""
        prefix = self._AGENT_FILE_PREFIX.get(self.agent_id, self.agent_id)
        filename = f"{prefix}.json"
        output_path = os.path.join(output_dir, filename)

        # Build serializable output (exclude raw_response which may not be JSON-safe)
        output = {
            "agent_id": self.agent_id,
            "timestamp": datetime.now().isoformat(),
            "confidence": result_data.get("confidence", 0.0),
            "entity_count": len(result_data.get("entities", [])),
            "entities": result_data.get("entities", []),
        }
        # Include any summary keys (e.g. metadata_summary, vision_summary)
        for key, value in result_data.items():
            if key.endswith("_summary") and key not in output:
                output[key] = value

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=2, ensure_ascii=False, default=str)
            self._logger.info(f"[{self.agent_id}] Saved output to {output_path}")
        except Exception as e:
            self._logger.warning(f"[{self.agent_id}] Failed to save output: {e}")

    def create_provenance(self, entity_id: str, confidence: float = 0.0,
                          source_pages: Optional[List[int]] = None) -> EntityProvenance:
        """Create a provenance record for an extracted entity."""
        return EntityProvenance(
            entity_id=entity_id,
            source_agent_id=self.agent_id,
            confidence_score=confidence,
            source_pages=source_pages or [],
            model_used=self._model_name,
        )
