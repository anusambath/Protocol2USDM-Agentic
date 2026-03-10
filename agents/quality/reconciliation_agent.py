"""
Reconciliation Agent - Merges duplicate entities and resolves conflicts.

Identifies duplicate entities across extraction sources, merges them using
priority-based rules, cleans entity names, reconciles SoA data from vision
and text agents, and generates reconciliation reports.
"""

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Set, Tuple
import logging
import re
import time

from agents.base import (
    AgentCapabilities,
    AgentResult,
    AgentState,
    AgentTask,
    BaseAgent,
)
from agents.context_store import ContextStore

logger = logging.getLogger(__name__)

# Source priority order (higher number = higher priority)
SOURCE_PRIORITY: Dict[str, int] = {
    "execution_agent": 5,
    "procedures_agent": 4,
    "soa_vision_agent": 3,
    "soa_text_agent": 2,
}
DEFAULT_SOURCE_PRIORITY = 1

# Footnote marker patterns to clean from entity names
FOOTNOTE_PATTERNS = [
    r"\s*[\*†‡§¶#]+\s*$",          # trailing symbols
    r"\s*\[\d+\]\s*$",              # trailing [1], [2]
    r"\s*\(\d+\)\s*$",              # trailing (1), (2)
    r"\s*[a-z]\)\s*$",              # trailing a), b)
    r"[\*†‡§¶#]+",                  # inline footnote symbols
]

# Compiled patterns for performance
_FOOTNOTE_RE = [re.compile(p) for p in FOOTNOTE_PATTERNS]
_MULTI_SPACE_RE = re.compile(r"\s+")


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class DuplicateGroup:
    """A group of entities identified as duplicates."""
    canonical_name: str
    entity_type: str
    entity_ids: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    merged_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "canonical_name": self.canonical_name,
            "entity_type": self.entity_type,
            "entity_ids": self.entity_ids,
            "sources": self.sources,
            "merged_id": self.merged_id,
        }


@dataclass
class ConflictDetail:
    """Details about a conflict between sources."""
    field_name: str
    entity_id: str
    entity_type: str
    values: Dict[str, Any] = field(default_factory=dict)  # source -> value
    resolved_value: Any = None
    resolution_strategy: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field_name": self.field_name,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "values": self.values,
            "resolved_value": self.resolved_value,
            "resolution_strategy": self.resolution_strategy,
        }


@dataclass
class ReconciliationReport:
    """Report summarising reconciliation results."""
    total_entities_before: int = 0
    total_entities_after: int = 0
    duplicate_groups: List[DuplicateGroup] = field(default_factory=list)
    conflicts: List[ConflictDetail] = field(default_factory=list)
    names_cleaned: int = 0
    references_updated: int = 0
    confidence_boosts: int = 0
    confidence_reductions: int = 0

    @property
    def duplicates_merged(self) -> int:
        return sum(len(g.entity_ids) - 1 for g in self.duplicate_groups)

    @property
    def conflict_count(self) -> int:
        return len(self.conflicts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_entities_before": self.total_entities_before,
            "total_entities_after": self.total_entities_after,
            "duplicates_merged": self.duplicates_merged,
            "duplicate_groups": [g.to_dict() for g in self.duplicate_groups],
            "conflicts": [c.to_dict() for c in self.conflicts],
            "conflict_count": self.conflict_count,
            "names_cleaned": self.names_cleaned,
            "references_updated": self.references_updated,
            "confidence_boosts": self.confidence_boosts,
            "confidence_reductions": self.confidence_reductions,
        }


# ---------------------------------------------------------------------------
# Pure helper functions
# ---------------------------------------------------------------------------

def clean_entity_name(name: str) -> str:
    """Remove footnote markers and normalise whitespace in an entity name.

    Steps:
    1. Strip leading/trailing whitespace.
    2. Remove footnote markers (symbols, bracketed numbers, etc.).
    3. Collapse multiple spaces to one.
    4. Strip again.
    """
    if not name:
        return name
    cleaned = name.strip()
    # Remove trailing footnote patterns first (order matters)
    for pat in _FOOTNOTE_RE[:4]:  # trailing patterns (symbols, [n], (n), a))
        cleaned = pat.sub("", cleaned)
    # Remove inline footnote symbols
    for pat in _FOOTNOTE_RE[4:]:
        cleaned = pat.sub("", cleaned)
    # Normalise whitespace
    cleaned = _MULTI_SPACE_RE.sub(" ", cleaned).strip()
    return cleaned


def fuzzy_match_score(name_a: str, name_b: str) -> float:
    """Return a similarity score in [0, 1] between two entity names."""
    if not name_a or not name_b:
        return 0.0
    a = clean_entity_name(name_a).lower()
    b = clean_entity_name(name_b).lower()
    if a == b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def get_source_priority(source: str) -> int:
    """Return the priority for a given source agent id."""
    return SOURCE_PRIORITY.get(source, DEFAULT_SOURCE_PRIORITY)


def _entity_name(entity: Dict[str, Any]) -> str:
    """Extract the name from an entity dict."""
    data = entity.get("data", {})
    return data.get("name", "") or data.get("label", "") or ""


def _entity_source(entity: Dict[str, Any]) -> str:
    """Extract the source agent id from an entity dict."""
    prov = entity.get("provenance", {})
    if isinstance(prov, dict):
        return prov.get("source_agent_id", "")
    # ContextEntity provenance object
    return getattr(prov, "source_agent_id", "")


def _entity_confidence(entity: Dict[str, Any]) -> float:
    """Extract the confidence score from an entity dict."""
    prov = entity.get("provenance", {})
    if isinstance(prov, dict):
        return float(prov.get("confidence_score", 0.0))
    return float(getattr(prov, "confidence_score", 0.0))


def _extract_timepoint(encounter_name: str) -> Optional[str]:
    """Extract normalized timepoint indicator from encounter name.
    
    Identifies and extracts timepoint patterns from encounter names such as:
    - Day numbers: "Day 2", "Day -42", "Day _42" (underscore for negative)
    - Day ranges: "Day -42 to -9", "Day 1 to 3", "(-42 to -9)", "(_42 to _9)"
    - Day ranges with "through": "Day _6 through _4"
    - Week numbers: "Week 4"
    - Parenthetical day numbers: "(Day 2)", "(-42)", "(_42)"
    
    Note: Handles both hyphens (-) and underscores (_) for negative numbers
    due to postprocessing agent substitution.
    
    Args:
        encounter_name: The encounter name to extract timepoint from
        
    Returns:
        Normalized timepoint string (e.g., "day_2", "day_range_-42_to_-9", "week_4")
        or None if no timepoint indicator is found
    """
    if not encounter_name:
        return None
    
    # Pattern 1: Day range with "Day" keyword and "through"
    # Matches: "Day _6 through _4", "Day -6 through -4", etc.
    match = re.search(r'Day\s+([_-]?\d+)\s+through\s+([_-]?\d+)', encounter_name, re.IGNORECASE)
    if match:
        start = match.group(1).replace('_', '-')
        end = match.group(2).replace('_', '-')
        return f"day_range_{start}_to_{end}"
    
    # Pattern 2: Day range with "Day" keyword and "to"
    # Matches: "Day -42 to -9", "Day _42 to _9", "Day 1 to 3", etc.
    match = re.search(r'Day\s+([_-]?\d+)\s+to\s+([_-]?\d+)', encounter_name, re.IGNORECASE)
    if match:
        start = match.group(1).replace('_', '-')
        end = match.group(2).replace('_', '-')
        return f"day_range_{start}_to_{end}"
    
    # Pattern 3: Parenthetical day range without "Day" keyword
    # Matches: "(-42 to -9)", "(_42 to _9)", "(1 to 5)", etc.
    match = re.search(r'\(([_-]?\d+)\s+to\s+([_-]?\d+)\)', encounter_name)
    if match:
        start = match.group(1).replace('_', '-')
        end = match.group(2).replace('_', '-')
        return f"day_range_{start}_to_{end}"
    
    # Pattern 4: Parenthetical day number with "Day" keyword
    # Matches: "(Day 2)", "(Day -42)", "(Day _42)", etc.
    match = re.search(r'\(Day\s+([_-]?\d+)\)', encounter_name, re.IGNORECASE)
    if match:
        day = match.group(1).replace('_', '-')
        return f"day_{day}"
    
    # Pattern 5: Single day number
    # Matches: "Day 2", "Day -42", "Day _42", etc.
    match = re.search(r'Day\s+([_-]?\d+)', encounter_name, re.IGNORECASE)
    if match:
        day = match.group(1).replace('_', '-')
        return f"day_{day}"
    
    # Pattern 6: Week number
    # Matches: "Week 4", "Week 12", etc.
    match = re.search(r'Week\s+(\d+)', encounter_name, re.IGNORECASE)
    if match:
        return f"week_{match.group(1)}"
    
    # Pattern 7: Parenthetical number without "Day" keyword
    # Matches: "(-42)", "(_42)", "(2)", etc.
    match = re.search(r'\(([_-]?\d+)\)', encounter_name)
    if match:
        day = match.group(1).replace('_', '-')
        return f"day_{day}"
    
    return None
def _are_encounters_duplicates(
    name_a: str,
    name_b: str,
    threshold: float
) -> bool:
    """Check if two encounters should be considered duplicates.

    Encounters are considered duplicates if:
    - Both have timepoint indicators and they match, AND fuzzy match score >= threshold
    - Neither has timepoint indicators, AND fuzzy match score >= threshold

    Encounters are NOT duplicates if:
    - Both have timepoint indicators but they differ (regardless of fuzzy match score)

    Args:
        name_a: First encounter name
        name_b: Second encounter name
        threshold: Fuzzy match score threshold (typically 0.85)

    Returns:
        True if encounters should be merged as duplicates, False otherwise
    """
    timepoint_a = _extract_timepoint(name_a)
    timepoint_b = _extract_timepoint(name_b)

    # If both have timepoints and they differ, NOT duplicates
    if timepoint_a is not None and timepoint_b is not None:
        if timepoint_a != timepoint_b:
            return False

    # Otherwise, use fuzzy matching as usual
    score = fuzzy_match_score(name_a, name_b)
    return score >= threshold



# ---------------------------------------------------------------------------
# ReconciliationAgent
# ---------------------------------------------------------------------------

class ReconciliationAgent(BaseAgent):
    """
    Merges duplicate entities and resolves conflicts across extraction sources.

    Capabilities:
    - Identify duplicate entities across extraction sources (same name, different IDs)
    - Merge duplicate entities using priority-based rules
    - Clean entity names (remove footnote markers, normalise whitespace)
    - Reconcile epochs, encounters, and activities from SoA, procedures, execution model
    - Use source priority to resolve conflicts (execution > procedures > SoA)
    - Maintain entity source attribution in extension attributes
    - Update all entity references after reconciliation
    - Validate reconciliation results for consistency
    - Generate reconciliation reports showing merged entities
    - Support fuzzy name matching with configurable thresholds
    - SoA cell-level reconciliation (vision vs text)
    - Confidence boosting for agreement, reduction for conflicts
    """

    def __init__(
        self,
        agent_id: str = "reconciliation_agent",
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(agent_id=agent_id, config=config or {})
        self._fuzzy_threshold: float = (config or {}).get("fuzzy_threshold", 0.85)
        self._confidence_boost: float = (config or {}).get("confidence_boost", 0.1)
        self._confidence_penalty: float = (config or {}).get("confidence_penalty", 0.15)
        self._reports: List[ReconciliationReport] = []

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        self.set_state(AgentState.READY)
        self._logger.info(
            f"[{self.agent_id}] Initialized. fuzzy_threshold={self._fuzzy_threshold}"
        )

    def terminate(self) -> None:
        self.set_state(AgentState.TERMINATED)

    def get_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            agent_type="reconciliation",
            input_types=["context_data"],
            output_types=["reconciled_entities", "reconciliation_report"],
            dependencies=["execution_extraction"],
            supports_parallel=False,
            timeout_seconds=300,
        )


    # ------------------------------------------------------------------
    # Main execution
    # ------------------------------------------------------------------

    def execute(self, task: AgentTask) -> AgentResult:
        """
        Reconcile entities.

        Input data can contain:
        - "entities": list of entity dicts
        - "context_store": a ContextStore instance
        - "fuzzy_threshold": override for fuzzy matching threshold
        """
        entities: List[Dict[str, Any]] = list(task.input_data.get("entities", []))
        context_store: Optional[ContextStore] = (
            task.input_data.get("context_store") or self._context_store
        )
        threshold = task.input_data.get("fuzzy_threshold", self._fuzzy_threshold)

        # Pull from context store if no entities provided
        if not entities and context_store:
            entities = self._entities_from_store(context_store)

        if not entities:
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=False,
                error="No entities provided for reconciliation",
            )

        report = ReconciliationReport(total_entities_before=len(entities))

        # Step 1: Clean entity names
        entities, names_cleaned = self._clean_all_names(entities)
        report.names_cleaned = names_cleaned

        # Step 2: Detect duplicates
        dup_groups = self._detect_duplicates(entities, threshold)
        report.duplicate_groups = dup_groups

        # Step 3: Merge duplicates
        entities, id_mapping = self._merge_duplicates(entities, dup_groups)
        for g in dup_groups:
            if g.merged_id is None and g.entity_ids:
                g.merged_id = g.entity_ids[0]

        # Step 4: Update references
        refs_updated = self._update_references(entities, id_mapping)
        report.references_updated = refs_updated

        # Step 5: SoA cell-level reconciliation
        entities, soa_conflicts, boosts, reductions = self._reconcile_soa_cells(entities)
        report.conflicts.extend(soa_conflicts)
        report.confidence_boosts += boosts
        report.confidence_reductions += reductions

        # Step 6: General conflict resolution
        entities, gen_conflicts, gen_boosts, gen_reductions = self._resolve_field_conflicts(entities)
        report.conflicts.extend(gen_conflicts)
        report.confidence_boosts += gen_boosts
        report.confidence_reductions += gen_reductions

        report.total_entities_after = len(entities)
        self._reports.append(report)

        # Update context store if available
        if context_store:
            self._update_context_store(context_store, entities, id_mapping)

        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            success=True,
            data={
                "entities": entities,
                "report": report.to_dict(),
                "id_mapping": id_mapping,
            },
            confidence_score=1.0 if report.conflict_count == 0 else max(0.5, 1.0 - 0.05 * report.conflict_count),
        )


    # ------------------------------------------------------------------
    # 19.1.4  Entity name cleaning
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_all_names(entities: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
        """Clean names on all entities. Returns (entities, count_cleaned)."""
        count = 0
        for entity in entities:
            data = entity.get("data", {})
            for key in ("name", "label"):
                original = data.get(key)
                if original and isinstance(original, str):
                    cleaned = clean_entity_name(original)
                    if cleaned != original:
                        data[key] = cleaned
                        count += 1
        return entities, count

    # ------------------------------------------------------------------
    # 19.1.2  Duplicate entity detection
    # ------------------------------------------------------------------

    def _detect_duplicates(
        self, entities: List[Dict[str, Any]], threshold: float
    ) -> List[DuplicateGroup]:
        """Identify groups of duplicate entities (same name, same type, different IDs)."""
        groups: List[DuplicateGroup] = []
        used: Set[str] = set()

        # Group by entity_type first for efficiency
        by_type: Dict[str, List[Dict[str, Any]]] = {}
        for e in entities:
            etype = e.get("entity_type", "")
            by_type.setdefault(etype, []).append(e)

        # Entity types that are inherently sequential and should never be
        # merged even when their names are similar (e.g. "Amendment 2" vs
        # "Amendment 5" differ by one digit but are distinct entities).
        _SKIP_DEDUP_TYPES = {
            "study_amendment", "amendment", "amendment_reason",
            "abbreviation", "governance_date",
            "eligibility_criterion", "criterion_item",
            "objective", "endpoint", "procedure",
        }

        for etype, type_entities in by_type.items():
            if etype in _SKIP_DEDUP_TYPES:
                continue

            for i, ea in enumerate(type_entities):
                eid_a = ea.get("id", "")
                if eid_a in used:
                    continue
                name_a = _entity_name(ea)
                if not name_a:
                    continue

                group_ids = [eid_a]
                group_sources = [_entity_source(ea)]

                for j in range(i + 1, len(type_entities)):
                    eb = type_entities[j]
                    eid_b = eb.get("id", "")
                    if eid_b in used or eid_b == eid_a:
                        continue
                    name_b = _entity_name(eb)
                    if not name_b:
                        continue
                    
                    # Use encounter-specific logic for encounter entities
                    if etype == "encounter":
                        is_duplicate = _are_encounters_duplicates(name_a, name_b, threshold)
                    else:
                        # Existing logic for all other entity types
                        score = fuzzy_match_score(name_a, name_b)
                        is_duplicate = score >= threshold
                    
                    if is_duplicate:
                        group_ids.append(eid_b)
                        group_sources.append(_entity_source(eb))
                        used.add(eid_b)

                if len(group_ids) > 1:
                    used.add(eid_a)
                    groups.append(DuplicateGroup(
                        canonical_name=name_a,
                        entity_type=etype,
                        entity_ids=group_ids,
                        sources=group_sources,
                    ))

        return groups

    # ------------------------------------------------------------------
    # 19.1.3  Entity merging with priority rules
    # ------------------------------------------------------------------

    def _merge_duplicates(
        self,
        entities: List[Dict[str, Any]],
        groups: List[DuplicateGroup],
    ) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
        """Merge duplicate groups. Returns (merged_entities, old_id->new_id mapping)."""
        id_mapping: Dict[str, str] = {}
        ids_to_remove: Set[str] = set()

        entity_index: Dict[str, Dict[str, Any]] = {e.get("id", ""): e for e in entities}

        for group in groups:
            if len(group.entity_ids) < 2:
                continue

            # Sort by source priority (highest first)
            members = [(eid, entity_index.get(eid, {})) for eid in group.entity_ids]
            members.sort(key=lambda x: get_source_priority(_entity_source(x[1])), reverse=True)

            primary_id, primary = members[0]
            group.merged_id = primary_id

            # Merge data from lower-priority entities into primary
            merged_sources = [_entity_source(primary)]
            for other_id, other in members[1:]:
                self._merge_entity_data(primary, other)
                merged_sources.append(_entity_source(other))
                id_mapping[other_id] = primary_id
                ids_to_remove.add(other_id)

            # Store source attribution in extension attributes
            primary.setdefault("data", {})["_sources"] = merged_sources
            primary["data"]["_reconciled"] = True

        # Remove merged-away entities
        result = [e for e in entities if e.get("id", "") not in ids_to_remove]
        return result, id_mapping

    @staticmethod
    def _merge_entity_data(primary: Dict[str, Any], secondary: Dict[str, Any]) -> None:
        """Merge secondary entity data into primary (primary wins on conflicts)."""
        p_data = primary.setdefault("data", {})
        s_data = secondary.get("data", {})
        for key, value in s_data.items():
            if key.startswith("_"):
                continue
            if key not in p_data or p_data[key] is None or p_data[key] == "":
                p_data[key] = value


    # ------------------------------------------------------------------
    # 19.1.5  Update entity references after reconciliation
    # ------------------------------------------------------------------

    @staticmethod
    def _update_references(
        entities: List[Dict[str, Any]], id_mapping: Dict[str, str]
    ) -> int:
        """Rewrite entity references using the id_mapping. Returns count of updates."""
        if not id_mapping:
            return 0

        count = 0

        def _rewrite(value: Any) -> Any:
            nonlocal count
            if isinstance(value, str) and value in id_mapping:
                count += 1
                return id_mapping[value]
            if isinstance(value, list):
                return [_rewrite(v) for v in value]
            if isinstance(value, dict):
                return {k: _rewrite(v) for k, v in value.items()}
            return value

        for entity in entities:
            # Rewrite data fields
            data = entity.get("data", {})
            for key in list(data.keys()):
                data[key] = _rewrite(data[key])
            # Rewrite relationships
            rels = entity.get("relationships", {})
            for rel_type in list(rels.keys()):
                rels[rel_type] = _rewrite(rels[rel_type])

        return count

    # ------------------------------------------------------------------
    # 19.1.6  SoA cell-level reconciliation logic
    # ------------------------------------------------------------------

    def _reconcile_soa_cells(
        self, entities: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[ConflictDetail], int, int]:
        """Reconcile SoA cell data from vision and text agents.

        Returns (entities, conflicts, boosts, reductions).
        """
        conflicts: List[ConflictDetail] = []
        boosts = 0
        reductions = 0

        for entity in entities:
            data = entity.get("data", {})
            cells = data.get("cells", {})
            if not cells:
                continue

            eid = entity.get("id", "")
            etype = entity.get("entity_type", "")

            # cells is expected to be a dict of cell_key -> {source -> value}
            # or a list of cell dicts with "vision_value" / "text_value"
            if isinstance(cells, list):
                for cell in cells:
                    c, b, r = self._reconcile_single_cell(cell, eid, etype)
                    conflicts.extend(c)
                    boosts += b
                    reductions += r
            elif isinstance(cells, dict):
                for cell_key, cell_data in cells.items():
                    if isinstance(cell_data, dict):
                        c, b, r = self._reconcile_single_cell(cell_data, eid, etype)
                        conflicts.extend(c)
                        boosts += b
                        reductions += r

        return entities, conflicts, boosts, reductions

    def _reconcile_single_cell(
        self, cell: Dict[str, Any], entity_id: str, entity_type: str
    ) -> Tuple[List[ConflictDetail], int, int]:
        """Reconcile a single SoA cell between vision and text sources.

        Returns (conflicts, boosts, reductions).
        """
        conflicts: List[ConflictDetail] = []
        boosts = 0
        reductions = 0

        vision_val = cell.get("vision_value")
        text_val = cell.get("text_value")

        if vision_val is None or text_val is None:
            # Only one source — nothing to reconcile
            if vision_val is not None:
                cell["resolved_value"] = vision_val
            elif text_val is not None:
                cell["resolved_value"] = text_val
            return conflicts, boosts, reductions

        # Both sources present — reconcile
        vision_conf = float(cell.get("vision_confidence", 0.5))
        text_conf = float(cell.get("text_confidence", 0.5))

        if self._values_agree(vision_val, text_val):
            # Agreement — boost confidence
            cell["resolved_value"] = vision_val
            cell["resolved_confidence"] = min(1.0, max(vision_conf, text_conf) + self._confidence_boost)
            boosts += 1
        else:
            # Conflict — resolve using strategy
            resolved, strategy = self._resolve_cell_conflict(
                vision_val, vision_conf, text_val, text_conf
            )
            cell["resolved_value"] = resolved
            cell["resolved_confidence"] = max(vision_conf, text_conf) - self._confidence_penalty
            if cell["resolved_confidence"] < 0:
                cell["resolved_confidence"] = 0.0
            reductions += 1
            conflicts.append(ConflictDetail(
                field_name="cell_value",
                entity_id=entity_id,
                entity_type=entity_type,
                values={"soa_vision_agent": vision_val, "soa_text_agent": text_val},
                resolved_value=resolved,
                resolution_strategy=strategy,
            ))

        return conflicts, boosts, reductions

    # ------------------------------------------------------------------
    # 19.1.7  Conflict resolution strategies
    # ------------------------------------------------------------------

    @staticmethod
    def _values_agree(a: Any, b: Any) -> bool:
        """Check if two cell values agree (tick marks, numbers, strings)."""
        if a == b:
            return True
        # Normalise tick marks
        tick_chars = {"X", "x", "✓", "✔", "√", "Y", "y", "Yes", "yes"}
        empty_chars = {"", "-", "—", "N", "n", "No", "no", None}
        a_str = str(a).strip() if a is not None else ""
        b_str = str(b).strip() if b is not None else ""
        if a_str in tick_chars and b_str in tick_chars:
            return True
        if a_str in empty_chars and b_str in empty_chars:
            return True
        # Numeric comparison
        try:
            return float(a_str) == float(b_str)
        except (ValueError, TypeError):
            pass
        # Case-insensitive string comparison
        return a_str.lower() == b_str.lower()

    def _resolve_cell_conflict(
        self,
        vision_val: Any,
        vision_conf: float,
        text_val: Any,
        text_conf: float,
    ) -> Tuple[Any, str]:
        """Resolve a conflict between vision and text cell values.

        Returns (resolved_value, strategy_name).
        """
        v_str = str(vision_val).strip() if vision_val is not None else ""
        t_str = str(text_val).strip() if text_val is not None else ""

        # Strategy 1: Tick mark resolution — prefer presence over absence
        tick_chars = {"X", "x", "✓", "✔", "√", "Y", "y", "Yes", "yes"}
        empty_chars = {"", "-", "—", "N", "n", "No", "no"}
        if v_str in tick_chars and t_str in empty_chars:
            return vision_val, "tick_present_over_absent"
        if t_str in tick_chars and v_str in empty_chars:
            return text_val, "tick_present_over_absent"

        # Strategy 2: Numeric — prefer higher confidence
        try:
            float(v_str)
            float(t_str)
            if vision_conf >= text_conf:
                return vision_val, "numeric_higher_confidence"
            return text_val, "numeric_higher_confidence"
        except (ValueError, TypeError):
            pass

        # Strategy 3: Source priority (vision > text for SoA)
        if get_source_priority("soa_vision_agent") >= get_source_priority("soa_text_agent"):
            return vision_val, "source_priority"
        return text_val, "source_priority"


    # ------------------------------------------------------------------
    # 19.1.8 / 19.1.9  Confidence boosting and reduction for field conflicts
    # ------------------------------------------------------------------

    def _resolve_field_conflicts(
        self, entities: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[ConflictDetail], int, int]:
        """Resolve field-level conflicts across entities that share data from multiple sources.

        Returns (entities, conflicts, boosts, reductions).
        """
        conflicts: List[ConflictDetail] = []
        boosts = 0
        reductions = 0

        for entity in entities:
            data = entity.get("data", {})
            source_data = data.get("_source_values")  # dict of field -> {source -> value}
            if not source_data or not isinstance(source_data, dict):
                continue

            eid = entity.get("id", "")
            etype = entity.get("entity_type", "")

            for field_name, source_values in source_data.items():
                if not isinstance(source_values, dict) or len(source_values) < 2:
                    continue

                unique_values = set()
                for v in source_values.values():
                    unique_values.add(str(v) if v is not None else "")

                if len(unique_values) == 1:
                    # All sources agree — boost confidence
                    boosts += 1
                    self._boost_entity_confidence(entity)
                else:
                    # Conflict — resolve by source priority
                    reductions += 1
                    self._reduce_entity_confidence(entity)
                    resolved_val, winning_source = self._pick_by_priority(source_values)
                    data[field_name] = resolved_val
                    conflicts.append(ConflictDetail(
                        field_name=field_name,
                        entity_id=eid,
                        entity_type=etype,
                        values=source_values,
                        resolved_value=resolved_val,
                        resolution_strategy=f"source_priority:{winning_source}",
                    ))

        return entities, conflicts, boosts, reductions

    def _boost_entity_confidence(self, entity: Dict[str, Any]) -> None:
        """Boost confidence score for an entity (agreement across sources)."""
        prov = entity.get("provenance", {})
        if isinstance(prov, dict):
            current = float(prov.get("confidence_score", 0.5))
            prov["confidence_score"] = min(1.0, current + self._confidence_boost)
        else:
            current = float(getattr(prov, "confidence_score", 0.5))
            prov.confidence_score = min(1.0, current + self._confidence_boost)

    def _reduce_entity_confidence(self, entity: Dict[str, Any]) -> None:
        """Reduce confidence score for an entity (conflict across sources)."""
        prov = entity.get("provenance", {})
        if isinstance(prov, dict):
            current = float(prov.get("confidence_score", 0.5))
            prov["confidence_score"] = max(0.0, current - self._confidence_penalty)
        else:
            current = float(getattr(prov, "confidence_score", 0.5))
            prov.confidence_score = max(0.0, current - self._confidence_penalty)

    @staticmethod
    def _pick_by_priority(source_values: Dict[str, Any]) -> Tuple[Any, str]:
        """Pick the value from the highest-priority source."""
        best_source = ""
        best_priority = -1
        best_value = None
        for source, value in source_values.items():
            p = get_source_priority(source)
            if p > best_priority:
                best_priority = p
                best_source = source
                best_value = value
        return best_value, best_source

    # ------------------------------------------------------------------
    # 19.1.10  Reconciliation reports
    # ------------------------------------------------------------------

    def get_reports(self) -> List[ReconciliationReport]:
        """Return all reconciliation reports."""
        return list(self._reports)

    # ------------------------------------------------------------------
    # Context Store helpers
    # ------------------------------------------------------------------

    def _update_context_store(
        self,
        store: ContextStore,
        entities: List[Dict[str, Any]],
        id_mapping: Dict[str, str],
    ) -> None:
        """Update the context store with reconciled entities."""
        # Remove merged-away entities
        for old_id in id_mapping:
            try:
                store.delete_entity(old_id)
            except (KeyError, ValueError):
                pass

        # Update remaining entities
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
                    # Update provenance
                    existing = store.get_entity(eid)
                    if existing:
                        pass  # source_agent_id preserved (original extractor attribution)
            except (KeyError, ValueError) as exc:
                self._logger.warning(
                    f"[{self.agent_id}] Could not update entity {eid}: {exc}"
                )

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
                "provenance": entity.provenance.to_dict(),
            })
        return result
