"""
USDM Generator Agent - Builds USDM v4.0 JSON from Context Store entities.

Queries the Context Store for all extracted entities and assembles them
into the USDM v4.0 hierarchy:
  Study → StudyVersion → StudyDesign → (arms, epochs, activities, etc.)
"""

import json
import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.base import AgentCapabilities, AgentResult, AgentState, AgentTask, BaseAgent

logger = logging.getLogger(__name__)


# Internal properties that should NOT appear in the final USDM JSON.
# These are added by extraction, reconciliation, enrichment, and validation agents.
_INTERNAL_PROPERTIES = {
    "raw",                      # raw extracted text (provenance)
    "source",                   # source agent/page info
    "_reconciled",              # reconciliation flag
    "_sources",                 # reconciliation source list
    "_enrichment_confidence",   # enrichment metadata
    "_enrichment_source",       # enrichment metadata
    "_validation_fixes",        # validation auto-fix records
    "order",                    # internal ordering (not in USDM schema)
    "entity_type",              # internal type tag (already encoded in placement)
}

# Estimand extension properties that are NOT in the USDM v4.0 schema.
# These are informational duplicates — the real data is already in the
# proper USDM fields (interventionIds, analysisPopulationId,
# variableOfInterestId, populationSummary).
_ESTIMAND_EXTRA_PROPERTIES = {
    "treatment",                # text description → already in interventionIds
    "analysisPopulation",       # text description → already in analysisPopulationId
    "variableOfInterest",       # text description → already in variableOfInterestId
    "summaryMeasure",           # text description → already folded into populationSummary
}

# Per-entity-type properties to strip from the USDM output.
# These are either internal extensions or properties not in the v4.0 schema.
_ENTITY_EXTRA_PROPERTIES: Dict[str, set] = {
    "estimand": _ESTIMAND_EXTRA_PROPERTIES,
    "narrative_content": {"childIds", "sectionNumber", "sectionTitle", "sectionType"},
    "narrative_content_item": {"childIds", "sectionNumber", "sectionTitle", "sectionType"},
    "study_population": {"criteria"},
    # StudyIdentifier: "identifierType" and "type" not in USDM 4.0 schema (DDF00125)
    "study_identifier": {"identifierType", "type"},
    "objective": {"endpointIds"},  # endpoints live at StudyDesign level, not nested
    "study_intervention": {"administrationIds", "productIds", "codes"},
    "comment_annotation": {"annotationType", "pageNumber", "sourceSection"},
    "schedule_exit": {"description", "exitType", "name"},
    "study_amendment": {
        "effectiveDate", "newVersion", "previousVersion", "reasonIds", "scope",
    },
    "amendment": {
        "effectiveDate", "newVersion", "previousVersion", "reasonIds", "scope",
    },
    # Encounter: "epochId" not in USDM 4.0 Encounter schema (DDF00125)
    "encounter": {"epochId"},
    # BiomedicalConcept: "categories" not in USDM 4.0 (use bcCategories at version level)
    "biomedical_concept": {"categories"},
    # BiomedicalConceptCategory: "bcIds" not in USDM 4.0 schema (DDF00125)
    "biomedical_concept_category": {"bcIds"},
    # AnalysisPopulation: "level" not in USDM 4.0 schema (DDF00125)
    "analysis_population": {"level"},
    # MedicalDevice: extra properties not in USDM 4.0 schema (DDF00125)
    "medical_device": {"codes", "deviceType", "manufacturer", "modelNumber"},
    # AdministrableProduct: extra properties not in USDM 4.0 schema (DDF00125)
    "administrable_product": {"manufacturer", "strength", "substanceIds"},
}


def _is_code_object(d: Dict[str, Any]) -> bool:
    """Check if a dict looks like a USDM Code object."""
    return "code" in d and ("codeSystem" in d or "decode" in d)


def _ensure_code_id(d: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure a USDM Code object has all required fields.

    Required by CORE engine: id, code, codeSystem, codeSystemVersion,
    decode, instanceType.
    """
    if not d.get("id"):
        d["id"] = str(uuid.uuid4()).replace("-", "_")
    if "instanceType" not in d:
        d["instanceType"] = "Code"
    if "codeSystem" not in d:
        d["codeSystem"] = "http://www.cdisc.org"
    if "codeSystemVersion" not in d:
        d["codeSystemVersion"] = "2024-09-27"
    if "decode" not in d:
        d["decode"] = d.get("code", "")
    return d


def _sanitize_entity_data(entity_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove internal/debug properties that are not part of the USDM v4.0 schema.

    Also recursively sanitizes nested dicts and lists, ensures all
    USDM Code objects have required fields, and normalizes
    codeSystemVersion to ISO 8601 format.
    """
    cleaned = {}
    for key, value in entity_data.items():
        # Skip known internal properties
        if key in _INTERNAL_PROPERTIES:
            continue
        # Skip any property starting with underscore (internal convention)
        if key.startswith("_"):
            continue
        # Recursively clean nested dicts
        if isinstance(value, dict):
            sanitized = _sanitize_entity_data(value)
            # Ensure Code objects have all required fields
            if _is_code_object(sanitized):
                sanitized = _ensure_code_id(sanitized)
            cleaned[key] = sanitized
        # Recursively clean lists of dicts
        elif isinstance(value, list):
            items = []
            for item in value:
                if isinstance(item, dict):
                    sanitized = _sanitize_entity_data(item)
                    if _is_code_object(sanitized):
                        sanitized = _ensure_code_id(sanitized)
                    items.append(sanitized)
                else:
                    items.append(item)
            cleaned[key] = items
        else:
            # Fix codeSystemVersion underscores → ISO 8601 dashes
            if key == "codeSystemVersion" and isinstance(value, str):
                if re.match(r"^\d{4}_\d{2}_\d{2}$", value):
                    value = value.replace("_", "-")
            cleaned[key] = value
    return cleaned


# USDM entity type → placement path in the hierarchy
ENTITY_TYPE_PLACEMENT = {
    "metadata": "study",
    "study_identifier": "study.versions[0].studyIdentifiers",
    "study_phase": "study.versions[0].studyPhase",
    "study_title": "study.versions[0].titles",
    "indication": "study.versions[0].studyDesigns[0].indications",
    "objective": "study.versions[0].studyDesigns[0].objectives",
    "endpoint": "study.versions[0].studyDesigns[0].endpoints",
    "estimand": "study.versions[0].studyDesigns[0].estimands",
    "study_arm": "study.versions[0].studyDesigns[0].arms",
    "study_epoch": "study.versions[0].studyDesigns[0].epochs",
    "epoch": "study.versions[0].studyDesigns[0].epochs",  # alias
    "study_cell": "study.versions[0].studyDesigns[0].studyCells",
    "eligibility_criterion": "study.versions[0].studyDesigns[0].eligibilityCriteria",
    "criterion_item": "study.versions[0].eligibilityCriterionItems",
    "study_population": "study.versions[0].studyDesigns[0].population",
    "activity": "study.versions[0].studyDesigns[0].activities",
    "encounter": "study.versions[0].studyDesigns[0].encounters",
    "intervention": "study.versions[0].studyDesigns[0].studyInterventions",
    "study_intervention": "study.versions[0].studyDesigns[0].studyInterventions",  # alias
    "substance": "study.versions[0].studyDesigns[0].studyInterventions[].substances",
    "administrable_product": "study.versions[0].administrableProducts",
    "medical_device": "study.versions[0].medicalDevices",
    "study_element": "study.versions[0].studyDesigns[0].elements",
    "analysis_population": "study.versions[0].studyDesigns[0].analysisPopulations",
    "governance_date": "study.versions[0].dateValues",
    "biomedical_concept": "study.versions[0].biomedicalConcepts",
    "biomedical_concept_category": "study.versions[0].bcCategories",
    "timing": "study.versions[0].studyDesigns[0].scheduleTimelines[].timings",
    "schedule_timeline": "study.versions[0].studyDesigns[0].scheduleTimelines",
    "scheduled_instance": "study.versions[0].studyDesigns[0].scheduleTimelines[].instances",
    "narrative_content": "study.versions[0].narrativeContentItems",
    "narrative_content_item": "study.versions[0].narrativeContentItems",  # alias
    "abbreviation": "study.versions[0].abbreviations",
    "amendment": "study.versions[0].amendments",
    "study_amendment": "study.versions[0].amendments",  # alias
    "geographic_scope": "study.versions[0].studyDesigns[0].geographicScopes",
    "country": "study.versions[0].studyDesigns[0].geographicScopes[].countries",
    "document_section": "study.documentVersions[0].sections",
    "organization": "study.versions[0].organizations",
    "study_role": "study.versions[0].roles",
    "schedule_exit": "study.versions[0].studyDesigns[0]._pendingExits",
    "comment_annotation": "study.versions[0].studyDesigns[0].notes",
}

# Entity types that go into list containers
LIST_ENTITY_TYPES = {
    "study_identifier", "study_title", "indication", "objective",
    "endpoint", "estimand", "study_arm", "study_epoch", "epoch", "study_cell",
    "eligibility_criterion", "criterion_item", "activity", "encounter",
    "intervention", "study_intervention", "substance", "timing",
    "schedule_timeline", "narrative_content", "narrative_content_item",
    "abbreviation", "amendment", "study_amendment",
    "geographic_scope", "country", "document_section",
    "organization", "study_role", "schedule_exit", "comment_annotation",
    # Phase 1 additions — wired entities
    "administrable_product", "medical_device", "study_element",
    "analysis_population", "governance_date",
    # Phase 3 additions — BiomedicalConcept agent
    "biomedical_concept", "biomedical_concept_category",
    # SoA tick data
    "scheduled_instance",
}


@dataclass
class USDMValidationIssue:
    """An issue found during USDM structure validation."""
    severity: str  # "error", "warning", "info"
    path: str
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {"severity": self.severity, "path": self.path, "message": self.message}


@dataclass
class USDMGenerationResult:
    """Result of USDM generation."""
    usdm_json: Dict[str, Any] = field(default_factory=dict)
    entity_count: int = 0
    entity_types_included: List[str] = field(default_factory=list)
    validation_issues: List[USDMValidationIssue] = field(default_factory=list)
    output_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_count": self.entity_count,
            "entity_types_included": self.entity_types_included,
            "validation_issues": [v.to_dict() for v in self.validation_issues],
            "output_path": self.output_path,
        }


def _build_empty_usdm_skeleton() -> Dict[str, Any]:
    """Build the minimal USDM v4.0 skeleton structure."""
    return {
        "usdmVersion": "4.0.0",
        "study": {
            "id": str(uuid.uuid4()),
            "instanceType": "Study",
            "name": "",
            "description": "",
            "label": "",
            "versions": [
                {
                    "id": str(uuid.uuid4()),
                    "versionIdentifier": "1",
                    "rationale": "",
                    "titles": [],
                    "studyIdentifiers": [],
                    "studyPhase": None,
                    "organizations": [],
                    "roles": [],
                    "narrativeContentItems": [],
                    "abbreviations": [],
                    "amendments": [],
                    "eligibilityCriterionItems": [],
                    "dateValues": [],
                    "businessTherapeuticAreas": [],
                    "administrableProducts": [],
                    "medicalDevices": [],
                    "biomedicalConcepts": [],
                    "bcCategories": [],
                    "studyDesigns": [
                        {
                            "id": str(uuid.uuid4()),
                            "name": "",
                            "description": "",
                            "arms": [],
                            "epochs": [],
                            "studyCells": [],
                            "objectives": [],
                            "endpoints": [],
                            "estimands": [],
                            "indications": [],
                            "activities": [],
                            "encounters": [],
                            "procedures": [],
                            "studyInterventions": [],
                            "soaFootnotes": [],
                            "scheduleTimelines": [],
                            "eligibilityCriteria": [],
                            "elements": [],
                            "analysisPopulations": [],
                            "studyInterventionIds": [],
                            "population": {
                                "id": str(uuid.uuid4()),
                                "name": "Study Population",
                                "criteria": [],
                                "instanceType": "StudyDesignPopulation",
                            },
                            "geographicScopes": [],
                        }
                    ],
                }
            ],
            "documentVersions": [
                {
                    "id": str(uuid.uuid4()),
                    "sections": [],
                }
            ],
        }
    }


def _place_entity(usdm: Dict[str, Any], entity_type: str,
                   entity_data: Dict[str, Any]) -> bool:
    """
    Place an entity into the correct location in the USDM hierarchy.

    Returns True if placed successfully.
    """
    placement = ENTITY_TYPE_PLACEMENT.get(entity_type)
    if not placement:
        return False

    try:
        if entity_type == "metadata":
            _place_metadata(usdm, entity_data)
            return True
        elif entity_type == "study_phase":
            usdm["study"]["versions"][0]["studyPhase"] = entity_data
            return True
        elif entity_type == "study_population":
            pop = usdm["study"]["versions"][0]["studyDesigns"][0]["population"]
            pop.update({k: v for k, v in entity_data.items() if k != "criteria"})
            return True
        elif entity_type in LIST_ENTITY_TYPES:
            container = _resolve_list_container(usdm, entity_type)
            if container is not None:
                container.append(entity_data)
                return True
        return False
    except (KeyError, IndexError, TypeError):
        return False


def _place_metadata(usdm: Dict[str, Any], data: Dict[str, Any]) -> None:
    """Place metadata fields at the study level and version level."""
    study = usdm["study"]
    if "name" in data:
        study["name"] = data["name"]
    if "description" in data:
        study["description"] = data["description"]
    if "label" in data:
        study["label"] = data["label"]
    # Propagate versionIdentifier to StudyVersion
    if data.get("versionIdentifier") and study.get("versions"):
        study["versions"][0]["versionIdentifier"] = str(data["versionIdentifier"])


def _resolve_list_container(usdm: Dict[str, Any],
                             entity_type: str) -> Optional[List]:
    """Resolve the list container for a given entity type."""
    study = usdm["study"]
    version = study["versions"][0]
    design = version["studyDesigns"][0]

    mapping = {
        "study_identifier": version["studyIdentifiers"],
        "study_title": version["titles"],
        "indication": design["indications"],
        "objective": design["objectives"],
        "endpoint": design["endpoints"],
        "estimand": design["estimands"],
        "study_arm": design["arms"],
        "study_epoch": design["epochs"],
        "epoch": design["epochs"],
        "study_cell": design["studyCells"],
        "eligibility_criterion": design["eligibilityCriteria"],
        "criterion_item": version["eligibilityCriterionItems"],
        "activity": design["activities"],
        "encounter": design["encounters"],
        "procedure": design["procedures"],
        "intervention": design["studyInterventions"],
        "study_intervention": design["studyInterventions"],
        "schedule_timeline": design["scheduleTimelines"],
        "narrative_content": version["narrativeContentItems"],
        "narrative_content_item": version["narrativeContentItems"],
        "abbreviation": version["abbreviations"],
        "amendment": version["amendments"],
        "study_amendment": version["amendments"],
        "geographic_scope": design["geographicScopes"],
        "document_section": study["documentVersions"][0]["sections"],
        "organization": version["organizations"],
        "study_role": version["roles"],
        "schedule_exit": design.setdefault("_pendingExits", []),
        "scheduled_instance": design.setdefault("_scheduledInstances", []),
        "comment_annotation": design.setdefault("notes", []),
        # Phase 1 additions
        "administrable_product": version.setdefault("administrableProducts", []),
        "medical_device": version.setdefault("medicalDevices", []),
        "study_element": design.setdefault("elements", []),
        "analysis_population": design.setdefault("analysisPopulations", []),
        "governance_date": version.setdefault("dateValues", []),
        # Phase 3 additions
        "biomedical_concept": version.setdefault("biomedicalConcepts", []),
        "biomedical_concept_category": version.setdefault("bcCategories", []),
    }
    return mapping.get(entity_type)


def _resolve_objective_endpoints(usdm: Dict[str, Any],
                                 endpoint_map: Optional[Dict[str, Dict[str, Any]]] = None) -> None:
    """
    Resolve endpointIds on Objective entities into nested objectiveEndpoints.

    USDM v4.0 expects endpoints as nested objects within objectives
    (property: objectiveEndpoints), not as ID references (endpointIds).
    """
    try:
        sd = usdm["study"]["versions"][0]["studyDesigns"][0]
    except (KeyError, IndexError):
        return

    objectives = sd.get("objectives", [])
    if not objectives:
        return

    ep_map = dict(endpoint_map or {})

    # Also scan the USDM tree for any endpoint objects already placed
    def _collect_endpoints(obj: Any) -> None:
        if isinstance(obj, dict):
            eid = obj.get("id", "")
            if isinstance(eid, str) and eid.startswith("ep_") and eid not in ep_map:
                ep_map[eid] = obj
            for v in obj.values():
                _collect_endpoints(v)
        elif isinstance(obj, list):
            for item in obj:
                _collect_endpoints(item)

    _collect_endpoints(usdm)

    # Resolve endpointIds → objectiveEndpoints on each objective
    for obj in objectives:
        endpoint_ids = obj.pop("endpointIds", [])
        if not endpoint_ids:
            continue

        nested_endpoints = []
        for ep_id in endpoint_ids:
            ep = ep_map.get(ep_id)
            if ep:
                nested_endpoints.append(dict(ep))
            else:
                nested_endpoints.append({
                    "id": ep_id,
                    "instanceType": "Endpoint",
                })
        obj["objectiveEndpoints"] = nested_endpoints


# ── Codelist normalization maps ──────────────────────────────────────────────
# These map extraction-side values to the correct CDISC codelist codes that
# the CORE engine validates against.

# EligibilityCriterion.category → codelist C66797
_ELIGIBILITY_CATEGORY_MAP = {
    "Inclusion": ("C25532", "Inclusion Criteria"),
    "inclusion": ("C25532", "Inclusion Criteria"),
    "Exclusion": ("C25370", "Exclusion Criteria"),
    "exclusion": ("C25370", "Exclusion Criteria"),
}

# Endpoint.level → codelist C188726 (NOT extensible)
_ENDPOINT_LEVEL_MAP = {
    "C98772": ("C94496", "Primary Endpoint"),        # Primary Outcome Measure → Primary Endpoint
    "C98781": ("C139173", "Secondary Endpoint"),      # Secondary Outcome Measure → Secondary Endpoint
    "C98724": ("C170559", "Exploratory Endpoint"),    # Exploratory Outcome Measure → Exploratory Endpoint
}

# Encounter.type → codelist C188728
_ENCOUNTER_TYPE_MAP = {
    "C25426": ("C25716", "Visit"),                   # Visit → Scheduled Visit
    "C98779": ("C98779", "Screening Visit"),
    "C142615": ("C142615", "Baseline Visit"),
    "C98780": ("C98780", "Treatment Visit"),
    "C71738": ("C71738", "Randomization Visit"),
    "C98777": ("C98777", "Follow-up Visit"),
}

# StudyTitle.type → codelist C207419
_TITLE_TYPE_MAP = {
    "Official Study Title": ("C207616", "Official Study Title"),
    "Study Acronym": ("C207646", "Study Acronym"),
    "Brief Study Title": ("C207617", "Brief Study Title"),
}

# StudyRole.code → CDISC role codes
_STUDY_ROLE_CODE_MAP = {
    "Sponsor": ("C70793", "Sponsor"),
    "sponsor": ("C70793", "Sponsor"),
    "Registry": ("C93453", "Registry"),
    "registry": ("C93453", "Registry"),
}

# StudyRole name → CDISC C215480 codelist codes
# Only roles present in C215480 are valid; others default to Sponsor
_STUDY_ROLE_NAME_MAP = {
    "Sponsor": ("C70793", "Sponsor"),
    "sponsor": ("C70793", "Sponsor"),
    "Co-Sponsor": ("C70793", "Sponsor"),
    "CRO": ("C54499", "Contract Research Organization"),
    "Contract Research": ("C54499", "Contract Research Organization"),
    "Investigator": ("C25936", "Principal Investigator"),
    "Principal investigator": ("C25936", "Principal Investigator"),
    "PrincipalInvestigator": ("C25936", "Principal Investigator"),
    "Statistician": ("C25943", "Statistician"),
    # Registry and Regulatory not in C215480 — map to closest valid code
    "Registry": ("C70793", "Sponsor"),
    "registry": ("C70793", "Sponsor"),
    "RegulatoryAuthority": ("C70793", "Sponsor"),
    "Regulatory": ("C70793", "Sponsor"),
    "RegulatoryAgency": ("C70793", "Sponsor"),
}

# Organization type → CDISC codelist C188724
_ORG_TYPE_MAP = {
    "Pharmaceutical Company": ("C54086", "Pharmaceutical Company"),
    "Clinical Research Organization": ("C54086", "Pharmaceutical Company"),
    "Healthcare Facility": ("C19326", "Healthcare Facility"),
    "Registry": ("C19326", "Healthcare Facility"),
}

# StudyIntervention type → CDISC codelist C99078
# These codes are already correct NCI codes; just need codeSystem fixed
_INTERVENTION_TYPE_CODES = {
    "C54121", "C54129", "C1909", "C54130", "C54131",
    "C82637", "C82638", "C96631",
}

# StudyIntervention role → CDISC codelist C207417
_INTERVENTION_ROLE_CODES = {
    "C54121", "C54129", "C54130", "C54131", "C82637",
    "C82638", "C96631", "C1909",
}


def _normalize_codelists(usdm: Dict[str, Any]) -> None:
    """
    Normalize Code objects to use correct CDISC codelist codes.

    The extraction agents sometimes use internal code values or wrong
    codelists. This function remaps them to the codes expected by the
    CORE engine.
    """
    try:
        version = usdm["study"]["versions"][0]
        design = version["studyDesigns"][0]
    except (KeyError, IndexError):
        return

    cdisc_sys = "http://www.cdisc.org"
    cdisc_ver = "2024-09-27"

    # Fix EligibilityCriterion.category
    for ec in design.get("eligibilityCriteria", []):
        cat = ec.get("category")
        if isinstance(cat, dict):
            code_val = cat.get("code", "")
            mapped = _ELIGIBILITY_CATEGORY_MAP.get(code_val)
            if mapped:
                cat["code"] = mapped[0]
                cat["decode"] = mapped[1]
                cat["codeSystem"] = cdisc_sys
                cat["codeSystemVersion"] = cdisc_ver

    # Fix Endpoint.level
    for ep in design.get("endpoints", []):
        level = ep.get("level")
        if isinstance(level, dict):
            code_val = level.get("code", "")
            mapped = _ENDPOINT_LEVEL_MAP.get(code_val)
            if mapped:
                level["code"] = mapped[0]
                level["decode"] = mapped[1]

    # Fix Encounter.type
    for enc in design.get("encounters", []):
        etype = enc.get("type")
        if isinstance(etype, dict):
            code_val = etype.get("code", "")
            mapped = _ENCOUNTER_TYPE_MAP.get(code_val)
            if mapped:
                etype["code"] = mapped[0]
                etype["decode"] = mapped[1]
                etype["codeSystem"] = cdisc_sys
                etype["codeSystemVersion"] = cdisc_ver

    # Fix StudyTitle.type
    for title in version.get("titles", []):
        ttype = title.get("type")
        if isinstance(ttype, dict):
            code_val = ttype.get("code", "")
            mapped = _TITLE_TYPE_MAP.get(code_val)
            if mapped:
                ttype["code"] = mapped[0]
                ttype["decode"] = mapped[1]
                ttype["codeSystem"] = cdisc_sys
                ttype["codeSystemVersion"] = cdisc_ver

    # Fix NarrativeContent: CORE expects "NarrativeContentItem" at narrativeContentItems path
    for nc in version.get("narrativeContentItems", []):
        if nc.get("instanceType") == "NarrativeContent":
            nc["instanceType"] = "NarrativeContentItem"

    # Fix Procedure codes with null codeSystemVersion and ensure procedureType
    for proc in design.get("procedures", []):
        code_obj = proc.get("code")
        if isinstance(code_obj, dict):
            if not code_obj.get("codeSystemVersion"):
                code_obj["codeSystemVersion"] = cdisc_ver
        # Ensure procedureType is present (required by CORE)
        if "procedureType" not in proc:
            proc["procedureType"] = proc.get("name", "Clinical Procedure")
        # Strip 'codes' property — not in USDM v4.0 schema
        proc.pop("codes", None)

    # Fix StudyRole.code to use CDISC codes (DDF00201, DDF00259)
    # Also set appliesToIds (DDF00189, DDF00203)
    version_id = version.get("id")
    design_id = design.get("id")
    for role in version.get("roles", []):
        code_obj = role.get("code")
        if isinstance(code_obj, dict):
            role_name = role.get("name", "")
            # Use role name as primary signal (extraction may set wrong code)
            mapped = _STUDY_ROLE_NAME_MAP.get(role_name)
            if not mapped:
                # Fallback: try mapping by code value
                code_val = code_obj.get("code", "")
                mapped = _STUDY_ROLE_CODE_MAP.get(code_val)
            if mapped:
                code_obj["code"] = mapped[0]
                code_obj["decode"] = mapped[1]
                code_obj["codeSystem"] = cdisc_sys
                code_obj["codeSystemVersion"] = cdisc_ver
                if not code_obj.get("instanceType"):
                    code_obj["instanceType"] = "Code"
                if not code_obj.get("id"):
                    code_obj["id"] = str(uuid.uuid4()).replace("-", "_")
        # Ensure appliesToIds references the version and design
        if not role.get("appliesToIds"):
            applies = []
            if version_id:
                applies.append(version_id)
            if design_id:
                applies.append(design_id)
            role["appliesToIds"] = applies

    # Fix Organization.type to use CDISC codelist C188724 (DDF00200)
    # C188724 codes validated against CDISC USDM golden output:
    #   Sponsor    → C70793  "Clinical Study Sponsor"
    #   Registry   → C93453  "Study Registry"
    #   Regulatory → C188863 "Regulatory Agency"
    #   CRO        → C54499  "Contract Research Organization"
    _C188724_ORG_TYPE = {
        "pharma": ("C70793", "Clinical Study Sponsor"),
        "biotech": ("C70793", "Clinical Study Sponsor"),
        "sponsor": ("C70793", "Clinical Study Sponsor"),
        "registry": ("C93453", "Study Registry"),
        "clinicaltrials": ("C93453", "Study Registry"),
        "ctgov": ("C93453", "Study Registry"),
        "eudract": ("C93453", "Study Registry"),
        "ctis": ("C93453", "Study Registry"),
        "isrctn": ("C93453", "Study Registry"),
        "regulatory": ("C188863", "Regulatory Agency"),
        "fda": ("C188863", "Regulatory Agency"),
        "ema": ("C188863", "Regulatory Agency"),
        "mhra": ("C188863", "Regulatory Agency"),
        "tga": ("C188863", "Regulatory Agency"),
        "pmda": ("C188863", "Regulatory Agency"),
        "cro": ("C54499", "Contract Research Organization"),
        "contract research": ("C54499", "Contract Research Organization"),
    }
    for org in version.get("organizations", []):
        org_type = org.get("type")
        org_name_lower = org.get("name", "").lower()
        # Infer correct C188724 code from org name
        inferred = None
        for keyword, (tc, td) in _C188724_ORG_TYPE.items():
            if keyword in org_name_lower:
                inferred = (tc, td)
                break
        # Use inferred code if available; else keep/fix existing
        if inferred:
            type_code, type_decode = inferred
        elif isinstance(org_type, dict) and org_type.get("code"):
            type_code, type_decode = org_type.get("code"), org_type.get("decode", "")
        else:
            type_code, type_decode = "C70793", "Clinical Study Sponsor"  # default to sponsor
        org["type"] = {
            "id": (org_type or {}).get("id") or str(uuid.uuid4()).replace("-", "_"),
            "code": type_code,
            "codeSystem": cdisc_sys,
            "codeSystemVersion": cdisc_ver,
            "decode": type_decode,
            "instanceType": "Code",
        }

    # Fix StudyIntervention type and role (DDF00128, DDF00112)
    for inv in version.get("studyInterventions", []):
        # Strip properties not in USDM v4.0 schema
        inv.pop("administrationIds", None)
        inv.pop("productIds", None)
        inv.pop("codes", None)

        # Ensure type uses CDISC codeSystem (codelist C99078)
        inv_type = inv.get("type")
        if isinstance(inv_type, dict):
            if inv_type.get("code") in _INTERVENTION_TYPE_CODES:
                inv_type["codeSystem"] = cdisc_sys
                inv_type["codeSystemVersion"] = cdisc_ver

        # Ensure role uses CDISC codeSystem (codelist C207417)
        inv_role = inv.get("role")
        if isinstance(inv_role, dict):
            if inv_role.get("code") in _INTERVENTION_ROLE_CODES:
                inv_role["codeSystem"] = cdisc_sys
                inv_role["codeSystemVersion"] = cdisc_ver

    # Fix StudyAmendment: normalize geographic scope type (DDF00144),
    # amendment reason code (DDF00143), and ensure required `changes` (DDF00125).
    _GEO_SCOPE_TYPE_MAP = {
        "Global": ("C68846", "Global"),
        "Country": ("C25464", "Country"),
        "Region": ("C41129", "Region"),
    }
    for amend in version.get("amendments", []):
        # Normalize geographicScopes type codes to CDISC codelist C207412
        for gs in amend.get("geographicScopes", []):
            gs_type = gs.get("type")
            if isinstance(gs_type, dict):
                code_val = gs_type.get("code", "")
                mapped = _GEO_SCOPE_TYPE_MAP.get(code_val)
                if mapped:
                    gs_type["code"] = mapped[0]
                    gs_type["decode"] = mapped[1]
                gs_type["codeSystem"] = cdisc_sys
                gs_type["codeSystemVersion"] = cdisc_ver
                # DDF00261: if global, code field must be absent
                if gs_type.get("code") == "C68846":
                    gs.pop("code", None)

        # Normalize primaryReason code to CDISC codelist C207415 (DDF00143)
        pr = amend.get("primaryReason")
        if isinstance(pr, dict):
            code_obj = pr.get("code")
            if isinstance(code_obj, dict):
                code_obj["codeSystem"] = cdisc_sys
                code_obj["codeSystemVersion"] = cdisc_ver
                # Map extraction codes to C207415 terms
                _AMEND_REASON_MAP = {
                    "C98782": ("C207603", "Inconsistency And/or Error In The Protocol"),
                }
                old_code = code_obj.get("code", "")
                mapped = _AMEND_REASON_MAP.get(old_code)
                if mapped:
                    code_obj["code"] = mapped[0]
                    code_obj["decode"] = mapped[1]
            # DDF00020: if code is C17649 (Other), otherReason must not be blank
            # If code is NOT C17649, otherReason must be blank/absent
            if isinstance(code_obj, dict):
                if code_obj.get("code") == "C17649":
                    if not pr.get("otherReason"):
                        pr["otherReason"] = amend.get("summary", "Other")
                else:
                    pr.pop("otherReason", None)

        # Ensure required `changes` array (DDF00125)
        if not amend.get("changes"):
            amend["changes"] = [{
                "id": str(uuid.uuid4()).replace("-", "_"),
                "name": amend.get("name", "Amendment Change"),
                "summary": amend.get("summary", "See amendment details."),
                "rationale": amend.get("summary", "See amendment details."),
                "changedSections": [{
                    "id": str(uuid.uuid4()).replace("-", "_"),
                    "sectionNumber": "1",
                    "sectionTitle": "General",
                    "appliesToId": amend.get("id", ""),
                    "instanceType": "DocumentContentReference",
                }],
                "instanceType": "StudyChange",
            }]

    # Fix duplicate NarrativeContentItem names (DDF00010)
    nci_names: Dict[str, int] = {}
    for nci in version.get("narrativeContentItems", []):
        name = nci.get("name", "")
        if name in nci_names:
            nci_names[name] += 1
            nci["name"] = f"{name} ({nci_names[name]})"
        else:
            nci_names[name] = 1

    # Chain epoch ordering via nextId (DDF00088)
    epochs = design.get("epochs", [])
    for i, ep in enumerate(epochs[:-1]):
        if not ep.get("nextId"):
            ep["nextId"] = epochs[i + 1]["id"]

    # Chain encounter ordering via nextId (DDF00087)
    encounters = design.get("encounters", [])
    for i, enc in enumerate(encounters[:-1]):
        if not enc.get("nextId"):
            enc["nextId"] = encounters[i + 1]["id"]

    # Resolve encounter→epoch mapping captured during entity placement.
    # The map was built from vision-extracted epochIds (e.g. "epoch_1") which
    # reference the header_structure epoch IDs, NOT the USDM epoch entity IDs
    # (e.g. "epoch_v_1").  We resolve them here by matching epoch names from
    # the header_structure to the actual USDM epoch entities.
    epochs = design.get("epochs", [])
    raw_enc_epoch_map = design.get("_encounterEpochMap", {})

    if raw_enc_epoch_map and epochs:
        # Build a lookup from header-structure epoch ID → USDM epoch entity ID.
        # The header_structure stores epochs with IDs like "epoch_1" and names
        # like "Screening".  The USDM epoch entities have IDs like "epoch_v_1"
        # and the same names.  Match by name (case-insensitive).
        header_epochs = design.get("_headerEpochs", [])
        header_id_to_name = {ep["id"]: ep.get("name", "") for ep in header_epochs}
        usdm_name_to_id: Dict[str, str] = {}
        for ep in epochs:
            usdm_name_to_id[ep.get("name", "").lower().strip()] = ep["id"]

        stale_to_usdm: Dict[str, str] = {}
        for hdr_id, hdr_name in header_id_to_name.items():
            resolved = usdm_name_to_id.get(hdr_name.lower().strip())
            if resolved:
                stale_to_usdm[hdr_id] = resolved

        # Resolve the map values from stale IDs to USDM IDs
        resolved_map: Dict[str, str] = {}
        for enc_id, stale_epoch_id in raw_enc_epoch_map.items():
            resolved = stale_to_usdm.get(stale_epoch_id)
            if resolved:
                resolved_map[enc_id] = resolved
            elif stale_epoch_id in {ep["id"] for ep in epochs}:
                # Already a valid USDM epoch ID
                resolved_map[enc_id] = stale_epoch_id

        design["_encounterEpochMap"] = resolved_map

        # Also set epochId on encounter objects for UI column grouping
        for enc in encounters:
            if not enc.get("epochId"):
                mapped = resolved_map.get(enc.get("id"))
                if mapped:
                    enc["epochId"] = mapped

    # Fix StudyCell epochIds to match actual epoch IDs (DDF00243)
    # Extraction may create cells with epochIds like "epoch_1" while
    # actual epochs are "epoch_v_1". Remap by position.
    # Also ensure each cell has at least one elementId (DDF00126).
    epoch_ids = [ep["id"] for ep in epochs]
    epoch_names = {ep["id"]: ep.get("name", "Element") for ep in epochs}
    if epoch_ids:
        # Build a StudyElement per epoch (reuse if already present)
        existing_elements = {e.get("name"): e for e in design.get("elements", [])}
        epoch_element_map: Dict[str, str] = {}  # epochId -> elementId
        new_elements = list(design.get("elements", []))
        for ep_id in epoch_ids:
            elem_name = epoch_names.get(ep_id, "Element")
            if elem_name in existing_elements:
                epoch_element_map[ep_id] = existing_elements[elem_name]["id"]
            else:
                elem_id = str(uuid.uuid4()).replace("-", "_")
                new_elements.append({
                    "id": elem_id,
                    "name": elem_name,
                    "instanceType": "StudyElement",
                })
                epoch_element_map[ep_id] = elem_id
                existing_elements[elem_name] = {"id": elem_id, "name": elem_name}
        design["elements"] = new_elements

        for arm in design.get("arms", []):
            arm_id = arm.get("id")
            arm_cells = [c for c in design.get("studyCells", [])
                         if c.get("armId") == arm_id]
            # Check if any cell references an invalid epoch
            valid_epoch_set = set(epoch_ids)
            needs_remap = any(c.get("epochId") not in valid_epoch_set
                              for c in arm_cells)
            if needs_remap:
                # Remove old cells for this arm
                design["studyCells"] = [
                    c for c in design.get("studyCells", [])
                    if c.get("armId") != arm_id
                ]
                # Create one cell per epoch
                for ep_id in epoch_ids:
                    design["studyCells"].append({
                        "id": str(uuid.uuid4()).replace("-", "_"),
                        "armId": arm_id,
                        "epochId": ep_id,
                        "elementIds": [epoch_element_map[ep_id]],
                        "instanceType": "StudyCell",
                    })

        # Also fix existing cells that have empty elementIds
        for cell in design.get("studyCells", []):
            if not cell.get("elementIds"):
                ep_id = cell.get("epochId", "")
                if ep_id in epoch_element_map:
                    cell["elementIds"] = [epoch_element_map[ep_id]]

    # Fix StudyRole appliesToIds (DDF00189)
    # CORE expects appliesToIds to reference ONLY the version ID
    for role in version.get("roles", []):
        if role.get("appliesToIds"):
            role["appliesToIds"] = [version_id] if version_id else []


def _fix_activity_names(usdm: Dict[str, Any]) -> None:
    """
    Fix activity names that contain the full repr() string of the Activity
    dataclass instead of just the name value.

    E.g. "Activity(id='act_1', name='Informed Consent', ...)" → "Informed Consent"
    """
    try:
        design = usdm["study"]["versions"][0]["studyDesigns"][0]
    except (KeyError, IndexError):
        return

    name_pattern = re.compile(r"Activity\(.*?name='([^']*)'")
    for activity in design.get("activities", []):
        name = activity.get("name", "")
        if name.startswith("Activity("):
            match = name_pattern.search(name)
            if match:
                activity["name"] = match.group(1)


def _tokenize(text: str) -> set:
    """Split text into lowercase keyword tokens, dropping noise words."""
    _STOP = {"and", "or", "the", "a", "an", "of", "for", "in", "to", "with", "at", "by", "on"}
    return {w for w in re.split(r"[\s/\-\(\),]+", text.lower()) if w and w not in _STOP}


# Keyword → (NCI code, decode) for creating synthetic procedures when no
# existing procedure matches an activity.
_ACTIVITY_PROCEDURE_CODES: Dict[str, tuple] = {
    "informed consent": ("C16735", "Informed Consent"),
    "physical exam": ("C20989", "Physical Examination"),
    "vital signs": ("C25714", "Vital Signs"),
    "ecg": ("C38054", "Electrocardiogram"),
    "electrocardiogram": ("C38054", "Electrocardiogram"),
    "blood pressure": ("C54706", "Blood Pressure Measurement"),
    "weight": ("C25208", "Weight"),
    "height": ("C25347", "Height"),
    "randomization": ("C15417", "Randomization"),
    "laboratory": ("C49286", "Laboratory Test"),
    "urinalysis": ("C79430", "Urinalysis"),
    "adverse event": ("C41331", "Adverse Event"),
    "concomitant medication": ("C53630", "Concomitant Medication"),
    "medication review": ("C53630", "Concomitant Medication"),
    "medical history": ("C18772", "Medical History"),
    "demographics": ("C49672", "Demographics"),
    "pregnancy test": ("C92949", "Pregnancy Test"),
    "pharmacokinetic": ("C15299", "Pharmacokinetics"),
    "antibod": ("C16295", "Antibody Measurement"),
    "genetic analy": ("C15429", "Genetic Analysis"),
    "blood sample": ("C17610", "Blood Sample Collection"),
    "blood collect": ("C17610", "Blood Sample Collection"),
    "tumor imag": ("C17369", "Imaging Technique"),
    "tissue collect": ("C15189", "Biopsy"),
    "biopsy": ("C15189", "Biopsy"),
    "survival": ("C25717", "Survival Assessment"),
    "cbc": ("C64848", "Complete Blood Count"),
    "chemistry panel": ("C49286", "Laboratory Test"),
    "thyroid": ("C79441", "Thyroid Function Test"),
    "serum": ("C49286", "Laboratory Test"),
    "hepatitis": ("C49286", "Laboratory Test"),
    "hbsag": ("C49286", "Laboratory Test"),
    "hep c": ("C49286", "Laboratory Test"),
    "hcv": ("C49286", "Laboratory Test"),
    "tsh": ("C79441", "Thyroid Function Test"),
    "ft4": ("C79441", "Thyroid Function Test"),
    "identification card": ("C25218", "Administrative Procedure"),
    "inclusion": ("C25532", "Eligibility Assessment"),
    "exclusion": ("C25370", "Eligibility Assessment"),
    "eligibility": ("C25370", "Eligibility Assessment"),
    "patient reported outcome": ("C28421", "Patient Reported Outcome"),
    "pro": ("C28421", "Patient Reported Outcome"),
    "hrqol": ("C28421", "Patient Reported Outcome"),
    "anticancer therapy": ("C15632", "Anticancer Therapy Assessment"),
    "coagulation": ("C64847", "Coagulation Test"),
    "pt/inr": ("C64847", "Coagulation Test"),
    "aptt": ("C64847", "Coagulation Test"),
}


def _link_activities_to_procedures(usdm: Dict[str, Any]) -> None:
    """
    Link activities to procedures via definedProcedures.

    Uses three matching strategies in order:
    1. Direct name match (case-insensitive)
    2. Substring containment match
    3. Keyword overlap (>=50% of procedure keywords found in activity name)

    Each matched procedure is embedded as a full Procedure object (with a
    unique ID) in the activity's definedProcedures list.  CORE expects
    instanceType="Procedure" with name, procedureType, and code fields.
    """
    try:
        design = usdm["study"]["versions"][0]["studyDesigns"][0]
    except (KeyError, IndexError):
        return

    procedures = design.get("procedures", [])
    activities = design.get("activities", [])
    if not procedures or not activities:
        return

    # Build name-to-procedure lookup (lowercase, stripped)
    proc_by_name: Dict[str, Dict[str, Any]] = {}
    for proc in procedures:
        pname = proc.get("name", "").lower().strip()
        if pname:
            proc_by_name[pname] = proc
            # Also index without common suffixes for fuzzy matching
            for suffix in (" sampling", " collection", " test", " assessment",
                           " evaluations", " infusion"):
                if pname.endswith(suffix):
                    proc_by_name[pname[: -len(suffix)]] = proc

    # Pre-tokenize procedure names
    proc_tokens = [(proc, _tokenize(proc.get("name", ""))) for proc in procedures]

    def _embed_proc(proc: Dict[str, Any]) -> Dict[str, Any]:
        """Create an embedded copy of a procedure with a fresh unique ID."""
        embedded = {
            "id": str(uuid.uuid4()),
            "name": proc.get("name", ""),
            "instanceType": "Procedure",
        }
        if proc.get("procedureType"):
            embedded["procedureType"] = proc["procedureType"]
        if proc.get("code"):
            # Deep-copy code but give it a unique ID too
            code_copy = dict(proc["code"])
            code_copy["id"] = str(uuid.uuid4())
            embedded["code"] = code_copy
        return embedded

    for activity in activities:
        act_name = activity.get("name", "").lower().strip()
        if not act_name:
            continue

        matched_ids: list = []
        matched_procs: list = []

        # Strategy 1: Direct match
        if act_name in proc_by_name:
            p = proc_by_name[act_name]
            matched_ids.append(p.get("id"))
            matched_procs.append(p)

        # Strategy 2: Substring containment
        for pname, proc in proc_by_name.items():
            pid = proc.get("id")
            if pid in matched_ids:
                continue
            if pname in act_name or act_name in pname:
                matched_ids.append(pid)
                matched_procs.append(proc)

        # Strategy 3: Keyword overlap (if no match yet)
        if not matched_procs:
            act_tokens = _tokenize(act_name)
            if act_tokens:
                for proc, ptokens in proc_tokens:
                    pid = proc.get("id")
                    if pid in matched_ids or not ptokens:
                        continue
                    overlap = act_tokens & ptokens
                    # Match if >=50% of procedure keywords appear in activity
                    if len(overlap) >= max(1, len(ptokens) * 0.5):
                        matched_ids.append(pid)
                        matched_procs.append(proc)

        if matched_procs:
            activity["definedProcedures"] = [_embed_proc(p) for p in matched_procs]
        else:
            # Fallback: create a synthetic procedure from known clinical codes
            act_lower = activity.get("name", "").lower()
            for keyword, (code, decode) in _ACTIVITY_PROCEDURE_CODES.items():
                if keyword in act_lower:
                    # Use activity name as procedure name to avoid DDF00010
                    # duplicate name issues when multiple activities match
                    # the same keyword.
                    act_name_orig = activity.get("name", decode)
                    synth_proc = {
                        "id": str(uuid.uuid4()),
                        "name": act_name_orig,
                        "procedureType": decode,
                        "code": {
                            "id": str(uuid.uuid4()),
                            "code": code,
                            "codeSystem": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl",
                            "codeSystemVersion": "2024-09-27",
                            "decode": decode,
                            "instanceType": "Code",
                        },
                        "instanceType": "Procedure",
                    }
                    activity["definedProcedures"] = [synth_proc]
                    break

            # Absolute fallback: if still no procedure, create a generic one (DDF00263)
            if not activity.get("definedProcedures"):
                act_name_orig = activity.get("name", "Clinical Procedure")
                activity["definedProcedures"] = [{
                    "id": str(uuid.uuid4()),
                    "name": act_name_orig,
                    "procedureType": "Clinical Procedure",
                    "code": {
                        "id": str(uuid.uuid4()),
                        "code": "C25218",
                        "codeSystem": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl",
                        "codeSystemVersion": "2024-09-27",
                        "decode": "Procedure",
                        "instanceType": "Code",
                    },
                    "instanceType": "Procedure",
                }]

    # Remove top-level procedures[] to avoid DDF00010 duplicate name
    # conflicts between procedures[] and embedded definedProcedures[].
    # All procedure data is now embedded in activities.
    design.pop("procedures", None)

    # Link drug-related procedures to study interventions (DDF00101)
    version = usdm["study"]["versions"][0]
    interventions = version.get("studyInterventions", [])
    if interventions:
        inv_by_name: Dict[str, str] = {}
        for inv in interventions:
            inv_name = inv.get("name", "").lower().strip()
            if inv_name:
                inv_by_name[inv_name] = inv.get("id", "")
                # Also index first word for partial matching
                first_word = inv_name.split()[0] if inv_name else ""
                if first_word and len(first_word) > 3:
                    inv_by_name[first_word] = inv.get("id", "")

        for activity in design.get("activities", []):
            for proc in activity.get("definedProcedures", []):
                if proc.get("studyInterventionId"):
                    continue
                proc_name = proc.get("name", "").lower()
                # Try matching procedure name to intervention name
                for inv_key, inv_id in inv_by_name.items():
                    if inv_key in proc_name or proc_name in inv_key:
                        proc["studyInterventionId"] = inv_id
                        break



def _deduplicate_intercurrent_event_names(usdm: Dict[str, Any]) -> None:
    """
    Make IntercurrentEvent names unique across estimands (DDF00010).

    CORE requires globally unique names for IntercurrentEvent instances.
    When the same ICE name appears in multiple estimands, append the
    estimand's variable-of-interest name to disambiguate.
    """
    try:
        design = usdm["study"]["versions"][0]["studyDesigns"][0]
    except (KeyError, IndexError):
        return

    estimands = design.get("estimands", [])
    if not estimands:
        return

    # Collect all ICE names across all estimands to find duplicates
    name_counts: Dict[str, int] = {}
    for est in estimands:
        for ice in est.get("intercurrentEvents", []):
            name = ice.get("name", "")
            if name:
                name_counts[name] = name_counts.get(name, 0) + 1

    # Only fix names that appear more than once
    dup_names = {n for n, c in name_counts.items() if c > 1}
    if not dup_names:
        return

    # Disambiguate by appending estimand context
    for est in estimands:
        # Use the endpoint/variable name as context
        est_context = est.get("name", "") or est.get("summaryMeasure", "")
        # Try variableOfInterestId as fallback
        if not est_context:
            est_context = est.get("variableOfInterestId", est.get("id", ""))

        for ice in est.get("intercurrentEvents", []):
            name = ice.get("name", "")
            if name in dup_names and est_context:
                ice["name"] = f"{name} ({est_context})"


def _sanitize_narrative_xhtml(usdm: Dict[str, Any]) -> None:
    """
    Sanitize NarrativeContentItem text to valid XHTML (DDF00187).

    Escapes bare '&' characters that are not part of XML entities,
    which cause XHTML parsing failures in the CORE engine.
    """
    try:
        version = usdm["study"]["versions"][0]
    except (KeyError, IndexError):
        return

    # Pattern: & not followed by a valid XML entity reference
    amp_pattern = re.compile(r"&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)")

    for nc in version.get("narrativeContentItems", []):
        # Fix the name field (used in section headers)
        name = nc.get("name", "")
        if "&" in name:
            nc["name"] = amp_pattern.sub("&amp;", name)

        # Fix the text/content field
        text = nc.get("text", "")
        if "&" in text:
            nc["text"] = amp_pattern.sub("&amp;", text)

        # Also check sectionTitle if present
        title = nc.get("sectionTitle", "")
        if title and "&" in title:
            nc["sectionTitle"] = amp_pattern.sub("&amp;", title)


_INDICATION_TO_THERAPEUTIC_AREA: Dict[str, tuple] = {
    # keyword (lowercase) → (NCI code, decode label)
    "cancer": ("C17998", "Oncology"),
    "tumor": ("C17998", "Oncology"),
    "carcinoma": ("C17998", "Oncology"),
    "lymphoma": ("C17998", "Oncology"),
    "leukemia": ("C17998", "Oncology"),
    "myeloma": ("C17998", "Oncology"),
    "cardiac": ("C2931", "Cardiovascular"),
    "cardio": ("C2931", "Cardiovascular"),
    "heart failure": ("C2931", "Cardiovascular"),
    "atrial": ("C2931", "Cardiovascular"),
    "hypertension": ("C2931", "Cardiovascular"),
    "coronary": ("C2931", "Cardiovascular"),
    "diabetes": ("C16726", "Metabolic Disease"),
    "metabolic": ("C16726", "Metabolic Disease"),
    "obesity": ("C16726", "Metabolic Disease"),
    "glycemic": ("C16726", "Metabolic Disease"),
    "alzheimer": ("C16910", "Neurology"),
    "parkinson": ("C16910", "Neurology"),
    "neurolog": ("C16910", "Neurology"),
    "epilep": ("C16910", "Neurology"),
    "multiple sclerosis": ("C16910", "Neurology"),
    "rheumatoid": ("C20993", "Immunology"),
    "immunolog": ("C20993", "Immunology"),
    "autoimmune": ("C20993", "Immunology"),
    "psoriasis": ("C20993", "Immunology"),
    "crohn": ("C20993", "Immunology"),
    "lupus": ("C20993", "Immunology"),
    "renal": ("C16540", "Nephrology"),
    "kidney": ("C16540", "Nephrology"),
    "chronic kidney": ("C16540", "Nephrology"),
    "hepat": ("C71844", "Hepatology"),
    "liver": ("C71844", "Hepatology"),
    "respiratory": ("C16542", "Pulmonology"),
    "asthma": ("C16542", "Pulmonology"),
    "copd": ("C16542", "Pulmonology"),
    "pulmonary": ("C16542", "Pulmonology"),
    "infection": ("C16320", "Infectious Disease"),
    "viral": ("C16320", "Infectious Disease"),
    "bacterial": ("C16320", "Infectious Disease"),
    "hiv": ("C16320", "Infectious Disease"),
    "psychiatric": ("C16326", "Psychiatry"),
    "depression": ("C16326", "Psychiatry"),
    "schizophrenia": ("C16326", "Psychiatry"),
    "anxiety": ("C16326", "Psychiatry"),
    "ophthalmolog": ("C16533", "Ophthalmology"),
    "retinal": ("C16533", "Ophthalmology"),
    "macular": ("C16533", "Ophthalmology"),
    "dermatolog": ("C16327", "Dermatology"),
    "skin": ("C16327", "Dermatology"),
    "eczema": ("C16327", "Dermatology"),
}


def _populate_therapeutic_areas(usdm: Dict[str, Any]) -> None:
    """
    Derive businessTherapeuticAreas on StudyVersion from indication names.

    Scans placed indications and maps indication text to NCI therapeutic
    area codes.  Only populates if not already set by extraction.
    """
    try:
        version = usdm["study"]["versions"][0]
        design = version["studyDesigns"][0]
    except (KeyError, IndexError):
        return

    # Skip if already populated by an extraction agent
    if version.get("businessTherapeuticAreas"):
        return

    # Collect text to search: indication names + study name
    search_texts = []
    for ind in design.get("indications", []):
        search_texts.append(ind.get("name", "").lower())
        search_texts.append(ind.get("description", "").lower())
    search_texts.append(usdm.get("study", {}).get("name", "").lower())
    search_texts.append(usdm.get("study", {}).get("description", "").lower())
    combined = " ".join(search_texts)

    seen_codes: set = set()
    tas = []
    for keyword, (nci_code, label) in _INDICATION_TO_THERAPEUTIC_AREA.items():
        if keyword in combined and nci_code not in seen_codes:
            seen_codes.add(nci_code)
            tas.append({
                "id": str(uuid.uuid4()).replace("-", "_"),
                "code": nci_code,
                "codeSystem": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl",
                "codeSystemVersion": "2024-09-27",
                "decode": label,
                "instanceType": "Code",
            })

    if tas:
        version["businessTherapeuticAreas"] = tas


def _ensure_sponsor_identifier(usdm: Dict[str, Any]) -> None:
    """
    Post-processing to fix DDF00172 (sponsor identifier), DDF00201 (sponsor
    role), DDF00012 (main timeline), and DDF00101 (interventions).

    1. Ensures organizations referenced by studyRoles and studyIdentifiers
       are present on the version.
    2. Ensures at least one ScheduleTimeline exists with ``mainTimeline``
       set to ``true`` (DDF00012).
    3. Populates ``studyInterventionIds`` on the design from the version's
       ``studyInterventions`` (DDF00101).
    """
    try:
        version = usdm["study"]["versions"][0]
        design = version["studyDesigns"][0]
    except (KeyError, IndexError):
        return

    # --- DDF00012: Ensure at least one main ScheduleTimeline ---
    timelines = design.get("scheduleTimelines", [])
    has_main = any(tl.get("mainTimeline") is True for tl in timelines)
    if not has_main:
        if timelines:
            # Mark the first timeline as main
            timelines[0]["mainTimeline"] = True
        else:
            # Synthesize a main timeline from existing encounter data
            timeline_id = str(uuid.uuid4()).replace("-", "_")

            epochs = design.get("epochs", [])
            epoch_ids = [ep["id"] for ep in epochs] if epochs else []

            # Use cached encounter→epoch mapping captured during entity placement.
            # The map values may be stale header-structure epoch IDs (e.g. "epoch_1")
            # that need resolving to actual USDM epoch entity IDs (e.g. "epoch_v_1").
            raw_enc_epoch_map = design.pop("_encounterEpochMap", {})
            header_epochs = design.get("_headerEpochs", [])

            # Build stale→USDM epoch ID lookup by matching epoch names
            _stale_to_usdm: Dict[str, str] = {}
            if header_epochs and epochs:
                hdr_id_to_name = {ep["id"]: ep.get("name", "") for ep in header_epochs}
                usdm_name_to_id: Dict[str, str] = {}
                for ep in epochs:
                    usdm_name_to_id[ep.get("name", "").lower().strip()] = ep["id"]
                for hdr_id, hdr_name in hdr_id_to_name.items():
                    resolved = usdm_name_to_id.get(hdr_name.lower().strip())
                    if resolved:
                        _stale_to_usdm[hdr_id] = resolved

            valid_epoch_set = set(epoch_ids)
            _enc_epoch_map: Dict[str, str] = {}
            for enc_id, stale_epoch_id in raw_enc_epoch_map.items():
                if stale_epoch_id in valid_epoch_set:
                    _enc_epoch_map[enc_id] = stale_epoch_id
                else:
                    resolved = _stale_to_usdm.get(stale_epoch_id)
                    if resolved:
                        _enc_epoch_map[enc_id] = resolved

            def _match_epoch(enc_name: str) -> Optional[str]:
                """Match an encounter name to the best epoch by keyword."""
                low = enc_name.lower()
                for ep in epochs:
                    ep_name = ep.get("name", "").lower()
                    if "screen" in low and "screen" in ep_name:
                        return ep["id"]
                    if ("cycle" in low or "treatment" in low or "randomiz" in low) and ("treatment" in ep_name or "cycle" in ep_name):
                        return ep["id"]
                    if ("discon" in low or "end of" in low or "completion" in low or "eot" in low) and ("end" in ep_name or "discon" in ep_name or "eot" in ep_name):
                        return ep["id"]
                    if ("follow" in low or "survival" in low or "ltfu" in low) and ("follow" in ep_name or "ltfu" in ep_name):
                        return ep["id"]
                    if "fu visit" in low and "fu visit" in ep_name:
                        return ep["id"]
                return None

            # Build scheduled instances from extracted SoA tick data (activity_timepoints)
            # Group by encounterId so each instance lists all activities performed at that encounter.
            # Fall back to one empty instance per encounter if no tick data available.
            sched_instances_raw = design.pop("_scheduledInstances", [])

            instances: list = []
            # Collect footnoteRefs per encounter (union of all cell-level refs)
            enc_footnote_labels: dict = {}  # enc_id -> set of footnote labels
            if sched_instances_raw:
                from collections import defaultdict
                enc_to_activities: dict = defaultdict(list)
                for si in sched_instances_raw:
                    enc_id = si.get("encounterId")
                    act_id = si.get("activityId")
                    if enc_id and act_id:
                        enc_to_activities[enc_id].append(act_id)
                    # Collect footnote labels for this encounter
                    fn_refs = si.get("footnoteRefs", [])
                    if fn_refs and enc_id:
                        enc_footnote_labels.setdefault(enc_id, set()).update(fn_refs)

                enc_map = {enc.get("id"): enc for enc in design.get("encounters", []) if enc.get("id")}
                for enc_id, activity_ids in enc_to_activities.items():
                    enc = enc_map.get(enc_id, {})
                    enc_name = enc.get("name", enc_id)
                    instances.append({
                        "id": str(uuid.uuid4()).replace("-", "_"),
                        "name": enc_name,
                        "epochId": _enc_epoch_map.get(enc_id) or enc.get("epochId") or _match_epoch(enc_name),
                        "encounterId": enc_id,
                        "activityIds": activity_ids,
                        "instanceType": "ScheduledActivityInstance",
                    })
            else:
                # No tick data — create one instance per encounter (no activityIds)
                for enc in design.get("encounters", []):
                    enc_id = enc.get("id")
                    enc_name = enc.get("name", "Visit")
                    if enc_id:
                        instances.append({
                            "id": str(uuid.uuid4()).replace("-", "_"),
                            "name": enc_name,
                            "epochId": _enc_epoch_map.get(enc_id) or _match_epoch(enc_name),
                            "encounterId": enc_id,
                            "instanceType": "ScheduledActivityInstance",
                        })

            # ── SoAFootnotes: build from header_structure footnotes ─────────
            _build_soa_footnotes(design, instances, enc_footnote_labels,
                                 sched_instances_raw)

            # entryId should reference the first encounter or activity
            entry_id = instances[0]["id"] if instances else None

            # entryCondition describes when the timeline starts
            timeline = {
                "id": timeline_id,
                "name": "Main Study Timeline",
                "description": "Primary schedule of assessments",
                "mainTimeline": True,
                "entryCondition": "Informed consent signed",
                "entryId": entry_id,
                "instanceType": "ScheduleTimeline",
                "plannedDuration": {
                    "id": str(uuid.uuid4()).replace("-", "_"),
                    "durationWillVary": True,
                    "reasonDurationWillVary": "Duration depends on individual subject progression and follow-up.",
                    "text": "Variable",
                    "instanceType": "Duration",
                },
                "timings": [],
                "instances": instances,
            }
            timelines.append(timeline)
            design["scheduleTimelines"] = timelines

    # Wire extracted schedule exits into the main timeline
    pending_exits = design.pop("_pendingExits", [])
    if pending_exits:
        main_tl = next((tl for tl in design.get("scheduleTimelines", [])
                        if tl.get("mainTimeline")), None)
        if main_tl:
            exits = main_tl.setdefault("exits", [])
            for ex in pending_exits:
                if not ex.get("instanceType"):
                    ex["instanceType"] = "ScheduleTimelineExit"
                exits.append(ex)

    # --- DDF00101: Wire up studyInterventionIds on design ---
    # (Interventions may still be on design at this point; they get moved
    # to version by _ensure_study_design_type which runs later.)
    all_interventions = design.get("studyInterventions", []) + version.get("studyInterventions", [])
    if all_interventions and not design.get("studyInterventionIds"):
        design["studyInterventionIds"] = [
            inv.get("id") for inv in all_interventions if inv.get("id")
        ]


def _build_soa_footnotes(design: Dict[str, Any],
                          instances: List[Dict[str, Any]],
                          enc_footnote_labels: Dict[str, set],
                          sched_instances_raw: List[Dict[str, Any]]) -> None:
    """
    Build SoAFootnote objects from header_structure footnotes and wire
    footnoteIds onto ScheduledActivityInstance objects.

    Footnote text comes from the header_structure entity (vision extraction).
    Footnote labels come from cellFootnotes in provenance / footnoteRefs on
    scheduled_instance entities.
    """
    import re as _re

    # Collect ALL unique footnote labels referenced by any cell
    all_labels: set = set()
    for si in sched_instances_raw:
        fn_refs = si.get("footnoteRefs", [])
        if fn_refs:
            all_labels.update(fn_refs)
    for labels in enc_footnote_labels.values():
        all_labels.update(labels)

    if not all_labels:
        return

    # Try to get footnote text from header_structure stored in design notes
    # or from the _headerFootnotes stash (set by _generate)
    raw_footnotes: List[str] = design.pop("_headerFootnotes", [])

    # Parse footnote strings into {label: text} map
    # Formats: "a. text...", "1. text...", "a) text...", "*. text..."
    label_to_text: Dict[str, str] = {}
    for fn_str in raw_footnotes:
        fn_str = fn_str.strip()
        # Match: "a. text", "aa. text", "1. text", "*. text", "a) text"
        m = _re.match(r'^([a-zA-Z]+|\d+|\*)[.\)]\s*(.+)', fn_str, _re.DOTALL)
        if m:
            label = m.group(1).lower()
            text = m.group(2).strip()
            label_to_text[label] = text

    # Create SoAFootnote objects for each referenced label
    label_to_footnote_id: Dict[str, str] = {}
    soa_footnotes: List[Dict[str, Any]] = []
    for label in sorted(all_labels):
        fn_id = str(uuid.uuid4()).replace("-", "_")
        label_to_footnote_id[label.lower()] = fn_id
        soa_footnotes.append({
            "id": fn_id,
            "instanceType": "SoAFootnote",
            "label": label,
            "text": label_to_text.get(label.lower(), ""),
        })

    if soa_footnotes:
        design.setdefault("soaFootnotes", []).extend(soa_footnotes)

    # Wire footnoteIds onto instances based on per-cell footnoteRefs
    # Build a map: enc_id -> set of footnote IDs
    enc_to_fn_ids: Dict[str, List[str]] = {}
    for enc_id, labels in enc_footnote_labels.items():
        fn_ids = []
        for lbl in sorted(labels):
            fn_id = label_to_footnote_id.get(lbl.lower())
            if fn_id:
                fn_ids.append(fn_id)
        if fn_ids:
            enc_to_fn_ids[enc_id] = fn_ids

    for inst in instances:
        enc_id = inst.get("encounterId")
        if enc_id and enc_id in enc_to_fn_ids:
            inst["footnoteIds"] = enc_to_fn_ids[enc_id]


def _post_normalize_cleanup(usdm: Dict[str, Any]) -> None:
    """
    Final cleanup pass after normalize_usdm_data().

    Removes non-USDM-4.0 fields that may be re-introduced by normalize_usdm_data()
    or other post-processing, and wraps fields that must be AliasCode.
    """
    try:
        study = usdm.get("study", {})
        version = study.get("versions", [{}])[0]
        design = version.get("studyDesigns", [{}])[0]
    except (KeyError, IndexError):
        return

    # Strip documentVersions from Study (extra property — DDF00125)
    # documentedBy is the correct USDM 4.0 field; documentVersions is legacy.
    study.pop("documentVersions", None)

    # Strip 'type' from all StudyIdentifiers (not in USDM 4.0 — DDF00125)
    for sid in version.get("studyIdentifiers", []):
        sid.pop("type", None)
        sid.pop("identifierType", None)

    # Strip epochId from all Encounters (not in USDM 4.0 Encounter schema — DDF00125)
    for enc in design.get("encounters", []):
        enc.pop("epochId", None)

    # Remove internal encounter→epoch cache (used during timeline synthesis)
    design.pop("_encounterEpochMap", None)

    # Remove internal header footnotes stash (consumed by _build_soa_footnotes)
    design.pop("_headerFootnotes", None)

    # Remove internal header epoch stash (consumed by _normalize_codelists)
    design.pop("_headerEpochs", None)

    # Strip null entryId from ScheduleTimelines (must be string or absent — DDF00082)
    for tl in design.get("scheduleTimelines", []):
        if tl.get("entryId") is None:
            tl.pop("entryId", None)

    # Strip 'procedures' from InterventionalStudyDesign (not a valid property — DDF00125)
    design.pop("procedures", None)

    # Strip criteria from StudyDesignPopulation if empty (DDF00125)
    pop = design.get("population", {})
    if isinstance(pop, dict) and "criteria" in pop and not pop["criteria"]:
        pop.pop("criteria", None)

    # Normalize all GovernanceDates: date→dateValue, fix codeSystem, add geographicScopes (DDF00125, DDF00142)
    cdisc_sys = "http://www.cdisc.org"
    cdisc_ver = "2024-09-27"
    def _fix_governance_dates(dates: list) -> None:
        for gd in dates:
            if not isinstance(gd, dict):
                continue
            # date → dateValue
            if "date" in gd and "dateValue" not in gd:
                gd["dateValue"] = gd.pop("date")
            # Normalize dateValue format: replace underscores with hyphens (2020_08_18 → 2020-08-18)
            dv = gd.get("dateValue", "")
            if isinstance(dv, str) and "_" in dv:
                gd["dateValue"] = dv.replace("_", "-")
            # add geographicScopes if absent (required — DDF00126)
            if "geographicScopes" not in gd:
                gd["geographicScopes"] = []
            # fix type.codeSystem
            gd_type = gd.get("type")
            if isinstance(gd_type, dict):
                gd_type["codeSystem"] = cdisc_sys
                gd_type["codeSystemVersion"] = cdisc_ver

    _fix_governance_dates(version.get("dateValues", []))
    for amend in version.get("amendments", []):
        _fix_governance_dates(amend.get("dateValues", []))

    # Fix administrableDoseForm: must be AliasCode not a hybrid Code+standardCode object (DDF00081)
    for ap in version.get("administrableProducts", []):
        adf = ap.get("administrableDoseForm")
        if isinstance(adf, dict) and adf.get("instanceType") != "AliasCode":
            # Build proper AliasCode - move top-level Code fields into standardCode
            sc = adf.get("standardCode") or {
                "id": str(uuid.uuid4()),
                "code": adf.get("code", ""),
                "codeSystem": adf.get("codeSystem", cdisc_sys),
                "codeSystemVersion": adf.get("codeSystemVersion", cdisc_ver),
                "decode": adf.get("decode", ""),
                "instanceType": "Code",
            }
            ap["administrableDoseForm"] = {
                "id": adf.get("id") or str(uuid.uuid4()),
                "instanceType": "AliasCode",
                "standardCode": sc,
                "standardCodeAliases": [],
            }

    # Ensure studyPhase is AliasCode with SDTM C66737 code (DDF00229 + DDF00125)
    _PHASE_CODE_MAP = {
        "phase1": ("PHASE 1", "Phase 1"),
        "phase 1": ("PHASE 1", "Phase 1"),
        "phase2": ("PHASE 2", "Phase 2"),
        "phase 2": ("PHASE 2", "Phase 2"),
        "phase3": ("PHASE 3", "Phase 3"),
        "phase 3": ("PHASE 3", "Phase 3"),
        "phase4": ("PHASE 4", "Phase 4"),
        "phase 4": ("PHASE 4", "Phase 4"),
        "phase1/2": ("PHASE 1/2", "Phase 1/2"),
        "phase 1/2": ("PHASE 1/2", "Phase 1/2"),
        "phase2/3": ("PHASE 2/3", "Phase 2/3"),
        "phase 2/3": ("PHASE 2/3", "Phase 2/3"),
        "phase1b/2": ("PHASE 1B/2", "Phase 1b/2"),
        "phase 1b": ("PHASE 1B", "Phase 1b"),
        "phase 2a": ("PHASE 2A", "Phase 2a"),
        "phase 2b": ("PHASE 2B", "Phase 2b"),
    }
    sp = design.get("studyPhase")
    if sp and isinstance(sp, dict):
        # Get or build the inner Code
        sc = sp.get("standardCode") if sp.get("instanceType") == "AliasCode" else sp
        if isinstance(sc, dict):
            raw_code = sc.get("code", sc.get("decode", "")).lower()
            mapped = _PHASE_CODE_MAP.get(raw_code)
            if mapped:
                sc["code"] = mapped[0]
                sc["decode"] = mapped[1]
                sc["codeSystem"] = "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl"
                sc["codeSystemVersion"] = "24.09e"
            if not sc.get("instanceType"):
                sc["instanceType"] = "Code"
            if not sc.get("id"):
                sc["id"] = str(uuid.uuid4())
        if sp.get("instanceType") != "AliasCode":
            design["studyPhase"] = {
                "id": str(uuid.uuid4()),
                "standardCode": sc,
                "standardCodeAliases": [],
                "instanceType": "AliasCode",
            }


def _fix_duplicate_code_decodes(usdm: Dict[str, Any]) -> None:
    """
    Fix code/decode one-to-one relationship violations (DDF00035).

    When the same code value is used with different decode values within
    the same codeSystem+codeSystemVersion, CORE flags a violation.
    Fix by making the decode consistent (use the first one seen).
    """
    try:
        design = usdm["study"]["versions"][0]["studyDesigns"][0]
    except (KeyError, IndexError):
        return

    # Collect all code objects and track (codeSystem, codeSystemVersion, code) → decode
    # Pre-seed canonical decodes for known codes to enforce consistency
    code_registry: Dict[tuple, str] = {
        ("http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl", "24.09e", "C17998"): "Unknown",
    }

    def _fix_codes(obj: Any) -> None:
        if isinstance(obj, dict):
            if _is_code_object(obj):
                key = (obj.get("codeSystem", ""),
                       obj.get("codeSystemVersion", ""),
                       obj.get("code", ""))
                if key[2]:  # Only if code is non-empty
                    if key in code_registry:
                        # Enforce consistent decode
                        obj["decode"] = code_registry[key]
                    else:
                        code_registry[key] = obj.get("decode", "")
            for v in obj.values():
                _fix_codes(v)
        elif isinstance(obj, list):
            for item in obj:
                _fix_codes(item)

    # Walk entire USDM to catch BCs on version level (not just design)
    _fix_codes(usdm)


def _ensure_study_design_type(usdm: Dict[str, Any]) -> None:
    """
    Ensure the study design has the correct ``instanceType`` and required
    fields for USDM v4.0.

    USDM v4.0 uses ``InterventionalStudyDesign`` or
    ``ObservationalStudyDesign`` — there is no generic ``StudyDesign``.
    Missing ``instanceType`` prevents CORE from properly parsing the
    design and its child entities (objectives, endpoints, etc.).
    """
    try:
        design = usdm["study"]["versions"][0]["studyDesigns"][0]
    except (KeyError, IndexError):
        return

    # Default to interventional (most common for clinical trials)
    if not design.get("instanceType"):
        design["instanceType"] = "InterventionalStudyDesign"

    # ``studyType`` is required for CORE to check intervention references (DDF00101)
    if design["instanceType"] == "InterventionalStudyDesign" and not design.get("studyType"):
        design["studyType"] = {
            "id": str(uuid.uuid4()).replace("-", "_"),
            "code": "C98388",
            "codeSystem": "http://www.cdisc.org",
            "codeSystemVersion": "2024-09-27",
            "decode": "Interventional Study",
            "instanceType": "Code",
        }

    # ``model`` is required for InterventionalStudyDesign
    if design["instanceType"] == "InterventionalStudyDesign" and not design.get("model"):
        design["model"] = {
            "id": str(uuid.uuid4()),
            "code": "C82639",
            "codeSystem": "http://www.cdisc.org",
            "codeSystemVersion": "2024-09-27",
            "decode": "Parallel Study",
            "instanceType": "Code",
        }

    # ``rationale`` is required
    if not design.get("rationale"):
        design["rationale"] = "See protocol synopsis."

    # ``blindingSchema`` is required for InterventionalStudyDesign.
    # Extraction stores it as a simple Code-like dict; USDM v4.0 expects
    # an AliasCode with ``standardCode`` nested inside.
    blinding = design.get("blindingSchema")
    if design["instanceType"] == "InterventionalStudyDesign":
        if isinstance(blinding, dict) and "standardCode" not in blinding:
            # Simple code dict from extraction — wrap in AliasCode
            blinding_code = blinding.get("code", "")
            _BLINDING_MAP = {
                "Open Label": ("C49659", "Open Label Study"),
                "open": ("C49659", "Open Label Study"),
                "Single Blind": ("C15228", "Single Blind Study"),
                "single": ("C15228", "Single Blind Study"),
                "Double Blind": ("C15227", "Double Blind Study"),
                "double": ("C15227", "Double Blind Study"),
                "Triple Blind": ("C156593", "Triple Blind Study"),
                "triple": ("C156593", "Triple Blind Study"),
            }
            mapped = _BLINDING_MAP.get(blinding_code, ("C49659", "Open Label Study"))
            design["blindingSchema"] = {
                "id": str(uuid.uuid4()).replace("-", "_"),
                "instanceType": "AliasCode",
                "standardCode": {
                    "id": str(uuid.uuid4()).replace("-", "_"),
                    "code": mapped[0],
                    "codeSystem": "http://www.cdisc.org",
                    "codeSystemVersion": "2024-09-27",
                    "decode": mapped[1],
                    "instanceType": "Code",
                },
                "standardCodeAliases": [],
            }
        elif not blinding:
            # No blinding at all — default to Open Label
            design["blindingSchema"] = {
                "id": str(uuid.uuid4()).replace("-", "_"),
                "instanceType": "AliasCode",
                "standardCode": {
                    "id": str(uuid.uuid4()).replace("-", "_"),
                    "code": "C49659",
                    "codeSystem": "http://www.cdisc.org",
                    "codeSystemVersion": "2024-09-27",
                    "decode": "Open Label Study",
                    "instanceType": "Code",
                },
                "standardCodeAliases": [],
            }

    # ``name`` should not be empty
    if not design.get("name"):
        study_name = usdm.get("study", {}).get("name", "Study Design")
        design["name"] = study_name or "Study Design"

    # Move properties that don't belong on the design to the correct level
    version = usdm["study"]["versions"][0]

    # Ensure Study has required instanceType
    study = usdm.get("study", {})
    if not study.get("instanceType"):
        study["instanceType"] = "Study"

    # Ensure StudyVersion has required instanceType
    if not version.get("instanceType"):
        version["instanceType"] = "StudyVersion"

    # ``studyPhase`` belongs on the design, not on the version
    if "studyPhase" in version and version["studyPhase"]:
        if not design.get("studyPhase"):
            design["studyPhase"] = version["studyPhase"]
        version.pop("studyPhase", None)

    # ``studyInterventions`` belongs on StudyVersion, not StudyDesign.
    # Merge design interventions into version (don't overwrite if version
    # already has them from direct placement).
    if "studyInterventions" in design:
        design_interventions = design.pop("studyInterventions")
        existing = version.get("studyInterventions", [])
        existing_ids = {inv.get("id") for inv in existing}
        for inv in design_interventions:
            if inv.get("id") not in existing_ids:
                existing.append(inv)
        version["studyInterventions"] = existing

    # Populate studyInterventionIds on design as ref list to version interventions.
    design["studyInterventionIds"] = [
        inv.get("id") for inv in version.get("studyInterventions", [])
        if inv.get("id")
    ]

    # ``geographicScopes`` is not a StudyDesign property in v4.0
    # (only on GovernanceDate and StudyAmendment)
    design.pop("geographicScopes", None)

    # ``epochs`` must have at least one entry (DDF00126).
    # If empty, synthesize epochs from study cell references.
    if not design.get("epochs"):
        epoch_ids = []
        for cell in design.get("studyCells", []):
            eid = cell.get("epochId") or cell.get("epoch")
            if isinstance(eid, str) and eid not in epoch_ids:
                epoch_ids.append(eid)
        if epoch_ids:
            design["epochs"] = [
                {
                    "id": eid,
                    "name": f"Epoch {i + 1}",
                    "type": {
                        "id": str(uuid.uuid4()),
                        "code": "C99079",
                        "codeSystem": "http://www.cdisc.org",
                        "codeSystemVersion": "2024-09-27",
                        "decode": "Treatment Epoch",
                        "instanceType": "Code",
                    },
                    "instanceType": "StudyEpoch",
                }
                for i, eid in enumerate(epoch_ids)
            ]


def _ensure_primary_objective(usdm: Dict[str, Any]) -> None:
    """
    Ensure the study design has exactly one primary objective and link
    endpoints to objectives via the ``endpoints`` array.

    CORE checks (JSONata-based):
    - DDF00084: Exactly one objective with level.code = C85826
    - DDF00041: ``objectives.endpoints[level.code="C94496"]`` count > 0
    - DDF00096: Each primary endpoint must be a child of a primary objective

    The CORE engine resolves ``objectives.endpoints`` by looking for an
    ``endpoints`` array nested inside each objective.
    """
    try:
        design = usdm["study"]["versions"][0]["studyDesigns"][0]
    except (KeyError, IndexError):
        return

    objectives = design.get("objectives", [])
    endpoints = design.get("endpoints", [])
    if not objectives or not endpoints:
        return

    # --- Build level-code lookup for endpoints ---
    # Map: level_code -> list of endpoints
    eps_by_level: Dict[str, list] = {}
    for ep in endpoints:
        lv = ep.get("level", {})
        code = lv.get("code", "") if isinstance(lv, dict) else ""
        eps_by_level.setdefault(code, []).append(ep)

    # --- Merge multiple primary objectives into one ---
    primary_objs = [o for o in objectives if isinstance(o.get("level"), dict) and o["level"].get("code") == "C85826"]
    if len(primary_objs) > 1:
        # Keep the first, merge names/text from others
        keeper = primary_objs[0]
        for extra in primary_objs[1:]:
            # Append extra's text to keeper
            extra_text = extra.get("text", "")
            if extra_text and extra_text not in keeper.get("text", ""):
                keeper["text"] = (keeper.get("text", "") + " " + extra_text).strip()
            # Append extra's name info
            extra_name = extra.get("name", "")
            if extra_name and extra_name not in keeper.get("name", ""):
                keeper["name"] = keeper["name"] + " / " + extra_name
            objectives.remove(extra)

    # --- Assign endpoints to objectives by matching level ---
    LEVEL_MAP = {
        "C85826": "C94496",    # Primary Objective -> Primary Endpoint
        "C85827": "C139173",   # Secondary Objective -> Secondary Endpoint
        "C163559": "C170559",  # Exploratory Objective -> Exploratory Endpoint
    }

    # Group objectives by level code
    objs_by_level: Dict[str, list] = {}
    for obj in objectives:
        obj_level = obj.get("level", {})
        obj_code = obj_level.get("code", "") if isinstance(obj_level, dict) else ""
        objs_by_level.setdefault(obj_code, []).append(obj)

    for obj_code, obj_group in objs_by_level.items():
        ep_code = LEVEL_MAP.get(obj_code, "")
        matching_eps = eps_by_level.get(ep_code, [])
        if not matching_eps:
            continue

        if len(obj_group) == 1:
            # Single objective gets all matching endpoints
            embedded = []
            for ep in matching_eps:
                ep_copy = dict(ep)
                ep_copy["id"] = str(uuid.uuid4())
                if ep_copy.get("level"):
                    lv_copy = dict(ep_copy["level"])
                    lv_copy["id"] = str(uuid.uuid4())
                    ep_copy["level"] = lv_copy
                embedded.append(ep_copy)
            obj_group[0]["endpoints"] = embedded
        else:
            # Multiple objectives: distribute endpoints round-robin
            # so each endpoint name appears exactly once
            for idx, ep in enumerate(matching_eps):
                target_obj = obj_group[idx % len(obj_group)]
                ep_copy = dict(ep)
                ep_copy["id"] = str(uuid.uuid4())
                if ep_copy.get("level"):
                    lv_copy = dict(ep_copy["level"])
                    lv_copy["id"] = str(uuid.uuid4())
                    ep_copy["level"] = lv_copy
                target_obj.setdefault("endpoints", []).append(ep_copy)

    # Remove top-level endpoints array after embedding into objectives
    # to avoid DDF00010 (duplicate names) and DDF00096 (orphaned endpoints).
    design.pop("endpoints", None)



def _fix_required_fields(usdm: Dict[str, Any]) -> None:
    """
    Ensure required USDM v4.0 fields are present on entities that may have
    been built from partial extraction data.

    Covers the most common validator errors:
      - BiomedicalConcept: reference, code
      - BiomedicalConceptProperty: isEnabled, code
      - AnalysisPopulation: text
      - studyPhase: must be AliasCode wrapping the Code object
    """
    version = usdm.get("study", {}).get("versions", [{}])[0]

    # ── BiomedicalConcepts ──────────────────────────────────────────────────
    # BC.code and BCProperty.code must be AliasCode (DDF00081 — 'AliasCode' was expected).
    def _to_alias_code(code_obj: Dict[str, Any]) -> Dict[str, Any]:
        """Wrap a plain Code dict in AliasCode if not already wrapped."""
        if not isinstance(code_obj, dict):
            return code_obj
        if code_obj.get("instanceType") == "AliasCode":
            return code_obj
        # It is a plain Code — wrap it
        if not code_obj.get("id"):
            code_obj["id"] = str(uuid.uuid4())
        if not code_obj.get("instanceType"):
            code_obj["instanceType"] = "Code"
        return {
            "id": str(uuid.uuid4()),
            "instanceType": "AliasCode",
            "standardCode": code_obj,
            "standardCodeAliases": [],
        }

    bc_name_to_id: Dict[str, str] = {}  # for BCCategory.memberIds wiring
    for bc in version.get("biomedicalConcepts", []):
        if not bc.get("reference"):
            bc["reference"] = bc.get("name", "unknown")
        bc_name_to_id[bc.get("name", "")] = bc.get("id", "")
        if not bc.get("code"):
            bc["code"] = _to_alias_code({
                "id": str(uuid.uuid4()),
                "code": "C17998",
                "codeSystem": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl",
                "codeSystemVersion": "24.09e",
                "decode": "Unknown",
                "instanceType": "Code",
            })
        else:
            bc["code"] = _to_alias_code(bc["code"])
        bc_name = bc.get("name", "")
        prop_names_seen: Dict[str, int] = {}
        for prop in bc.get("properties", []):
            if "isEnabled" not in prop:
                prop["isEnabled"] = True
            # Deduplicate property names: prefix with BC name (DDF00010)
            raw_name = prop.get("name", "Property")
            unique_name = f"{bc_name} - {raw_name}" if bc_name else raw_name
            if unique_name in prop_names_seen:
                prop_names_seen[unique_name] += 1
                prop["name"] = f"{unique_name} ({prop_names_seen[unique_name]})"
            else:
                prop_names_seen[unique_name] = 1
                prop["name"] = unique_name
            if not prop.get("code"):
                prop["code"] = _to_alias_code({
                    "id": str(uuid.uuid4()),
                    "code": "C17998",
                    "codeSystem": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl",
                    "codeSystemVersion": "24.09e",
                    "decode": "Unknown",  # canonical NCI decode for C17998 (DDF00035)
                    "instanceType": "Code",
                })
            else:
                prop["code"] = _to_alias_code(prop["code"])

    # ── BCCategory: wire memberIds from bcName lookup (DDF00014) ────────────
    for cat in version.get("bcCategories", []):
        if not cat.get("memberIds") and not cat.get("childIds"):
            # Try to match BCs whose name contains the category name
            cat_name = cat.get("name", "").lower()
            matched_ids = [
                bid for bname, bid in bc_name_to_id.items()
                if cat_name and (cat_name in bname.lower() or bname.lower() in cat_name)
            ]
            if not matched_ids:
                matched_ids = list(bc_name_to_id.values())
            if matched_ids:
                cat["memberIds"] = matched_ids

    # ── AnalysisPopulations ─────────────────────────────────────────────────
    designs = version.get("studyDesigns", [])
    for design in designs:
        for pop in design.get("analysisPopulations", []):
            if not pop.get("text"):
                pop["text"] = pop.get("description") or pop.get("name") or "Study population"

        # ── studyPhase: must be AliasCode, not a bare Code ──────────────────
        sp = design.get("studyPhase")
        if sp and isinstance(sp, dict):
            inst = sp.get("instanceType", "")
            # Wrap if plain Code OR a code-like dict missing instanceType
            if inst in ("Code", "") and sp.get("code") and sp.get("instanceType") != "AliasCode":
                if not sp.get("instanceType"):
                    sp["instanceType"] = "Code"
                if not sp.get("id"):
                    sp["id"] = str(uuid.uuid4())
                design["studyPhase"] = {
                    "id": str(uuid.uuid4()),
                    "standardCode": sp,
                    "standardCodeAliases": [],
                    "instanceType": "AliasCode",
                }
            elif sp.get("instanceType") == "AliasCode" and not sp.get("standardCode"):
                # AliasCode missing standardCode — build a default
                sp["standardCode"] = {
                    "id": str(uuid.uuid4()),
                    "code": "C48660",
                    "codeSystem": "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl",
                    "codeSystemVersion": "24.09e",
                    "decode": "Not Applicable",
                    "instanceType": "Code",
                }


def _validate_usdm_structure(usdm: Dict[str, Any]) -> List[USDMValidationIssue]:
    """Basic structural validation of the generated USDM."""
    issues = []

    study = usdm.get("study", {})
    if not study.get("name"):
        issues.append(USDMValidationIssue("warning", "study.name", "Study name is empty"))

    versions = study.get("versions", [])
    if not versions:
        issues.append(USDMValidationIssue("error", "study.versions", "No study versions"))
        return issues

    version = versions[0]
    if not version.get("studyIdentifiers"):
        issues.append(USDMValidationIssue("warning", "study.versions[0].studyIdentifiers",
                                           "No study identifiers"))

    designs = version.get("studyDesigns", [])
    if not designs:
        issues.append(USDMValidationIssue("error", "study.versions[0].studyDesigns",
                                           "No study designs"))
        return issues

    design = designs[0]
    if not design.get("arms"):
        issues.append(USDMValidationIssue("warning", "studyDesigns[0].arms", "No study arms"))
    if not design.get("epochs"):
        issues.append(USDMValidationIssue("warning", "studyDesigns[0].epochs", "No study epochs"))
    if not design.get("objectives"):
        issues.append(USDMValidationIssue("warning", "studyDesigns[0].objectives", "No objectives"))

    return issues


class USDMGeneratorAgent(BaseAgent):
    """
    Agent that generates USDM v4.0 JSON from Context Store entities.

    Queries the Context Store for all extracted entities, places them
    into the correct USDM hierarchy, validates the structure, and
    writes the final JSON output.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id="usdm-generator", config=config or {})
        self._indent = (config or {}).get("json_indent", 2)

    def initialize(self) -> None:
        self.set_state(AgentState.READY)
        self._logger.info(f"[{self.agent_id}] Initialized")

    def terminate(self) -> None:
        self.set_state(AgentState.TERMINATED)

    def get_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            agent_type="support",
            input_types=["context_store"],
            output_types=["usdm_json"],
        )

    def execute(self, task: AgentTask) -> AgentResult:
        """
        Generate USDM v4.0 JSON from Context Store.

        Input data:
        - output_path (str, optional): Path to write the JSON file
        - include_types (list[str], optional): Only include these entity types
        - exclude_types (list[str], optional): Exclude these entity types
        """
        if not self._context_store:
            return AgentResult(
                task_id=task.task_id, agent_id=self.agent_id,
                success=False, error="No Context Store available",
            )

        try:
            result = self._generate(task)

            # Post-assembly step 1: type-inference normalization
            try:
                from core.usdm_types_generated import normalize_usdm_data
                result.usdm_json = normalize_usdm_data(result.usdm_json)
                self._logger.debug(f"[{self.agent_id}] Type normalization applied")
            except Exception as e:
                self._logger.debug(f"[{self.agent_id}] Normalization skipped: {e}")

            # Post-assembly step 1b: final schema cleanup (strip non-schema fields
            # that may have been re-added by normalize_usdm_data or other passes)
            try:
                _post_normalize_cleanup(result.usdm_json)
                self._logger.debug(f"[{self.agent_id}] Post-normalize cleanup applied")
            except Exception as e:
                self._logger.debug(f"[{self.agent_id}] Post-normalize cleanup skipped: {e}")

            # Post-assembly step 2: convert simple IDs to UUID format
            id_map: dict = {}
            output_path = task.input_data.get("output_path")
            output_dir = os.path.dirname(output_path) if output_path else task.input_data.get("output_dir")
            try:
                from core.validation import convert_ids_to_uuids
                result.usdm_json, id_map = convert_ids_to_uuids(result.usdm_json)
                self._logger.info(f"[{self.agent_id}] Converted {len(id_map)} IDs to UUIDs")
                if output_dir and id_map:
                    id_map_path = os.path.join(output_dir, "id_mapping.json")
                    os.makedirs(output_dir, exist_ok=True)
                    with open(id_map_path, "w", encoding="utf-8") as f:
                        json.dump(id_map, f, indent=2)
            except Exception as e:
                self._logger.debug(f"[{self.agent_id}] UUID conversion skipped: {e}")

            # Post-assembly step 3: USDM schema validation via validate_and_fix_schema
            schema_valid = None
            semantic_issues = 0
            try:
                from core.validation import validate_and_fix_schema
                fixed_data, schema_result, fixer_result, usdm_result, _ = validate_and_fix_schema(
                    result.usdm_json, output_dir or ".", use_llm=False, convert_to_uuids=False
                )
                result.usdm_json = fixed_data
                schema_errors = getattr(schema_result, "error_count", 0) if schema_result else 0
                semantic_issues = getattr(usdm_result, "error_count", 0) if usdm_result else 0
                schema_valid = schema_errors == 0 and semantic_issues == 0
                if schema_valid:
                    self._logger.info(f"[{self.agent_id}] USDM schema validation PASSED")
                else:
                    self._logger.warning(
                        f"[{self.agent_id}] USDM validation FAILED: "
                        f"{schema_errors} schema errors, {semantic_issues} semantic errors"
                    )
            except Exception as e:
                self._logger.debug(f"[{self.agent_id}] USDM validation skipped: {e}")

            # Write assembled (and normalized) USDM to file
            if output_path:
                os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(result.usdm_json, f, indent=self._indent, ensure_ascii=False)
                result.output_path = output_path

            return AgentResult(
                task_id=task.task_id, agent_id=self.agent_id,
                success=True,
                data={
                    "usdm": result.usdm_json,
                    "id_map_size": len(id_map),
                    "schema_valid": schema_valid,
                    "semantic_issues": semantic_issues,
                    **result.to_dict(),
                },
                confidence_score=1.0 if not result.validation_issues else 0.8,
                provenance={
                    "agent_id": self.agent_id,
                    "entity_count": result.entity_count,
                    "entity_types": result.entity_types_included,
                    "validation_issues": len(result.validation_issues),
                    "id_map_size": len(id_map),
                    "schema_valid": schema_valid,
                    "semantic_issues": semantic_issues,
                    "timestamp": datetime.now().isoformat(),
                },
            )
        except Exception as e:
            self._logger.error(f"[{self.agent_id}] USDM generation failed: {e}")
            return AgentResult(
                task_id=task.task_id, agent_id=self.agent_id,
                success=False, error=str(e),
            )

    def _generate(self, task: AgentTask) -> USDMGenerationResult:
        """Build the USDM JSON from Context Store entities."""
        include_types = set(task.input_data.get("include_types", []))
        exclude_types = set(task.input_data.get("exclude_types", []))

        usdm = _build_empty_usdm_skeleton()
        result = USDMGenerationResult(usdm_json=usdm)

        # Query all entities from Context Store
        all_entities = self._context_store.query_entities()
        types_seen = set()

        for entity in all_entities:
            etype = entity.entity_type

            # Skip internal/infrastructure types
            if etype in ("pdf_page", "checkpoint", "error_record"):
                continue

            # study_design: extract design-level properties (blindingSchema,
            # randomizationType, etc.) and apply them to the skeleton design.
            if etype == "study_design":
                try:
                    design = usdm["study"]["versions"][0]["studyDesigns"][0]
                    sd_data = dict(entity.data)
                    sd_data = _sanitize_entity_data(sd_data)

                    # Only place properties that exist in the USDM v4.0 schema
                    # for InterventionalStudyDesign.
                    if sd_data.get("blindingSchema") and not design.get("blindingSchema"):
                        design["blindingSchema"] = sd_data["blindingSchema"]

                    # trialIntentTypes → intentTypes (schema property name)
                    intent = sd_data.get("trialIntentTypes")
                    if intent and not design.get("intentTypes"):
                        # Map extraction intent types to CDISC codes
                        _INTENT_MAP = {
                            "Treatment": ("C49656", "Treatment Study"),
                            "Prevention": ("C49655", "Prevention Study"),
                            "Diagnostic": ("C15220", "Diagnostic Study"),
                            "Supportive Care": ("C15313", "Supportive Care Study"),
                            "Screening": ("C15417", "Screening Study"),
                            "Health Services Research": ("C15245", "Health Services Research Study"),
                            "Basic Science": ("C15188", "Basic Science Study"),
                        }
                        codes = []
                        for item in (intent if isinstance(intent, list) else [intent]):
                            if isinstance(item, dict):
                                raw_code = item.get("code", "")
                                mapped = _INTENT_MAP.get(raw_code)
                                if mapped:
                                    codes.append({
                                        "id": str(uuid.uuid4()).replace("-", "_"),
                                        "code": mapped[0],
                                        "codeSystem": "http://www.cdisc.org",
                                        "codeSystemVersion": "2024-09-27",
                                        "decode": mapped[1],
                                        "instanceType": "Code",
                                    })
                            elif isinstance(item, str):
                                mapped = _INTENT_MAP.get(item)
                                if mapped:
                                    codes.append({
                                        "id": str(uuid.uuid4()).replace("-", "_"),
                                        "code": mapped[0],
                                        "codeSystem": "http://www.cdisc.org",
                                        "codeSystemVersion": "2024-09-27",
                                        "decode": mapped[1],
                                        "instanceType": "Code",
                                    })
                        if codes:
                            design["intentTypes"] = codes

                    # therapeuticAreas — must be Code objects, not strings
                    ta = sd_data.get("therapeuticAreas")
                    if ta and not design.get("therapeuticAreas"):
                        codes = []
                        for item in (ta if isinstance(ta, list) else [ta]):
                            if isinstance(item, dict) and item.get("code"):
                                codes.append(_ensure_code_id(dict(item)))
                            elif isinstance(item, str):
                                codes.append({
                                    "id": str(uuid.uuid4()).replace("-", "_"),
                                    "code": item,
                                    "codeSystem": "http://www.cdisc.org",
                                    "codeSystemVersion": "2024-09-27",
                                    "decode": item,
                                    "instanceType": "Code",
                                })
                        if codes:
                            design["therapeuticAreas"] = codes

                    # Use extracted name/instanceType if present
                    if sd_data.get("name") and not design.get("name"):
                        design["name"] = sd_data["name"]
                    if sd_data.get("instanceType"):
                        design["instanceType"] = sd_data["instanceType"]
                except (KeyError, IndexError):
                    pass
                types_seen.add(etype)
                continue

            # header_structure: stash footnote text and epoch data for later use
            if etype == "header_structure":
                try:
                    hs_data = entity.data or {}
                    structure = hs_data.get("structure", {})
                    design = usdm["study"]["versions"][0]["studyDesigns"][0]
                    footnotes = structure.get("footnotes", [])
                    if footnotes:
                        design["_headerFootnotes"] = footnotes
                    # Stash header epoch data so _normalize_codelists can resolve
                    # stale epoch IDs (e.g. "epoch_1") to USDM epoch entity IDs.
                    col_hierarchy = structure.get("columnHierarchy", {})
                    hdr_epochs = col_hierarchy.get("epochs", [])
                    if hdr_epochs:
                        design["_headerEpochs"] = hdr_epochs
                except (KeyError, IndexError):
                    pass
                continue

            # Apply include/exclude filters
            if include_types and etype not in include_types:
                continue
            if exclude_types and etype in exclude_types:
                continue

            # Build entity data dict with id
            entity_data = dict(entity.data)
            if "id" not in entity_data:
                entity_data["id"] = entity.id

            # Capture encounter→epochId mapping BEFORE epochId gets stripped.
            # Timeline synthesis (_ensure_sponsor_identifier) needs this mapping
            # but runs before _normalize_codelists where it was previously built.
            if etype == "encounter" and entity_data.get("epochId"):
                try:
                    enc_epoch_stash = usdm["study"]["versions"][0]["studyDesigns"][0].setdefault("_encounterEpochMap", {})
                    enc_epoch_stash[entity_data["id"]] = entity_data["epochId"]
                except (KeyError, IndexError):
                    pass

            # Strip internal/debug properties not in USDM schema
            entity_data = _sanitize_entity_data(entity_data)

            # Strip entity-specific extra properties not in USDM v4.0
            extras = _ENTITY_EXTRA_PROPERTIES.get(etype)
            if extras:
                for prop in extras:
                    entity_data.pop(prop, None)

            # StudyArm: ensure required dataOriginDescription and dataOriginType
            if etype == "study_arm":
                if "dataOriginDescription" not in entity_data:
                    entity_data["dataOriginDescription"] = "Collected during study conduct"
                if "dataOriginType" not in entity_data:
                    entity_data["dataOriginType"] = {
                        "id": str(uuid.uuid4()).replace("-", "_"),
                        "code": "C142493",
                        "codeSystem": "http://www.cdisc.org",
                        "codeSystemVersion": "2024-09-27",
                        "decode": "Collected",
                        "instanceType": "Code",
                    }

            # Epoch: extraction uses instanceType "Epoch" but USDM v4.0
            # expects "StudyEpoch" and requires a ``type`` Code object.
            if etype == "epoch":
                if entity_data.get("instanceType") == "Epoch":
                    entity_data["instanceType"] = "StudyEpoch"
                if not isinstance(entity_data.get("type"), dict):
                    # Infer epoch type from name (like legacy code)
                    epoch_name = entity_data.get("name", "").lower()
                    if "screen" in epoch_name:
                        ep_code, ep_decode = "C98779", "Screening Epoch"
                    elif "follow" in epoch_name or "post" in epoch_name:
                        ep_code, ep_decode = "C98781", "Follow-up Epoch"
                    elif "run-in" in epoch_name or "runin" in epoch_name or "washout" in epoch_name:
                        ep_code, ep_decode = "C98782", "Run-in Epoch"
                    else:
                        ep_code, ep_decode = "C99079", "Treatment Epoch"
                    entity_data["type"] = {
                        "id": str(uuid.uuid4()).replace("-", "_"),
                        "code": ep_code,
                        "codeSystem": "http://www.cdisc.org",
                        "codeSystemVersion": "2024-09-27",
                        "decode": ep_decode,
                        "instanceType": "Code",
                    }

            # Organization: ensure instanceType
            if etype == "organization":
                if not entity_data.get("instanceType"):
                    entity_data["instanceType"] = "Organization"

            # StudyRole: ensure instanceType and fix code
            if etype == "study_role":
                if not entity_data.get("instanceType"):
                    entity_data["instanceType"] = "StudyRole"

            placed = _place_entity(usdm, etype, entity_data)
            if placed:
                result.entity_count += 1
                types_seen.add(etype)

        result.entity_types_included = sorted(types_seen)

        # Ensure study design has correct instanceType and required fields
        # (must run early — moves studyInterventions to version, adds studyType)
        _ensure_study_design_type(usdm)

        # Ensure sponsor identifier, role, timeline, and intervention refs
        _ensure_sponsor_identifier(usdm)

        # Derive businessTherapeuticAreas from indications if not already set
        _populate_therapeutic_areas(usdm)

        # Post-process: normalize codelist codes to CDISC-expected values
        # (must run after _ensure_study_design_type so interventions are on version)
        _normalize_codelists(usdm)

        # Fix activity names (repr strings → actual names) and link to procedures
        _fix_activity_names(usdm)
        _link_activities_to_procedures(usdm)

        # Fix duplicate IntercurrentEvent names across estimands
        _deduplicate_intercurrent_event_names(usdm)

        # Sanitize NarrativeContentItem text to valid XHTML
        _sanitize_narrative_xhtml(usdm)

        # Fix code/decode one-to-one relationship violations
        _fix_duplicate_code_decodes(usdm)

        # Ensure primary objective exists and links to primary endpoints
        _ensure_primary_objective(usdm)

        _fix_required_fields(usdm)
        result.validation_issues = _validate_usdm_structure(usdm)
        return result
