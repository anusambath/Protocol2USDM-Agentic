"""
Layer 3 — USDM JSON Indexer

Walks the USDM JSON and builds an inverted index from canonical section name
to resolved USDM entity instances.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .models import SectionMap, SectionSpec, USDMTarget

logger = logging.getLogger(__name__)


@dataclass
class ResolvedEntity:
    """A USDM entity with cross-references resolved to actual content."""
    entity_type: str
    json_path: str
    data: Dict[str, Any]
    resolved_refs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SectionIndex:
    """Index of USDM entities for a single protocol section."""
    section_id: str
    entities: List[ResolvedEntity] = field(default_factory=list)

    @property
    def entity_count(self) -> int:
        return len(self.entities)

    @property
    def is_populated(self) -> bool:
        return len(self.entities) > 0


@dataclass
class USDMIndex:
    """Complete inverted index from sections to USDM entities."""
    usdm_path: str
    sections: Dict[str, SectionIndex] = field(default_factory=dict)
    unmatched_entities: List[ResolvedEntity] = field(default_factory=list)


def index_usdm(
    usdm_path: str,
    section_map: SectionMap,
) -> USDMIndex:
    """
    Walk the USDM JSON and build an inverted index.

    For each section in the section map:
    1. Navigate to the JSON path(s) specified in usdm_targets.
    2. Collect all entity instances found there.
    3. Resolve cross-references.
    4. Store resolved entities in the section index.
    """
    with open(usdm_path, "r", encoding="utf-8") as f:
        usdm_data = json.load(f)

    index = USDMIndex(usdm_path=usdm_path)

    for section_spec in section_map.sections:
        section_index = SectionIndex(section_id=section_spec.id)

        for target in section_spec.usdm_targets:
            entities = navigate_json_path(usdm_data, target.path)
            for i, entity in enumerate(entities):
                if not entity or not isinstance(entity, dict):
                    continue

                # Build the actual JSON path for this instance
                actual_path = target.path
                if "[]" in target.path:
                    actual_path = target.path.replace("[]", f"[{i}]")

                # Resolve cross-references
                resolved = resolve_references(entity, usdm_data, target.entity)

                section_index.entities.append(ResolvedEntity(
                    entity_type=target.entity,
                    json_path=actual_path,
                    data=entity,
                    resolved_refs=resolved,
                ))

        index.sections[section_spec.id] = section_index
        logger.debug(
            f"Section '{section_spec.id}': {section_index.entity_count} entities indexed"
        )

    return index


def resolve_references(
    entity: Dict[str, Any],
    usdm_data: Dict[str, Any],
    entity_type: str,
) -> Dict[str, Any]:
    """
    Resolve ID references in an entity to their actual content.

    Handles common USDM reference patterns:
    - *Ids (array of IDs) → resolved to list of referenced objects
    - *Id (single ID) → resolved to the referenced object
    """
    resolved = {}

    # Get the design for lookups
    try:
        version = usdm_data["study"]["versions"][0]
        design = version.get("studyDesigns", [{}])[0]
    except (KeyError, IndexError):
        return resolved

    # Build lookup maps for common entity types
    _entity_pools = {
        "activities": design.get("activities", []),
        "encounters": design.get("encounters", []),
        "epochs": design.get("epochs", []),
        "endpoints": version.get("studyDesigns", [{}])[0].get("endpoints", []),
        "objectives": design.get("objectives", []),
        "procedures": design.get("procedures", []),
        "organizations": version.get("organizations", []),
        "studyInterventions": version.get("studyInterventions", []),
    }

    id_maps: Dict[str, Dict[str, Any]] = {}
    for pool_name, pool in _entity_pools.items():
        id_maps[pool_name] = {item.get("id"): item for item in pool if item.get("id")}

    # Resolve reference fields
    _REF_FIELDS = {
        "activityIds": "activities",
        "epochId": "epochs",
        "encounterId": "encounters",
        "endpointIds": "endpoints",
        "objectiveId": "objectives",
        "procedureIds": "procedures",
        "organizationId": "organizations",
        "studyInterventionIds": "studyInterventions",
        "scopeId": "organizations",
    }

    for ref_field, pool_name in _REF_FIELDS.items():
        if ref_field not in entity:
            continue
        value = entity[ref_field]
        pool = id_maps.get(pool_name, {})

        if isinstance(value, list):
            # Array of IDs
            resolved[ref_field] = [pool.get(vid) for vid in value if pool.get(vid)]
        elif isinstance(value, str):
            # Single ID
            obj = pool.get(value)
            if obj:
                resolved[ref_field] = obj

    return resolved


def navigate_json_path(data: Dict[str, Any], path: str) -> List[Dict[str, Any]]:
    """
    Navigate a JSON path template and return matching entities.

    Supports:
    - Dot notation: "study.versions[0].studyDesigns[0]"
    - Array indexing: "[0]", "[1]"
    - Array wildcard: "[]" (returns all items in the array)
    """
    # Parse path into segments
    segments = _parse_path(path)
    results = [data]

    for segment in segments:
        next_results = []
        for current in results:
            if current is None:
                continue

            if segment["type"] == "key":
                val = current.get(segment["value"]) if isinstance(current, dict) else None
                if val is not None:
                    next_results.append(val)

            elif segment["type"] == "index":
                idx = segment["value"]
                if isinstance(current, list) and 0 <= idx < len(current):
                    next_results.append(current[idx])

            elif segment["type"] == "wildcard":
                if isinstance(current, list):
                    next_results.extend(current)

        results = next_results

    # Ensure we return a list of dicts
    final = []
    for r in results:
        if isinstance(r, dict):
            final.append(r)
        elif isinstance(r, list):
            final.extend(item for item in r if isinstance(item, dict))

    return final


def _parse_path(path: str) -> List[Dict[str, Any]]:
    """Parse a JSON path string into segments."""
    segments = []
    # Split on dots, but handle brackets
    parts = re.split(r'\.(?![^\[]*\])', path)

    for part in parts:
        # Check for array access
        bracket_match = re.match(r'^(\w+)\[(\d+|\*|)\]$', part)
        if bracket_match:
            key = bracket_match.group(1)
            idx_str = bracket_match.group(2)
            segments.append({"type": "key", "value": key})
            if idx_str == "" or idx_str == "*":
                segments.append({"type": "wildcard", "value": None})
            else:
                segments.append({"type": "index", "value": int(idx_str)})
        elif re.match(r'^\[\d+\]$', part):
            segments.append({"type": "index", "value": int(part[1:-1])})
        elif part == "[]":
            segments.append({"type": "wildcard", "value": None})
        else:
            segments.append({"type": "key", "value": part})

    return segments


def format_entities_for_llm(
    section_index: SectionIndex,
    max_chars: int = 8000,
) -> str:
    """
    Format resolved USDM entities into a text representation for LLM evaluation.
    """
    lines = []
    char_count = 0

    for i, entity in enumerate(section_index.entities):
        header = f"\n--- {entity.entity_type} [{i+1}] (path: {entity.json_path}) ---"
        lines.append(header)
        char_count += len(header)

        # Format key attributes
        for key, value in entity.data.items():
            if key in ("id", "instanceType"):
                continue
            if value is None or value == "" or value == []:
                continue

            if isinstance(value, str):
                line = f"  {key}: {value[:200]}"
            elif isinstance(value, list) and len(value) > 0:
                if all(isinstance(v, str) for v in value):
                    line = f"  {key}: {value}"
                else:
                    line = f"  {key}: [{len(value)} items]"
            elif isinstance(value, dict):
                # Show code objects inline
                if "decode" in value:
                    line = f"  {key}: {value.get('decode', '')} (code={value.get('code', '')})"
                else:
                    line = f"  {key}: {{...}}"
            else:
                line = f"  {key}: {value}"

            if char_count + len(line) > max_chars:
                lines.append("  ... [truncated]")
                return "\n".join(lines)

            lines.append(line)
            char_count += len(line)

        # Show resolved references
        for ref_field, ref_data in entity.resolved_refs.items():
            if isinstance(ref_data, list):
                for j, ref_item in enumerate(ref_data[:5]):
                    name = ref_item.get("name", ref_item.get("text", "?"))
                    line = f"  → {ref_field}[{j}]: {name}"
                    lines.append(line)
                    char_count += len(line)
            elif isinstance(ref_data, dict):
                name = ref_data.get("name", ref_data.get("text", "?"))
                line = f"  → {ref_field}: {name}"
                lines.append(line)
                char_count += len(line)

            if char_count > max_chars:
                lines.append("  ... [truncated]")
                return "\n".join(lines)

    return "\n".join(lines)
