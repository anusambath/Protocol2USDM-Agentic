"""Data models for the Prodigy-to-USDM converter."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProdigyDocument:
    """Parsed Prodigy JSON, categorized by section type."""

    study: dict
    """The Study entity (from top-level "Study" key)."""

    identifiers: list[dict]
    """From top-level "Identifier" (may be single or list)."""

    population_definition: dict | None
    """From top-level "PopulationDefinition"."""

    scheduled_instances: list[dict]
    """From top-level "ScheduledInstance"."""

    syntax_templates: list[dict]
    """From top-level "SyntaxTemplate"."""

    metadata: dict
    """From top-level "metadata"."""

    relationships: list[dict]
    """From top-level "relationships"."""

    domain_modules: dict[str, Any]
    """Domain-specific modules (e.g., biomarker_driven_design_module)."""

    auxiliary: dict[str, Any]
    """sdtm_trial_design_views, document_map, schedule_of_activity,
    table_of_contents, list_of_tables, list_of_figures."""

    raw_keys: list[str]
    """All original top-level keys (for diagnostics)."""


@dataclass
class ConversionStats:
    """Statistics collected during conversion for logging."""

    metadata_fields_stripped: dict[str, int] = field(default_factory=dict)
    """Count per metadata field name stripped."""

    extension_attributes_injected: int = 0
    """Number of extensionAttributes arrays injected."""

    relationships_processed: int = 0
    """Number of relationships successfully processed."""

    relationships_discarded: int = 0
    """Number of relationships discarded (no USDM mapping)."""

    domain_modules_mapped: int = 0
    """Number of domain modules successfully mapped."""

    domain_modules_skipped: int = 0
    """Number of domain modules skipped (no USDM mapping)."""

    entities_without_instance_type: int = 0
    """Number of entities where instanceType had to be inferred or set."""


@dataclass
class USDMDocument:
    """USDM 4.0 document ready for serialization."""

    study: dict
    """The study object (id, name, description, label, versions, documentedBy, instanceType)."""

    warnings: list[str] = field(default_factory=list)
    """Accumulated warnings from mapping/enrichment."""

    stats: ConversionStats = field(default_factory=ConversionStats)
    """Conversion statistics for logging."""
