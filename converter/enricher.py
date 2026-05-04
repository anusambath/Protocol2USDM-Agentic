"""Enrichment and normalization for USDM 4.0 entities.

Provides recursive enrichment (extensionAttributes injection, instanceType
validation), Code entity normalization, and ID-reference validation.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from converter.constants import KNOWN_INSTANCE_TYPES
from converter.models import USDMDocument

logger = logging.getLogger(__name__)

# Code entity normalization constants
_NCI_THESAURUS = "NCI Thesaurus"
_CDISC_CODE_SYSTEM = "http://www.cdisc.org"
_DEFAULT_CODE_SYSTEM_VERSION = "2024-09-27"

# Required fields on a Code entity
_CODE_REQUIRED_FIELDS: list[str] = [
    "id",
    "extensionAttributes",
    "code",
    "codeSystem",
    "codeSystemVersion",
    "decode",
    "instanceType",
]

# Fields whose values are ID references (scalar)
_SCALAR_ID_REF_FIELDS: set[str] = {
    "epochId",
    "armId",
    "populationId",
    "encounterId",
    "scopeId",
}

# Fields whose values are lists of ID references
_LIST_ID_REF_FIELDS: set[str] = {
    "epochIds",
    "armIds",
    "activityIds",
    "encounterIds",
    "scheduleTimelineIds",
    "populationIds",
    "estimandIds",
    "objectiveIds",
    "endpointIds",
    "indicationIds",
    "studyCellIds",
    "elementIds",
    "organizationIds",
    "studyInterventionIds",
    "documentVersionIds",
    "childIds",
}



def enrich(obj: Any) -> Any:
    """Recursively enrich a USDM object tree.

    For every dict that has an ``instanceType`` field (i.e., represents a
    USDM entity), injects ``extensionAttributes: []`` if missing and
    validates/adds ``instanceType``.  Also ensures every entity has a
    non-empty ``id``.

    Parameters
    ----------
    obj:
        Any JSON-like object (dict, list, or scalar).

    Returns
    -------
    Any
        The enriched object (modified in place for dicts/lists).
    """
    if isinstance(obj, dict):
        # If this dict looks like a USDM entity (has instanceType), enrich it
        if "instanceType" in obj:
            inject_extension_attributes(obj)
            validate_instance_type(obj, context="")
            _ensure_id(obj)

        # Recurse into all values
        for value in obj.values():
            enrich(value)

    elif isinstance(obj, list):
        for item in obj:
            enrich(item)

    return obj


def inject_extension_attributes(entity: dict) -> None:
    """Add ``extensionAttributes: []`` if missing; preserve if present.

    Parameters
    ----------
    entity:
        A dict representing a USDM entity (must have ``instanceType``).
    """
    if "extensionAttributes" not in entity:
        entity["extensionAttributes"] = []
        logger.debug(
            "Injected extensionAttributes on %s (id=%s)",
            entity.get("instanceType", "unknown"),
            entity.get("id", "unknown"),
        )


def validate_instance_type(entity: dict, context: str = "") -> None:
    """Ensure ``instanceType`` is present and valid.

    If ``instanceType`` is missing, attempts to infer it from *context*
    (a hint string such as a parent field name).  If inference fails,
    sets it to ``"Unknown"`` and logs a warning.

    Parameters
    ----------
    entity:
        A dict representing a USDM entity.
    context:
        A hint string (e.g. parent field name) used to infer the type
        when ``instanceType`` is absent.
    """
    instance_type = entity.get("instanceType")

    if instance_type and isinstance(instance_type, str) and instance_type.strip():
        # Already present and non-empty — nothing to do
        return

    # Attempt inference from context
    inferred = _infer_instance_type(context)
    if inferred:
        entity["instanceType"] = inferred
        logger.info(
            "Inferred instanceType '%s' from context '%s' for entity id=%s",
            inferred,
            context,
            entity.get("id", "unknown"),
        )
    else:
        entity["instanceType"] = "Unknown"
        logger.warning(
            "Entity id=%s has no instanceType and could not infer from "
            "context '%s'; set to 'Unknown'",
            entity.get("id", "unknown"),
            context,
        )


def _infer_instance_type(context: str) -> str | None:
    """Try to infer an instanceType from a context hint.

    Maps common USDM field/key names to their expected entity types.
    """
    _CONTEXT_MAP: dict[str, str] = {
        "studyDesigns": "InterventionalStudyDesign",
        "titles": "StudyTitle",
        "studyIdentifiers": "StudyIdentifier",
        "encounters": "Encounter",
        "activities": "Activity",
        "epochs": "StudyEpoch",
        "arms": "StudyArm",
        "studyCells": "StudyCell",
        "elements": "StudyElement",
        "objectives": "Objective",
        "endpoints": "Endpoint",
        "indications": "Indication",
        "organizations": "Organization",
        "conditions": "Condition",
        "abbreviations": "Abbreviation",
        "notes": "CommentAnnotation",
        "amendments": "StudyAmendment",
        "documentedBy": "StudyDefinitionDocument",
        "versions": "StudyDefinitionDocumentVersion",
        "scheduleTimelines": "ScheduleTimeline",
        "biomedicalConcepts": "BiomedicalConcept",
        "studyInterventions": "StudyIntervention",
        "narrativeContentItems": "NarrativeContentItem",
        "eligibilityCriterionItems": "EligibilityCriterionItem",
        "dateValues": "GovernanceDate",
        "roles": "StudyRole",
    }
    return _CONTEXT_MAP.get(context)


def _ensure_id(entity: dict) -> None:
    """Ensure the entity has a non-empty ``id`` field.

    If ``id`` is missing or empty, generates a UUID.
    """
    entity_id = entity.get("id")
    if not entity_id or (isinstance(entity_id, str) and not entity_id.strip()):
        entity["id"] = str(uuid.uuid4())
        logger.debug(
            "Generated id %s for %s entity",
            entity["id"],
            entity.get("instanceType", "unknown"),
        )


def normalize_codes(obj: Any) -> Any:
    """Recursively normalize Code entities in a USDM object tree.

    For every dict with ``instanceType: "Code"``:
    - Replace ``codeSystem: "NCI Thesaurus"`` with ``"http://www.cdisc.org"``
    - Set missing ``codeSystemVersion`` to ``"2024-09-27"``
    - Ensure all required Code fields are present
    - Set ``instanceType`` to ``"Code"`` if missing

    Parameters
    ----------
    obj:
        Any JSON-like object (dict, list, or scalar).

    Returns
    -------
    Any
        The object with all Code entities normalized (modified in place).
    """
    if isinstance(obj, dict):
        # Check if this is a Code entity
        if obj.get("instanceType") == "Code":
            _normalize_single_code(obj)

        # Recurse into all values
        for value in obj.values():
            normalize_codes(value)

    elif isinstance(obj, list):
        for item in obj:
            normalize_codes(item)

    return obj


def _normalize_single_code(code: dict) -> None:
    """Normalize a single Code entity dict in place."""
    # Replace NCI Thesaurus with CDISC URI
    if code.get("codeSystem") == _NCI_THESAURUS:
        code["codeSystem"] = _CDISC_CODE_SYSTEM
        logger.debug(
            "Normalized codeSystem from '%s' to '%s' on Code id=%s",
            _NCI_THESAURUS,
            _CDISC_CODE_SYSTEM,
            code.get("id", "unknown"),
        )

    # Set default codeSystemVersion if missing
    if not code.get("codeSystemVersion"):
        code["codeSystemVersion"] = _DEFAULT_CODE_SYSTEM_VERSION

    # Ensure instanceType is "Code"
    code["instanceType"] = "Code"

    # Ensure extensionAttributes
    if "extensionAttributes" not in code:
        code["extensionAttributes"] = []

    # Ensure id exists
    if not code.get("id"):
        code["id"] = str(uuid.uuid4())

    # Ensure code field exists (default to empty string)
    if "code" not in code:
        code["code"] = ""

    # Ensure codeSystem exists
    if "codeSystem" not in code:
        code["codeSystem"] = ""

    # Ensure decode exists
    if "decode" not in code:
        code["decode"] = ""


def validate_id_references(usdm_doc: USDMDocument) -> list[str]:
    """Check that all ID-reference fields point to valid entity IDs.

    Walks the entire USDM document tree, collects all entity IDs, then
    checks every scalar and list ID-reference field to ensure the
    referenced IDs exist.

    Parameters
    ----------
    usdm_doc:
        The USDM document to validate.

    Returns
    -------
    list[str]
        A list of warning strings for dangling references.
    """
    # Collect all entity IDs
    all_ids: set[str] = set()
    _collect_ids(usdm_doc.study, all_ids)

    # Check all ID references
    warnings: list[str] = []
    _check_references(usdm_doc.study, all_ids, warnings)

    for w in warnings:
        logger.warning(w)

    return warnings


def _collect_ids(obj: Any, ids: set[str]) -> None:
    """Recursively collect all entity IDs from the object tree."""
    if isinstance(obj, dict):
        entity_id = obj.get("id")
        if entity_id and isinstance(entity_id, str):
            ids.add(entity_id)
        for value in obj.values():
            _collect_ids(value, ids)
    elif isinstance(obj, list):
        for item in obj:
            _collect_ids(item, ids)


def _check_references(
    obj: Any, valid_ids: set[str], warnings: list[str]
) -> None:
    """Recursively check ID-reference fields against the set of valid IDs."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            # Scalar ID reference fields
            if key in _SCALAR_ID_REF_FIELDS:
                if isinstance(value, str) and value and value not in valid_ids:
                    warnings.append(
                        f"Dangling ID reference: {key}='{value}' not found "
                        f"in entity IDs (on entity id={obj.get('id', 'unknown')})"
                    )

            # List ID reference fields
            elif key in _LIST_ID_REF_FIELDS:
                if isinstance(value, list):
                    for ref_id in value:
                        if (
                            isinstance(ref_id, str)
                            and ref_id
                            and ref_id not in valid_ids
                        ):
                            warnings.append(
                                f"Dangling ID reference: {key} contains "
                                f"'{ref_id}' not found in entity IDs "
                                f"(on entity id={obj.get('id', 'unknown')})"
                            )

            # Recurse into nested structures
            else:
                _check_references(value, valid_ids, warnings)

    elif isinstance(obj, list):
        for item in obj:
            _check_references(item, valid_ids, warnings)
