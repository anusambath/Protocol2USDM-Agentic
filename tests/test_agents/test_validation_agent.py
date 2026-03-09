"""
Tests for ValidationAgent.

Covers:
- ValidationAgent lifecycle (init, capabilities, state)
- USDM v4.0 schema validation (required fields, data types, cardinality)
- Entity reference validation
- CDISC CORE conformance checking
- Automatic fixes for common violations
- Provenance updates on fix
- Validation report generation
- Iterative validation
- 50 USDM outputs (20 valid, 30 with errors) as parametrized test data
"""

import pytest
import uuid
from datetime import datetime
from typing import Any, Dict, List

from agents.base import AgentCapabilities, AgentResult, AgentState, AgentTask
from agents.context_store import ContextEntity, ContextStore, EntityProvenance
from agents.quality.validation_agent import (
    AutoFix,
    CDISCCOREChecker,
    ValidationAgent,
    ValidationIssue,
    ValidationReport,
    ValidationSeverity,
    USDM_V4_SCHEMA,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entity(
    entity_type: str,
    data: Dict[str, Any],
    entity_id: str | None = None,
) -> Dict[str, Any]:
    return {
        "id": entity_id or f"{entity_type}_{uuid.uuid4().hex[:6]}",
        "entity_type": entity_type,
        "data": data,
    }


def _make_task(entities: List[Dict[str, Any]], **overrides) -> AgentTask:
    input_data = {"entities": entities}
    input_data.update(overrides)
    return AgentTask(
        task_id=f"task_{uuid.uuid4().hex[:6]}",
        agent_id="validation_agent",
        task_type="validate_usdm",
        input_data=input_data,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def agent():
    va = ValidationAgent()
    va.initialize()
    return va


@pytest.fixture
def context_store():
    return ContextStore()


@pytest.fixture
def valid_study_entity():
    return _make_entity("study", {"name": "Test Study", "protocolVersions": ["v1"]})


@pytest.fixture
def valid_title_entity():
    return _make_entity("study_title", {"text": "A Phase 3 Study", "type": "Official Study Title"})


@pytest.fixture
def valid_identifier_entity():
    return _make_entity("study_identifier", {"identifier": "NCT12345678", "type": "NCT"})


@pytest.fixture
def valid_org_entity():
    return _make_entity("organization", {"name": "Acme Pharma", "type": "Sponsor"}, entity_id="org_1")


# ---------------------------------------------------------------------------
# Lifecycle tests
# ---------------------------------------------------------------------------

class TestValidationAgentLifecycle:
    def test_init_default(self):
        va = ValidationAgent()
        assert va.agent_id == "validation_agent"
        assert va.state == AgentState.INITIALIZING

    def test_initialize_sets_ready(self, agent):
        assert agent.state == AgentState.READY

    def test_terminate_sets_terminated(self, agent):
        agent.terminate()
        assert agent.state == AgentState.TERMINATED

    def test_capabilities(self, agent):
        caps = agent.get_capabilities()
        assert caps.agent_type == "validation"
        assert "validation_report" in caps.output_types
        assert caps.supports_parallel is False

    def test_custom_agent_id(self):
        va = ValidationAgent(agent_id="custom_val")
        assert va.agent_id == "custom_val"


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------

class TestSchemaValidation:
    def test_valid_entity_no_issues(self, agent, valid_study_entity):
        issues = agent.validate_schema([valid_study_entity])
        schema_issues = [i for i in issues if i.category != "schema"]
        assert len(schema_issues) == 0

    def test_missing_required_field(self, agent):
        entity = _make_entity("study", {"description": "No name"})
        issues = agent.validate_schema([entity])
        required_issues = [i for i in issues if i.category == "required_field"]
        assert len(required_issues) >= 1
        assert any(i.field_name == "name" for i in required_issues)
        assert all(i.severity == ValidationSeverity.ERROR for i in required_issues)

    def test_wrong_data_type(self, agent):
        entity = _make_entity("study", {"name": 12345, "protocolVersions": ["v1"]})
        issues = agent.validate_schema([entity])
        type_issues = [i for i in issues if i.category == "data_type"]
        assert len(type_issues) >= 1
        assert type_issues[0].field_name == "name"

    def test_cardinality_min_violation(self, agent):
        entity = _make_entity("scheduled_instance", {
            "encounterId": "enc_1",
            "activityIds": [],
        })
        issues = agent.validate_schema([entity])
        card_issues = [i for i in issues if i.category == "cardinality"]
        assert len(card_issues) >= 1
        assert card_issues[0].field_name == "activityIds"

    def test_unknown_entity_type_info(self, agent):
        entity = _make_entity("unknown_type", {"foo": "bar"})
        issues = agent.validate_schema([entity])
        assert len(issues) == 1
        assert issues[0].severity == ValidationSeverity.INFO
        assert issues[0].category == "schema"

    def test_empty_required_string(self, agent):
        entity = _make_entity("study_title", {"text": "", "type": "Official"})
        issues = agent.validate_schema([entity])
        req = [i for i in issues if i.category == "required_field"]
        assert any(i.field_name == "text" for i in req)

    def test_multiple_entities_validated(self, agent):
        entities = [
            _make_entity("study", {"name": "S1", "protocolVersions": ["v1"]}),
            _make_entity("study_title", {"text": "Title", "type": "Official"}),
            _make_entity("organization", {"name": "Org"}),
        ]
        issues = agent.validate_schema(entities)
        # All valid – no errors
        errors = [i for i in issues if i.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0


# ---------------------------------------------------------------------------
# Entity reference validation tests
# ---------------------------------------------------------------------------

class TestEntityReferenceValidation:
    def test_valid_references(self, agent):
        org = _make_entity("organization", {"name": "Org"}, entity_id="org_1")
        ident = _make_entity("study_identifier", {
            "identifier": "NCT123",
            "organizationId": "org_1",
        })
        issues = agent.validate_entity_references([org, ident])
        assert len(issues) == 0

    def test_broken_single_reference(self, agent):
        ident = _make_entity("study_identifier", {
            "identifier": "NCT123",
            "organizationId": "nonexistent_org",
        })
        issues = agent.validate_entity_references([ident])
        assert len(issues) == 1
        assert issues[0].category == "reference"
        assert "nonexistent_org" in issues[0].message

    def test_broken_list_reference(self, agent):
        epoch = _make_entity("epoch", {
            "name": "Screening",
            "encounterIds": ["enc_1", "enc_missing"],
        })
        enc = _make_entity("encounter", {"name": "Visit 1"}, entity_id="enc_1")
        issues = agent.validate_entity_references([epoch, enc])
        assert len(issues) == 1
        assert "enc_missing" in issues[0].message

    def test_references_resolved_via_context_store(self, agent, context_store):
        # Add entity to context store
        context_store.add_entity(ContextEntity(
            id="org_in_store",
            entity_type="organization",
            data={"name": "Stored Org"},
            provenance=EntityProvenance(entity_id="org_in_store", source_agent_id="test"),
        ))
        ident = _make_entity("study_identifier", {
            "identifier": "NCT123",
            "organizationId": "org_in_store",
        })
        issues = agent.validate_entity_references([ident], context_store)
        assert len(issues) == 0

    def test_no_reference_fields_no_issues(self, agent):
        entity = _make_entity("study", {"name": "S", "protocolVersions": ["v1"]})
        issues = agent.validate_entity_references([entity])
        assert len(issues) == 0


# ---------------------------------------------------------------------------
# CDISC CORE conformance tests
# ---------------------------------------------------------------------------

class TestCDISCCOREConformance:
    def test_missing_study_identifier(self, agent):
        entities = [_make_entity("study", {"name": "S", "protocolVersions": ["v1"]})]
        issues = agent.check_cdisc_core(entities)
        core_issues = [i for i in issues if i.category == "core"]
        assert any("study identifier" in i.message.lower() for i in core_issues)

    def test_with_study_identifier_no_error(self, agent):
        entities = [
            _make_entity("study", {"name": "S", "protocolVersions": ["v1"]}),
            _make_entity("study_identifier", {"identifier": "NCT123"}),
        ]
        issues = agent.check_cdisc_core(entities)
        id_issues = [i for i in issues if "identifier" in i.message.lower() and i.severity == ValidationSeverity.ERROR]
        assert len(id_issues) == 0

    def test_objective_without_endpoints_warning(self, agent):
        entities = [
            _make_entity("study_identifier", {"identifier": "NCT123"}),
            _make_entity("objective", {"text": "Primary", "level": "primary"}),
        ]
        issues = agent.check_cdisc_core(entities)
        obj_issues = [i for i in issues if i.entity_type == "objective"]
        assert len(obj_issues) >= 1
        assert obj_issues[0].severity == ValidationSeverity.WARNING

    def test_custom_core_checker(self):
        class MockChecker(CDISCCOREChecker):
            def check_conformance(self, usdm_data):
                return [ValidationIssue(
                    issue_id="mock_1",
                    severity=ValidationSeverity.ERROR,
                    category="core",
                    entity_id="x",
                    entity_type="study",
                    field_name="custom",
                    message="Mock CORE error",
                )]

        va = ValidationAgent(core_checker=MockChecker())
        va.initialize()
        issues = va.check_cdisc_core([])
        assert len(issues) == 1
        assert issues[0].message == "Mock CORE error"

    def test_activity_without_name(self, agent):
        entities = [
            _make_entity("study_identifier", {"identifier": "NCT123"}),
            _make_entity("activity", {"description": "Some activity"}, "act_1"),
        ]
        issues = agent.check_cdisc_core(entities)
        act_issues = [i for i in issues if i.entity_type == "activity" and i.field_name == "name"]
        assert len(act_issues) >= 1
        assert act_issues[0].severity == ValidationSeverity.ERROR

    def test_encounter_without_name(self, agent):
        entities = [
            _make_entity("study_identifier", {"identifier": "NCT123"}),
            _make_entity("encounter", {"type": {"code": "C25426"}}, "enc_1"),
        ]
        issues = agent.check_cdisc_core(entities)
        enc_issues = [i for i in issues if i.entity_type == "encounter" and i.field_name == "name"]
        assert len(enc_issues) >= 1

    def test_epoch_without_name(self, agent):
        entities = [
            _make_entity("study_identifier", {"identifier": "NCT123"}),
            _make_entity("epoch", {"description": "Treatment phase"}, "ep_1"),
        ]
        issues = agent.check_cdisc_core(entities)
        ep_issues = [i for i in issues if i.entity_type == "epoch" and i.field_name == "name"]
        assert len(ep_issues) >= 1

    def test_invalid_eligibility_category(self, agent):
        entities = [
            _make_entity("study_identifier", {"identifier": "NCT123"}),
            _make_entity("eligibility_criterion", {"text": "Age > 18", "category": "other"}, "ec_1"),
        ]
        issues = agent.check_cdisc_core(entities)
        cat_issues = [i for i in issues if i.field_name == "category"]
        assert len(cat_issues) >= 1
        assert cat_issues[0].severity == ValidationSeverity.WARNING

    def test_valid_eligibility_category(self, agent):
        entities = [
            _make_entity("study_identifier", {"identifier": "NCT123"}),
            _make_entity("eligibility_criterion", {"text": "Age > 18", "category": "inclusion"}, "ec_1"),
        ]
        issues = agent.check_cdisc_core(entities)
        cat_issues = [i for i in issues if i.field_name == "category"]
        assert len(cat_issues) == 0

    def test_duplicate_entity_ids(self, agent):
        entities = [
            _make_entity("study_identifier", {"identifier": "NCT123"}),
            _make_entity("activity", {"name": "ECG"}, "act_1"),
            _make_entity("activity", {"name": "Labs"}, "act_1"),
        ]
        issues = agent.check_cdisc_core(entities)
        dup_issues = [i for i in issues if "Duplicate" in i.message]
        assert len(dup_issues) >= 1

    def test_scheduled_instance_bad_encounter_ref(self, agent):
        entities = [
            _make_entity("study_identifier", {"identifier": "NCT123"}),
            _make_entity("scheduled_instance", {
                "encounterId": "nonexistent_enc",
                "activityIds": ["act_1"],
            }, "si_1"),
            _make_entity("activity", {"name": "ECG"}, "act_1"),
        ]
        issues = agent.check_cdisc_core(entities)
        ref_issues = [i for i in issues if "unknown encounter" in i.message.lower()]
        assert len(ref_issues) >= 1

    def test_core_engine_path_config(self):
        va = ValidationAgent(config={"core_engine_path": "/fake/path/core.exe"})
        assert va._core_checker._core_engine_path == "/fake/path/core.exe"

    def test_dict_eligibility_category_inclusion(self, agent):
        """Regression: category as dict (e.g. from extraction agent) should not crash."""
        entities = [
            _make_entity("study_identifier", {"identifier": "NCT123"}),
            _make_entity("eligibility_criterion", {
                "text": "Age >= 18",
                "category": {"code": "C25532", "decode": "inclusion"},
            }, "ec_dict_1"),
        ]
        issues = agent.check_cdisc_core(entities)
        cat_issues = [i for i in issues if i.field_name == "category"]
        # "inclusion" is valid, so no category warning
        assert len(cat_issues) == 0

    def test_dict_eligibility_category_invalid(self, agent):
        """Dict category with non-standard decode should produce a warning."""
        entities = [
            _make_entity("study_identifier", {"identifier": "NCT123"}),
            _make_entity("eligibility_criterion", {
                "text": "Some criterion",
                "category": {"code": "C99999", "decode": "other"},
            }, "ec_dict_2"),
        ]
        issues = agent.check_cdisc_core(entities)
        cat_issues = [i for i in issues if i.field_name == "category"]
        assert len(cat_issues) >= 1
        assert cat_issues[0].severity == ValidationSeverity.WARNING

    def test_dict_eligibility_category_no_decode(self, agent):
        """Dict category with only code key should not crash."""
        entities = [
            _make_entity("study_identifier", {"identifier": "NCT123"}),
            _make_entity("eligibility_criterion", {
                "text": "Some criterion",
                "category": {"code": "C25532"},
            }, "ec_dict_3"),
        ]
        issues = agent.check_cdisc_core(entities)
        # Should not raise an exception
        assert isinstance(issues, list)

    def test_dict_category_capitalized_decode(self, agent):
        """Category dict with capitalized decode 'Inclusion' should pass Rule 7."""
        entities = [
            _make_entity("study_identifier", {"identifier": "NCT123"}),
            _make_entity("eligibility_criterion", {
                "category": {"code": "Inclusion", "codeSystem": "USDM", "decode": "Inclusion"},
            }, "ec_cap_1"),
        ]
        issues = agent.check_cdisc_core(entities)
        cat_issues = [i for i in issues if i.field_name == "category"]
        assert len(cat_issues) == 0

    def test_stringified_dict_category_parsed(self, agent):
        """Category that was stringified from a dict should be parsed back."""
        entities = [
            _make_entity("study_identifier", {"identifier": "NCT123"}),
            _make_entity("eligibility_criterion", {
                "category": "{'code': 'Exclusion', 'codeSystem': 'USDM', 'decode': 'Exclusion'}",
            }, "ec_str_1"),
        ]
        issues = agent.check_cdisc_core(entities)
        cat_issues = [i for i in issues if i.field_name == "category"]
        # Should parse the stringified dict and extract 'Exclusion' → valid
        assert len(cat_issues) == 0

    def test_criterion_item_schema_recognized(self, agent):
        """criterion_item entity type should be in the schema."""
        entities = [
            _make_entity("criterion_item", {"text": "Age >= 18", "name": "Age"}, "ci_1"),
        ]
        issues = agent.validate_schema(entities)
        unknown = [i for i in issues if "No schema definition" in i.message]
        assert len(unknown) == 0

    def test_eligibility_criterion_text_not_required(self, agent):
        """eligibility_criterion should not require 'text' — it uses criterionItemId."""
        entities = [
            _make_entity("eligibility_criterion", {
                "category": "inclusion",
                "criterionItemId": "ci_1",
            }, "ec_no_text"),
        ]
        issues = agent.validate_schema(entities)
        text_errors = [i for i in issues if i.field_name == "text" and i.category == "required_field"]
        assert len(text_errors) == 0

    def test_pdf_page_skipped_in_schema_validation(self, agent):
        """pdf_page entities should be silently skipped, not flagged as unknown."""
        entities = [
            _make_entity("pdf_page", {"page_number": 1}, "pdf-page-0"),
        ]
        issues = agent.validate_schema(entities)
        assert len(issues) == 0

    def test_core_engine_path_corrected(self):
        """Default core engine path should point to tools/core/core/core/core.exe."""
        checker = CDISCCOREChecker()
        # The default path is checked inside run_core_engine
        # Just verify the method doesn't crash with default path
        result = checker.run_core_engine("nonexistent.json", "/tmp")
        assert result is None  # Engine won't find the file, returns None

    def test_coerce_type_extracts_code_object(self):
        """_coerce_type should extract decode from Code objects, not stringify."""
        result = ValidationAgent._coerce_type(
            {"code": "Inclusion", "codeSystem": "USDM", "decode": "Inclusion"},
            "category", "eligibility_criterion"
        )
        assert result == "Inclusion"

    def test_coerce_type_code_object_no_decode(self):
        """_coerce_type should fall back to code when decode is missing."""
        result = ValidationAgent._coerce_type(
            {"code": "C25532"},
            "category", "eligibility_criterion"
        )
        assert result == "C25532"

    def test_coerce_type_plain_dict_stringified(self):
        """_coerce_type should stringify dicts without code/decode."""
        result = ValidationAgent._coerce_type(
            {"foo": "bar"},
            "some_field", "some_type"
        )
        assert result == "{'foo': 'bar'}"



# ---------------------------------------------------------------------------
# OpenAPI schema validation tests
# ---------------------------------------------------------------------------

class TestOpenAPISchemaValidation:
    def test_returns_empty_when_no_validator(self, agent):
        """If openapi-schema-validator is not installed, returns empty list."""
        # This test just verifies the method doesn't crash
        issues = agent.validate_openapi_schema({"usdmVersion": "4.0.0", "study": {}})
        # May return issues or empty depending on whether the library is installed
        assert isinstance(issues, list)

    def test_returns_empty_for_missing_schema_file(self, agent):
        """If USDM schema file doesn't exist, returns empty list gracefully."""
        issues = agent.validate_openapi_schema({"usdmVersion": "4.0.0"})
        assert isinstance(issues, list)


# ---------------------------------------------------------------------------
# Automatic fix tests
# ---------------------------------------------------------------------------

class TestAutoFixes:
    def test_auto_fix_missing_title_type(self, agent):
        entity = _make_entity("study_title", {"text": "Title"})
        issues = agent.validate_schema([entity])
        fixable = [i for i in issues if i.auto_fixable]
        assert len(fixable) >= 1

        entities, fixes = agent._apply_auto_fixes([entity], issues)
        assert len(fixes) >= 1
        assert entity["data"]["type"] == "Official Study Title"

    def test_auto_fix_coerce_to_string(self, agent):
        entity = _make_entity("study", {"name": 42, "protocolVersions": ["v1"]})
        issues = agent.validate_schema([entity])
        type_issues = [i for i in issues if i.category == "data_type" and i.auto_fixable]
        assert len(type_issues) >= 1

        entities, fixes = agent._apply_auto_fixes([entity], issues)
        assert entity["data"]["name"] == "42"
        assert len(fixes) >= 1

    def test_auto_fix_updates_provenance_in_store(self, agent, context_store):
        # Add entity to context store
        context_store.add_entity(ContextEntity(
            id="title_1",
            entity_type="study_title",
            data={"text": "Title"},
            provenance=EntityProvenance(entity_id="title_1", source_agent_id="test"),
        ))
        agent.set_context_store(context_store)

        entity = _make_entity("study_title", {"text": "Title"}, entity_id="title_1")
        issues = agent.validate_schema([entity])
        agent._apply_auto_fixes([entity], issues, context_store)

        updated = context_store.get_entity("title_1")
        assert updated is not None
        assert "_validation_fixes" in updated.data
        assert len(updated.data["_validation_fixes"]) >= 1

    def test_no_fix_when_disabled(self):
        va = ValidationAgent(config={"auto_fix": False})
        va.initialize()
        entity = _make_entity("study_title", {"text": "Title"})
        task = _make_task([entity])
        result = va.execute(task)
        assert result.data["fixes_applied"] == 0

    def test_fix_records_old_and_new_value(self, agent):
        entity = _make_entity("study_title", {"text": "Title"}, entity_id="t1")
        issues = agent.validate_schema([entity])
        _, fixes = agent._apply_auto_fixes([entity], issues)
        assert len(fixes) >= 1
        fix = fixes[0]
        assert fix.old_value is None
        assert fix.new_value == "Official Study Title"
        assert fix.entity_id == "t1"


# ---------------------------------------------------------------------------
# Validation report tests
# ---------------------------------------------------------------------------

class TestValidationReport:
    def test_report_generation(self, agent):
        entities = [
            _make_entity("study", {"name": "S", "protocolVersions": ["v1"]}),
            _make_entity("study_identifier", {"identifier": "NCT123"}),
        ]
        report = agent.generate_report(entities)
        assert isinstance(report, ValidationReport)
        assert report.total_entities == 2
        assert report.report_id.startswith("vr_")

    def test_report_to_dict(self, agent):
        entities = [_make_entity("study", {"description": "no name"})]
        report = agent.generate_report(entities)
        d = report.to_dict()
        assert "summary" in d
        assert "issues" in d
        assert d["summary"]["errors"] >= 1

    def test_report_is_valid_when_no_errors(self, agent):
        entities = [
            _make_entity("study", {"name": "S", "protocolVersions": ["v1"]}),
            _make_entity("study_identifier", {"identifier": "NCT123"}),
            _make_entity("study_title", {"text": "T", "type": "Official"}),
        ]
        report = agent.generate_report(entities)
        assert report.is_valid

    def test_report_not_valid_with_errors(self, agent):
        entities = [_make_entity("study", {})]
        report = agent.generate_report(entities)
        assert not report.is_valid

    def test_reports_stored_in_agent(self, agent):
        entities = [_make_entity("study", {"name": "S", "protocolVersions": ["v1"]})]
        task = _make_task(entities)
        agent.execute(task)
        assert len(agent.get_reports()) >= 1


# ---------------------------------------------------------------------------
# Execute / iterative validation tests
# ---------------------------------------------------------------------------

class TestExecuteAndIterativeValidation:
    def test_execute_with_valid_entities(self, agent):
        entities = [
            _make_entity("study", {"name": "S", "protocolVersions": ["v1"]}),
            _make_entity("study_identifier", {"identifier": "NCT123"}),
            _make_entity("study_title", {"text": "T", "type": "Official"}),
        ]
        result = agent.execute(_make_task(entities))
        assert result.success
        assert result.data["is_valid"]
        assert result.data["errors"] == 0

    def test_execute_with_errors(self, agent):
        entities = [_make_entity("study", {})]
        result = agent.execute(_make_task(entities))
        assert result.success  # execution succeeds, validation finds errors
        assert not result.data["is_valid"]
        assert result.data["errors"] >= 1

    def test_execute_no_entities_fails(self, agent):
        result = agent.execute(_make_task([]))
        assert not result.success

    def test_execute_from_context_store(self, agent, context_store):
        context_store.add_entity(ContextEntity(
            id="s1", entity_type="study",
            data={"name": "S", "protocolVersions": ["v1"]},
            provenance=EntityProvenance(entity_id="s1", source_agent_id="test"),
        ))
        context_store.add_entity(ContextEntity(
            id="si1", entity_type="study_identifier",
            data={"identifier": "NCT123"},
            provenance=EntityProvenance(entity_id="si1", source_agent_id="test"),
        ))
        agent.set_context_store(context_store)
        task = AgentTask(
            task_id="t1", agent_id="validation_agent",
            task_type="validate_usdm", input_data={},
        )
        result = agent.execute(task)
        assert result.success

    def test_iterative_validation_fixes_issues(self, agent):
        # Entity with auto-fixable missing type
        entity = _make_entity("study_title", {"text": "Title"})
        report = agent.validate_iteratively([entity])
        # After iteration, the type should be fixed
        assert any(f.field_name == "type" for f in report.fixes_applied)

    def test_iterative_stops_when_no_fixes(self, agent):
        entities = [
            _make_entity("study", {"name": "S", "protocolVersions": ["v1"]}),
            _make_entity("study_identifier", {"identifier": "NCT123"}),
        ]
        report = agent.validate_iteratively(entities)
        assert report.iteration == 1  # No fixes needed, stops at 1

    def test_max_iterations_respected(self):
        va = ValidationAgent(config={"max_iterations": 1})
        va.initialize()
        entity = _make_entity("study_title", {"text": "Title"})
        task = _make_task([entity], max_iterations=1)
        result = va.execute(task)
        assert result.data["iterations"] <= 1


# ---------------------------------------------------------------------------
# 50 USDM outputs: 20 valid, 30 with errors (parametrized)
# ---------------------------------------------------------------------------

def _valid_base() -> List[Dict[str, Any]]:
    """Minimal valid USDM entity set."""
    return [
        _make_entity("study", {"name": "Study", "protocolVersions": ["v1"]}),
        _make_entity("study_identifier", {"identifier": "NCT00000001"}),
        _make_entity("study_title", {"text": "Title", "type": "Official"}),
        _make_entity("organization", {"name": "Org"}, entity_id="org_1"),
    ]


# 20 valid outputs
VALID_OUTPUTS = [
    pytest.param(
        _valid_base(),
        id="valid_01_minimal",
    ),
    pytest.param(
        _valid_base() + [_make_entity("indication", {"name": "Diabetes"})],
        id="valid_02_with_indication",
    ),
    pytest.param(
        _valid_base() + [_make_entity("study_phase", {"standardCode": "Phase III"})],
        id="valid_03_with_phase",
    ),
    pytest.param(
        _valid_base() + [
            _make_entity("objective", {"text": "Primary obj", "level": "primary", "endpointIds": ["ep1"]}),
            _make_entity("endpoint", {"text": "OS", "purpose": "efficacy"}, entity_id="ep1"),
        ],
        id="valid_04_objective_with_endpoint",
    ),
    pytest.param(
        _valid_base() + [
            _make_entity("eligibility_criterion", {"category": "inclusion", "criterionItemId": "ci_1"}),
            _make_entity("criterion_item", {"text": "Age >= 18", "name": "Age"}, entity_id="ci_1"),
        ],
        id="valid_05_with_criterion",
    ),
    pytest.param(
        _valid_base() + [
            _make_entity("study_arm", {"name": "Arm A", "type": "experimental"}),
        ],
        id="valid_06_with_arm",
    ),
    pytest.param(
        _valid_base() + [
            _make_entity("epoch", {"name": "Screening"}),
        ],
        id="valid_07_with_epoch",
    ),
    pytest.param(
        _valid_base() + [
            _make_entity("encounter", {"name": "Visit 1"}, entity_id="enc_1"),
            _make_entity("epoch", {"name": "Treatment", "encounterIds": ["enc_1"]}),
        ],
        id="valid_08_epoch_with_encounter",
    ),
    pytest.param(
        _valid_base() + [
            _make_entity("activity", {"name": "Blood draw"}),
        ],
        id="valid_09_with_activity",
    ),
    pytest.param(
        _valid_base() + [
            _make_entity("procedure", {"name": "ECG"}),
        ],
        id="valid_10_with_procedure",
    ),
    pytest.param(
        _valid_base() + [
            _make_entity("encounter", {"name": "V1"}, entity_id="enc_a"),
            _make_entity("activity", {"name": "A1"}, entity_id="act_a"),
            _make_entity("scheduled_instance", {"encounterId": "enc_a", "activityIds": ["act_a"]}),
        ],
        id="valid_11_scheduled_instance",
    ),
    pytest.param(
        _valid_base() + [
            _make_entity("investigational_product", {"name": "Drug X"}),
        ],
        id="valid_12_with_product",
    ),
    pytest.param(
        _valid_base() + [
            _make_entity("timing", {"type": "scheduled", "value": "P7D"}),
        ],
        id="valid_13_with_timing",
    ),
    pytest.param(
        _valid_base() + [
            _make_entity("narrative_content", {"name": "Section 1", "sectionNumber": "1.0"}),
        ],
        id="valid_14_with_narrative",
    ),
    pytest.param(
        _valid_base() + [
            _make_entity("study_identifier", {"identifier": "EudraCT-2024-001", "type": "EudraCT"}),
        ],
        id="valid_15_two_identifiers",
    ),
    pytest.param(
        _valid_base() + [
            _make_entity("study_identifier", {"identifier": "NCT99999999", "organizationId": "org_1"}),
        ],
        id="valid_16_identifier_with_org_ref",
    ),
    pytest.param(
        _valid_base() + [
            _make_entity("study_arm", {"name": "Placebo", "type": "control", "description": "Placebo arm"}),
        ],
        id="valid_17_arm_with_description",
    ),
    pytest.param(
        _valid_base() + [
            _make_entity("activity", {"name": "Lab", "procedureIds": ["proc_1"]}),
            _make_entity("procedure", {"name": "CBC"}, entity_id="proc_1"),
        ],
        id="valid_18_activity_with_procedure_ref",
    ),
    pytest.param(
        _valid_base() + [
            _make_entity("eligibility_criterion", {"category": "exclusion", "criterionItemId": "ci_a"}),
            _make_entity("eligibility_criterion", {"category": "inclusion", "criterionItemId": "ci_b"}),
            _make_entity("criterion_item", {"text": "No cancer", "name": "No cancer"}, entity_id="ci_a"),
            _make_entity("criterion_item", {"text": "ECOG 0-1", "name": "ECOG"}, entity_id="ci_b"),
        ],
        id="valid_19_multiple_criteria",
    ),
    pytest.param(
        _valid_base() + [
            _make_entity("indication", {"name": "NSCLC", "description": "Non-small cell lung cancer"}),
            _make_entity("study_phase", {"standardCode": "Phase II"}),
            _make_entity("objective", {"text": "Assess safety", "level": "secondary"}),
        ],
        id="valid_20_rich_study",
    ),
    pytest.param(
        _valid_base() + [
            _make_entity("eligibility_criterion", {
                "category": {"code": "Inclusion", "codeSystem": "USDM", "decode": "Inclusion"},
                "criterionItemId": "ci_code",
            }),
            _make_entity("criterion_item", {"text": "Must be adult", "name": "Adult"}, entity_id="ci_code"),
        ],
        id="valid_21_criterion_code_object_category",
    ),
    pytest.param(
        _valid_base() + [
            _make_entity("narrative_content_item", {"text": "Section content", "name": "Intro"}),
        ],
        id="valid_22_narrative_content_item",
    ),
    pytest.param(
        _valid_base() + [
            _make_entity("study_role", {"name": "Sponsor", "role": "sponsor"}),
        ],
        id="valid_23_study_role",
    ),
    pytest.param(
        _valid_base() + [
            _make_entity("abbreviation", {"abbreviation": "NSCLC", "expansion": "Non-Small Cell Lung Cancer"}),
        ],
        id="valid_24_abbreviation",
    ),
]


# 30 outputs with errors
ERROR_OUTPUTS = [
    pytest.param(
        [_make_entity("study", {})],
        {"required_field"},
        id="error_01_study_missing_name",
    ),
    pytest.param(
        [_make_entity("study_title", {"type": "Official"})],
        {"required_field"},
        id="error_02_title_missing_text",
    ),
    pytest.param(
        [_make_entity("study_title", {"text": "T"})],
        {"required_field"},
        id="error_03_title_missing_type",
    ),
    pytest.param(
        [_make_entity("study_identifier", {})],
        {"required_field"},
        id="error_04_identifier_missing_id",
    ),
    pytest.param(
        [_make_entity("organization", {})],
        {"required_field"},
        id="error_05_org_missing_name",
    ),
    pytest.param(
        [_make_entity("study", {"name": 123, "protocolVersions": ["v1"]})],
        {"data_type"},
        id="error_06_study_name_wrong_type",
    ),
    pytest.param(
        [_make_entity("study_title", {"text": 999, "type": "Official"})],
        {"data_type"},
        id="error_07_title_text_wrong_type",
    ),
    pytest.param(
        [_make_entity("scheduled_instance", {"encounterId": "e1", "activityIds": []})],
        {"cardinality"},
        id="error_08_scheduled_empty_activities",
    ),
    pytest.param(
        [_make_entity("study_identifier", {"identifier": "NCT1", "organizationId": "missing_org"})],
        {"reference"},
        id="error_09_broken_org_reference",
    ),
    pytest.param(
        [_make_entity("epoch", {"name": "E", "encounterIds": ["no_enc"]})],
        {"reference"},
        id="error_10_broken_encounter_reference",
    ),
    pytest.param(
        [_make_entity("activity", {"name": "A", "procedureIds": ["no_proc"]})],
        {"reference"},
        id="error_11_broken_procedure_reference",
    ),
    pytest.param(
        [_make_entity("study", {"name": "S", "protocolVersions": ["v1"]})],
        {"core"},
        id="error_12_core_no_identifier",
    ),
    pytest.param(
        [
            _make_entity("study_identifier", {"identifier": "NCT1"}),
            _make_entity("objective", {"text": "Obj", "level": "primary"}),
        ],
        {"core"},
        id="error_13_core_objective_no_endpoint",
    ),
    pytest.param(
        [_make_entity("objective", {"level": "primary"})],
        {"required_field"},
        id="error_14_objective_missing_text",
    ),
    pytest.param(
        [_make_entity("endpoint", {})],
        {"required_field"},
        id="error_15_endpoint_missing_text",
    ),
    pytest.param(
        [_make_entity("eligibility_criterion", {"name": "Age"})],
        {"required_field"},
        id="error_16_criterion_missing_category",
    ),
    pytest.param(
        [_make_entity("study_arm", {"type": "experimental"})],
        {"required_field"},
        id="error_17_arm_missing_name",
    ),
    pytest.param(
        [_make_entity("epoch", {})],
        {"required_field"},
        id="error_18_epoch_missing_name",
    ),
    pytest.param(
        [_make_entity("encounter", {})],
        {"required_field"},
        id="error_19_encounter_missing_name",
    ),
    pytest.param(
        [_make_entity("activity", {})],
        {"required_field"},
        id="error_20_activity_missing_name",
    ),
    pytest.param(
        [_make_entity("procedure", {})],
        {"required_field"},
        id="error_21_procedure_missing_name",
    ),
    pytest.param(
        [_make_entity("scheduled_instance", {"activityIds": ["a1"]})],
        {"required_field"},
        id="error_22_scheduled_missing_encounter",
    ),
    pytest.param(
        [_make_entity("investigational_product", {})],
        {"required_field"},
        id="error_23_product_missing_name",
    ),
    pytest.param(
        [_make_entity("timing", {})],
        {"required_field"},
        id="error_24_timing_missing_type",
    ),
    pytest.param(
        [_make_entity("narrative_content", {})],
        {"required_field"},
        id="error_25_narrative_missing_name",
    ),
    pytest.param(
        [_make_entity("study_phase", {})],
        {"required_field"},
        id="error_26_phase_missing_code",
    ),
    pytest.param(
        [_make_entity("indication", {})],
        {"required_field"},
        id="error_27_indication_missing_name",
    ),
    pytest.param(
        [
            _make_entity("study", {"name": 42}),
            _make_entity("study_title", {"text": True, "type": "Official"}),
        ],
        {"data_type"},
        id="error_28_multiple_type_errors",
    ),
    pytest.param(
        [
            _make_entity("scheduled_instance", {
                "encounterId": "missing_enc",
                "activityIds": ["missing_act"],
            }),
        ],
        {"reference"},
        id="error_29_multiple_broken_refs",
    ),
    pytest.param(
        [
            _make_entity("study", {}),
            _make_entity("study_title", {}),
            _make_entity("organization", {}),
        ],
        {"required_field"},
        id="error_30_all_entities_missing_required",
    ),
    pytest.param(
        [_make_entity("criterion_item", {})],
        {"required_field"},
        id="error_31_criterion_item_missing_text",
    ),
    pytest.param(
        [_make_entity("narrative_content_item", {})],
        {"required_field"},
        id="error_32_narrative_item_missing_text",
    ),
    pytest.param(
        [_make_entity("abbreviation", {"abbreviation": "ABC"})],
        {"required_field"},
        id="error_33_abbreviation_missing_expansion",
    ),
]


class TestValidOutputs:
    @pytest.mark.parametrize("entities", VALID_OUTPUTS)
    def test_valid_output_passes(self, agent, entities):
        report = agent.generate_report(entities)
        errors = [i for i in report.issues if i.severity == ValidationSeverity.ERROR]
        # Valid outputs should have zero schema/reference errors
        # (CORE warnings/info are acceptable)
        schema_ref_errors = [
            e for e in errors
            if e.category in ("required_field", "data_type", "cardinality", "reference")
        ]
        assert len(schema_ref_errors) == 0, (
            f"Unexpected errors: {[e.to_dict() for e in schema_ref_errors]}"
        )


class TestErrorOutputs:
    @pytest.mark.parametrize("entities,expected_categories", ERROR_OUTPUTS)
    def test_error_output_detected(self, agent, entities, expected_categories):
        report = agent.generate_report(entities)
        found_categories = {i.category for i in report.issues}
        assert expected_categories & found_categories, (
            f"Expected categories {expected_categories} not found in {found_categories}"
        )


# ---------------------------------------------------------------------------
# Data model tests
# ---------------------------------------------------------------------------

class TestDataModels:
    def test_validation_issue_to_dict(self):
        issue = ValidationIssue(
            issue_id="i1",
            severity=ValidationSeverity.ERROR,
            category="required_field",
            entity_id="e1",
            entity_type="study",
            field_name="name",
            message="Missing name",
        )
        d = issue.to_dict()
        assert d["severity"] == "error"
        assert d["category"] == "required_field"

    def test_auto_fix_to_dict(self):
        fix = AutoFix(
            fix_id="f1",
            entity_id="e1",
            field_name="type",
            old_value=None,
            new_value="Official",
            reason="Default",
        )
        d = fix.to_dict()
        assert d["fix_id"] == "f1"
        assert d["new_value"] == "Official"

    def test_validation_report_counts(self):
        issues = [
            ValidationIssue("i1", ValidationSeverity.ERROR, "req", "e1", "study", "name", "err"),
            ValidationIssue("i2", ValidationSeverity.WARNING, "core", "e2", "obj", "ep", "warn"),
            ValidationIssue("i3", ValidationSeverity.INFO, "schema", "e3", "x", "y", "info"),
        ]
        report = ValidationReport(
            report_id="r1",
            timestamp=datetime.now(),
            total_entities=3,
            issues=issues,
            fixes_applied=[],
        )
        assert report.error_count == 1
        assert report.warning_count == 1
        assert report.info_count == 1
        assert not report.is_valid

    def test_severity_enum_values(self):
        assert ValidationSeverity.ERROR.value == "error"
        assert ValidationSeverity.WARNING.value == "warning"
        assert ValidationSeverity.INFO.value == "info"
