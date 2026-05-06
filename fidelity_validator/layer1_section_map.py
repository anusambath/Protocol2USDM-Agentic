"""
Layer 1 — USDM Section Map Loader

Loads and validates the usdm_section_map.yaml configuration.
Provides lookup methods for mapping protocol sections to USDM targets.
"""

import os
from pathlib import Path
from typing import Optional

import yaml

from .models import SectionMap, SectionSpec

# Default path to the bundled section map
_DEFAULT_MAP_PATH = Path(__file__).parent / "usdm_section_map.yaml"


def load_section_map(yaml_path: Optional[str] = None) -> SectionMap:
    """
    Load and validate the USDM section map from YAML.

    Args:
        yaml_path: Path to the YAML file. Defaults to bundled usdm_section_map.yaml.

    Returns:
        Validated SectionMap instance.

    Raises:
        FileNotFoundError: If YAML file doesn't exist.
        ValidationError: If YAML doesn't conform to schema.
    """
    path = Path(yaml_path) if yaml_path else _DEFAULT_MAP_PATH
    if not path.exists():
        raise FileNotFoundError(f"Section map not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    return SectionMap(**raw)


def resolve_section(section_map: SectionMap, heading: str) -> Optional[SectionSpec]:
    """
    Given a protocol heading text, resolve it to a canonical section spec.

    Uses exact match on name, then alias match, then substring/fuzzy matching.

    Args:
        section_map: The loaded section map.
        heading: The heading text from the protocol PDF.

    Returns:
        Matching SectionSpec, or None if no match found.
    """
    if not heading:
        return None

    heading_lower = heading.lower().strip()

    # Exact name match
    for s in section_map.sections:
        if s.name.lower() == heading_lower:
            return s

    # Alias match
    for s in section_map.sections:
        for alias in s.aliases:
            if alias.lower() == heading_lower:
                return s

    # Substring match — heading contains an alias or vice versa
    for s in section_map.sections:
        if s.name.lower() in heading_lower or heading_lower in s.name.lower():
            return s
        for alias in s.aliases:
            if alias.lower() in heading_lower or heading_lower in alias.lower():
                return s

    return None


def get_all_usdm_paths(section_map: SectionMap) -> dict:
    """
    Build a complete mapping of USDM JSON paths → section IDs.

    Used by the indexer to know which USDM entities belong to which sections.

    Returns:
        Dict mapping JSON path patterns to section IDs.
    """
    path_to_section = {}
    for section in section_map.sections:
        for target in section.usdm_targets:
            path_to_section[target.path] = section.id
    return path_to_section
