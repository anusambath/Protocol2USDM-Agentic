"""Prodigy metadata stripping for the Prodigy-to-USDM converter.

Recursively removes Prodigy-specific metadata fields from JSON structures
while preserving scopeId on whitelisted entity types (e.g., StudyIdentifier).
"""

from __future__ import annotations

from typing import Any

from converter.constants import PRODIGY_METADATA_FIELDS, SCOPEID_WHITELIST_TYPES


def strip_metadata(obj: Any, parent_instance_type: str | None = None) -> Any:
    """Recursively remove Prodigy metadata fields from a JSON-like structure.

    Returns a new object with metadata fields removed (does not mutate input).

    Args:
        obj: A dict, list, or scalar value from parsed JSON.
        parent_instance_type: The ``instanceType`` of the enclosing dict, used
            to decide whether ``scopeId`` should be preserved.

    Returns:
        A cleaned copy of *obj* with Prodigy metadata fields removed.
    """
    if isinstance(obj, dict):
        instance_type = obj.get("instanceType", parent_instance_type)
        result: dict[str, Any] = {}
        for key, value in obj.items():
            if key in PRODIGY_METADATA_FIELDS:
                # Preserve scopeId on whitelisted types
                if key == "scopeId" and instance_type in SCOPEID_WHITELIST_TYPES:
                    result[key] = strip_metadata(value, instance_type)
                # Otherwise skip (strip) the field
                continue
            result[key] = strip_metadata(value, instance_type)
        return result

    if isinstance(obj, list):
        return [strip_metadata(item, parent_instance_type) for item in obj]

    # Scalars (str, int, float, bool, None) pass through unchanged
    return obj


def count_stripped(obj: Any) -> dict[str, int]:
    """Count occurrences of each Prodigy metadata field in *obj*.

    Walks the entire structure and tallies how many times each metadata
    field name appears as a dict key, regardless of nesting depth.
    This is intended for logging before stripping.

    Args:
        obj: A dict, list, or scalar value from parsed JSON.

    Returns:
        A mapping of field name → occurrence count (only fields with
        count > 0 are included).
    """
    counts: dict[str, int] = {}
    _count_recursive(obj, counts)
    return counts


def _count_recursive(obj: Any, counts: dict[str, int]) -> None:
    """Recursively accumulate metadata field counts into *counts*."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in PRODIGY_METADATA_FIELDS:
                counts[key] = counts.get(key, 0) + 1
            _count_recursive(value, counts)
    elif isinstance(obj, list):
        for item in obj:
            _count_recursive(item, counts)
