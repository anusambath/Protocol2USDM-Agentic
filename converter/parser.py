"""Prodigy JSON parser and pretty-printer.

Parses raw Prodigy JSON dicts into a categorized ProdigyDocument and
reassembles them back for round-trip verification.
"""

from __future__ import annotations

import logging
from typing import Any

from converter.models import ProdigyDocument

logger = logging.getLogger(__name__)

# Keys that map directly to named ProdigyDocument fields (not domain modules).
_KNOWN_KEYS: set[str] = {
    "Study",
    "Identifier",
    "PopulationDefinition",
    "ScheduledInstance",
    "SyntaxTemplate",
    "metadata",
    "relationships",
}

# Auxiliary keys that are NOT domain modules.
_AUXILIARY_KEYS: set[str] = {
    "sdtm_trial_design_views",
    "document_map",
    "schedule_of_activity",
    "table_of_contents",
    "list_of_tables",
    "list_of_figures",
}


def _wrap_list(value: Any) -> list[dict]:
    """Wrap a single dict in a list; pass through if already a list."""
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    return []


def _unwrap_single(items: list) -> Any:
    """Unwrap a single-element list back to its element for round-trip fidelity."""
    if len(items) == 1:
        return items[0]
    return items


def parse_prodigy(raw: dict) -> ProdigyDocument:
    """Categorize a raw Prodigy JSON dict into a :class:`ProdigyDocument`.

    Parameters
    ----------
    raw:
        The top-level dict loaded from a Prodigy JSON file.

    Returns
    -------
    ProdigyDocument
        Categorized representation of the input.

    Raises
    ------
    ValueError
        If the required ``Study`` key is missing.
    """
    if "Study" not in raw:
        raise ValueError("Required 'Study' key is missing from Prodigy JSON input")

    raw_keys = list(raw.keys())
    logger.info("Prodigy JSON contains %d top-level keys: %s", len(raw_keys), raw_keys)

    # --- Named sections ---
    study: dict = raw["Study"]
    identifiers: list[dict] = _wrap_list(raw.get("Identifier", []))
    population_definition: dict | None = raw.get("PopulationDefinition")
    scheduled_instances: list[dict] = _wrap_list(raw.get("ScheduledInstance", []))
    syntax_templates: list[dict] = _wrap_list(raw.get("SyntaxTemplate", []))
    metadata: dict = raw.get("metadata", {})
    relationships: list[dict] = raw.get("relationships", [])

    logger.info("Relationships found: %d", len(relationships))

    # --- Auxiliary & domain modules ---
    auxiliary: dict[str, Any] = {}
    domain_modules: dict[str, Any] = {}

    for key in raw_keys:
        if key in _KNOWN_KEYS:
            continue
        if key in _AUXILIARY_KEYS:
            auxiliary[key] = raw[key]
        else:
            domain_modules[key] = raw[key]

    if domain_modules:
        logger.info("Domain modules detected: %s", list(domain_modules.keys()))

    return ProdigyDocument(
        study=study,
        identifiers=identifiers,
        population_definition=population_definition,
        scheduled_instances=scheduled_instances,
        syntax_templates=syntax_templates,
        metadata=metadata,
        relationships=relationships,
        domain_modules=domain_modules,
        auxiliary=auxiliary,
        raw_keys=raw_keys,
    )


def pretty_print_prodigy(doc: ProdigyDocument) -> dict:
    """Reassemble a :class:`ProdigyDocument` back to a Prodigy-like JSON dict.

    The output preserves the original key ordering recorded in
    ``doc.raw_keys`` so that a parse → pretty-print round-trip produces
    a semantically equivalent dict.

    Parameters
    ----------
    doc:
        A parsed Prodigy document.

    Returns
    -------
    dict
        A dict matching the original Prodigy JSON structure.
    """
    raw_key_set = set(doc.raw_keys)

    # Build a lookup of section data keyed by original top-level key name.
    section_map: dict[str, Any] = {}

    section_map["Study"] = doc.study

    if "Identifier" in raw_key_set:
        section_map["Identifier"] = _unwrap_single(doc.identifiers)

    if "PopulationDefinition" in raw_key_set:
        section_map["PopulationDefinition"] = doc.population_definition

    if "ScheduledInstance" in raw_key_set:
        section_map["ScheduledInstance"] = _unwrap_single(doc.scheduled_instances)

    if "SyntaxTemplate" in raw_key_set:
        section_map["SyntaxTemplate"] = _unwrap_single(doc.syntax_templates)

    if "metadata" in raw_key_set:
        section_map["metadata"] = doc.metadata

    if "relationships" in raw_key_set:
        section_map["relationships"] = doc.relationships

    # Auxiliary and domain modules
    for key, value in doc.auxiliary.items():
        section_map[key] = value

    for key, value in doc.domain_modules.items():
        section_map[key] = value

    # Reconstruct in original key order.
    result: dict[str, Any] = {}
    for key in doc.raw_keys:
        if key in section_map:
            result[key] = section_map[key]

    return result
