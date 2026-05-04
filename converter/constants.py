"""Constants used throughout the Prodigy-to-USDM converter."""

# Converter and USDM version strings
CONVERTER_VERSION: str = "1.0.0"
USDM_VERSION: str = "4.0.0"

# Prodigy-specific metadata fields to strip from all entities.
# These are not part of USDM 4.0 and must be removed during conversion.
PRODIGY_METADATA_FIELDS: set[str] = {
    "provenance",
    "confidenceScoring",
    "hash",
    "unmapped",
    "kgLabel",
    "scopeId",
    "complexityScoring",
}

# Entity types where scopeId is a valid USDM 4.0 field and should be preserved.
SCOPEID_WHITELIST_TYPES: set[str] = {"StudyIdentifier"}

# All USDM 4.0 entity types found in the golden reference files.
KNOWN_INSTANCE_TYPES: set[str] = {
    "Abbreviation",
    "Activity",
    "Address",
    "Administration",
    "AliasCode",
    "BiomedicalConcept",
    "BiomedicalConceptProperty",
    "BiomedicalConceptSurrogate",
    "Characteristic",
    "Code",
    "CommentAnnotation",
    "Condition",
    "ConditionAssignment",
    "DocumentContentReference",
    "Duration",
    "EligibilityCriterion",
    "EligibilityCriterionItem",
    "Encounter",
    "Endpoint",
    "GeographicScope",
    "GovernanceDate",
    "Indication",
    "InterventionalStudyDesign",
    "Masking",
    "NarrativeContent",
    "NarrativeContentItem",
    "Objective",
    "Organization",
    "ParameterMap",
    "Procedure",
    "Quantity",
    "Range",
    "ResponseCode",
    "ScheduleTimeline",
    "ScheduleTimelineExit",
    "ScheduledActivityInstance",
    "ScheduledDecisionInstance",
    "Study",
    "StudyAmendment",
    "StudyAmendmentImpact",
    "StudyAmendmentReason",
    "StudyArm",
    "StudyCell",
    "StudyChange",
    "StudyCohort",
    "StudyDefinitionDocument",
    "StudyDefinitionDocumentVersion",
    "StudyDesignPopulation",
    "StudyElement",
    "StudyEpoch",
    "StudyIdentifier",
    "StudyIntervention",
    "StudyRole",
    "StudySite",
    "StudyTitle",
    "StudyVersion",
    "SubjectEnrollment",
    "SyntaxTemplateDictionary",
    "Timing",
    "TransitionRule",
}
