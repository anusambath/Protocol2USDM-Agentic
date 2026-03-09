"""
ValidationAgent - Validates extracted data against USDM v4.0 schema and CDISC CORE rules.

Responsibilities:
- Validate USDM v4.0 schema compliance (required fields, data types, cardinality)
- Validate entity references (all IDs resolve to existing entities)
- Run CDISC CORE conformance checks
- Classify validation errors by severity (error, warning, info)
- Attempt automatic fixes for common schema violations
- Document fixes in provenance
- Generate validation reports with actionable messages
- Support iterative validation (re-validate after fixes)
"""

import logging
import uuid
from copy import deepcopy
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from agents.base import AgentCapabilities, AgentResult, AgentState, AgentTask, BaseAgent
from agents.context_store import ContextEntity, ContextStore, EntityProvenance

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Severity & issue models
# ---------------------------------------------------------------------------

class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """A single validation finding."""
    issue_id: str
    severity: ValidationSeverity
    category: str          # e.g. "required_field", "data_type", "cardinality", "reference", "core"
    entity_id: str
    entity_type: str
    field_name: str
    message: str
    suggestion: str = ""
    auto_fixable: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "severity": self.severity.value,
            "category": self.category,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "field_name": self.field_name,
            "message": self.message,
            "suggestion": self.suggestion,
            "auto_fixable": self.auto_fixable,
        }


@dataclass
class AutoFix:
    """Record of an automatic fix applied."""
    fix_id: str
    entity_id: str
    field_name: str
    old_value: Any
    new_value: Any
    reason: str
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fix_id": self.fix_id,
            "entity_id": self.entity_id,
            "field_name": self.field_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ValidationReport:
    """Complete validation report."""
    report_id: str
    timestamp: datetime
    total_entities: int
    issues: List[ValidationIssue]
    fixes_applied: List[AutoFix]
    iteration: int = 1

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.INFO)

    @property
    def is_valid(self) -> bool:
        return self.error_count == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "timestamp": self.timestamp.isoformat(),
            "total_entities": self.total_entities,
            "summary": {
                "errors": self.error_count,
                "warnings": self.warning_count,
                "info": self.info_count,
                "is_valid": self.is_valid,
                "fixes_applied": len(self.fixes_applied),
            },
            "iteration": self.iteration,
            "issues": [i.to_dict() for i in self.issues],
            "fixes": [f.to_dict() for f in self.fixes_applied],
        }


# ---------------------------------------------------------------------------
# USDM v4.0 Schema Definition (data-driven, no external files)
# ---------------------------------------------------------------------------

@dataclass
class FieldSpec:
    """Specification for a single field in a USDM entity type."""
    name: str
    data_type: str          # "string", "integer", "float", "boolean", "list", "dict", "date"
    required: bool = False
    min_cardinality: int = 0
    max_cardinality: Optional[int] = None   # None = unbounded
    reference_type: Optional[str] = None    # entity_type this ID references

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "data_type": self.data_type,
            "required": self.required,
            "min_cardinality": self.min_cardinality,
            "max_cardinality": self.max_cardinality,
            "reference_type": self.reference_type,
        }


@dataclass
class EntitySchema:
    """Schema definition for a USDM entity type."""
    entity_type: str
    fields: Dict[str, FieldSpec]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "fields": {k: v.to_dict() for k, v in self.fields.items()},
        }


# Type mapping for validation
_PYTHON_TYPE_MAP: Dict[str, type] = {
    "string": str,
    "integer": int,
    "float": (int, float),  # type: ignore[assignment]
    "boolean": bool,
    "list": list,
    "dict": dict,
}


def _build_usdm_v4_schema() -> Dict[str, EntitySchema]:
    """Build the USDM v4.0 schema as in-memory data structures."""
    schemas: Dict[str, EntitySchema] = {}

    # Study
    schemas["study"] = EntitySchema(
        entity_type="study",
        fields={
            "name": FieldSpec("name", "string", required=True),
            "description": FieldSpec("description", "string"),
            "label": FieldSpec("label", "string"),
            "protocolVersions": FieldSpec("protocolVersions", "list", min_cardinality=1),
        },
    )

    # Study Title
    schemas["study_title"] = EntitySchema(
        entity_type="study_title",
        fields={
            "text": FieldSpec("text", "string", required=True),
            "type": FieldSpec("type", "string", required=True),
        },
    )

    # Study Identifier
    schemas["study_identifier"] = EntitySchema(
        entity_type="study_identifier",
        fields={
            "identifier": FieldSpec("identifier", "string", required=True),
            "type": FieldSpec("type", "string"),
            "organizationId": FieldSpec("organizationId", "string", reference_type="organization"),
        },
    )

    # Organization
    schemas["organization"] = EntitySchema(
        entity_type="organization",
        fields={
            "name": FieldSpec("name", "string", required=True),
            "type": FieldSpec("type", "string"),
            "identifier": FieldSpec("identifier", "string"),
        },
    )

    # Study Phase
    schemas["study_phase"] = EntitySchema(
        entity_type="study_phase",
        fields={
            "standardCode": FieldSpec("standardCode", "string", required=True),
        },
    )

    # Indication
    schemas["indication"] = EntitySchema(
        entity_type="indication",
        fields={
            "name": FieldSpec("name", "string", required=True),
            "description": FieldSpec("description", "string"),
        },
    )

    # Objective
    schemas["objective"] = EntitySchema(
        entity_type="objective",
        fields={
            "text": FieldSpec("text", "string", required=True),
            "level": FieldSpec("level", "string", required=True),
            "endpointIds": FieldSpec("endpointIds", "list", reference_type="endpoint"),
        },
    )

    # Endpoint
    schemas["endpoint"] = EntitySchema(
        entity_type="endpoint",
        fields={
            "text": FieldSpec("text", "string", required=True),
            "purpose": FieldSpec("purpose", "string"),
            "level": FieldSpec("level", "string"),
        },
    )

    # Eligibility Criterion
    # category is a USDM Code object (dict) with code/codeSystem/decode,
    # or a plain string.  text lives on the linked criterion_item entity.
    schemas["eligibility_criterion"] = EntitySchema(
        entity_type="eligibility_criterion",
        fields={
            "name": FieldSpec("name", "string"),
            "category": FieldSpec("category", "string", required=True),
            "identifier": FieldSpec("identifier", "string"),
            "text": FieldSpec("text", "string"),
            "criterionItemId": FieldSpec("criterionItemId", "string", reference_type="criterion_item"),
        },
    )

    # Criterion Item (holds the actual eligibility text)
    schemas["criterion_item"] = EntitySchema(
        entity_type="criterion_item",
        fields={
            "name": FieldSpec("name", "string"),
            "text": FieldSpec("text", "string", required=True),
        },
    )

    # Study Arm
    schemas["study_arm"] = EntitySchema(
        entity_type="study_arm",
        fields={
            "name": FieldSpec("name", "string", required=True),
            "type": FieldSpec("type", "string"),
            "description": FieldSpec("description", "string"),
        },
    )

    # Epoch
    schemas["epoch"] = EntitySchema(
        entity_type="epoch",
        fields={
            "name": FieldSpec("name", "string", required=True),
            "type": FieldSpec("type", "string"),
            "description": FieldSpec("description", "string"),
            "encounterIds": FieldSpec("encounterIds", "list", reference_type="encounter"),
        },
    )

    # Encounter
    schemas["encounter"] = EntitySchema(
        entity_type="encounter",
        fields={
            "name": FieldSpec("name", "string", required=True),
            "type": FieldSpec("type", "string"),
            "description": FieldSpec("description", "string"),
        },
    )

    # Activity
    schemas["activity"] = EntitySchema(
        entity_type="activity",
        fields={
            "name": FieldSpec("name", "string", required=True),
            "description": FieldSpec("description", "string"),
            "procedureIds": FieldSpec("procedureIds", "list", reference_type="procedure"),
        },
    )

    # Procedure
    schemas["procedure"] = EntitySchema(
        entity_type="procedure",
        fields={
            "name": FieldSpec("name", "string", required=True),
            "type": FieldSpec("type", "string"),
            "description": FieldSpec("description", "string"),
        },
    )

    # Scheduled Instance
    schemas["scheduled_instance"] = EntitySchema(
        entity_type="scheduled_instance",
        fields={
            "encounterId": FieldSpec("encounterId", "string", required=True, reference_type="encounter"),
            "activityIds": FieldSpec("activityIds", "list", required=True, reference_type="activity", min_cardinality=1),
        },
    )

    # Investigational Product
    schemas["investigational_product"] = EntitySchema(
        entity_type="investigational_product",
        fields={
            "name": FieldSpec("name", "string", required=True),
            "description": FieldSpec("description", "string"),
            "administrationRoute": FieldSpec("administrationRoute", "string"),
        },
    )

    # Timing
    schemas["timing"] = EntitySchema(
        entity_type="timing",
        fields={
            "type": FieldSpec("type", "string", required=True),
            "value": FieldSpec("value", "string"),
            "description": FieldSpec("description", "string"),
        },
    )

    # Narrative Content
    schemas["narrative_content"] = EntitySchema(
        entity_type="narrative_content",
        fields={
            "name": FieldSpec("name", "string", required=True),
            "sectionNumber": FieldSpec("sectionNumber", "string"),
            "text": FieldSpec("text", "string"),
        },
    )

    # Narrative Content Item
    schemas["narrative_content_item"] = EntitySchema(
        entity_type="narrative_content_item",
        fields={
            "name": FieldSpec("name", "string"),
            "text": FieldSpec("text", "string", required=True),
            "sectionNumber": FieldSpec("sectionNumber", "string"),
        },
    )

    # Study Role (sponsor, investigator, etc.)
    schemas["study_role"] = EntitySchema(
        entity_type="study_role",
        fields={
            "name": FieldSpec("name", "string"),
            "role": FieldSpec("role", "string"),
            "organizationId": FieldSpec("organizationId", "string", reference_type="organization"),
        },
    )

    # Abbreviation
    schemas["abbreviation"] = EntitySchema(
        entity_type="abbreviation",
        fields={
            "abbreviation": FieldSpec("abbreviation", "string", required=True),
            "expansion": FieldSpec("expansion", "string", required=True),
        },
    )

    # Study Definition Document
    schemas["study_definition_document"] = EntitySchema(
        entity_type="study_definition_document",
        fields={
            "name": FieldSpec("name", "string"),
            "version": FieldSpec("version", "string"),
        },
    )

    # Document Content Reference
    schemas["document_content_reference"] = EntitySchema(
        entity_type="document_content_reference",
        fields={
            "name": FieldSpec("name", "string"),
            "sectionNumber": FieldSpec("sectionNumber", "string"),
        },
    )

    return schemas


USDM_V4_SCHEMA: Dict[str, EntitySchema] = _build_usdm_v4_schema()


# ---------------------------------------------------------------------------
# CDISC CORE Conformance Checker (mockable interface)
# ---------------------------------------------------------------------------

class CDISCCOREChecker:
    """
    CDISC CORE conformance checking.

    Implements key USDM v4.0 conformance rules. In production this can also
    delegate to the real CDISC CORE engine (tools/core/core.exe) if installed.
    For testing it can be replaced with a mock.
    """

    def __init__(self, core_engine_path: Optional[str] = None):
        self._core_engine_path = core_engine_path

    def check_conformance(self, usdm_data: Dict[str, Any]) -> List[ValidationIssue]:
        """Run CDISC CORE rules and return issues found."""
        issues: List[ValidationIssue] = []
        entities = usdm_data.get("entities", [])

        # Rule 1: Study must have at least one identifier
        has_identifier = any(
            e.get("entity_type") == "study_identifier" for e in entities
        )
        if not has_identifier:
            issues.append(ValidationIssue(
                issue_id=f"core_{uuid.uuid4().hex[:8]}",
                severity=ValidationSeverity.ERROR,
                category="core",
                entity_id="study",
                entity_type="study",
                field_name="identifiers",
                message="CDISC CORE: Study must have at least one study identifier",
                suggestion="Add a study identifier (e.g. NCT number)",
            ))

        # Rule 2: All objectives should have at least one endpoint
        objectives = [e for e in entities if e.get("entity_type") == "objective"]
        for obj in objectives:
            data = obj.get("data", {})
            endpoint_ids = data.get("endpointIds", [])
            if not endpoint_ids:
                issues.append(ValidationIssue(
                    issue_id=f"core_{uuid.uuid4().hex[:8]}",
                    severity=ValidationSeverity.WARNING,
                    category="core",
                    entity_id=obj.get("id", "unknown"),
                    entity_type="objective",
                    field_name="endpointIds",
                    message="CDISC CORE: Objective should have at least one linked endpoint",
                    suggestion="Link endpoints to this objective",
                ))

        # Rule 3: Study arms should have a type
        arms = [e for e in entities if e.get("entity_type") == "study_arm"]
        for arm in arms:
            data = arm.get("data", {})
            if not data.get("type"):
                issues.append(ValidationIssue(
                    issue_id=f"core_{uuid.uuid4().hex[:8]}",
                    severity=ValidationSeverity.INFO,
                    category="core",
                    entity_id=arm.get("id", "unknown"),
                    entity_type="study_arm",
                    field_name="type",
                    message="CDISC CORE: Study arm should specify a type (e.g. experimental, control)",
                    suggestion="Set arm type to a standard value",
                ))

        # Rule 4: Activities must have a name
        activities = [e for e in entities if e.get("entity_type") == "activity"]
        for act in activities:
            data = act.get("data", {})
            if not data.get("name"):
                issues.append(ValidationIssue(
                    issue_id=f"core_{uuid.uuid4().hex[:8]}",
                    severity=ValidationSeverity.ERROR,
                    category="core",
                    entity_id=act.get("id", "unknown"),
                    entity_type="activity",
                    field_name="name",
                    message="CDISC CORE: Activity must have a name",
                    suggestion="Provide a name for this activity",
                ))

        # Rule 5: Encounters must have a name
        encounters = [e for e in entities if e.get("entity_type") == "encounter"]
        for enc in encounters:
            data = enc.get("data", {})
            if not data.get("name"):
                issues.append(ValidationIssue(
                    issue_id=f"core_{uuid.uuid4().hex[:8]}",
                    severity=ValidationSeverity.ERROR,
                    category="core",
                    entity_id=enc.get("id", "unknown"),
                    entity_type="encounter",
                    field_name="name",
                    message="CDISC CORE: Encounter must have a name",
                    suggestion="Provide a name for this encounter",
                ))

        # Rule 6: Epochs must have a name
        epochs = [e for e in entities if e.get("entity_type") == "epoch"]
        for ep in epochs:
            data = ep.get("data", {})
            if not data.get("name"):
                issues.append(ValidationIssue(
                    issue_id=f"core_{uuid.uuid4().hex[:8]}",
                    severity=ValidationSeverity.ERROR,
                    category="core",
                    entity_id=ep.get("id", "unknown"),
                    entity_type="epoch",
                    field_name="name",
                    message="CDISC CORE: Epoch must have a name",
                    suggestion="Provide a name for this epoch",
                ))

        # Rule 7: Eligibility criteria must have a category (inclusion/exclusion)
        criteria = [e for e in entities if e.get("entity_type") == "eligibility_criterion"]
        for crit in criteria:
            data = crit.get("data", {})
            cat = data.get("category", "")
            # category may be a USDM Code object dict
            # e.g. {"code": "Inclusion", "codeSystem": "USDM", "decode": "Inclusion"}
            if isinstance(cat, dict):
                cat = cat.get("decode") or cat.get("code") or ""
            # cat may also be a stringified dict from a prior coercion — try to parse
            if isinstance(cat, str) and cat.startswith("{") and "decode" in cat:
                try:
                    import ast
                    parsed = ast.literal_eval(cat)
                    if isinstance(parsed, dict):
                        cat = parsed.get("decode") or parsed.get("code") or cat
                except (ValueError, SyntaxError):
                    pass
            if cat and isinstance(cat, str) and cat.lower() not in ("inclusion", "exclusion"):
                issues.append(ValidationIssue(
                    issue_id=f"core_{uuid.uuid4().hex[:8]}",
                    severity=ValidationSeverity.WARNING,
                    category="core",
                    entity_id=crit.get("id", "unknown"),
                    entity_type="eligibility_criterion",
                    field_name="category",
                    message=f"CDISC CORE: Eligibility criterion category '{cat}' should be 'inclusion' or 'exclusion'",
                    suggestion="Set category to 'inclusion' or 'exclusion'",
                ))

        # Rule 8: Scheduled instances must reference valid encounters and activities
        scheduled = [e for e in entities if e.get("entity_type") == "scheduled_instance"]
        known_ids = {e.get("id") for e in entities if e.get("id")}
        for si in scheduled:
            data = si.get("data", {})
            enc_id = data.get("encounterId")
            if enc_id and enc_id not in known_ids:
                issues.append(ValidationIssue(
                    issue_id=f"core_{uuid.uuid4().hex[:8]}",
                    severity=ValidationSeverity.ERROR,
                    category="core",
                    entity_id=si.get("id", "unknown"),
                    entity_type="scheduled_instance",
                    field_name="encounterId",
                    message=f"CDISC CORE: Scheduled instance references unknown encounter '{enc_id}'",
                    suggestion="Ensure the referenced encounter exists",
                ))
            act_ids = data.get("activityIds", [])
            for aid in act_ids:
                if aid and aid not in known_ids:
                    issues.append(ValidationIssue(
                        issue_id=f"core_{uuid.uuid4().hex[:8]}",
                        severity=ValidationSeverity.ERROR,
                        category="core",
                        entity_id=si.get("id", "unknown"),
                        entity_type="scheduled_instance",
                        field_name="activityIds",
                        message=f"CDISC CORE: Scheduled instance references unknown activity '{aid}'",
                        suggestion="Ensure the referenced activity exists",
                    ))

        # Rule 9: No duplicate entity IDs
        seen_ids: Dict[str, str] = {}
        for e in entities:
            eid = e.get("id", "")
            if not eid:
                continue
            if eid in seen_ids:
                issues.append(ValidationIssue(
                    issue_id=f"core_{uuid.uuid4().hex[:8]}",
                    severity=ValidationSeverity.ERROR,
                    category="core",
                    entity_id=eid,
                    entity_type=e.get("entity_type", ""),
                    field_name="id",
                    message=f"CDISC CORE: Duplicate entity ID '{eid}' (also used by {seen_ids[eid]})",
                    suggestion="Ensure all entity IDs are unique",
                ))
            else:
                seen_ids[eid] = e.get("entity_type", "")

        return issues

    # CDISC CORE rule IDs that indicate critical structural problems → ERROR
    _CORE_ERROR_RULES: set = {
        "DDF00012",  # Missing main timeline
        "DDF00010",  # Duplicate names
        "DDF00041",  # No primary endpoint
        "DDF00172",  # No sponsor identifier
        "DDF00201",  # No sponsor role
        "DDF00101",  # Interventional but no intervention
    }

    # CDISC CORE rule IDs for schema/attribute issues → WARNING
    _CORE_WARNING_RULES: set = {
        "DDF00125",  # Schema attribute violations
        "DDF00081",  # Relationship violations
        "DDF00035",  # Code/decode mismatch
        "DDF00155",  # Invalid CT version date
        "DDF00147",  # Invalid codelist usage
        "DDF00263",  # Activity missing references
        "DDF00261",  # Geographic scope issue
    }

    def run_core_engine(self, usdm_json_path: str, output_dir: str) -> Optional[Dict[str, Any]]:
        """
        Run the real CDISC CORE engine if installed.

        Returns conformance report dict, or None if engine not available.
        The report follows the CORE engine v0.14.1 JSON format with keys:
        Conformance_Details, Entity_Details, Issue_Summary, Issue_Details, Rules_Report.
        """
        import subprocess
        from pathlib import Path

        engine_path = Path(self._core_engine_path) if self._core_engine_path else Path("tools/core/core/core/core.exe")
        if not engine_path.exists():
            logger.info("CDISC CORE engine not installed, using built-in rules only")
            return None

        output_path = Path(output_dir) / "conformance_report"
        try:
            result = subprocess.run(
                [str(engine_path), "validate", "-s", "usdm", "-v", "4-0",
                 "-dp", str(Path(usdm_json_path).absolute()),
                 "-o", str(output_path.absolute()), "-of", "JSON"],
                capture_output=True, text=True, cwd=str(engine_path.parent), timeout=3600
            )
            report_file = str(output_path) + ".json"
            if Path(report_file).exists():
                import json
                with open(report_file) as f:
                    return json.load(f)
            elif result.returncode != 0:
                logger.warning(f"CORE engine failed (rc={result.returncode}): {result.stderr[:200]}")
        except Exception as e:
            logger.warning(f"CORE engine error: {e}")
        return None

    def _parse_core_engine_report(self, report: Dict[str, Any]) -> List[ValidationIssue]:
        """
        Parse a CDISC CORE engine JSON report into ValidationIssue objects.

        The CORE engine v0.14.1 report has:
        - Issue_Summary: aggregated counts per rule
        - Issue_Details: individual findings with core_id, cdisc_rule_id,
          message, executability, entity, instance_id, path, attributes, values
        - Rules_Report: all 207 rules with status (PASSED/FAILED/SKIPPED)
        """
        issues: List[ValidationIssue] = []
        for detail in report.get("Issue_Details", []):
            rule_id = detail.get("cdisc_rule_id", "")
            core_id = detail.get("core_id", "")

            # Derive severity from rule ID
            if rule_id in self._CORE_ERROR_RULES:
                severity = ValidationSeverity.ERROR
            elif rule_id in self._CORE_WARNING_RULES:
                severity = ValidationSeverity.WARNING
            else:
                severity = ValidationSeverity.INFO

            entity_type = detail.get("entity", "unknown") or "unknown"
            instance_id = detail.get("instance_id", "unknown") or "unknown"
            path = detail.get("path", "")
            message = detail.get("message", "")

            # Build a descriptive field from attributes/values
            attrs = detail.get("attributes", [])
            vals = detail.get("values", [])
            detail_str = ""
            if attrs and vals:
                # First value often has the specific error detail
                detail_str = "; ".join(
                    f"{a}={v}" for a, v in zip(attrs[:3], vals[:3])
                    if v and v != "null"
                )

            issues.append(ValidationIssue(
                issue_id=f"core_ext_{uuid.uuid4().hex[:8]}",
                severity=severity,
                category="core_engine",
                entity_id=str(instance_id),
                entity_type=entity_type,
                field_name=path,
                message=f"CDISC CORE [{core_id}/{rule_id}]: {message}",
                suggestion=detail_str if detail_str else f"See CDISC rule {rule_id}",
            ))
        return issues


# ---------------------------------------------------------------------------
# ValidationAgent
# ---------------------------------------------------------------------------

class ValidationAgent(BaseAgent):
    """
    Validates extracted USDM data for schema compliance, entity reference
    integrity, and CDISC CORE conformance.

    Capabilities:
    - USDM v4.0 schema validation (required fields, data types, cardinality)
    - Entity reference validation (all IDs resolve)
    - CDISC CORE conformance checking
    - Automatic fixes for common violations
    - Provenance updates when fixes are applied
    - Validation report generation
    - Iterative validation (re-validate after fixes)
    """

    def __init__(
        self,
        agent_id: str = "validation_agent",
        config: Optional[Dict[str, Any]] = None,
        core_checker: Optional[CDISCCOREChecker] = None,
    ):
        super().__init__(agent_id=agent_id, config=config or {})
        self._schema = USDM_V4_SCHEMA
        core_engine_path = (config or {}).get("core_engine_path")
        self._core_checker = core_checker or CDISCCOREChecker(core_engine_path=core_engine_path)
        self._reports: List[ValidationReport] = []
        self._auto_fix_enabled: bool = (config or {}).get("auto_fix", True)
        self._max_iterations: int = (config or {}).get("max_iterations", 3)
        # Paths for external CDISC CORE engine (set during execute)
        self._usdm_json_path: Optional[str] = None
        self._output_dir: Optional[str] = None

    # --- Lifecycle ---

    def initialize(self) -> None:
        self.set_state(AgentState.READY)
        self._logger.info(f"[{self.agent_id}] Initialized with {len(self._schema)} entity schemas")

    def terminate(self) -> None:
        self.set_state(AgentState.TERMINATED)

    def get_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            agent_type="validation",
            input_types=["context_data", "usdm_output"],
            output_types=["validation_report"],
            dependencies=["execution_extraction"],
            supports_parallel=False,
            timeout_seconds=120,
        )


    # --- Main execution ---

    def execute(self, task: AgentTask) -> AgentResult:
        """
        Validate USDM data provided in the task.

        Input data can be:
        - "entities": list of entity dicts (from Context Store or direct)
        - "context_store": a ContextStore instance
        - "auto_fix": bool override for this run
        - "max_iterations": int override for this run
        """
        entities_data = task.input_data.get("entities", [])
        context_store: Optional[ContextStore] = task.input_data.get("context_store") or self._context_store
        auto_fix = task.input_data.get("auto_fix", self._auto_fix_enabled)
        max_iterations = task.input_data.get("max_iterations", self._max_iterations)

        # Paths for external CDISC CORE engine validation
        self._usdm_json_path = task.input_data.get("usdm_json_path")
        self._output_dir = task.input_data.get("output_dir")

        # If a context store is provided but no entities list, pull from store
        if not entities_data and context_store:
            entities_data = self._entities_from_store(context_store)

        if not entities_data:
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=False,
                error="No entities provided for validation",
            )

        # Iterative validation loop
        all_fixes: List[AutoFix] = []
        iteration = 0
        final_report: Optional[ValidationReport] = None

        for iteration in range(1, max_iterations + 1):
            issues = self._run_all_validations(entities_data, context_store)
            fixes: List[AutoFix] = []

            if auto_fix and issues:
                entities_data, fixes = self._apply_auto_fixes(entities_data, issues, context_store)
                all_fixes.extend(fixes)

            # Build report for this iteration
            report = ValidationReport(
                report_id=f"vr_{uuid.uuid4().hex[:8]}",
                timestamp=datetime.now(),
                total_entities=len(entities_data),
                issues=issues if not fixes else self._run_all_validations(entities_data, context_store),
                fixes_applied=fixes,
                iteration=iteration,
            )
            self._reports.append(report)
            final_report = report

            # Stop iterating if no fixes were applied (nothing more to improve)
            if not fixes:
                break

        report_dict = final_report.to_dict() if final_report else {}

        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            success=True,
            data={
                "validation_report": report_dict,
                "is_valid": final_report.is_valid if final_report else False,
                "total_issues": len(final_report.issues) if final_report else 0,
                "errors": final_report.error_count if final_report else 0,
                "warnings": final_report.warning_count if final_report else 0,
                "info": final_report.info_count if final_report else 0,
                "fixes_applied": len(all_fixes),
                "iterations": iteration,
            },
            confidence_score=1.0 if (final_report and final_report.is_valid) else 0.5,
        )

    # --- Helpers to pull entities from Context Store ---

    @staticmethod
    def _entities_from_store(store: ContextStore) -> List[Dict[str, Any]]:
        """Convert Context Store entities to the list-of-dicts format used internally."""
        result: List[Dict[str, Any]] = []
        for entity in store.query_entities():
            result.append({
                "id": entity.id,
                "entity_type": entity.entity_type,
                "data": entity.data,
                "relationships": entity.relationships,
            })
        return result

    # --- Validation orchestration ---

    def _run_all_validations(
        self,
        entities: List[Dict[str, Any]],
        context_store: Optional[ContextStore] = None,
    ) -> List[ValidationIssue]:
        """Run all validation checks and return combined issues."""
        issues: List[ValidationIssue] = []
        issues.extend(self.validate_schema(entities))
        issues.extend(self.validate_entity_references(entities, context_store))
        issues.extend(self.check_cdisc_core(entities))

        # Run external CDISC CORE engine if available
        usdm_json_path = self._usdm_json_path
        output_dir = self._output_dir
        if usdm_json_path and output_dir:
            engine_report = self._core_checker.run_core_engine(usdm_json_path, output_dir)
            if engine_report:
                issues.extend(self._core_checker._parse_core_engine_report(engine_report))

        return issues


    # ------------------------------------------------------------------
    # 1. Schema validation (required fields, data types, cardinality)
    # ------------------------------------------------------------------

    def validate_schema(self, entities: List[Dict[str, Any]]) -> List[ValidationIssue]:
        """Validate entities against USDM v4.0 schema definitions."""
        # Internal entity types that are not part of USDM — skip silently
        _INTERNAL_TYPES = {"pdf_page"}

        issues: List[ValidationIssue] = []
        for entity in entities:
            etype = entity.get("entity_type", "")
            eid = entity.get("id", "unknown")
            data = entity.get("data", {})

            if etype in _INTERNAL_TYPES:
                continue

            schema = self._schema.get(etype)
            if not schema:
                # Unknown entity type – info-level
                issues.append(ValidationIssue(
                    issue_id=f"schema_{uuid.uuid4().hex[:8]}",
                    severity=ValidationSeverity.INFO,
                    category="schema",
                    entity_id=eid,
                    entity_type=etype,
                    field_name="entity_type",
                    message=f"No schema definition for entity type '{etype}'",
                    suggestion="Verify entity type is a valid USDM v4.0 type",
                ))
                continue

            for field_name, spec in schema.fields.items():
                value = data.get(field_name)

                # Required field check
                # For list fields with min_cardinality, empty lists are
                # reported as cardinality violations rather than required-field.
                is_empty_list = spec.data_type == "list" and isinstance(value, list) and len(value) == 0
                if spec.required and (value is None or value == ""):
                    issues.append(ValidationIssue(
                        issue_id=f"req_{uuid.uuid4().hex[:8]}",
                        severity=ValidationSeverity.ERROR,
                        category="required_field",
                        entity_id=eid,
                        entity_type=etype,
                        field_name=field_name,
                        message=f"Required field '{field_name}' is missing or empty",
                        suggestion=f"Provide a value for '{field_name}'",
                        auto_fixable=self._can_auto_fix_required(field_name, etype),
                    ))
                    continue
                elif spec.required and is_empty_list and spec.min_cardinality:
                    # Will be caught by cardinality check below
                    pass
                elif spec.required and is_empty_list:
                    issues.append(ValidationIssue(
                        issue_id=f"req_{uuid.uuid4().hex[:8]}",
                        severity=ValidationSeverity.ERROR,
                        category="required_field",
                        entity_id=eid,
                        entity_type=etype,
                        field_name=field_name,
                        message=f"Required field '{field_name}' is missing or empty",
                        suggestion=f"Provide a value for '{field_name}'",
                        auto_fixable=self._can_auto_fix_required(field_name, etype),
                    ))
                    continue

                if value is None:
                    continue

                # Data type check
                # USDM Code objects (dicts with code/decode) are accepted for
                # string fields — they carry coded terminology values.
                expected = _PYTHON_TYPE_MAP.get(spec.data_type)
                if expected and not isinstance(value, expected):
                    # Allow dict Code objects for string-typed fields
                    if spec.data_type == "string" and isinstance(value, dict):
                        pass  # Code object — acceptable
                    else:
                        issues.append(ValidationIssue(
                            issue_id=f"type_{uuid.uuid4().hex[:8]}",
                            severity=ValidationSeverity.ERROR,
                            category="data_type",
                            entity_id=eid,
                            entity_type=etype,
                            field_name=field_name,
                            message=(
                                f"Field '{field_name}' expected type '{spec.data_type}' "
                                f"but got '{type(value).__name__}'"
                            ),
                            suggestion=f"Convert '{field_name}' to {spec.data_type}",
                            auto_fixable=spec.data_type == "string",
                        ))

                # Cardinality check (for list fields)
                if spec.data_type == "list" and isinstance(value, list):
                    if spec.min_cardinality and len(value) < spec.min_cardinality:
                        issues.append(ValidationIssue(
                            issue_id=f"card_{uuid.uuid4().hex[:8]}",
                            severity=ValidationSeverity.ERROR,
                            category="cardinality",
                            entity_id=eid,
                            entity_type=etype,
                            field_name=field_name,
                            message=(
                                f"Field '{field_name}' has {len(value)} items, "
                                f"minimum is {spec.min_cardinality}"
                            ),
                            suggestion=f"Add at least {spec.min_cardinality - len(value)} more item(s)",
                        ))
                    if spec.max_cardinality is not None and len(value) > spec.max_cardinality:
                        issues.append(ValidationIssue(
                            issue_id=f"card_{uuid.uuid4().hex[:8]}",
                            severity=ValidationSeverity.WARNING,
                            category="cardinality",
                            entity_id=eid,
                            entity_type=etype,
                            field_name=field_name,
                            message=(
                                f"Field '{field_name}' has {len(value)} items, "
                                f"maximum is {spec.max_cardinality}"
                            ),
                            suggestion=f"Remove excess items (max {spec.max_cardinality})",
                        ))
        return issues

    @staticmethod
    def _can_auto_fix_required(field_name: str, entity_type: str) -> bool:
        """Determine if a missing required field can be auto-fixed with a default."""
        # Fields where we can safely provide a default
        auto_fixable_defaults = {
            ("study_title", "type"): True,
            ("eligibility_criterion", "category"): True,
            ("objective", "level"): True,
            ("timing", "type"): True,
        }
        return auto_fixable_defaults.get((entity_type, field_name), False)

    # ------------------------------------------------------------------
    # 2. Entity reference validation
    # ------------------------------------------------------------------

    def validate_entity_references(
        self,
        entities: List[Dict[str, Any]],
        context_store: Optional[ContextStore] = None,
    ) -> List[ValidationIssue]:
        """Validate that all entity ID references resolve to existing entities."""
        issues: List[ValidationIssue] = []

        # Build set of all known entity IDs
        known_ids: Set[str] = set()
        for entity in entities:
            eid = entity.get("id")
            if eid:
                known_ids.add(eid)

        # Also include IDs from context store if available
        if context_store:
            for entity in context_store.query_entities():
                known_ids.add(entity.id)

        # Check reference fields
        for entity in entities:
            etype = entity.get("entity_type", "")
            eid = entity.get("id", "unknown")
            data = entity.get("data", {})
            schema = self._schema.get(etype)
            if not schema:
                continue

            for field_name, spec in schema.fields.items():
                if not spec.reference_type:
                    continue

                value = data.get(field_name)
                if value is None:
                    continue

                # Single reference (string ID)
                if isinstance(value, str) and value:
                    if value not in known_ids:
                        issues.append(ValidationIssue(
                            issue_id=f"ref_{uuid.uuid4().hex[:8]}",
                            severity=ValidationSeverity.ERROR,
                            category="reference",
                            entity_id=eid,
                            entity_type=etype,
                            field_name=field_name,
                            message=(
                                f"Reference '{value}' in field '{field_name}' "
                                f"does not resolve to any known entity"
                            ),
                            suggestion=f"Ensure referenced {spec.reference_type} entity exists",
                        ))

                # List of references
                elif isinstance(value, list):
                    for ref_id in value:
                        if isinstance(ref_id, str) and ref_id and ref_id not in known_ids:
                            issues.append(ValidationIssue(
                                issue_id=f"ref_{uuid.uuid4().hex[:8]}",
                                severity=ValidationSeverity.ERROR,
                                category="reference",
                                entity_id=eid,
                                entity_type=etype,
                                field_name=field_name,
                                message=(
                                    f"Reference '{ref_id}' in field '{field_name}' "
                                    f"does not resolve to any known entity"
                                ),
                                suggestion=f"Ensure referenced {spec.reference_type} entity exists",
                            ))

        return issues

    # ------------------------------------------------------------------
    # 3. CDISC CORE conformance
    # ------------------------------------------------------------------

    def check_cdisc_core(self, entities: List[Dict[str, Any]]) -> List[ValidationIssue]:
        """Run CDISC CORE conformance rules via the checker."""
        return self._core_checker.check_conformance({"entities": entities})

    # ------------------------------------------------------------------
    # 4. OpenAPI schema validation (real USDM v4.0 spec)
    # ------------------------------------------------------------------

    def validate_openapi_schema(
        self, usdm_json: Dict[str, Any], component_name: str = "Wrapper-Input"
    ) -> List[ValidationIssue]:
        """
        Validate USDM JSON against the real USDM v4.0 OpenAPI schema.

        This uses the official USDM_API.json schema file if available,
        falling back gracefully if the schema file or validator library
        is not installed.

        Args:
            usdm_json: The complete USDM Wrapper-Input JSON
            component_name: OpenAPI component to validate against

        Returns:
            List of validation issues found
        """
        issues: List[ValidationIssue] = []

        try:
            from openapi_schema_validator import OAS31Validator
        except ImportError:
            logger.info("openapi-schema-validator not installed, skipping OpenAPI validation")
            return issues

        # Try to find the USDM schema file
        import os
        import json as json_mod
        schema_paths = [
            os.path.join("archive", "tests_legacy", "USDM OpenAPI schema", "USDM_API.json"),
            os.path.join("USDM OpenAPI schema", "USDM_API.json"),
            os.path.join("schema", "USDM_API.json"),
        ]

        usdm_schema = None
        for path in schema_paths:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        usdm_schema = json_mod.load(f)
                    break
                except Exception:
                    continue

        if not usdm_schema:
            logger.info("USDM OpenAPI schema file not found, skipping OpenAPI validation")
            return issues

        try:
            # Ensure Study-Input stub exists to prevent resolution errors
            schemas = usdm_schema.setdefault("components", {}).setdefault("schemas", {})
            if "Study-Input" not in schemas:
                schemas["Study-Input"] = {
                    "title": "Study (Stub)",
                    "type": "object",
                    "description": "Stub to satisfy $ref",
                    "additionalProperties": True,
                }

            validation_schema = {
                "$ref": f"#/components/schemas/{component_name}",
                "components": usdm_schema.get("components", {}),
            }

            validator = OAS31Validator(validation_schema)
            errors = list(validator.iter_errors(usdm_json))

            for error in errors[:50]:  # Cap at 50 to avoid flooding
                path_str = ".".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"
                issues.append(ValidationIssue(
                    issue_id=f"openapi_{uuid.uuid4().hex[:8]}",
                    severity=ValidationSeverity.WARNING,
                    category="openapi_schema",
                    entity_id=path_str,
                    entity_type="usdm_document",
                    field_name=path_str,
                    message=f"OpenAPI schema: {error.message[:200]}",
                    suggestion="Fix the USDM structure to match the official schema",
                ))

        except Exception as e:
            logger.warning(f"OpenAPI schema validation failed: {e}")

        return issues


    # ------------------------------------------------------------------
    # 4. Automatic fixes for common violations
    # ------------------------------------------------------------------

    def _apply_auto_fixes(
        self,
        entities: List[Dict[str, Any]],
        issues: List[ValidationIssue],
        context_store: Optional[ContextStore] = None,
    ) -> Tuple[List[Dict[str, Any]], List[AutoFix]]:
        """
        Apply automatic fixes for auto_fixable issues.
        Returns the updated entities list and a list of fixes applied.
        Provenance is updated when fixes are applied.
        """
        fixes: List[AutoFix] = []
        # Index entities by id for quick lookup
        entity_map: Dict[str, Dict[str, Any]] = {e["id"]: e for e in entities if "id" in e}

        for issue in issues:
            if not issue.auto_fixable:
                continue

            entity = entity_map.get(issue.entity_id)
            if not entity:
                continue

            data = entity.setdefault("data", {})
            old_value = data.get(issue.field_name)
            new_value = None

            if issue.category == "required_field":
                new_value = self._default_for_required(issue.entity_type, issue.field_name)
            elif issue.category == "data_type":
                new_value = self._coerce_type(old_value, issue.field_name, issue.entity_type)

            if new_value is not None:
                data[issue.field_name] = new_value
                fix = AutoFix(
                    fix_id=f"fix_{uuid.uuid4().hex[:8]}",
                    entity_id=issue.entity_id,
                    field_name=issue.field_name,
                    old_value=old_value,
                    new_value=new_value,
                    reason=f"Auto-fix for {issue.category}: {issue.message}",
                )
                fixes.append(fix)

                # Update provenance in context store
                self._update_provenance_for_fix(issue.entity_id, fix, context_store)

        return entities, fixes

    @staticmethod
    def _default_for_required(entity_type: str, field_name: str) -> Optional[Any]:
        """Return a sensible default value for a missing required field."""
        defaults: Dict[Tuple[str, str], Any] = {
            ("study_title", "type"): "Official Study Title",
            ("eligibility_criterion", "category"): "inclusion",
            ("objective", "level"): "primary",
            ("timing", "type"): "scheduled",
        }
        return defaults.get((entity_type, field_name))

    @staticmethod
    def _coerce_type(value: Any, field_name: str, entity_type: str) -> Optional[str]:
        """Attempt to coerce a value to string (the most common auto-fix).

        For dict values that look like USDM Code objects, extract the
        meaningful text (decode or code) instead of blindly calling str().
        """
        if value is None:
            return None
        if isinstance(value, dict):
            # USDM Code objects have decode/code — use that instead of repr
            decoded = value.get("decode") or value.get("code")
            if decoded is not None:
                return str(decoded)
        return str(value)

    def _update_provenance_for_fix(
        self,
        entity_id: str,
        fix: AutoFix,
        context_store: Optional[ContextStore] = None,
    ) -> None:
        """Update provenance metadata when an automatic fix is applied."""
        if not context_store:
            return
        try:
            entity = context_store.get_entity(entity_id)
            if entity:
                # Record the fix in the entity data under a provenance key
                fix_record = {
                    "fix_id": fix.fix_id,
                    "field": fix.field_name,
                    "old_value": fix.old_value,
                    "new_value": fix.new_value,
                    "reason": fix.reason,
                    "agent_id": self.agent_id,
                    "timestamp": fix.timestamp.isoformat(),
                }
                existing_fixes = entity.data.get("_validation_fixes", [])
                existing_fixes.append(fix_record)
                context_store.update_entity(
                    entity_id,
                    {
                        fix.field_name: fix.new_value,
                        "_validation_fixes": existing_fixes,
                    },
                    agent_id=self.agent_id,
                )
        except (KeyError, ValueError) as exc:
            self._logger.warning(
                f"[{self.agent_id}] Could not update provenance for entity {entity_id}: {exc}"
            )

    # ------------------------------------------------------------------
    # 5. Validation report generation
    # ------------------------------------------------------------------

    def generate_report(
        self,
        entities: List[Dict[str, Any]],
        context_store: Optional[ContextStore] = None,
    ) -> ValidationReport:
        """
        Run full validation and return a ValidationReport.
        This is a convenience method for direct use outside of task execution.
        """
        issues = self._run_all_validations(entities, context_store)
        return ValidationReport(
            report_id=f"vr_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now(),
            total_entities=len(entities),
            issues=issues,
            fixes_applied=[],
        )

    def get_reports(self) -> List[ValidationReport]:
        """Return all reports generated during this agent's lifetime."""
        return list(self._reports)

    # ------------------------------------------------------------------
    # 6. Iterative validation support
    # ------------------------------------------------------------------

    def validate_iteratively(
        self,
        entities: List[Dict[str, Any]],
        context_store: Optional[ContextStore] = None,
        max_iterations: Optional[int] = None,
    ) -> ValidationReport:
        """
        Run validation with automatic fixes in a loop until no more
        fixes can be applied or max_iterations is reached.
        """
        max_iter = max_iterations or self._max_iterations
        all_fixes: List[AutoFix] = []
        final_issues: List[ValidationIssue] = []

        for iteration in range(1, max_iter + 1):
            issues = self._run_all_validations(entities, context_store)
            if not self._auto_fix_enabled:
                final_issues = issues
                break

            fixable = [i for i in issues if i.auto_fixable]
            if not fixable:
                final_issues = issues
                break

            entities, fixes = self._apply_auto_fixes(entities, issues, context_store)
            all_fixes.extend(fixes)

            if not fixes:
                final_issues = issues
                break

            # Re-validate after fixes
            final_issues = self._run_all_validations(entities, context_store)

        report = ValidationReport(
            report_id=f"vr_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now(),
            total_entities=len(entities),
            issues=final_issues,
            fixes_applied=all_fixes,
            iteration=iteration,
        )
        self._reports.append(report)
        return report
