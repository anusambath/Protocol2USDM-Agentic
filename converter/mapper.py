"""Entity mapping from Prodigy structure to USDM 4.0 hierarchy.

Transforms a parsed ProdigyDocument into a USDMDocument by mapping
the Prodigy Study entity to the USDM study root, mapping study versions
with all required USDM 4.0 fields, mapping documentedBy structures,
consolidating top-level entities, resolving relationships, and handling
schedule-of-activity and domain module data.
"""

from __future__ import annotations

import logging
from typing import Any

from converter.models import ConversionStats, ProdigyDocument, USDMDocument

logger = logging.getLogger(__name__)

# Required list fields on a USDM 4.0 StudyVersion entity.
# Absent fields default to empty arrays.
_STUDY_VERSION_LIST_FIELDS: list[str] = [
    "extensionAttributes",
    "documentVersionIds",
    "dateValues",
    "amendments",
    "businessTherapeuticAreas",
    "studyIdentifiers",
    "referenceIdentifiers",
    "studyDesigns",
    "titles",
    "eligibilityCriterionItems",
    "narrativeContentItems",
    "abbreviations",
    "roles",
    "organizations",
    "studyInterventions",
    "administrableProducts",
    "medicalDevices",
    "productOrganizationRoles",
    "biomedicalConcepts",
    "bcCategories",
    "bcSurrogates",
    "dictionaries",
    "conditions",
    "notes",
]

# Required scalar fields on a USDM 4.0 StudyVersion entity.
# Absent fields default to None.
_STUDY_VERSION_SCALAR_FIELDS: list[str] = [
    "versionIdentifier",
    "rationale",
]

# The canonical set of USDM 4.0 StudyVersion keys (for detecting extra fields).
_USDM_STUDY_VERSION_KEYS: set[str] = (
    {"id", "instanceType"}
    | set(_STUDY_VERSION_LIST_FIELDS)
    | set(_STUDY_VERSION_SCALAR_FIELDS)
)


# Required fields on a StudyDefinitionDocument entity.
_STUDY_DEF_DOC_FIELDS: list[str] = [
    "id",
    "extensionAttributes",
    "name",
    "label",
    "description",
    "language",
    "type",
    "templateName",
    "versions",
    "childIds",
    "notes",
    "instanceType",
]

# Required fields on a StudyDefinitionDocumentVersion entity.
_STUDY_DEF_DOC_VERSION_FIELDS: list[str] = [
    "id",
    "extensionAttributes",
    "version",
    "status",
    "dateValues",
    "contents",
    "notes",
    "instanceType",
]


def map_to_usdm(doc: ProdigyDocument) -> USDMDocument:
    """Transform a :class:`ProdigyDocument` into a USDM 4.0 :class:`USDMDocument`.

    Orchestrates the full mapping: study root, versions, documentedBy,
    top-level entity consolidation, relationship resolution, schedule-of-activity
    mapping, and domain module handling.

    Parameters
    ----------
    doc:
        A parsed (and ideally metadata-stripped) Prodigy document.

    Returns
    -------
    USDMDocument
        The mapped USDM 4.0 document with warnings and stats.
    """
    warnings: list[str] = []
    stats = ConversionStats()

    study = map_study(doc.study, warnings)

    logger.info(
        "Mapped study '%s' with %d version(s) and %d documentedBy entry/entries",
        study.get("name"),
        len(study.get("versions", [])),
        len(study.get("documentedBy", [])),
    )

    usdm_doc = USDMDocument(study=study, warnings=warnings, stats=stats)

    # --- Consolidate top-level entities into the first study version ---
    versions = study.get("versions", [])
    if versions:
        consolidate_top_level_entities(doc, versions[0])

    # --- Map schedule_of_activity into studyDesigns ---
    soa_data = doc.auxiliary.get("schedule_of_activity")
    if soa_data and versions:
        study_designs = versions[0].get("studyDesigns", [])
        if study_designs:
            map_schedule_of_activity(soa_data, study_designs[0])

    # --- Map domain modules ---
    if doc.domain_modules:
        mapped_data, module_warnings = map_domain_modules(doc.domain_modules)
        warnings.extend(module_warnings)
        stats.domain_modules_mapped = len(mapped_data)
        stats.domain_modules_skipped = len(doc.domain_modules) - len(mapped_data)

    # --- Resolve relationships ---
    if doc.relationships:
        resolve_relationships(doc.relationships, usdm_doc)

    return usdm_doc


def map_study(study_data: dict, warnings: list[str] | None = None) -> dict:
    """Map a Prodigy ``Study`` entity to the USDM 4.0 ``study`` root.

    Produces a lowercase-keyed study dict with the required USDM 4.0 fields:
    ``id``, ``name``, ``description``, ``label``, ``versions``,
    ``documentedBy``, and ``instanceType``.

    Parameters
    ----------
    study_data:
        The raw Prodigy Study dict (from ``ProdigyDocument.study``).
    warnings:
        Optional list to accumulate mapping warnings.

    Returns
    -------
    dict
        The USDM 4.0 study root object.
    """
    if warnings is None:
        warnings = []

    # Map versions
    raw_versions = study_data.get("versions", [])
    versions = [
        map_study_version(v, warnings) for v in raw_versions
    ]

    # Map documentedBy
    raw_documented_by = study_data.get("documentedBy", [])
    documented_by = map_documented_by(raw_documented_by)

    return {
        "id": study_data.get("id"),
        "name": study_data.get("name"),
        "description": study_data.get("description"),
        "label": study_data.get("label"),
        "versions": versions,
        "documentedBy": documented_by,
        "instanceType": "Study",
    }


def map_study_version(version_data: dict, warnings: list[str] | None = None) -> dict:
    """Map a Prodigy version object to a USDM 4.0 ``StudyVersion`` entity.

    Ensures all required USDM 4.0 fields are present, defaulting absent
    list fields to empty arrays and absent scalar fields to ``None``.

    Extra Prodigy fields that are not in the USDM 4.0 golden schema
    (e.g. ``safetyMonitoring``, ``statisticalConsiderations``) are dropped
    with a logged warning.

    Parameters
    ----------
    version_data:
        A single version dict from ``Study.versions``.
    warnings:
        Optional list to accumulate mapping warnings.

    Returns
    -------
    dict
        A USDM 4.0 ``StudyVersion`` entity dict.
    """
    if warnings is None:
        warnings = []

    result: dict[str, Any] = {}

    # id
    result["id"] = version_data.get("id")

    # List fields — default to empty array if absent
    for field_name in _STUDY_VERSION_LIST_FIELDS:
        result[field_name] = version_data.get(field_name, [])
        # Ensure None values become empty arrays for list fields
        if result[field_name] is None:
            result[field_name] = []

    # Scalar fields — default to None if absent
    for field_name in _STUDY_VERSION_SCALAR_FIELDS:
        result[field_name] = version_data.get(field_name)

    # instanceType — always set to StudyVersion
    result["instanceType"] = "StudyVersion"

    # Detect and warn about extra Prodigy fields not in USDM 4.0
    for key in version_data:
        if key not in _USDM_STUDY_VERSION_KEYS:
            msg = (
                f"StudyVersion field '{key}' is not in the USDM 4.0 schema "
                f"and has been dropped"
            )
            logger.warning(msg)
            warnings.append(msg)

    return result


def map_documented_by(docs: list[dict]) -> list[dict]:
    """Map a Prodigy ``documentedBy`` array to USDM 4.0 document entities.

    Each entry is mapped to a ``StudyDefinitionDocument`` with its nested
    ``versions`` mapped to ``StudyDefinitionDocumentVersion`` entities.

    Parameters
    ----------
    docs:
        The ``documentedBy`` array from the Prodigy Study entity.

    Returns
    -------
    list[dict]
        A list of ``StudyDefinitionDocument`` entity dicts.
    """
    return [_map_single_document(doc) for doc in docs]


def _map_single_document(doc: dict) -> dict:
    """Map a single Prodigy document entry to a ``StudyDefinitionDocument``."""
    result: dict[str, Any] = {}

    for field_name in _STUDY_DEF_DOC_FIELDS:
        if field_name == "instanceType":
            result["instanceType"] = "StudyDefinitionDocument"
        elif field_name == "versions":
            raw_versions = doc.get("versions", [])
            result["versions"] = [
                _map_single_document_version(v) for v in raw_versions
            ]
        elif field_name == "extensionAttributes":
            result["extensionAttributes"] = doc.get("extensionAttributes", [])
            if result["extensionAttributes"] is None:
                result["extensionAttributes"] = []
        elif field_name in ("childIds", "notes"):
            # List fields — default to empty array
            result[field_name] = doc.get(field_name, [])
            if result[field_name] is None:
                result[field_name] = []
        else:
            # Scalar fields (id, name, label, description, language, type, templateName)
            result[field_name] = doc.get(field_name)

    return result


def _map_single_document_version(version: dict) -> dict:
    """Map a single document version to a ``StudyDefinitionDocumentVersion``."""
    result: dict[str, Any] = {}

    for field_name in _STUDY_DEF_DOC_VERSION_FIELDS:
        if field_name == "instanceType":
            result["instanceType"] = "StudyDefinitionDocumentVersion"
        elif field_name == "extensionAttributes":
            result["extensionAttributes"] = version.get("extensionAttributes", [])
            if result["extensionAttributes"] is None:
                result["extensionAttributes"] = []
        elif field_name in ("dateValues", "contents", "notes"):
            # List fields — default to empty array
            result[field_name] = version.get(field_name, [])
            if result[field_name] is None:
                result[field_name] = []
        else:
            # Scalar fields (id, version, status)
            result[field_name] = version.get(field_name)

    return result


# ---------------------------------------------------------------------------
# Top-level entity consolidation
# ---------------------------------------------------------------------------


def consolidate_top_level_entities(
    doc: ProdigyDocument, study_version: dict
) -> None:
    """Merge Prodigy top-level entities into the USDM study version in place.

    Handles:
    - ``Identifier`` → ``studyIdentifiers`` array
    - ``PopulationDefinition`` → ``population`` field in studyDesigns[0]
    - ``ScheduledInstance`` → schedule-related structures in studyDesigns[0]
    - ``SyntaxTemplate`` → discarded with warning
    - ``metadata`` → relevant fields extracted into appropriate USDM fields

    Parameters
    ----------
    doc:
        The parsed Prodigy document containing top-level entities.
    study_version:
        The first USDM StudyVersion dict to merge entities into.
        Modified in place.
    """
    # --- Identifier → studyIdentifiers ---
    if doc.identifiers:
        existing = study_version.get("studyIdentifiers", [])
        if existing is None:
            existing = []
        existing.extend(doc.identifiers)
        study_version["studyIdentifiers"] = existing
        logger.info(
            "Consolidated %d identifier(s) into studyIdentifiers",
            len(doc.identifiers),
        )

    # --- PopulationDefinition → studyDesigns[0].population ---
    if doc.population_definition is not None:
        study_designs = study_version.get("studyDesigns", [])
        if study_designs:
            study_designs[0]["population"] = doc.population_definition
            logger.info("Consolidated PopulationDefinition into studyDesigns[0].population")
        else:
            logger.warning(
                "PopulationDefinition present but no studyDesigns to merge into"
            )

    # --- ScheduledInstance → schedule-related structures in studyDesigns[0] ---
    if doc.scheduled_instances:
        study_designs = study_version.get("studyDesigns", [])
        if study_designs:
            design = study_designs[0]
            # Merge scheduled instances into scheduleTimelines
            existing_timelines = design.get("scheduleTimelines", [])
            if existing_timelines is None:
                existing_timelines = []
            existing_timelines.extend(doc.scheduled_instances)
            design["scheduleTimelines"] = existing_timelines
            logger.info(
                "Consolidated %d scheduled instance(s) into "
                "studyDesigns[0].scheduleTimelines",
                len(doc.scheduled_instances),
            )
        else:
            logger.warning(
                "ScheduledInstance present but no studyDesigns to merge into"
            )

    # --- SyntaxTemplate → discard with warning ---
    if doc.syntax_templates:
        for tmpl in doc.syntax_templates:
            tmpl_id = tmpl.get("id", "unknown")
            msg = (
                f"SyntaxTemplate '{tmpl_id}' has no USDM 4.0 mapping "
                f"and has been discarded"
            )
            logger.warning(msg)

    # --- metadata → extract relevant fields ---
    if doc.metadata:
        _merge_metadata(doc.metadata, study_version)


def _merge_metadata(metadata: dict, study_version: dict) -> None:
    """Extract relevant metadata fields into USDM study version fields.

    Maps document dates from metadata into ``dateValues`` on the study version.

    Parameters
    ----------
    metadata:
        The Prodigy ``metadata`` dict.
    study_version:
        The USDM StudyVersion dict to update in place.
    """
    date_values = study_version.get("dateValues", [])
    if date_values is None:
        date_values = []

    protocol_date = metadata.get("protocol_date")
    if protocol_date:
        date_values.append({
            "id": metadata.get("id", "metadata_date"),
            "type": "protocol_date",
            "dateValue": protocol_date,
            "instanceType": "GovernanceDate",
        })

    extraction_timestamp = metadata.get("extraction_timestamp")
    if extraction_timestamp:
        date_values.append({
            "id": f"{metadata.get('id', 'metadata')}_extraction",
            "type": "extraction_date",
            "dateValue": extraction_timestamp,
            "instanceType": "GovernanceDate",
        })

    if date_values:
        study_version["dateValues"] = date_values
        logger.info(
            "Merged %d date value(s) from metadata into studyVersion.dateValues",
            len(date_values),
        )


# ---------------------------------------------------------------------------
# Relationship resolution
# ---------------------------------------------------------------------------

# Relationship types that map to known USDM ID-reference fields on entities.
_RELATIONSHIP_TYPE_TO_FIELD: dict[str, str] = {
    "epoch": "epochId",
    "epochs": "epochIds",
    "arm": "armId",
    "arms": "armIds",
    "activities": "activityIds",
    "encounters": "encounterIds",
    "scheduleTimelines": "scheduleTimelineIds",
    "population": "populationId",
    "populations": "populationIds",
    "estimands": "estimandIds",
    "objectives": "objectiveIds",
    "endpoints": "endpointIds",
    "indications": "indicationIds",
    "studyCells": "studyCellIds",
    "elements": "elementIds",
    "organizations": "organizationIds",
    "studyInterventions": "studyInterventionIds",
}


def resolve_relationships(
    relationships: list[dict], usdm_doc: USDMDocument
) -> None:
    """Process the Prodigy relationships array to populate ID-reference fields.

    Each relationship has ``id``, ``type``, ``startNodeId``, ``endNodeId``,
    and ``properties``. The ``type`` is mapped to a USDM ID-reference field
    name, and the ``endNodeId`` is added to the corresponding field on the
    entity identified by ``startNodeId``.

    Relationships with no USDM mapping are logged as warnings and discarded.

    Parameters
    ----------
    relationships:
        The Prodigy ``relationships`` array.
    usdm_doc:
        The USDM document being built. Stats are updated in place.
    """
    # Build an index of all entities by ID for fast lookup
    entity_index: dict[str, dict] = {}
    _index_entities(usdm_doc.study, entity_index)

    processed = 0
    discarded = 0

    for rel in relationships:
        rel_type = rel.get("type", "")
        start_id = rel.get("startNodeId", "")
        end_id = rel.get("endNodeId", "")

        # Check if this relationship type maps to a USDM field
        usdm_field = _RELATIONSHIP_TYPE_TO_FIELD.get(rel_type)

        if usdm_field is None:
            # No direct mapping — discard with warning
            discarded += 1
            logger.debug(
                "Relationship '%s' (type=%s) has no USDM 4.0 mapping; discarded",
                rel.get("id", "unknown"),
                rel_type,
            )
            continue

        # Find the source entity
        source_entity = entity_index.get(start_id)
        if source_entity is None:
            discarded += 1
            logger.debug(
                "Relationship '%s': source entity '%s' not found in USDM output",
                rel.get("id", "unknown"),
                start_id,
            )
            continue

        # Populate the ID-reference field
        if usdm_field.endswith("Ids") or usdm_field.endswith("ids"):
            # Array reference field
            existing = source_entity.get(usdm_field, [])
            if existing is None:
                existing = []
            if end_id not in existing:
                existing.append(end_id)
            source_entity[usdm_field] = existing
        else:
            # Scalar reference field
            source_entity[usdm_field] = end_id

        processed += 1

    usdm_doc.stats.relationships_processed = processed
    usdm_doc.stats.relationships_discarded = discarded

    logger.info(
        "Relationships: %d processed, %d discarded (no USDM mapping or missing entity)",
        processed,
        discarded,
    )


def _index_entities(obj: Any, index: dict[str, dict]) -> None:
    """Recursively index all entities (dicts with ``id``) in the USDM tree."""
    if isinstance(obj, dict):
        entity_id = obj.get("id")
        if entity_id and isinstance(entity_id, str):
            index[entity_id] = obj
        for value in obj.values():
            _index_entities(value, index)
    elif isinstance(obj, list):
        for item in obj:
            _index_entities(item, index)


# ---------------------------------------------------------------------------
# Schedule of Activity mapping
# ---------------------------------------------------------------------------


def map_schedule_of_activity(soa_data: Any, study_design: dict) -> None:
    """Map schedule_of_activity data into USDM schedule structures.

    The ``schedule_of_activity`` is a list with one element containing:
    ``title``, ``structure``, ``id``, ``table_reference``, ``page_number``,
    ``span_hash``. The ``structure`` dict contains ``periods``, ``encounter``,
    ``activity``, ``cells``, ``footnotes``, and ``table_metadata``.

    Maps into ``encounters``, ``activities``, ``epochs``, and
    ``scheduleTimelines`` within the study design.

    Parameters
    ----------
    soa_data:
        The ``schedule_of_activity`` value from Prodigy auxiliary data.
        Expected to be a list with one dict element.
    study_design:
        The first studyDesigns entry to populate. Modified in place.
    """
    # Normalize to list
    if isinstance(soa_data, dict):
        soa_list = [soa_data]
    elif isinstance(soa_data, list):
        soa_list = soa_data
    else:
        logger.warning("schedule_of_activity has unexpected type: %s", type(soa_data))
        return

    if not soa_list:
        return

    soa_entry = soa_list[0]
    structure = soa_entry.get("structure", {})
    if not isinstance(structure, dict):
        logger.warning("schedule_of_activity structure is not a dict")
        return

    # --- Map periods → epochs ---
    periods = structure.get("periods", [])
    epochs: list[dict] = []
    for period in periods:
        epoch: dict[str, Any] = {
            "id": period.get("id", ""),
            "name": period.get("name", ""),
            "instanceType": "StudyEpoch",
        }
        epochs.append(epoch)

    if epochs:
        existing_epochs = study_design.get("epochs", [])
        if existing_epochs is None:
            existing_epochs = []
        existing_epochs.extend(epochs)
        study_design["epochs"] = existing_epochs

    # --- Map encounters ---
    raw_encounters = structure.get("encounter", [])
    encounters: list[dict] = []
    for enc in raw_encounters:
        encounter: dict[str, Any] = {
            "id": enc.get("id", ""),
            "name": enc.get("name", ""),
            "instanceType": "Encounter",
        }
        # Link to epoch via period_id
        period_id = enc.get("period_id")
        if period_id:
            encounter["epochId"] = period_id
        encounters.append(encounter)

    if encounters:
        existing_encounters = study_design.get("encounters", [])
        if existing_encounters is None:
            existing_encounters = []
        existing_encounters.extend(encounters)
        study_design["encounters"] = existing_encounters

    # --- Map activities ---
    raw_activities = structure.get("activity", [])
    activities: list[dict] = []
    for act in raw_activities:
        activity: dict[str, Any] = {
            "id": act.get("id", ""),
            "name": act.get("name", ""),
            "instanceType": "Activity",
        }
        activities.append(activity)

    if activities:
        existing_activities = study_design.get("activities", [])
        if existing_activities is None:
            existing_activities = []
        existing_activities.extend(activities)
        study_design["activities"] = existing_activities

    # --- Map cells → ScheduledActivityInstance entries in scheduleTimelines ---
    raw_cells = structure.get("cells", [])
    scheduled_instances: list[dict] = []
    for cell in raw_cells:
        if cell.get("value") and cell.get("activity_id") and cell.get("encounter_id"):
            sai: dict[str, Any] = {
                "id": cell.get("id", ""),
                "activityIds": [cell["activity_id"]],
                "encounterId": cell["encounter_id"],
                "instanceType": "ScheduledActivityInstance",
            }
            scheduled_instances.append(sai)

    if scheduled_instances:
        # Create or extend a schedule timeline for SoA instances
        timelines = study_design.get("scheduleTimelines", [])
        if timelines is None:
            timelines = []

        soa_timeline: dict[str, Any] = {
            "id": soa_entry.get("id", "soa_timeline"),
            "name": soa_entry.get("title", "Schedule of Activities"),
            "instances": scheduled_instances,
            "instanceType": "ScheduleTimeline",
        }
        timelines.append(soa_timeline)
        study_design["scheduleTimelines"] = timelines

    logger.info(
        "Mapped schedule_of_activity: %d epoch(s), %d encounter(s), "
        "%d activity/activities, %d scheduled instance(s)",
        len(epochs),
        len(encounters),
        len(activities),
        len(scheduled_instances),
    )


# ---------------------------------------------------------------------------
# Domain module mapping
# ---------------------------------------------------------------------------


def map_domain_modules(
    modules: dict[str, Any],
) -> tuple[dict, list[str]]:
    """Attempt to map Prodigy domain modules to USDM 4.0 fields.

    Most domain modules have no USDM 4.0 mapping and are discarded with
    warnings. Returns a tuple of (mapped_data, warnings_list).

    Parameters
    ----------
    modules:
        Dict of domain module name → module data.

    Returns
    -------
    tuple[dict, list[str]]
        A tuple of (mapped_data dict, list of warning strings).
        ``mapped_data`` contains any successfully mapped module data
        (currently empty for all known domain modules).
    """
    mapped_data: dict[str, Any] = {}
    warnings: list[str] = []

    for module_name, module_data in modules.items():
        # Currently no domain modules have a defined USDM 4.0 mapping.
        msg = (
            f"Domain module '{module_name}' has no USDM 4.0 mapping "
            f"and has been discarded"
        )
        logger.warning(msg)
        warnings.append(msg)

    logger.info(
        "Domain modules: %d total, %d mapped, %d discarded",
        len(modules),
        len(mapped_data),
        len(modules) - len(mapped_data),
    )

    return mapped_data, warnings
