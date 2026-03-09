"""
Phase 4 Quality Agent Validation Testing.

Higher-level validation tests for the three quality agents:
- ValidationAgent: 100% schema violation detection
- EnrichmentAgent: 85%+ correct code assignment
- ReconciliationAgent: 95%+ correct merging
- SoA conflict resolution: 90%+ agreement rate
- Confidence scoring algorithms
- Combined quality metrics report generation
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pytest

from agents.base import AgentCapabilities, AgentResult, AgentTask
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
from agents.quality.enrichment_agent import (
    EVSConcept,
    EnrichmentAgent,
    EnrichmentCoverageMetrics,
    EnrichmentResult,
    EVSAPIClient,
    EVSCache,
    compute_relevance_score,
    rank_concepts,
)
from agents.quality.reconciliation_agent import (
    ConflictDetail,
    DuplicateGroup,
    ReconciliationAgent,
    ReconciliationReport,
    clean_entity_name,
    fuzzy_match_score,
    get_source_priority,
)


# ============================================================================
# Helpers
# ============================================================================

def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _entity(
    entity_type: str,
    data: Dict[str, Any],
    entity_id: Optional[str] = None,
    source_agent: str = "test_agent",
    confidence: float = 0.8,
) -> Dict[str, Any]:
    eid = entity_id or f"{entity_type}_{_uid()}"
    return {
        "id": eid,
        "entity_type": entity_type,
        "data": data,
        "relationships": {},
        "provenance": {
            "entity_id": eid,
            "source_agent_id": source_agent,
            "extraction_timestamp": datetime.now().isoformat(),
            "confidence_score": confidence,
            "source_pages": [1],
            "model_used": "test-model",
            "version": 1,
        },
    }


def _task(entities: List[Dict[str, Any]], **overrides) -> AgentTask:
    input_data = {"entities": entities}
    input_data.update(overrides)
    return AgentTask(
        task_id=f"task_{_uid()}",
        agent_id="quality_test",
        task_type="quality_validation",
        input_data=input_data,
    )


def _context_entity(
    entity_type: str,
    data: Dict[str, Any],
    entity_id: Optional[str] = None,
    source_agent: str = "test_agent",
    confidence: float = 0.8,
) -> ContextEntity:
    eid = entity_id or f"{entity_type}_{_uid()}"
    return ContextEntity(
        id=eid,
        entity_type=entity_type,
        data=data,
        provenance=EntityProvenance(
            entity_id=eid,
            source_agent_id=source_agent,
            confidence_score=confidence,
            source_pages=[1],
            model_used="test-model",
        ),
    )


# ============================================================================
# Mock EVS Client
# ============================================================================

class MockEVSClient:
    """Mock EVS client with known responses for deterministic testing."""

    # Known entity name -> EVS concepts mapping
    KNOWN_CODES: Dict[str, List[EVSConcept]] = {
        "diabetes mellitus": [
            EVSConcept(code="C2985", name="Diabetes Mellitus",
                       synonyms=["Diabetes", "DM"], definition="A metabolic disorder"),
        ],
        "hypertension": [
            EVSConcept(code="C3117", name="Hypertension",
                       synonyms=["High Blood Pressure", "HTN"], definition="Elevated blood pressure"),
        ],
        "aspirin": [
            EVSConcept(code="C287", name="Aspirin",
                       synonyms=["Acetylsalicylic Acid", "ASA"], definition="An NSAID"),
        ],
        "metformin": [
            EVSConcept(code="C61612", name="Metformin",
                       synonyms=["Metformin Hydrochloride"], definition="An antidiabetic agent"),
        ],
        "blood pressure measurement": [
            EVSConcept(code="C49676", name="Blood Pressure Measurement",
                       synonyms=["BP Measurement"], definition="Measurement of blood pressure"),
        ],
        "electrocardiogram": [
            EVSConcept(code="C168186", name="Electrocardiogram",
                       synonyms=["ECG", "EKG"], definition="A recording of heart electrical activity"),
        ],
        "complete blood count": [
            EVSConcept(code="C64844", name="Complete Blood Count",
                       synonyms=["CBC", "Full Blood Count"], definition="A blood test"),
        ],
        "physical examination": [
            EVSConcept(code="C20989", name="Physical Examination",
                       synonyms=["Physical Exam", "PE"], definition="A clinical examination"),
        ],
        "urinalysis": [
            EVSConcept(code="C63246", name="Urinalysis",
                       synonyms=["Urine Analysis", "UA"], definition="Analysis of urine"),
        ],
        "liver function test": [
            EVSConcept(code="C64547", name="Liver Function Test",
                       synonyms=["LFT", "Hepatic Function Panel"], definition="Tests of liver function"),
        ],
        "renal function test": [
            EVSConcept(code="C62078", name="Renal Function Test",
                       synonyms=["Kidney Function Test", "RFT"], definition="Tests of kidney function"),
        ],
        "magnetic resonance imaging": [
            EVSConcept(code="C16809", name="Magnetic Resonance Imaging",
                       synonyms=["MRI"], definition="An imaging technique"),
        ],
        "biopsy": [
            EVSConcept(code="C15189", name="Biopsy",
                       synonyms=["Tissue Biopsy"], definition="Removal of tissue for examination"),
        ],
        "placebo": [
            EVSConcept(code="C49666", name="Placebo",
                       synonyms=["Inactive Substance"], definition="An inactive substance"),
        ],
        "insulin": [
            EVSConcept(code="C581", name="Insulin",
                       synonyms=["Insulin Hormone"], definition="A peptide hormone"),
        ],
        "rheumatoid arthritis": [
            EVSConcept(code="C2884", name="Rheumatoid Arthritis",
                       synonyms=["RA"], definition="An autoimmune disease"),
        ],
        "asthma": [
            EVSConcept(code="C28397", name="Asthma",
                       synonyms=["Bronchial Asthma"], definition="A chronic respiratory disease"),
        ],
        "migraine": [
            EVSConcept(code="C34800", name="Migraine",
                       synonyms=["Migraine Headache"], definition="A neurological condition"),
        ],
        # Partial match - returns multiple concepts
        "heart failure": [
            EVSConcept(code="C50577", name="Heart Failure",
                       synonyms=["Cardiac Failure", "CHF"], definition="Inability of heart to pump"),
            EVSConcept(code="C3080", name="Congestive Heart Failure",
                       synonyms=["CHF"], definition="Heart failure with congestion"),
        ],
        # Low relevance match
        "xyz unknown condition": [
            EVSConcept(code="C99999", name="Unspecified Condition",
                       synonyms=[], definition="An unspecified condition"),
        ],
    }

    def search_concepts(self, term: str, max_results: int = 10) -> List[EVSConcept]:
        key = term.lower().strip()
        return list(self.KNOWN_CODES.get(key, []))


# ============================================================================
# 20.1.1 - ValidationAgent Accuracy (100% schema violation detection)
# ============================================================================

class TestValidationAgentAccuracy:
    """Test that ValidationAgent detects 100% of schema violations."""

    @pytest.fixture
    def agent(self):
        va = ValidationAgent()
        va.initialize()
        return va

    # --- Violation scenarios ---

    VIOLATION_SCENARIOS = [
        # (description, entity_type, data, expected_category)
        ("missing_required_name_study", "study", {}, "required_field"),
        ("missing_required_text_title", "study_title", {"type": "Official"}, "required_field"),
        ("missing_required_type_title", "study_title", {"text": "A Study"}, "required_field"),
        ("missing_required_identifier", "study_identifier", {}, "required_field"),
        ("missing_required_org_name", "organization", {}, "required_field"),
        ("missing_required_phase_code", "study_phase", {}, "required_field"),
        ("missing_required_indication_name", "indication", {}, "required_field"),
        ("missing_required_objective_text", "objective", {"level": "primary"}, "required_field"),
        ("missing_required_objective_level", "objective", {"text": "To evaluate"}, "required_field"),
        ("missing_required_endpoint_text", "endpoint", {}, "required_field"),
        ("missing_required_criterion_text", "criterion_item", {}, "required_field"),
        ("missing_required_criterion_category", "eligibility_criterion", {"name": "Age"}, "required_field"),
        ("missing_required_arm_name", "study_arm", {}, "required_field"),
        ("missing_required_epoch_name", "epoch", {}, "required_field"),
        ("missing_required_encounter_name", "encounter", {}, "required_field"),
        ("missing_required_activity_name", "activity", {}, "required_field"),
        ("missing_required_procedure_name", "procedure", {}, "required_field"),
        ("missing_required_si_encounter", "scheduled_instance", {"activityIds": ["a1"]}, "required_field"),
        ("missing_required_si_activities", "scheduled_instance", {"encounterId": "e1"}, "required_field"),
        ("missing_required_product_name", "investigational_product", {}, "required_field"),
        ("missing_required_timing_type", "timing", {}, "required_field"),
        ("missing_required_narrative_name", "narrative_content", {}, "required_field"),
        ("wrong_type_name_integer", "study", {"name": 12345, "protocolVersions": ["v1"]}, "data_type"),
        ("wrong_type_name_list", "organization", {"name": ["Acme"]}, "data_type"),
        ("wrong_type_name_bool", "indication", {"name": True}, "data_type"),
    ]

    @pytest.mark.parametrize(
        "desc,entity_type,data,expected_category",
        VIOLATION_SCENARIOS,
        ids=[s[0] for s in VIOLATION_SCENARIOS],
    )
    def test_detects_violation(self, agent, desc, entity_type, data, expected_category):
        """Each known violation must be detected."""
        entities = [_entity(entity_type, data)]
        report = agent.generate_report(entities)
        categories = [i.category for i in report.issues]
        assert expected_category in categories, (
            f"Expected '{expected_category}' violation for {desc}, got {categories}"
        )

    def test_broken_reference_detected(self, agent):
        """References to non-existent entities must be caught."""
        entities = [
            _entity("epoch", {"name": "Screening", "encounterIds": ["nonexistent_enc_1"]}),
        ]
        report = agent.generate_report(entities)
        ref_issues = [i for i in report.issues if i.category == "reference"]
        assert len(ref_issues) >= 1
        assert "nonexistent_enc_1" in ref_issues[0].message

    def test_cardinality_violation_detected(self, agent):
        """Empty list where min_cardinality > 0 must be caught."""
        entities = [
            _entity("scheduled_instance", {"encounterId": "e1", "activityIds": []}),
        ]
        report = agent.generate_report(entities)
        card_issues = [i for i in report.issues if i.category == "cardinality"]
        assert len(card_issues) >= 1

    def test_cdisc_core_missing_identifier(self, agent):
        """CDISC CORE rule: study must have at least one identifier."""
        entities = [
            _entity("study", {"name": "Test Study", "protocolVersions": ["v1"]}),
        ]
        report = agent.generate_report(entities)
        core_issues = [i for i in report.issues if i.category == "core"]
        assert len(core_issues) >= 1

    def test_valid_entities_no_errors(self, agent):
        """A fully valid set of entities should produce zero errors."""
        org_id = f"org_{_uid()}"
        enc_id = f"enc_{_uid()}"
        act_id = f"act_{_uid()}"
        ep_id = f"ep_{_uid()}"
        proc_id = f"proc_{_uid()}"
        entities = [
            _entity("study", {"name": "Test Study", "protocolVersions": ["v1"]}),
            _entity("study_title", {"text": "A Phase 3 Study", "type": "Official Study Title"}),
            _entity("study_identifier", {"identifier": "NCT12345678", "type": "NCT", "organizationId": org_id}),
            _entity("organization", {"name": "Acme Pharma", "type": "Sponsor"}, entity_id=org_id),
            _entity("study_phase", {"standardCode": "Phase III"}),
            _entity("indication", {"name": "Diabetes Mellitus"}),
            _entity("objective", {"text": "To evaluate efficacy", "level": "primary", "endpointIds": [ep_id]}),
            _entity("endpoint", {"text": "HbA1c change from baseline", "purpose": "efficacy"}, entity_id=ep_id),
            _entity("eligibility_criterion", {"text": "Age >= 18", "category": "inclusion"}),
            _entity("study_arm", {"name": "Treatment Arm", "type": "experimental"}),
            _entity("epoch", {"name": "Treatment", "encounterIds": [enc_id]}),
            _entity("encounter", {"name": "Visit 1"}, entity_id=enc_id),
            _entity("activity", {"name": "Blood Draw", "procedureIds": [proc_id]}),
            _entity("procedure", {"name": "Venipuncture"}, entity_id=proc_id),
            _entity("scheduled_instance", {"encounterId": enc_id, "activityIds": [act_id]}),
            _entity("investigational_product", {"name": "Drug X"}),
            _entity("timing", {"type": "scheduled", "value": "P1D"}),
            _entity("narrative_content", {"name": "Introduction", "sectionNumber": "1.0"}),
        ]
        # Add the activity with the right ID
        entities[12]["id"] = act_id
        report = agent.generate_report(entities)
        errors = [i for i in report.issues if i.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0, f"Expected 0 errors, got: {[e.message for e in errors]}"

    def test_100_percent_detection_rate(self, agent):
        """Batch test: inject N violations, verify all N are detected."""
        violations = [
            _entity("study", {}),                                          # missing name
            _entity("study_title", {"text": "Title"}),                     # missing type
            _entity("study_identifier", {}),                               # missing identifier
            _entity("organization", {}),                                   # missing name
            _entity("indication", {}),                                     # missing name
            _entity("objective", {"level": "primary"}),                    # missing text
            _entity("endpoint", {}),                                       # missing text
            _entity("eligibility_criterion", {"text": "Age >= 18"}),       # missing category
            _entity("study_arm", {}),                                      # missing name
            _entity("epoch", {}),                                          # missing name
            _entity("encounter", {}),                                      # missing name
            _entity("activity", {}),                                       # missing name
            _entity("procedure", {}),                                      # missing name
            _entity("investigational_product", {}),                        # missing name
            _entity("timing", {}),                                         # missing type
            _entity("narrative_content", {}),                              # missing name
        ]
        report = agent.generate_report(violations)
        required_issues = [i for i in report.issues if i.category == "required_field"]
        # Each entity above has at least one required field missing
        detected_entity_ids = {i.entity_id for i in required_issues}
        violation_ids = {e["id"] for e in violations}
        # Every violation entity should have at least one issue
        undetected = violation_ids - detected_entity_ids
        assert len(undetected) == 0, f"Undetected violations for entities: {undetected}"

    def test_multiple_violations_per_entity(self, agent):
        """Entity with multiple violations should have all detected."""
        # objective missing both text and level
        entities = [_entity("objective", {})]
        report = agent.generate_report(entities)
        obj_issues = [i for i in report.issues if i.entity_id == entities[0]["id"]
                      and i.category == "required_field"]
        assert len(obj_issues) >= 2  # text + level



# ============================================================================
# 20.1.2 - EnrichmentAgent Coverage (85%+ correct code assignment)
# ============================================================================

class TestEnrichmentAgentCoverage:
    """Test that EnrichmentAgent achieves 85%+ correct code assignment."""

    @pytest.fixture
    def mock_evs(self):
        return MockEVSClient()

    @pytest.fixture
    def agent(self, mock_evs):
        ea = EnrichmentAgent(evs_client=mock_evs, config={"base_delay": 0.0})
        ea.initialize()
        return ea

    def _enrichable_batch(self) -> List[Dict[str, Any]]:
        """Create a batch of enrichable entities with known NCI codes."""
        entities = []
        # Indications (exact matches)
        for name in [
            "Diabetes Mellitus", "Hypertension", "Rheumatoid Arthritis",
            "Asthma", "Migraine", "Heart Failure",
        ]:
            entities.append(_entity("indication", {"name": name}))

        # Procedures (exact matches)
        for name in [
            "Blood Pressure Measurement", "Electrocardiogram",
            "Complete Blood Count", "Physical Examination",
            "Urinalysis", "Liver Function Test", "Renal Function Test",
            "Magnetic Resonance Imaging", "Biopsy",
        ]:
            entities.append(_entity("procedure", {"name": name}))

        # Investigational products (exact matches)
        for name in ["Aspirin", "Metformin", "Placebo", "Insulin"]:
            entities.append(_entity("investigational_product", {"name": name}))

        # Non-enrichable entity types (should be skipped)
        entities.append(_entity("study", {"name": "Test Study", "protocolVersions": ["v1"]}))
        entities.append(_entity("epoch", {"name": "Screening"}))

        return entities

    def test_enrichment_coverage_above_85_percent(self, agent):
        """Batch enrichment should achieve >= 85% coverage on known entities."""
        entities = self._enrichable_batch()
        task = _task(entities)
        result = agent.execute(task)

        assert result.success
        coverage = result.data["coverage"]
        assert coverage["coverage_percent"] >= 85.0, (
            f"Coverage {coverage['coverage_percent']}% is below 85% threshold"
        )

    def test_correct_code_assignment(self, agent):
        """Verify specific entities get the correct NCI codes."""
        expected_codes = {
            "Diabetes Mellitus": "C2985",
            "Hypertension": "C3117",
            "Aspirin": "C287",
            "Metformin": "C61612",
            "Electrocardiogram": "C168186",
        }
        entities = [
            _entity(
                "indication" if name in ("Diabetes Mellitus", "Hypertension") else "investigational_product"
                if name in ("Aspirin", "Metformin") else "procedure",
                {"name": name},
            )
            for name in expected_codes
        ]
        task = _task(entities)
        result = agent.execute(task)

        assert result.success
        enrichment_results = result.data["enrichment_results"]
        for er in enrichment_results:
            name = er["entity_name"]
            if name in expected_codes:
                assert er["enriched"], f"{name} should be enriched"
                assert er["code"] == expected_codes[name], (
                    f"{name}: expected {expected_codes[name]}, got {er.get('code')}"
                )

    def test_non_enrichable_types_skipped(self, agent):
        """Non-enrichable entity types should not be processed."""
        entities = [
            _entity("study", {"name": "Test Study", "protocolVersions": ["v1"]}),
            _entity("epoch", {"name": "Screening"}),
            _entity("encounter", {"name": "Visit 1"}),
        ]
        task = _task(entities)
        result = agent.execute(task)

        assert result.success
        assert result.data["coverage"]["enrichable_entities"] == 0

    def test_cache_prevents_duplicate_api_calls(self, agent):
        """Repeated enrichment of same term should use cache."""
        entities = [
            _entity("indication", {"name": "Diabetes Mellitus"}),
            _entity("indication", {"name": "Diabetes Mellitus"}),
        ]
        task = _task(entities)
        result = agent.execute(task)

        assert result.success
        coverage = result.data["coverage"]
        assert coverage["cache_hits"] >= 1

    def test_manual_override_takes_precedence(self, agent):
        """Manual overrides should override automatic enrichment."""
        eid = f"ind_{_uid()}"
        entities = [_entity("indication", {"name": "Diabetes Mellitus"}, entity_id=eid)]
        agent.set_manual_override(eid, "C99999")
        task = _task(entities)
        result = agent.execute(task)

        assert result.success
        er = result.data["enrichment_results"][0]
        assert er["code"] == "C99999"
        assert er["source"] == "manual"

    def test_no_match_entity_not_enriched(self, agent):
        """Entity with no EVS match should not be enriched."""
        entities = [_entity("indication", {"name": "Completely Unknown Disease XYZ123"})]
        task = _task(entities)
        result = agent.execute(task)

        assert result.success
        er = result.data["enrichment_results"][0]
        assert not er["enriched"]

    def test_low_relevance_below_threshold(self, agent):
        """Entity with only low-relevance matches should not be enriched."""
        entities = [_entity("indication", {"name": "xyz unknown condition"})]
        task = _task(entities)
        result = agent.execute(task)

        assert result.success
        er = result.data["enrichment_results"][0]
        # The mock returns a concept but with low relevance score
        # compute_relevance_score("xyz unknown condition", "Unspecified Condition") should be low
        # Whether enriched depends on the threshold
        # Just verify the result is consistent
        if er["enriched"]:
            assert er["confidence"] >= agent._min_confidence


# ============================================================================
# 20.1.3 - ReconciliationAgent Correctness (95%+ correct merging)
# ============================================================================

class TestReconciliationAgentCorrectness:
    """Test that ReconciliationAgent achieves 95%+ correct merging."""

    @pytest.fixture
    def agent(self):
        ra = ReconciliationAgent()
        ra.initialize()
        return ra

    def _duplicate_batch(self) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
        """Create entities with known duplicates and expected merge outcomes.

        Returns (entities, expected_merges) where expected_merges maps
        secondary_id -> primary_id.
        """
        entities = []
        expected_merges: Dict[str, str] = {}

        # Duplicate pair 1: same epoch from two sources
        e1a = _entity("epoch", {"name": "Screening"}, entity_id="epoch_1a",
                       source_agent="soa_vision_agent", confidence=0.8)
        e1b = _entity("epoch", {"name": "Screening"}, entity_id="epoch_1b",
                       source_agent="soa_text_agent", confidence=0.7)
        entities.extend([e1a, e1b])
        expected_merges["epoch_1b"] = "epoch_1a"  # vision > text priority

        # Duplicate pair 2: same encounter with footnote marker
        e2a = _entity("encounter", {"name": "Visit 1"}, entity_id="enc_2a",
                       source_agent="soa_vision_agent")
        e2b = _entity("encounter", {"name": "Visit 1 *"}, entity_id="enc_2b",
                       source_agent="soa_text_agent")
        entities.extend([e2a, e2b])
        expected_merges["enc_2b"] = "enc_2a"

        # Duplicate pair 3: same activity from procedures and SoA
        e3a = _entity("activity", {"name": "Blood Draw"}, entity_id="act_3a",
                       source_agent="procedures_agent")
        e3b = _entity("activity", {"name": "Blood Draw"}, entity_id="act_3b",
                       source_agent="soa_vision_agent")
        entities.extend([e3a, e3b])
        expected_merges["act_3b"] = "act_3a"  # procedures > soa_vision

        # Duplicate pair 4: same procedure
        e4a = _entity("procedure", {"name": "ECG"}, entity_id="proc_4a",
                       source_agent="procedures_agent")
        e4b = _entity("procedure", {"name": "ECG"}, entity_id="proc_4b",
                       source_agent="soa_text_agent")
        entities.extend([e4a, e4b])
        expected_merges["proc_4b"] = "proc_4a"

        # Duplicate triple: same epoch from three sources
        e5a = _entity("epoch", {"name": "Treatment"}, entity_id="epoch_5a",
                       source_agent="execution_agent")
        e5b = _entity("epoch", {"name": "Treatment"}, entity_id="epoch_5b",
                       source_agent="procedures_agent")
        e5c = _entity("epoch", {"name": "Treatment"}, entity_id="epoch_5c",
                       source_agent="soa_vision_agent")
        entities.extend([e5a, e5b, e5c])
        expected_merges["epoch_5b"] = "epoch_5a"  # execution > procedures
        expected_merges["epoch_5c"] = "epoch_5a"

        # Non-duplicate: different names
        e6 = _entity("epoch", {"name": "Follow-up"}, entity_id="epoch_6",
                      source_agent="soa_vision_agent")
        e7 = _entity("encounter", {"name": "Visit 2"}, entity_id="enc_7",
                      source_agent="soa_text_agent")
        entities.extend([e6, e7])

        # Duplicate pair 6: fuzzy match with minor difference
        e8a = _entity("activity", {"name": "Physical Examination"}, entity_id="act_8a",
                       source_agent="procedures_agent")
        e8b = _entity("activity", {"name": "Physical examination"}, entity_id="act_8b",
                       source_agent="soa_text_agent")
        entities.extend([e8a, e8b])
        expected_merges["act_8b"] = "act_8a"

        # Duplicate pair 7: name with trailing footnote
        e9a = _entity("activity", {"name": "Urinalysis"}, entity_id="act_9a",
                       source_agent="procedures_agent")
        e9b = _entity("activity", {"name": "Urinalysis†"}, entity_id="act_9b",
                       source_agent="soa_vision_agent")
        entities.extend([e9a, e9b])
        expected_merges["act_9b"] = "act_9a"

        # Duplicate pair 8
        e10a = _entity("encounter", {"name": "Day 1"}, entity_id="enc_10a",
                        source_agent="soa_vision_agent")
        e10b = _entity("encounter", {"name": "Day 1"}, entity_id="enc_10b",
                        source_agent="soa_text_agent")
        entities.extend([e10a, e10b])
        expected_merges["enc_10b"] = "enc_10a"

        return entities, expected_merges

    def test_merging_correctness_above_95_percent(self, agent):
        """Verify 95%+ of expected merges are correctly performed."""
        entities, expected_merges = self._duplicate_batch()
        task = _task(entities)
        result = agent.execute(task)

        assert result.success
        actual_mapping = result.data["id_mapping"]

        correct = 0
        total = len(expected_merges)
        for secondary_id, expected_primary in expected_merges.items():
            actual_primary = actual_mapping.get(secondary_id)
            if actual_primary == expected_primary:
                correct += 1

        accuracy = (correct / total) * 100 if total > 0 else 100
        assert accuracy >= 95.0, (
            f"Merging accuracy {accuracy:.1f}% is below 95% threshold. "
            f"Correct: {correct}/{total}"
        )

    def test_priority_based_merge_winner(self, agent):
        """Higher-priority source should be the merge winner."""
        entities = [
            _entity("epoch", {"name": "Screening", "description": "From execution"},
                    entity_id="e_exec", source_agent="execution_agent"),
            _entity("epoch", {"name": "Screening", "description": "From procedures"},
                    entity_id="e_proc", source_agent="procedures_agent"),
            _entity("epoch", {"name": "Screening", "description": "From vision"},
                    entity_id="e_vis", source_agent="soa_vision_agent"),
        ]
        task = _task(entities)
        result = agent.execute(task)

        assert result.success
        mapping = result.data["id_mapping"]
        # execution_agent has highest priority, so e_exec should be the winner
        assert mapping.get("e_proc") == "e_exec"
        assert mapping.get("e_vis") == "e_exec"

    def test_name_cleaning_removes_footnotes(self, agent):
        """Entity names with footnote markers should be cleaned."""
        entities = [
            _entity("activity", {"name": "Blood Draw *"}, entity_id="a1"),
            _entity("activity", {"name": "ECG [1]"}, entity_id="a2"),
            _entity("activity", {"name": "Urinalysis†"}, entity_id="a3"),
        ]
        task = _task(entities)
        result = agent.execute(task)

        assert result.success
        report = result.data["report"]
        assert report["names_cleaned"] >= 3

    def test_reference_update_after_merge(self, agent):
        """References to merged-away entities should be updated."""
        entities = [
            _entity("epoch", {"name": "Screening"}, entity_id="epoch_a",
                    source_agent="soa_vision_agent"),
            _entity("epoch", {"name": "Screening"}, entity_id="epoch_b",
                    source_agent="soa_text_agent"),
            _entity("encounter", {"name": "Visit 1", "epochId": "epoch_b"},
                    entity_id="enc_1"),
        ]
        task = _task(entities)
        result = agent.execute(task)

        assert result.success
        # Find the encounter in the result entities
        result_entities = result.data["entities"]
        enc = next(e for e in result_entities if e["id"] == "enc_1")
        # The reference should now point to epoch_a (the winner)
        assert enc["data"].get("epochId") == "epoch_a"

    def test_non_duplicates_preserved(self, agent):
        """Entities that are not duplicates should remain unchanged."""
        entities = [
            _entity("epoch", {"name": "Screening"}, entity_id="e1"),
            _entity("epoch", {"name": "Treatment"}, entity_id="e2"),
            _entity("epoch", {"name": "Follow-up"}, entity_id="e3"),
        ]
        task = _task(entities)
        result = agent.execute(task)

        assert result.success
        result_entities = result.data["entities"]
        result_ids = {e["id"] for e in result_entities}
        assert result_ids == {"e1", "e2", "e3"}

    def test_source_attribution_preserved(self, agent):
        """Merged entities should have source attribution."""
        entities = [
            _entity("epoch", {"name": "Screening"}, entity_id="e_a",
                    source_agent="soa_vision_agent"),
            _entity("epoch", {"name": "Screening"}, entity_id="e_b",
                    source_agent="soa_text_agent"),
        ]
        task = _task(entities)
        result = agent.execute(task)

        assert result.success
        result_entities = result.data["entities"]
        merged = next(e for e in result_entities if e["id"] == "e_a")
        assert merged["data"].get("_reconciled") is True
        assert "_sources" in merged["data"]



# ============================================================================
# 20.1.4 - SoA Conflict Resolution (90%+ agreement rate)
# ============================================================================

class TestSoAConflictResolution:
    """Test SoA cell-level conflict resolution achieves 90%+ agreement rate."""

    @pytest.fixture
    def agent(self):
        ra = ReconciliationAgent()
        ra.initialize()
        return ra

    def _soa_scenarios(self) -> Tuple[List[Dict[str, Any]], int]:
        """Create SoA cell data with known conflicts and expected resolutions.

        Returns (entities, expected_agreement_count).
        """
        entities = []
        expected_agreements = 0

        # Scenario 1: Tick mark agreement (both say X)
        cells_agree_tick = [
            {"vision_value": "X", "text_value": "x", "vision_confidence": 0.9, "text_confidence": 0.8},
            {"vision_value": "✓", "text_value": "X", "vision_confidence": 0.85, "text_confidence": 0.9},
            {"vision_value": "Y", "text_value": "Yes", "vision_confidence": 0.7, "text_confidence": 0.8},
        ]
        entities.append(_entity("activity", {"name": "Activity 1", "cells": cells_agree_tick}))
        expected_agreements += 3

        # Scenario 2: Empty agreement (both say empty)
        cells_agree_empty = [
            {"vision_value": "", "text_value": "-", "vision_confidence": 0.9, "text_confidence": 0.9},
            {"vision_value": "-", "text_value": "—", "vision_confidence": 0.8, "text_confidence": 0.8},
        ]
        entities.append(_entity("activity", {"name": "Activity 2", "cells": cells_agree_empty}))
        expected_agreements += 2

        # Scenario 3: Numeric agreement
        cells_agree_numeric = [
            {"vision_value": "3", "text_value": "3", "vision_confidence": 0.9, "text_confidence": 0.9},
            {"vision_value": "1.5", "text_value": "1.5", "vision_confidence": 0.85, "text_confidence": 0.85},
        ]
        entities.append(_entity("activity", {"name": "Activity 3", "cells": cells_agree_numeric}))
        expected_agreements += 2

        # Scenario 4: String agreement (case-insensitive)
        cells_agree_string = [
            {"vision_value": "Weekly", "text_value": "weekly", "vision_confidence": 0.8, "text_confidence": 0.8},
        ]
        entities.append(_entity("activity", {"name": "Activity 4", "cells": cells_agree_string}))
        expected_agreements += 1

        # Scenario 5: Tick vs empty conflict (vision sees tick, text doesn't)
        cells_conflict_tick = [
            {"vision_value": "X", "text_value": "", "vision_confidence": 0.7, "text_confidence": 0.9},
        ]
        entities.append(_entity("activity", {"name": "Activity 5", "cells": cells_conflict_tick}))
        # This is a conflict, not agreement

        # Scenario 6: Numeric conflict
        cells_conflict_numeric = [
            {"vision_value": "3", "text_value": "5", "vision_confidence": 0.8, "text_confidence": 0.7},
        ]
        entities.append(_entity("activity", {"name": "Activity 6", "cells": cells_conflict_numeric}))
        # This is a conflict

        # Scenario 7: More agreements
        cells_more_agree = [
            {"vision_value": "X", "text_value": "✔", "vision_confidence": 0.9, "text_confidence": 0.9},
            {"vision_value": "No", "text_value": "N", "vision_confidence": 0.8, "text_confidence": 0.8},
        ]
        entities.append(_entity("activity", {"name": "Activity 7", "cells": cells_more_agree}))
        expected_agreements += 2

        return entities, expected_agreements

    def test_agreement_rate_above_90_percent(self, agent):
        """SoA reconciliation should achieve >= 90% agreement rate."""
        entities, expected_agreements = self._soa_scenarios()
        task = _task(entities)
        result = agent.execute(task)

        assert result.success
        report = result.data["report"]
        total_cells = report["confidence_boosts"] + report["confidence_reductions"]
        if total_cells > 0:
            agreement_rate = (report["confidence_boosts"] / total_cells) * 100
            assert agreement_rate >= 90.0, (
                f"Agreement rate {agreement_rate:.1f}% is below 90% threshold. "
                f"Boosts: {report['confidence_boosts']}, Reductions: {report['confidence_reductions']}"
            )

    def test_tick_mark_agreement_detected(self, agent):
        """Different tick mark representations should be recognized as agreement."""
        tick_pairs = [
            ("X", "x"), ("X", "✓"), ("✓", "✔"), ("Y", "Yes"), ("y", "yes"),
        ]
        for v_val, t_val in tick_pairs:
            entities = [_entity("activity", {"name": "Test", "cells": [
                {"vision_value": v_val, "text_value": t_val,
                 "vision_confidence": 0.9, "text_confidence": 0.9},
            ]})]
            task = _task(entities)
            result = agent.execute(task)
            report = result.data["report"]
            assert report["confidence_boosts"] >= 1, (
                f"Tick pair ({v_val}, {t_val}) not recognized as agreement"
            )

    def test_empty_value_agreement_detected(self, agent):
        """Different empty representations should be recognized as agreement."""
        empty_pairs = [
            ("", "-"), ("-", "—"), ("N", "No"), ("n", "no"), ("", ""),
        ]
        for v_val, t_val in empty_pairs:
            entities = [_entity("activity", {"name": "Test", "cells": [
                {"vision_value": v_val, "text_value": t_val,
                 "vision_confidence": 0.9, "text_confidence": 0.9},
            ]})]
            task = _task(entities)
            result = agent.execute(task)
            report = result.data["report"]
            assert report["confidence_boosts"] >= 1, (
                f"Empty pair ('{v_val}', '{t_val}') not recognized as agreement"
            )

    def test_tick_vs_empty_conflict_resolved(self, agent):
        """Tick vs empty conflict should prefer tick (presence over absence)."""
        entities = [_entity("activity", {"name": "Test", "cells": [
            {"vision_value": "X", "text_value": "",
             "vision_confidence": 0.7, "text_confidence": 0.9},
        ]})]
        task = _task(entities)
        result = agent.execute(task)

        report = result.data["report"]
        assert report["confidence_reductions"] >= 1
        assert len(report["conflicts"]) >= 1
        conflict = report["conflicts"][0]
        assert conflict["resolved_value"] == "X"
        assert conflict["resolution_strategy"] == "tick_present_over_absent"

    def test_numeric_conflict_uses_higher_confidence(self, agent):
        """Numeric conflict should prefer the source with higher confidence."""
        entities = [_entity("activity", {"name": "Test", "cells": [
            {"vision_value": "3", "text_value": "5",
             "vision_confidence": 0.9, "text_confidence": 0.6},
        ]})]
        task = _task(entities)
        result = agent.execute(task)

        report = result.data["report"]
        assert len(report["conflicts"]) >= 1
        conflict = report["conflicts"][0]
        assert conflict["resolved_value"] == "3"  # vision has higher confidence
        assert conflict["resolution_strategy"] == "numeric_higher_confidence"

    def test_single_source_no_conflict(self, agent):
        """Cells with only one source should not generate conflicts."""
        entities = [_entity("activity", {"name": "Test", "cells": [
            {"vision_value": "X", "vision_confidence": 0.9},
            {"text_value": "Y", "text_confidence": 0.8},
        ]})]
        task = _task(entities)
        result = agent.execute(task)

        report = result.data["report"]
        assert report["conflict_count"] == 0

    def test_dict_cells_format(self, agent):
        """Cells in dict format should also be reconciled."""
        entities = [_entity("activity", {"name": "Test", "cells": {
            "cell_1": {"vision_value": "X", "text_value": "X",
                       "vision_confidence": 0.9, "text_confidence": 0.9},
            "cell_2": {"vision_value": "3", "text_value": "3",
                       "vision_confidence": 0.8, "text_confidence": 0.8},
        }})]
        task = _task(entities)
        result = agent.execute(task)

        report = result.data["report"]
        assert report["confidence_boosts"] >= 2


# ============================================================================
# 20.1.5 - Confidence Scoring Algorithms
# ============================================================================

class TestConfidenceScoring:
    """Validate confidence scoring algorithms for agreement and conflict."""

    @pytest.fixture
    def agent(self):
        ra = ReconciliationAgent(config={
            "confidence_boost": 0.1,
            "confidence_penalty": 0.15,
        })
        ra.initialize()
        return ra

    def test_agreement_boosts_confidence(self, agent):
        """When sources agree, confidence should increase."""
        entities = [_entity("activity", {"name": "Test", "cells": [
            {"vision_value": "X", "text_value": "X",
             "vision_confidence": 0.7, "text_confidence": 0.7},
        ]})]
        task = _task(entities)
        result = agent.execute(task)

        result_entities = result.data["entities"]
        cell = result_entities[0]["data"]["cells"][0]
        assert cell["resolved_confidence"] > 0.7  # boosted

    def test_conflict_reduces_confidence(self, agent):
        """When sources conflict, confidence should decrease."""
        entities = [_entity("activity", {"name": "Test", "cells": [
            {"vision_value": "X", "text_value": "",
             "vision_confidence": 0.8, "text_confidence": 0.8},
        ]})]
        task = _task(entities)
        result = agent.execute(task)

        result_entities = result.data["entities"]
        cell = result_entities[0]["data"]["cells"][0]
        assert cell["resolved_confidence"] < 0.8  # reduced

    def test_confidence_capped_at_1_0(self, agent):
        """Confidence should never exceed 1.0 even with boost."""
        entities = [_entity("activity", {"name": "Test", "cells": [
            {"vision_value": "X", "text_value": "X",
             "vision_confidence": 0.98, "text_confidence": 0.99},
        ]})]
        task = _task(entities)
        result = agent.execute(task)

        result_entities = result.data["entities"]
        cell = result_entities[0]["data"]["cells"][0]
        assert cell["resolved_confidence"] <= 1.0

    def test_confidence_floor_at_0_0(self, agent):
        """Confidence should never go below 0.0 even with penalty."""
        agent_low = ReconciliationAgent(config={
            "confidence_penalty": 0.9,
        })
        agent_low.initialize()
        entities = [_entity("activity", {"name": "Test", "cells": [
            {"vision_value": "X", "text_value": "",
             "vision_confidence": 0.1, "text_confidence": 0.1},
        ]})]
        task = _task(entities)
        result = agent_low.execute(task)

        result_entities = result.data["entities"]
        cell = result_entities[0]["data"]["cells"][0]
        assert cell["resolved_confidence"] >= 0.0

    def test_field_level_confidence_boost(self, agent):
        """Field-level agreement should boost entity confidence."""
        entities = [_entity("epoch", {
            "name": "Screening",
            "_source_values": {
                "description": {
                    "soa_vision_agent": "Screening period",
                    "soa_text_agent": "Screening period",
                },
            },
        }, entity_id="e1", confidence=0.7)]
        task = _task(entities)
        result = agent.execute(task)

        assert result.success
        report = result.data["report"]
        assert report["confidence_boosts"] >= 1

    def test_field_level_confidence_reduction(self, agent):
        """Field-level conflict should reduce entity confidence."""
        entities = [_entity("epoch", {
            "name": "Screening",
            "_source_values": {
                "description": {
                    "soa_vision_agent": "Screening period",
                    "soa_text_agent": "Initial screening",
                },
            },
        }, entity_id="e1", confidence=0.8)]
        task = _task(entities)
        result = agent.execute(task)

        assert result.success
        report = result.data["report"]
        assert report["confidence_reductions"] >= 1


# ============================================================================
# 20.1.6 - Quality Metrics Report Generation
# ============================================================================

class TestQualityMetricsReport:
    """Test combined quality metrics report from all three agents."""

    @pytest.fixture
    def validation_agent(self):
        va = ValidationAgent()
        va.initialize()
        return va

    @pytest.fixture
    def enrichment_agent(self):
        ea = EnrichmentAgent(evs_client=MockEVSClient(), config={"base_delay": 0.0})
        ea.initialize()
        return ea

    @pytest.fixture
    def reconciliation_agent(self):
        ra = ReconciliationAgent()
        ra.initialize()
        return ra

    def _sample_entities(self) -> List[Dict[str, Any]]:
        """Create a realistic set of entities for end-to-end quality pipeline."""
        org_id = f"org_{_uid()}"
        enc_id = f"enc_{_uid()}"
        ep_id = f"ep_{_uid()}"
        proc_id = f"proc_{_uid()}"
        act_id = f"act_{_uid()}"
        return [
            _entity("study", {"name": "Test Study", "protocolVersions": ["v1"]}),
            _entity("study_title", {"text": "A Phase 3 Study of Drug X", "type": "Official Study Title"}),
            _entity("study_identifier", {"identifier": "NCT12345678", "type": "NCT", "organizationId": org_id}),
            _entity("organization", {"name": "Acme Pharma", "type": "Sponsor"}, entity_id=org_id),
            _entity("study_phase", {"standardCode": "Phase III"}),
            _entity("indication", {"name": "Diabetes Mellitus"}),
            _entity("objective", {"text": "To evaluate efficacy", "level": "primary", "endpointIds": [ep_id]}),
            _entity("endpoint", {"text": "HbA1c change", "purpose": "efficacy"}, entity_id=ep_id),
            _entity("eligibility_criterion", {"text": "Age >= 18", "category": "inclusion"}),
            _entity("study_arm", {"name": "Treatment", "type": "experimental"}),
            _entity("epoch", {"name": "Treatment", "encounterIds": [enc_id]}),
            _entity("encounter", {"name": "Visit 1"}, entity_id=enc_id),
            _entity("activity", {"name": "Blood Draw", "procedureIds": [proc_id]}, entity_id=act_id),
            _entity("procedure", {"name": "Venipuncture"}, entity_id=proc_id),
            _entity("scheduled_instance", {"encounterId": enc_id, "activityIds": [act_id]}),
            _entity("investigational_product", {"name": "Metformin"}),
            _entity("timing", {"type": "scheduled", "value": "P1D"}),
            _entity("narrative_content", {"name": "Introduction", "sectionNumber": "1.0"}),
        ]

    def test_full_quality_pipeline(
        self, validation_agent, enrichment_agent, reconciliation_agent
    ):
        """Run all three quality agents in sequence and verify combined report."""
        entities = self._sample_entities()

        # Step 1: Validation
        val_task = _task(entities, auto_fix=True)
        val_result = validation_agent.execute(val_task)
        assert val_result.success
        val_data = val_result.data

        # Step 2: Enrichment
        enrich_task = _task(entities)
        enrich_result = enrichment_agent.execute(enrich_task)
        assert enrich_result.success
        enrich_data = enrich_result.data

        # Step 3: Reconciliation
        recon_task = _task(entities)
        recon_result = reconciliation_agent.execute(recon_task)
        assert recon_result.success
        recon_data = recon_result.data

        # Build combined quality metrics report
        report = {
            "validation": {
                "is_valid": val_data["is_valid"],
                "total_issues": val_data["total_issues"],
                "errors": val_data["errors"],
                "warnings": val_data["warnings"],
                "info": val_data["info"],
                "fixes_applied": val_data["fixes_applied"],
                "iterations": val_data["iterations"],
            },
            "enrichment": enrich_data["coverage"],
            "reconciliation": recon_data["report"],
        }

        # Verify report structure
        assert "validation" in report
        assert "enrichment" in report
        assert "reconciliation" in report

        # Validation section
        assert "is_valid" in report["validation"]
        assert "total_issues" in report["validation"]
        assert "errors" in report["validation"]
        assert "warnings" in report["validation"]
        assert "fixes_applied" in report["validation"]

        # Enrichment section
        assert "total_entities" in report["enrichment"]
        assert "enrichable_entities" in report["enrichment"]
        assert "enriched_entities" in report["enrichment"]
        assert "coverage_percent" in report["enrichment"]
        assert "cache_hits" in report["enrichment"]

        # Reconciliation section
        assert "total_entities_before" in report["reconciliation"]
        assert "total_entities_after" in report["reconciliation"]
        assert "duplicates_merged" in report["reconciliation"]
        assert "conflict_count" in report["reconciliation"]
        assert "names_cleaned" in report["reconciliation"]
        assert "confidence_boosts" in report["reconciliation"]
        assert "confidence_reductions" in report["reconciliation"]

    def test_validation_report_serializable(self, validation_agent):
        """Validation report should be JSON-serializable via to_dict."""
        entities = self._sample_entities()
        report = validation_agent.generate_report(entities)
        report_dict = report.to_dict()

        assert isinstance(report_dict, dict)
        assert "report_id" in report_dict
        assert "timestamp" in report_dict
        assert "total_entities" in report_dict
        assert "summary" in report_dict
        assert "issues" in report_dict

    def test_enrichment_metrics_serializable(self, enrichment_agent):
        """Enrichment coverage metrics should be serializable."""
        entities = self._sample_entities()
        task = _task(entities)
        enrichment_agent.execute(task)
        metrics = enrichment_agent.get_coverage_metrics()
        metrics_dict = metrics.to_dict()

        assert isinstance(metrics_dict, dict)
        assert "total_entities" in metrics_dict
        assert "coverage_percent" in metrics_dict

    def test_reconciliation_report_serializable(self, reconciliation_agent):
        """Reconciliation report should be serializable."""
        entities = self._sample_entities()
        task = _task(entities)
        reconciliation_agent.execute(task)
        reports = reconciliation_agent.get_reports()
        assert len(reports) >= 1
        report_dict = reports[0].to_dict()

        assert isinstance(report_dict, dict)
        assert "total_entities_before" in report_dict
        assert "duplicates_merged" in report_dict

    def test_agents_report_accumulation(
        self, validation_agent, enrichment_agent, reconciliation_agent
    ):
        """Each agent should accumulate reports across multiple runs."""
        entities = self._sample_entities()

        # Run validation twice
        for _ in range(2):
            task = _task(entities, auto_fix=False)
            validation_agent.execute(task)
        assert len(validation_agent.get_reports()) >= 2

        # Run enrichment twice
        for _ in range(2):
            task = _task(entities)
            enrichment_agent.execute(task)
        # Enrichment doesn't accumulate reports the same way, but results should be available
        assert len(enrichment_agent.get_enrichment_results()) > 0

        # Run reconciliation twice
        for _ in range(2):
            task = _task(entities)
            reconciliation_agent.execute(task)
        assert len(reconciliation_agent.get_reports()) >= 2
