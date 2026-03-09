"""
Tests for EnrichmentAgent.

Covers:
- EnrichmentAgent lifecycle (init, capabilities, state)
- Entity identification for enrichment
- EVS query and code matching
- Code ranking and selection
- EVS response caching
- Enrichment coverage metrics
- API failure handling with retry
- Manual code overrides
- Context Store updates
- Provenance (automatic vs manual)
- 100 entities with known NCI codes (parametrized)
"""

import pytest
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

from agents.base import AgentCapabilities, AgentResult, AgentState, AgentTask
from agents.context_store import ContextEntity, ContextStore, EntityProvenance
from agents.quality.enrichment_agent import (
    ENRICHABLE_ENTITY_TYPES,
    DefaultEVSAPIClient,
    EVSCache,
    EVSConcept,
    EnrichmentAgent,
    EnrichmentCoverageMetrics,
    EnrichmentResult,
    compute_relevance_score,
    rank_concepts,
)


# ---------------------------------------------------------------------------
# Mock EVS Client
# ---------------------------------------------------------------------------

class MockEVSClient:
    """Mock EVS API client for testing."""

    def __init__(self, responses: Optional[Dict[str, List[EVSConcept]]] = None, fail_count: int = 0):
        self.responses = responses or {}
        self.fail_count = fail_count
        self._call_count = 0
        self.calls: List[str] = []

    def search_concepts(self, term: str, max_results: int = 10) -> List[EVSConcept]:
        self._call_count += 1
        self.calls.append(term)
        if self._call_count <= self.fail_count:
            raise ConnectionError(f"Simulated EVS API failure (call {self._call_count})")
        return self.responses.get(term.lower().strip(), [])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_concept(code: str, name: str, synonyms: Optional[List[str]] = None) -> EVSConcept:
    return EVSConcept(code=code, name=name, synonyms=synonyms or [])


def _make_entity(
    entity_type: str,
    data: Dict[str, Any],
    entity_id: Optional[str] = None,
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
        agent_id="enrichment_agent",
        task_type="enrich_entities",
        input_data=input_data,
    )


def _make_context_entity(entity_type: str, name: str, entity_id: Optional[str] = None) -> ContextEntity:
    eid = entity_id or f"{entity_type}_{uuid.uuid4().hex[:6]}"
    return ContextEntity(
        id=eid,
        entity_type=entity_type,
        data={"name": name},
        provenance=EntityProvenance(
            entity_id=eid,
            source_agent_id="test_agent",
            confidence_score=0.8,
        ),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_evs():
    """Mock EVS client with some standard responses."""
    return MockEVSClient(responses={
        "diabetes mellitus": [
            _make_concept("C2985", "Diabetes Mellitus", ["DM", "Diabetes"]),
            _make_concept("C26747", "Diabetes Mellitus Type 2", ["T2DM"]),
        ],
        "aspirin": [
            _make_concept("C287", "Aspirin", ["Acetylsalicylic Acid", "ASA"]),
        ],
        "blood pressure measurement": [
            _make_concept("C25298", "Blood Pressure Measurement"),
        ],
        "hypertension": [
            _make_concept("C3117", "Hypertension", ["High Blood Pressure", "HTN"]),
        ],
    })


@pytest.fixture
def agent(mock_evs):
    ea = EnrichmentAgent(evs_client=mock_evs, config={"base_delay": 0.0})
    ea.initialize()
    return ea


@pytest.fixture
def context_store():
    return ContextStore()


# ---------------------------------------------------------------------------
# Lifecycle tests
# ---------------------------------------------------------------------------

class TestEnrichmentAgentLifecycle:
    def test_init_default(self):
        ea = EnrichmentAgent()
        assert ea.agent_id == "enrichment_agent"
        assert ea.state == AgentState.INITIALIZING

    def test_initialize_sets_ready(self, agent):
        assert agent.state == AgentState.READY

    def test_terminate_sets_terminated(self, agent):
        agent.terminate()
        assert agent.state == AgentState.TERMINATED

    def test_capabilities(self, agent):
        caps = agent.get_capabilities()
        assert caps.agent_type == "enrichment"
        assert "context_data" in caps.input_types
        assert "enriched_entities" in caps.output_types

    def test_custom_agent_id(self):
        ea = EnrichmentAgent(agent_id="custom_enrichment")
        assert ea.agent_id == "custom_enrichment"

    def test_terminate_clears_cache(self, agent):
        agent._cache.put("test", [_make_concept("C1", "Test")])
        assert agent._cache.size == 1
        agent.terminate()
        assert agent._cache.size == 0


# ---------------------------------------------------------------------------
# Entity identification tests
# ---------------------------------------------------------------------------

class TestEntityIdentification:
    def test_enrichable_types_identified(self, agent):
        entities = [
            _make_entity("indication", {"name": "Diabetes Mellitus"}),
            _make_entity("procedure", {"name": "Blood Draw"}),
            _make_entity("investigational_product", {"name": "Aspirin"}),
            _make_entity("study_intervention", {"name": "Placebo"}),
            _make_entity("medical_device", {"name": "Blood Pressure Monitor"}),
        ]
        enrichable = agent._identify_enrichable_entities(entities)
        assert len(enrichable) == 5

    def test_non_enrichable_types_excluded(self, agent):
        entities = [
            _make_entity("study", {"name": "Test Study"}),
            _make_entity("epoch", {"name": "Screening"}),
            _make_entity("study_arm", {"name": "Arm A"}),
        ]
        enrichable = agent._identify_enrichable_entities(entities)
        assert len(enrichable) == 0

    def test_entities_without_name_excluded(self, agent):
        entities = [
            _make_entity("indication", {"description": "Some indication"}),
            _make_entity("indication", {"name": ""}),
            _make_entity("indication", {"name": "  "}),
        ]
        enrichable = agent._identify_enrichable_entities(entities)
        assert len(enrichable) == 0

    def test_mixed_entities(self, agent):
        entities = [
            _make_entity("indication", {"name": "Diabetes"}),
            _make_entity("study", {"name": "Study A"}),
            _make_entity("procedure", {"name": "Biopsy"}),
        ]
        enrichable = agent._identify_enrichable_entities(entities)
        assert len(enrichable) == 2


# ---------------------------------------------------------------------------
# Code ranking tests
# ---------------------------------------------------------------------------

class TestCodeRanking:
    def test_exact_match_scores_1(self):
        concept = _make_concept("C1", "Diabetes Mellitus")
        score = compute_relevance_score("Diabetes Mellitus", concept)
        assert score == 1.0

    def test_exact_match_case_insensitive(self):
        concept = _make_concept("C1", "Diabetes Mellitus")
        score = compute_relevance_score("diabetes mellitus", concept)
        assert score == 1.0

    def test_synonym_match_scores_0_9(self):
        concept = _make_concept("C1", "Diabetes Mellitus", ["DM", "Diabetes"])
        score = compute_relevance_score("DM", concept)
        assert score == 0.9

    def test_containment_scores_0_7(self):
        concept = _make_concept("C1", "Diabetes Mellitus Type 2")
        score = compute_relevance_score("Diabetes Mellitus", concept)
        assert score == 0.7

    def test_synonym_containment_scores_0_6(self):
        concept = _make_concept("C1", "Aspirin", ["Acetylsalicylic Acid"])
        score = compute_relevance_score("Acetylsalicylic", concept)
        assert score == 0.6

    def test_no_match_scores_low(self):
        concept = _make_concept("C1", "Aspirin")
        score = compute_relevance_score("Completely Unrelated", concept)
        assert score < 0.3

    def test_rank_concepts_sorted_descending(self):
        concepts = [
            _make_concept("C1", "Diabetes Type 1"),
            _make_concept("C2", "Diabetes Mellitus"),
            _make_concept("C3", "Unrelated Concept"),
        ]
        ranked = rank_concepts("Diabetes Mellitus", concepts)
        assert ranked[0][0].code == "C2"
        assert ranked[0][1] == 1.0

    def test_word_overlap_partial_score(self):
        concept = _make_concept("C1", "Blood Pressure")
        score = compute_relevance_score("Blood Test", concept)
        assert 0.0 < score < 0.5


# ---------------------------------------------------------------------------
# EVS Cache tests
# ---------------------------------------------------------------------------

class TestEVSCache:
    def test_put_and_get(self):
        cache = EVSCache()
        concepts = [_make_concept("C1", "Test")]
        cache.put("test term", concepts)
        assert cache.get("test term") == concepts

    def test_case_insensitive(self):
        cache = EVSCache()
        concepts = [_make_concept("C1", "Test")]
        cache.put("Test Term", concepts)
        assert cache.get("test term") == concepts

    def test_miss_returns_none(self):
        cache = EVSCache()
        assert cache.get("nonexistent") is None

    def test_lru_eviction(self):
        cache = EVSCache(max_size=2)
        cache.put("a", [_make_concept("C1", "A")])
        cache.put("b", [_make_concept("C2", "B")])
        cache.put("c", [_make_concept("C3", "C")])
        assert cache.get("a") is None  # evicted
        assert cache.get("b") is not None
        assert cache.get("c") is not None

    def test_access_refreshes_lru(self):
        cache = EVSCache(max_size=2)
        cache.put("a", [_make_concept("C1", "A")])
        cache.put("b", [_make_concept("C2", "B")])
        cache.get("a")  # refresh 'a'
        cache.put("c", [_make_concept("C3", "C")])
        assert cache.get("a") is not None  # still present
        assert cache.get("b") is None  # evicted

    def test_clear(self):
        cache = EVSCache()
        cache.put("a", [])
        cache.clear()
        assert cache.size == 0

    def test_contains(self):
        cache = EVSCache()
        cache.put("test", [])
        assert cache.contains("test")
        assert not cache.contains("other")


# ---------------------------------------------------------------------------
# EVS query and retry tests
# ---------------------------------------------------------------------------

class TestEVSQueryAndRetry:
    def test_successful_query(self, agent, mock_evs):
        concepts = agent._query_evs_with_cache("Diabetes Mellitus")
        assert concepts is not None
        assert len(concepts) == 2
        assert concepts[0].code == "C2985"

    def test_query_caches_result(self, agent, mock_evs):
        agent._query_evs_with_cache("Aspirin")
        assert agent._cache.contains("aspirin")
        # Second call should hit cache
        agent._query_evs_with_cache("Aspirin")
        assert agent._coverage.cache_hits == 1

    def test_retry_on_failure(self):
        # Fail first 2 calls, succeed on 3rd
        client = MockEVSClient(
            responses={"test": [_make_concept("C1", "Test")]},
            fail_count=2,
        )
        ea = EnrichmentAgent(evs_client=client, config={"base_delay": 0.0, "max_retries": 3})
        ea.initialize()
        concepts = ea._query_evs_with_retry("test")
        assert concepts is not None
        assert len(concepts) == 1
        assert ea._coverage.api_failures == 2
        assert ea._coverage.api_calls == 3

    def test_all_retries_fail(self):
        client = MockEVSClient(fail_count=10)
        ea = EnrichmentAgent(evs_client=client, config={"base_delay": 0.0, "max_retries": 3})
        ea.initialize()
        result = ea._query_evs_with_retry("test")
        assert result is None
        assert ea._coverage.api_failures == 3
        assert ea._coverage.api_calls == 3

    def test_empty_results_cached(self, agent, mock_evs):
        concepts = agent._query_evs_with_cache("unknown_term_xyz")
        assert concepts is not None
        assert len(concepts) == 0
        assert agent._cache.contains("unknown_term_xyz")


# ---------------------------------------------------------------------------
# Execute and enrichment tests
# ---------------------------------------------------------------------------

class TestExecuteEnrichment:
    def test_execute_enriches_entities(self, agent):
        entities = [
            _make_entity("indication", {"name": "Diabetes Mellitus"}),
            _make_entity("procedure", {"name": "Blood Pressure Measurement"}),
        ]
        task = _make_task(entities)
        result = agent.execute(task)
        assert result.success
        enrichment_results = result.data["enrichment_results"]
        assert len(enrichment_results) == 2
        assert enrichment_results[0]["enriched"]
        assert enrichment_results[0]["code"] == "C2985"

    def test_execute_no_entities_fails(self, agent):
        task = _make_task([])
        result = agent.execute(task)
        assert not result.success
        assert "No entities" in result.error

    def test_execute_skips_non_enrichable(self, agent):
        entities = [
            _make_entity("study", {"name": "Test Study"}),
            _make_entity("indication", {"name": "Diabetes Mellitus"}),
        ]
        task = _make_task(entities)
        result = agent.execute(task)
        assert result.success
        assert len(result.data["enrichment_results"]) == 1

    def test_execute_from_context_store(self, agent, context_store):
        entity = _make_context_entity("indication", "Hypertension")
        context_store.add_entity(entity)
        agent.set_context_store(context_store)
        task = AgentTask(
            task_id="t1", agent_id="enrichment_agent", task_type="enrich_entities",
            input_data={},
        )
        result = agent.execute(task)
        assert result.success

    def test_execute_coverage_metrics(self, agent):
        entities = [
            _make_entity("indication", {"name": "Diabetes Mellitus"}),
            _make_entity("indication", {"name": "Hypertension"}),
            _make_entity("study", {"name": "Study A"}),
        ]
        task = _make_task(entities)
        result = agent.execute(task)
        coverage = result.data["coverage"]
        assert coverage["total_entities"] == 3
        assert coverage["enrichable_entities"] == 2
        assert coverage["enriched_entities"] == 2
        assert coverage["coverage_percent"] == 100.0

    def test_execute_with_api_failure(self):
        client = MockEVSClient(fail_count=100)
        ea = EnrichmentAgent(evs_client=client, config={"base_delay": 0.0, "max_retries": 2})
        ea.initialize()
        entities = [_make_entity("indication", {"name": "Something"})]
        task = _make_task(entities)
        result = ea.execute(task)
        assert result.success  # Agent succeeds even if enrichment fails
        coverage = result.data["coverage"]
        assert coverage["failed_entities"] == 1
        assert coverage["enriched_entities"] == 0


# ---------------------------------------------------------------------------
# Manual override tests
# ---------------------------------------------------------------------------

class TestManualOverrides:
    def test_manual_override_applied(self, agent):
        entity_id = "ind_001"
        agent.set_manual_override(entity_id, "C99999")
        entities = [_make_entity("indication", {"name": "Custom Indication"}, entity_id=entity_id)]
        task = _make_task(entities)
        result = agent.execute(task)
        enrichment_results = result.data["enrichment_results"]
        assert enrichment_results[0]["code"] == "C99999"
        assert enrichment_results[0]["source"] == "manual"

    def test_manual_override_via_task_input(self, agent):
        entity_id = "ind_002"
        entities = [_make_entity("indication", {"name": "Custom"}, entity_id=entity_id)]
        task = _make_task(entities, manual_overrides={entity_id: "C88888"})
        result = agent.execute(task)
        enrichment_results = result.data["enrichment_results"]
        assert enrichment_results[0]["code"] == "C88888"
        assert enrichment_results[0]["source"] == "manual"

    def test_remove_manual_override(self, agent):
        agent.set_manual_override("e1", "C1")
        assert agent.remove_manual_override("e1")
        assert not agent.remove_manual_override("e1")

    def test_get_manual_overrides(self, agent):
        agent.set_manual_override("e1", "C1")
        agent.set_manual_override("e2", "C2")
        overrides = agent.get_manual_overrides()
        assert overrides == {"e1": "C1", "e2": "C2"}

    def test_manual_override_confidence_is_1(self, agent):
        entity_id = "ind_003"
        agent.set_manual_override(entity_id, "C77777")
        entities = [_make_entity("indication", {"name": "Override Test"}, entity_id=entity_id)]
        task = _make_task(entities)
        result = agent.execute(task)
        enrichment_results = result.data["enrichment_results"]
        assert enrichment_results[0]["confidence"] == 1.0


# ---------------------------------------------------------------------------
# Context Store update tests
# ---------------------------------------------------------------------------

class TestContextStoreUpdate:
    def test_enrichment_updates_context_store(self, agent, context_store):
        entity = _make_context_entity("indication", "Diabetes Mellitus", entity_id="ind_cs_1")
        context_store.add_entity(entity)
        agent.set_context_store(context_store)

        entities = [{
            "id": "ind_cs_1",
            "entity_type": "indication",
            "data": {"name": "Diabetes Mellitus"},
        }]
        task = _make_task(entities, context_store=context_store)
        result = agent.execute(task)
        assert result.success

        updated = context_store.get_entity("ind_cs_1")
        assert updated is not None
        assert "codes" in updated.data
        assert len(updated.data["codes"]) == 1
        assert updated.data["codes"][0]["code"] == "C2985"

    def test_enrichment_provenance_source_automatic(self, agent, context_store):
        entity = _make_context_entity("indication", "Aspirin", entity_id="ind_cs_2")
        # Aspirin is an investigational_product type, but let's use indication for simplicity
        # Actually let's use the right type
        entity.entity_type = "investigational_product"
        context_store.add_entity(entity)

        entities = [{
            "id": "ind_cs_2",
            "entity_type": "investigational_product",
            "data": {"name": "Aspirin"},
        }]
        task = _make_task(entities, context_store=context_store)
        result = agent.execute(task)
        assert result.success

        updated = context_store.get_entity("ind_cs_2")
        assert updated.data.get("_enrichment_source") == "automatic"

    def test_enrichment_provenance_source_manual(self, agent, context_store):
        entity = _make_context_entity("indication", "Custom Drug", entity_id="ind_cs_3")
        context_store.add_entity(entity)
        agent.set_manual_override("ind_cs_3", "C55555")

        entities = [{
            "id": "ind_cs_3",
            "entity_type": "indication",
            "data": {"name": "Custom Drug"},
        }]
        task = _make_task(entities, context_store=context_store)
        result = agent.execute(task)
        assert result.success

        updated = context_store.get_entity("ind_cs_3")
        assert updated.data.get("_enrichment_source") == "manual"

    def test_context_store_version_incremented(self, agent, context_store):
        entity = _make_context_entity("indication", "Hypertension", entity_id="ind_cs_4")
        context_store.add_entity(entity)
        original_version = entity.version

        entities = [{
            "id": "ind_cs_4",
            "entity_type": "indication",
            "data": {"name": "Hypertension"},
        }]
        task = _make_task(entities, context_store=context_store)
        agent.execute(task)

        updated = context_store.get_entity("ind_cs_4")
        assert updated.version > original_version


# ---------------------------------------------------------------------------
# Coverage metrics tests
# ---------------------------------------------------------------------------

class TestCoverageMetrics:
    def test_coverage_percent_calculation(self):
        m = EnrichmentCoverageMetrics(enrichable_entities=10, enriched_entities=8)
        assert m.coverage_percent == 80.0

    def test_coverage_percent_zero_enrichable(self):
        m = EnrichmentCoverageMetrics(enrichable_entities=0)
        assert m.coverage_percent == 0.0

    def test_cache_hit_rate(self):
        m = EnrichmentCoverageMetrics(cache_hits=3, cache_misses=7)
        assert m.cache_hit_rate == 30.0

    def test_cache_hit_rate_zero(self):
        m = EnrichmentCoverageMetrics()
        assert m.cache_hit_rate == 0.0

    def test_to_dict(self):
        m = EnrichmentCoverageMetrics(
            total_entities=10, enrichable_entities=5,
            enriched_entities=4, failed_entities=1,
        )
        d = m.to_dict()
        assert d["coverage_percent"] == 80.0
        assert d["total_entities"] == 10


# ---------------------------------------------------------------------------
# Data model tests
# ---------------------------------------------------------------------------

class TestDataModels:
    def test_evs_concept_round_trip(self):
        c = EVSConcept(code="C123", name="Test", synonyms=["T"], definition="Def")
        d = c.to_dict()
        c2 = EVSConcept.from_dict(d)
        assert c2.code == c.code
        assert c2.name == c.name
        assert c2.synonyms == c.synonyms

    def test_enrichment_result_enriched(self):
        r = EnrichmentResult(
            entity_id="e1", entity_type="indication", entity_name="Test",
            code="C1", confidence=0.9,
        )
        assert r.enriched
        d = r.to_dict()
        assert d["code"] == "C1"

    def test_enrichment_result_not_enriched(self):
        r = EnrichmentResult(
            entity_id="e1", entity_type="indication", entity_name="Test",
            error="No match",
        )
        assert not r.enriched
        d = r.to_dict()
        assert "code" not in d
        assert d["error"] == "No match"

    def test_enrichable_entity_types(self):
        assert "indication" in ENRICHABLE_ENTITY_TYPES
        assert "procedure" in ENRICHABLE_ENTITY_TYPES
        assert "investigational_product" in ENRICHABLE_ENTITY_TYPES
        assert "study_intervention" in ENRICHABLE_ENTITY_TYPES
        assert "medical_device" in ENRICHABLE_ENTITY_TYPES
        assert "study" not in ENRICHABLE_ENTITY_TYPES


# ---------------------------------------------------------------------------
# 100 entities with known NCI codes (parametrized test data)
# ---------------------------------------------------------------------------

# Test data: (entity_type, entity_name, expected_nci_code, display_name)
_KNOWN_NCI_ENTITIES = [
    # Indications (40 entities)
    ("indication", "Diabetes Mellitus", "C2985", "Diabetes Mellitus"),
    ("indication", "Hypertension", "C3117", "Hypertension"),
    ("indication", "Asthma", "C28397", "Asthma"),
    ("indication", "Breast Cancer", "C4872", "Breast Cancer"),
    ("indication", "Lung Cancer", "C4878", "Lung Cancer"),
    ("indication", "Rheumatoid Arthritis", "C2884", "Rheumatoid Arthritis"),
    ("indication", "Chronic Obstructive Pulmonary Disease", "C3199", "COPD"),
    ("indication", "Heart Failure", "C50577", "Heart Failure"),
    ("indication", "Atrial Fibrillation", "C50466", "Atrial Fibrillation"),
    ("indication", "Major Depressive Disorder", "C35078", "Major Depressive Disorder"),
    ("indication", "Schizophrenia", "C3362", "Schizophrenia"),
    ("indication", "Epilepsy", "C3020", "Epilepsy"),
    ("indication", "Multiple Sclerosis", "C3243", "Multiple Sclerosis"),
    ("indication", "Parkinson Disease", "C26845", "Parkinson Disease"),
    ("indication", "Alzheimer Disease", "C2866", "Alzheimer Disease"),
    ("indication", "Crohn Disease", "C2965", "Crohn Disease"),
    ("indication", "Ulcerative Colitis", "C3495", "Ulcerative Colitis"),
    ("indication", "Psoriasis", "C3346", "Psoriasis"),
    ("indication", "Melanoma", "C3224", "Melanoma"),
    ("indication", "Prostate Cancer", "C7378", "Prostate Cancer"),
    ("indication", "Colorectal Cancer", "C4978", "Colorectal Cancer"),
    ("indication", "Pancreatic Cancer", "C9005", "Pancreatic Cancer"),
    ("indication", "Ovarian Cancer", "C4908", "Ovarian Cancer"),
    ("indication", "Leukemia", "C3161", "Leukemia"),
    ("indication", "Lymphoma", "C3208", "Lymphoma"),
    ("indication", "Hepatitis C", "C3097", "Hepatitis C"),
    ("indication", "HIV Infection", "C14219", "HIV Infection"),
    ("indication", "Osteoporosis", "C3298", "Osteoporosis"),
    ("indication", "Migraine", "C34817", "Migraine"),
    ("indication", "Obesity", "C3283", "Obesity"),
    ("indication", "Type 2 Diabetes", "C26747", "Type 2 Diabetes Mellitus"),
    ("indication", "Anemia", "C2869", "Anemia"),
    ("indication", "Chronic Kidney Disease", "C9384", "Chronic Kidney Disease"),
    ("indication", "Gout", "C3070", "Gout"),
    ("indication", "Systemic Lupus Erythematosus", "C3375", "Systemic Lupus Erythematosus"),
    ("indication", "Pneumonia", "C3333", "Pneumonia"),
    ("indication", "Sepsis", "C3364", "Sepsis"),
    ("indication", "Stroke", "C3390", "Stroke"),
    ("indication", "Myocardial Infarction", "C27996", "Myocardial Infarction"),
    ("indication", "Deep Vein Thrombosis", "C2975", "Deep Vein Thrombosis"),
    # Procedures (25 entities)
    ("procedure", "Blood Pressure Measurement", "C25298", "Blood Pressure Measurement"),
    ("procedure", "Electrocardiogram", "C38033", "Electrocardiogram"),
    ("procedure", "Complete Blood Count", "C64844", "Complete Blood Count"),
    ("procedure", "Urinalysis", "C62662", "Urinalysis"),
    ("procedure", "Liver Function Test", "C62165", "Liver Function Test"),
    ("procedure", "Renal Function Test", "C62166", "Renal Function Test"),
    ("procedure", "Chest X-Ray", "C38101", "Chest X-Ray"),
    ("procedure", "MRI Scan", "C16809", "MRI Scan"),
    ("procedure", "CT Scan", "C17204", "CT Scan"),
    ("procedure", "PET Scan", "C17007", "PET Scan"),
    ("procedure", "Biopsy", "C15189", "Biopsy"),
    ("procedure", "Bone Marrow Biopsy", "C15192", "Bone Marrow Biopsy"),
    ("procedure", "Lumbar Puncture", "C15327", "Lumbar Puncture"),
    ("procedure", "Spirometry", "C38084", "Spirometry"),
    ("procedure", "Echocardiogram", "C38034", "Echocardiogram"),
    ("procedure", "Colonoscopy", "C16818", "Colonoscopy"),
    ("procedure", "Endoscopy", "C16546", "Endoscopy"),
    ("procedure", "Mammography", "C16818", "Mammography"),
    ("procedure", "Ultrasound", "C17230", "Ultrasound"),
    ("procedure", "Physical Examination", "C20989", "Physical Examination"),
    ("procedure", "Vital Signs", "C25710", "Vital Signs"),
    ("procedure", "Body Weight Measurement", "C25208", "Body Weight Measurement"),
    ("procedure", "Height Measurement", "C25347", "Height Measurement"),
    ("procedure", "BMI Calculation", "C16358", "BMI Calculation"),
    ("procedure", "Ophthalmologic Examination", "C38078", "Ophthalmologic Examination"),
    # Investigational Products (20 entities)
    ("investigational_product", "Aspirin", "C287", "Aspirin"),
    ("investigational_product", "Metformin", "C61612", "Metformin"),
    ("investigational_product", "Ibuprofen", "C561", "Ibuprofen"),
    ("investigational_product", "Atorvastatin", "C47396", "Atorvastatin"),
    ("investigational_product", "Lisinopril", "C29226", "Lisinopril"),
    ("investigational_product", "Amlodipine", "C47398", "Amlodipine"),
    ("investigational_product", "Omeprazole", "C29298", "Omeprazole"),
    ("investigational_product", "Metoprolol", "C29268", "Metoprolol"),
    ("investigational_product", "Warfarin", "C948", "Warfarin"),
    ("investigational_product", "Prednisone", "C770", "Prednisone"),
    ("investigational_product", "Insulin", "C545", "Insulin"),
    ("investigational_product", "Dexamethasone", "C422", "Dexamethasone"),
    ("investigational_product", "Pembrolizumab", "C106432", "Pembrolizumab"),
    ("investigational_product", "Nivolumab", "C68814", "Nivolumab"),
    ("investigational_product", "Trastuzumab", "C1647", "Trastuzumab"),
    ("investigational_product", "Rituximab", "C1441", "Rituximab"),
    ("investigational_product", "Bevacizumab", "C2039", "Bevacizumab"),
    ("investigational_product", "Adalimumab", "C65216", "Adalimumab"),
    ("investigational_product", "Infliximab", "C1873", "Infliximab"),
    ("investigational_product", "Etanercept", "C1879", "Etanercept"),
    # Study Interventions (10 entities)
    ("study_intervention", "Placebo", "C49648", "Placebo"),
    ("study_intervention", "Standard of Care", "C94626", "Standard of Care"),
    ("study_intervention", "Chemotherapy", "C15632", "Chemotherapy"),
    ("study_intervention", "Radiation Therapy", "C15313", "Radiation Therapy"),
    ("study_intervention", "Immunotherapy", "C15262", "Immunotherapy"),
    ("study_intervention", "Gene Therapy", "C15238", "Gene Therapy"),
    ("study_intervention", "Stem Cell Transplant", "C15431", "Stem Cell Transplant"),
    ("study_intervention", "Cognitive Behavioral Therapy", "C15170", "Cognitive Behavioral Therapy"),
    ("study_intervention", "Physical Therapy", "C15315", "Physical Therapy"),
    ("study_intervention", "Dietary Intervention", "C15222", "Dietary Intervention"),
    # Medical Devices (5 entities)
    ("medical_device", "Continuous Glucose Monitor", "C95405", "Continuous Glucose Monitor"),
    ("medical_device", "Cardiac Pacemaker", "C50185", "Cardiac Pacemaker"),
    ("medical_device", "Insulin Pump", "C95406", "Insulin Pump"),
    ("medical_device", "Blood Pressure Monitor", "C95407", "Blood Pressure Monitor"),
    ("medical_device", "Pulse Oximeter", "C95408", "Pulse Oximeter"),
]

assert len(_KNOWN_NCI_ENTITIES) == 100, f"Expected 100 entities, got {len(_KNOWN_NCI_ENTITIES)}"


def _build_100_entity_evs_responses() -> Dict[str, List[EVSConcept]]:
    """Build mock EVS responses for all 100 known entities."""
    responses: Dict[str, List[EVSConcept]] = {}
    for entity_type, name, code, display in _KNOWN_NCI_ENTITIES:
        key = name.lower().strip()
        responses[key] = [_make_concept(code, display, [name] if display != name else [])]
    return responses


@pytest.fixture
def agent_100():
    """Agent configured with mock EVS responses for all 100 entities."""
    responses = _build_100_entity_evs_responses()
    client = MockEVSClient(responses=responses)
    ea = EnrichmentAgent(evs_client=client, config={"base_delay": 0.0})
    ea.initialize()
    return ea


class TestWith100Entities:
    """Test enrichment with 100 entities with known NCI codes."""

    @pytest.mark.parametrize(
        "entity_type,entity_name,expected_code,display_name",
        _KNOWN_NCI_ENTITIES,
        ids=[f"{t}_{n.replace(' ', '_')[:30]}" for t, n, c, d in _KNOWN_NCI_ENTITIES],
    )
    def test_entity_enriched_with_correct_code(
        self, agent_100, entity_type, entity_name, expected_code, display_name
    ):
        entity = _make_entity(entity_type, {"name": entity_name})
        task = _make_task([entity])
        result = agent_100.execute(task)
        assert result.success
        enrichment_results = result.data["enrichment_results"]
        assert len(enrichment_results) == 1
        er = enrichment_results[0]
        assert er["enriched"], f"Entity '{entity_name}' was not enriched"
        assert er["code"] == expected_code, (
            f"Expected code {expected_code} for '{entity_name}', got {er['code']}"
        )

    def test_all_100_entities_in_batch(self, agent_100):
        """Run all 100 entities through enrichment in a single batch."""
        entities = [
            _make_entity(etype, {"name": name}, entity_id=f"batch_{i}")
            for i, (etype, name, code, display) in enumerate(_KNOWN_NCI_ENTITIES)
        ]
        task = _make_task(entities)
        result = agent_100.execute(task)
        assert result.success
        coverage = result.data["coverage"]
        assert coverage["total_entities"] == 100
        assert coverage["enrichable_entities"] == 100
        assert coverage["enriched_entities"] == 100
        assert coverage["coverage_percent"] == 100.0
        assert coverage["failed_entities"] == 0

    def test_batch_enrichment_codes_correct(self, agent_100):
        """Verify each entity in the batch got the correct code."""
        entities = [
            _make_entity(etype, {"name": name}, entity_id=f"verify_{i}")
            for i, (etype, name, code, display) in enumerate(_KNOWN_NCI_ENTITIES)
        ]
        task = _make_task(entities)
        result = agent_100.execute(task)
        enrichment_results = result.data["enrichment_results"]

        for i, er in enumerate(enrichment_results):
            expected_code = _KNOWN_NCI_ENTITIES[i][2]
            assert er["code"] == expected_code, (
                f"Entity {i} ({_KNOWN_NCI_ENTITIES[i][1]}): "
                f"expected {expected_code}, got {er['code']}"
            )
