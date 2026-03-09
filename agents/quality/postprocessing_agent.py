"""
SoA Post-Processing Agent - Normalizes and repairs extracted SoA data.

Bridges the gap between raw extraction output and USDM-compliant output by:
- Normalizing entity names (remove timing text, footnote markers)
- Filling missing required fields with sensible defaults
- Injecting epochs/encounters from header structure when missing
- Assigning activityGroupIds from header structure
- Resolving activity-group links by name matching
- Normalizing superscript footnote references in entity names
- Standardizing IDs (hyphens → underscores)
- Normalizing timing codes to CDISC controlled terminology

Equivalent to legacy pipeline steps 7-8 (soa_postprocess_consolidated.py +
soa_validate_header.py) plus v2 pipeline's _resolve_activity_group_links()
and normalize_soa_with_footnotes().
"""

import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from agents.base import AgentCapabilities, AgentResult, AgentState, AgentTask, BaseAgent
from agents.context_store import ContextStore

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class PostProcessingFix:
    """Record of a fix applied during post-processing."""
    fix_type: str       # e.g. "name_normalized", "field_filled", "id_standardized"
    entity_id: str
    entity_type: str
    field_name: str
    old_value: Any
    new_value: Any
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fix_type": self.fix_type,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "field_name": self.field_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "reason": self.reason,
        }


@dataclass
class PostProcessingReport:
    """Report of all post-processing actions."""
    total_entities: int = 0
    names_normalized: int = 0
    fields_filled: int = 0
    ids_standardized: int = 0
    groups_linked: int = 0
    superscripts_cleaned: int = 0
    epochs_injected: int = 0
    encounters_injected: int = 0
    timing_codes_normalized: int = 0
    fixes: List[PostProcessingFix] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_entities": self.total_entities,
            "names_normalized": self.names_normalized,
            "fields_filled": self.fields_filled,
            "ids_standardized": self.ids_standardized,
            "groups_linked": self.groups_linked,
            "superscripts_cleaned": self.superscripts_cleaned,
            "epochs_injected": self.epochs_injected,
            "encounters_injected": self.encounters_injected,
            "timing_codes_normalized": self.timing_codes_normalized,
            "fixes_count": len(self.fixes),
            "fixes": [f.to_dict() for f in self.fixes],
        }


# ---------------------------------------------------------------------------
# Pure helper functions
# ---------------------------------------------------------------------------

# Patterns for timing text that gets mixed into entity names
_TIMING_PATTERNS = [
    r"\s*\((?:Day|Week|Month|Visit|Hour|Year)\s*[-\d]+.*?\)\s*$",
    r"\s*[-–]\s*(?:Day|Week|Month|Visit)\s*[-\d]+.*$",
]
_TIMING_RE = [re.compile(p, re.IGNORECASE) for p in _TIMING_PATTERNS]

# Superscript Unicode characters
_SUPERSCRIPT_MAP = {
    '⁰': '0', '¹': '1', '²': '2', '³': '3', '⁴': '4',
    '⁵': '5', '⁶': '6', '⁷': '7', '⁸': '8', '⁹': '9',
    'ᵃ': 'a', 'ᵇ': 'b', 'ᶜ': 'c', 'ᵈ': 'd', 'ᵉ': 'e',
    'ᶠ': 'f', 'ᵍ': 'g', 'ʰ': 'h', 'ⁱ': 'i', 'ʲ': 'j',
    'ᵏ': 'k', 'ˡ': 'l', 'ᵐ': 'm', 'ⁿ': 'n', 'ᵒ': 'o',
    'ᵖ': 'p', 'ʳ': 'r', 'ˢ': 's', 'ᵗ': 't', 'ᵘ': 'u',
    'ᵛ': 'v', 'ʷ': 'w', 'ˣ': 'x', 'ʸ': 'y', 'ᶻ': 'z',
}
_SUPERSCRIPT_RE = re.compile('[' + ''.join(_SUPERSCRIPT_MAP.keys()) + ']+')


def normalize_entity_name(name: str) -> str:
    """Remove timing text from entity names (e.g., 'Vital Signs (Day 1)' → 'Vital Signs')."""
    if not name:
        return name
    cleaned = name.strip()
    for pat in _TIMING_RE:
        cleaned = pat.sub("", cleaned)
    return cleaned.strip()


def strip_superscripts(name: str) -> str:
    """Remove superscript footnote references from entity names."""
    if not name:
        return name
    return _SUPERSCRIPT_RE.sub("", name).strip()


def standardize_id(id_str: str) -> str:
    """Standardize entity IDs: replace hyphens with underscores."""
    if not id_str or not isinstance(id_str, str):
        return id_str
    return id_str.replace("-", "_")


# Required field defaults by entity type
_REQUIRED_FIELD_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "study": {"name": "Auto-generated Study", "instanceType": "Study"},
    "study_version": {"versionIdentifier": "1.0.0", "instanceType": "StudyVersion"},
    "epoch": {"instanceType": "Epoch"},
    "encounter": {"instanceType": "Encounter", "type": {"code": "C25426", "decode": "Visit"}},
    "activity": {"instanceType": "Activity"},
    "activity_group": {"instanceType": "ActivityGroup"},
    "planned_timepoint": {"instanceType": "PlannedTimepoint"},
}

# Timing code normalization maps
_PT_TYPE_CODE_MAP = {"Fixed Reference": "C99073"}
_REL_TO_FROM_CODE_MAP = {"Start to Start": "C99074"}


# ---------------------------------------------------------------------------
# SoAPostProcessingAgent
# ---------------------------------------------------------------------------

class SoAPostProcessingAgent(BaseAgent):
    """
    Post-processes extracted SoA data to normalize, fill gaps, and repair
    entity relationships before final USDM generation.

    Runs after extraction agents and before validation/USDM generation.
    Equivalent to legacy soa_postprocess_consolidated.py + soa_validate_header.py
    plus v2 pipeline's activity-group linking and superscript normalization.
    """

    def __init__(
        self,
        agent_id: str = "postprocessing_agent",
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(agent_id=agent_id, config=config or {})

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        self.set_state(AgentState.READY)
        self._logger.info(f"[{self.agent_id}] Initialized")

    def terminate(self) -> None:
        self.set_state(AgentState.TERMINATED)

    def get_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            agent_type="quality",
            input_types=["context_data"],
            output_types=["postprocessed_entities", "postprocessing_report"],
            dependencies=["execution_extraction"],
            supports_parallel=False,
            timeout_seconds=300,
        )

    # ------------------------------------------------------------------
    # Main execution
    # ------------------------------------------------------------------

    def execute(self, task: AgentTask) -> AgentResult:
        """
        Post-process entities from the Context Store or input data.

        Input data can contain:
        - "entities": list of entity dicts
        - "context_store": a ContextStore instance
        - "header_structure": dict with header analysis results (epochs, encounters, groups)
        """
        entities: List[Dict[str, Any]] = list(task.input_data.get("entities", []))
        context_store: Optional[ContextStore] = (
            task.input_data.get("context_store") or self._context_store
        )
        header_structure = task.input_data.get("header_structure", {})

        if not entities and context_store:
            entities = self._entities_from_store(context_store)

        if not entities:
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=False,
                error="No entities provided for post-processing",
            )

        report = PostProcessingReport(total_entities=len(entities))

        # Step 1: Standardize IDs
        entities, id_fixes = self._standardize_all_ids(entities)
        report.ids_standardized = len(id_fixes)
        report.fixes.extend(id_fixes)

        # Step 2: Normalize entity names (remove timing text)
        entities, name_fixes = self._normalize_names(entities)
        report.names_normalized = len(name_fixes)
        report.fixes.extend(name_fixes)

        # Step 3: Strip superscript footnote references
        entities, super_fixes = self._strip_superscripts(entities)
        report.superscripts_cleaned = len(super_fixes)
        report.fixes.extend(super_fixes)

        # Step 4: Fill missing required fields
        entities, field_fixes = self._fill_required_fields(entities)
        report.fields_filled = len(field_fixes)
        report.fixes.extend(field_fixes)

        # Step 5: Inject epochs/encounters from header structure
        entities, epoch_count, enc_count, inject_fixes = self._inject_from_header(
            entities, header_structure
        )
        report.epochs_injected = epoch_count
        report.encounters_injected = enc_count
        report.fixes.extend(inject_fixes)

        # Step 6: Resolve activity-group links
        entities, group_fixes = self._resolve_activity_groups(entities, header_structure)
        report.groups_linked = len(group_fixes)
        report.fixes.extend(group_fixes)

        # Step 7: Normalize timing codes
        entities, timing_fixes = self._normalize_timing_codes(entities)
        report.timing_codes_normalized = len(timing_fixes)
        report.fixes.extend(timing_fixes)

        # Update context store
        if context_store:
            self._update_context_store(context_store, entities)

        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            success=True,
            data={
                "entities": entities,
                "report": report.to_dict(),
            },
            confidence_score=1.0,
        )

    # ------------------------------------------------------------------
    # Step 1: Standardize IDs
    # ------------------------------------------------------------------

    @staticmethod
    def _standardize_all_ids(
        entities: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], List[PostProcessingFix]]:
        """Replace hyphens with underscores in all entity IDs and references."""
        fixes: List[PostProcessingFix] = []

        def _rewrite_id(value: Any) -> Any:
            if isinstance(value, str) and "-" in value:
                return standardize_id(value)
            if isinstance(value, list):
                return [_rewrite_id(v) for v in value]
            if isinstance(value, dict):
                return {k: _rewrite_id(v) for k, v in value.items()}
            return value

        for entity in entities:
            old_id = entity.get("id", "")
            new_id = standardize_id(old_id)
            if old_id and new_id != old_id:
                entity["id"] = new_id
                fixes.append(PostProcessingFix(
                    fix_type="id_standardized",
                    entity_id=new_id,
                    entity_type=entity.get("entity_type", ""),
                    field_name="id",
                    old_value=old_id,
                    new_value=new_id,
                    reason="Standardized hyphenated ID to underscores",
                ))

            # Rewrite references in data
            data = entity.get("data", {})
            for key in list(data.keys()):
                new_val = _rewrite_id(data[key])
                if new_val != data[key]:
                    data[key] = new_val

        return entities, fixes

    # ------------------------------------------------------------------
    # Step 2: Normalize entity names
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_names(
        entities: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], List[PostProcessingFix]]:
        """Remove timing text from entity names (except encounters - they need timepoint info)."""
        fixes: List[PostProcessingFix] = []
        for entity in entities:
            entity_type = entity.get("entity_type", "")
            # Skip normalization for encounters - they need timepoint information preserved
            if entity_type == "encounter":
                continue
            
            data = entity.get("data", {})
            for key in ("name", "label"):
                original = data.get(key)
                if original and isinstance(original, str):
                    cleaned = normalize_entity_name(original)
                    if cleaned != original:
                        data[key] = cleaned
                        fixes.append(PostProcessingFix(
                            fix_type="name_normalized",
                            entity_id=entity.get("id", ""),
                            entity_type=entity_type,
                            field_name=key,
                            old_value=original,
                            new_value=cleaned,
                            reason="Removed timing text from entity name",
                        ))
        return entities, fixes

    # ------------------------------------------------------------------
    # Step 3: Strip superscript footnote references
    # ------------------------------------------------------------------

    @staticmethod
    def _strip_superscripts(
        entities: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], List[PostProcessingFix]]:
        """Remove superscript footnote refs from entity names."""
        fixes: List[PostProcessingFix] = []
        for entity in entities:
            data = entity.get("data", {})
            for key in ("name", "label"):
                original = data.get(key)
                if original and isinstance(original, str):
                    cleaned = strip_superscripts(original)
                    if cleaned != original:
                        # Preserve original in a metadata field
                        data.setdefault("_original_name", original)
                        data[key] = cleaned
                        fixes.append(PostProcessingFix(
                            fix_type="superscript_cleaned",
                            entity_id=entity.get("id", ""),
                            entity_type=entity.get("entity_type", ""),
                            field_name=key,
                            old_value=original,
                            new_value=cleaned,
                            reason="Removed superscript footnote references",
                        ))
        return entities, fixes

    # ------------------------------------------------------------------
    # Step 4: Fill missing required fields
    # ------------------------------------------------------------------

    @staticmethod
    def _fill_required_fields(
        entities: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], List[PostProcessingFix]]:
        """Fill missing required fields with sensible defaults."""
        fixes: List[PostProcessingFix] = []
        for entity in entities:
            etype = entity.get("entity_type", "")
            defaults = _REQUIRED_FIELD_DEFAULTS.get(etype, {})
            data = entity.setdefault("data", {})
            for field_name, default_value in defaults.items():
                if field_name not in data or data[field_name] is None or data[field_name] == "":
                    data[field_name] = default_value
                    fixes.append(PostProcessingFix(
                        fix_type="field_filled",
                        entity_id=entity.get("id", ""),
                        entity_type=etype,
                        field_name=field_name,
                        old_value=None,
                        new_value=default_value,
                        reason=f"Filled missing required field with default",
                    ))
        return entities, fixes

    # ------------------------------------------------------------------
    # Step 5: Inject epochs/encounters from header structure
    # ------------------------------------------------------------------

    @staticmethod
    def _inject_from_header(
        entities: List[Dict[str, Any]],
        header_structure: Dict[str, Any],
    ) -> Tuple[List[Dict[str, Any]], int, int, List[PostProcessingFix]]:
        """Inject missing epochs and encounters from header structure analysis."""
        fixes: List[PostProcessingFix] = []
        epoch_count = 0
        enc_count = 0

        if not header_structure:
            return entities, 0, 0, fixes

        existing_ids: Set[str] = {e.get("id", "") for e in entities}

        # Inject epochs
        header_epochs = header_structure.get("epochs", [])
        for epoch in header_epochs:
            epoch_id = epoch.get("id", "")
            if epoch_id and epoch_id not in existing_ids:
                entities.append({
                    "id": epoch_id,
                    "entity_type": "epoch",
                    "data": {
                        "id": epoch_id,
                        "name": epoch.get("name", ""),
                        "description": epoch.get("description", ""),
                        "instanceType": "Epoch",
                    },
                })
                existing_ids.add(epoch_id)
                epoch_count += 1
                fixes.append(PostProcessingFix(
                    fix_type="epoch_injected",
                    entity_id=epoch_id,
                    entity_type="epoch",
                    field_name="id",
                    old_value=None,
                    new_value=epoch_id,
                    reason="Injected epoch from header structure",
                ))

        # Inject encounters
        header_encounters = header_structure.get("encounters", [])
        for enc in header_encounters:
            enc_id = enc.get("id", "")
            if enc_id and enc_id not in existing_ids:
                entities.append({
                    "id": enc_id,
                    "entity_type": "encounter",
                    "data": {
                        "id": enc_id,
                        "name": enc.get("name", ""),
                        "description": enc.get("description", ""),
                        "type": {"code": "C25426", "decode": "Visit"},
                        "instanceType": "Encounter",
                    },
                })
                existing_ids.add(enc_id)
                enc_count += 1
                fixes.append(PostProcessingFix(
                    fix_type="encounter_injected",
                    entity_id=enc_id,
                    entity_type="encounter",
                    field_name="id",
                    old_value=None,
                    new_value=enc_id,
                    reason="Injected encounter from header structure",
                ))

        return entities, epoch_count, enc_count, fixes

    # ------------------------------------------------------------------
    # Step 6: Resolve activity-group links
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_activity_groups(
        entities: List[Dict[str, Any]],
        header_structure: Dict[str, Any],
    ) -> Tuple[List[Dict[str, Any]], List[PostProcessingFix]]:
        """Link activities to activity groups using header structure and name matching."""
        fixes: List[PostProcessingFix] = []

        if not header_structure:
            return entities, fixes

        # Build group name→id map from header structure
        header_groups = header_structure.get("activityGroups", [])
        if not header_groups:
            return entities, fixes

        # Build activity_name → group_id from header groups
        name_to_group: Dict[str, str] = {}
        for group in header_groups:
            gid = group.get("id", "")
            activity_names = group.get("activity_names", []) or group.get("activities", [])
            for act_name in activity_names:
                if act_name and isinstance(act_name, str):
                    name_to_group[act_name.strip().lower()] = gid

        # Assign activityGroupId to activities that don't have one
        for entity in entities:
            if entity.get("entity_type") != "activity":
                continue
            data = entity.get("data", {})
            if data.get("activityGroupId"):
                continue  # Already assigned

            act_name = (data.get("name") or "").strip().lower()
            if act_name and act_name in name_to_group:
                gid = name_to_group[act_name]
                data["activityGroupId"] = gid
                fixes.append(PostProcessingFix(
                    fix_type="group_linked",
                    entity_id=entity.get("id", ""),
                    entity_type="activity",
                    field_name="activityGroupId",
                    old_value=None,
                    new_value=gid,
                    reason=f"Linked activity to group '{gid}' by name matching",
                ))

        return entities, fixes

    # ------------------------------------------------------------------
    # Step 7: Normalize timing codes
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_timing_codes(
        entities: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], List[PostProcessingFix]]:
        """Normalize timing-related codes to CDISC controlled terminology."""
        fixes: List[PostProcessingFix] = []

        for entity in entities:
            etype = entity.get("entity_type", "")
            data = entity.get("data", {})

            if etype == "planned_timepoint":
                # Normalize type code
                t = data.get("type")
                if isinstance(t, dict):
                    code_val = t.get("code", "")
                    if code_val in _PT_TYPE_CODE_MAP:
                        old = t.get("code")
                        t["code"] = _PT_TYPE_CODE_MAP[code_val]
                        if not t.get("decode"):
                            t["decode"] = code_val
                        fixes.append(PostProcessingFix(
                            fix_type="timing_code_normalized",
                            entity_id=entity.get("id", ""),
                            entity_type=etype,
                            field_name="type.code",
                            old_value=old,
                            new_value=t["code"],
                            reason="Normalized timing type code to CDISC CT",
                        ))
                elif isinstance(t, str) and t in _PT_TYPE_CODE_MAP:
                    data["type"] = {"code": _PT_TYPE_CODE_MAP[t], "decode": t}
                    fixes.append(PostProcessingFix(
                        fix_type="timing_code_normalized",
                        entity_id=entity.get("id", ""),
                        entity_type=etype,
                        field_name="type",
                        old_value=t,
                        new_value=data["type"],
                        reason="Converted string type to coded type with CDISC CT",
                    ))

            elif etype == "encounter":
                # Default encounter type to Visit if missing
                t = data.get("type")
                if not t or (isinstance(t, dict) and not t.get("code") and not t.get("decode")):
                    data["type"] = {"code": "C25426", "decode": "Visit"}
                    fixes.append(PostProcessingFix(
                        fix_type="timing_code_normalized",
                        entity_id=entity.get("id", ""),
                        entity_type=etype,
                        field_name="type",
                        old_value=t,
                        new_value=data["type"],
                        reason="Set default encounter type to Visit",
                    ))

        return entities, fixes

    # ------------------------------------------------------------------
    # Context Store helpers
    # ------------------------------------------------------------------

    def _update_context_store(
        self, store: ContextStore, entities: List[Dict[str, Any]]
    ) -> None:
        """Update the context store with post-processed entities."""
        for entity in entities:
            eid = entity.get("id", "")
            if not eid:
                continue
            try:
                existing = store.get_entity(eid)
                if existing:
                    store.update_entity(
                        eid,
                        entity.get("data", {}),
                        agent_id=self.agent_id,
                    )
            except (KeyError, ValueError):
                pass

    @staticmethod
    def _entities_from_store(store: ContextStore) -> List[Dict[str, Any]]:
        """Convert Context Store entities to list-of-dicts format."""
        result: List[Dict[str, Any]] = []
        for entity in store.query_entities():
            result.append({
                "id": entity.id,
                "entity_type": entity.entity_type,
                "data": dict(entity.data),
                "relationships": dict(entity.relationships),
            })
        return result
