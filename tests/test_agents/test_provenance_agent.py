"""
Tests for ProvenanceAgent.
"""

import json
import os
import tempfile
import pytest

from agents.base import AgentTask, AgentState
from agents.context_store import ContextStore, ContextEntity, EntityProvenance
from agents.support.provenance_agent import (
    ProvenanceAgent,
    ProvenanceRecord,
    ProvenanceSummary,
    determine_source_type,
    compute_aggregate_confidence,
    CONFIDENCE_WEIGHTS,
    LOW_CONFIDENCE_THRESHOLD,
)


# --- Helper ---

def _make_store(entities_spec):
    """Create a store with entities. entities_spec: list of (id, type, agent_id, confidence)."""
    store = ContextStore()
    for eid, etype, agent_id, conf in entities_spec:
        entity = ContextEntity(
            id=eid,
            entity_type=etype,
            data={"name": f"Entity {eid}"},
            provenance=EntityProvenance(
                entity_id=eid,
                source_agent_id=agent_id,
                confidence_score=conf,
                source_pages=[1, 2],
                model_used="gemini-2.5-pro",
            ),
        )
        store.add_entity(entity)
    return store


# --- Data Model Tests ---

class TestProvenanceRecord:
    def test_to_dict(self):
        r = ProvenanceRecord(
            entity_id="e1", entity_type="objective",
            source_agent_id="objectives-agent",
            confidence_score=0.85, source_pages=[1, 2],
            model_used="gemini", source_type="text",
        )
        d = r.to_dict()
        assert d["entity_id"] == "e1"
        assert d["confidence_score"] == 0.85
        assert d["source_type"] == "text"

    def test_defaults(self):
        r = ProvenanceRecord(entity_id="e1", entity_type="arm",
                             source_agent_id="test")
        assert r.confidence_score == 0.0
        assert r.source_type == "text"
        assert r.contributing_agents == []


class TestProvenanceSummary:
    def test_to_dict_empty(self):
        s = ProvenanceSummary()
        d = s.to_dict()
        assert d["total_entities"] == 0
        assert d["coverage_percent"] == 0.0

    def test_to_dict_with_data(self):
        s = ProvenanceSummary(
            total_entities=10,
            entities_with_provenance=8,
            avg_confidence=0.85,
            min_confidence=0.5,
            max_confidence=1.0,
        )
        d = s.to_dict()
        assert d["coverage_percent"] == 80.0
        assert d["avg_confidence"] == 0.85


# --- Utility Function Tests ---

class TestDetermineSourceType:
    def test_vision_agent(self):
        assert determine_source_type("soa-vision") == "vision"

    def test_text_agent(self):
        assert determine_source_type("metadata-agent") == "text"

    def test_reconciliation_agent(self):
        assert determine_source_type("reconciliation-agent") == "both"

    def test_enrichment_agent(self):
        assert determine_source_type("enrichment-agent") == "derived"

    def test_validation_agent(self):
        assert determine_source_type("validation-agent") == "derived"

    def test_generic_agent(self):
        assert determine_source_type("some-agent") == "text"


class TestComputeAggregateConfidence:
    def test_text_source(self):
        result = compute_aggregate_confidence(1.0, "text", 1)
        assert result == CONFIDENCE_WEIGHTS["text"]

    def test_vision_source(self):
        result = compute_aggregate_confidence(1.0, "vision", 1)
        assert result == CONFIDENCE_WEIGHTS["vision"]

    def test_both_source(self):
        result = compute_aggregate_confidence(1.0, "both", 1)
        assert result == CONFIDENCE_WEIGHTS["both"]

    def test_multi_agent_boost(self):
        single = compute_aggregate_confidence(0.9, "text", 1)
        multi = compute_aggregate_confidence(0.9, "text", 3)
        assert multi > single

    def test_boost_capped_at_point_one(self):
        result = compute_aggregate_confidence(0.95, "both", 10)
        assert result <= 1.0

    def test_zero_confidence(self):
        result = compute_aggregate_confidence(0.0, "text", 1)
        assert result == 0.0

    def test_never_exceeds_one(self):
        result = compute_aggregate_confidence(1.0, "both", 10)
        assert result <= 1.0

    def test_unknown_source_type(self):
        result = compute_aggregate_confidence(1.0, "unknown_type", 1)
        assert result == 0.75  # Default weight


# --- ProvenanceAgent Tests ---

class TestProvenanceAgent:
    def setup_method(self):
        self.agent = ProvenanceAgent()
        self.agent.initialize()

    def test_init(self):
        assert self.agent.agent_id == "provenance"
        assert self.agent.state == AgentState.READY

    def test_custom_config(self):
        agent = ProvenanceAgent(config={"low_confidence_threshold": 0.7})
        assert agent._low_confidence_threshold == 0.7

    def test_get_capabilities(self):
        caps = self.agent.get_capabilities()
        assert caps.agent_type == "support"
        assert "provenance_json" in caps.output_types

    def test_terminate(self):
        self.agent.terminate()
        assert self.agent.state == AgentState.TERMINATED

    def test_execute_no_context_store(self):
        task = AgentTask(task_id="t1", agent_id="provenance",
                         task_type="provenance_generate", input_data={})
        result = self.agent.execute(task)
        assert not result.success
        assert "Context Store" in result.error

    def test_generate_empty_store(self):
        store = ContextStore()
        self.agent.set_context_store(store)
        task = AgentTask(task_id="t1", agent_id="provenance",
                         task_type="provenance_generate", input_data={})
        result = self.agent.execute(task)
        assert result.success
        assert result.data["record_count"] == 0

    def test_generate_with_entities(self):
        store = _make_store([
            ("e1", "objective", "objectives-agent", 0.9),
            ("e2", "study_arm", "studydesign-agent", 0.85),
            ("e3", "eligibility_criterion", "eligibility-agent", 0.8),
        ])
        self.agent.set_context_store(store)

        task = AgentTask(task_id="t1", agent_id="provenance",
                         task_type="provenance_generate", input_data={})
        result = self.agent.execute(task)
        assert result.success
        assert result.data["record_count"] == 3
        assert result.data["summary"]["total_entities"] == 3

    def test_generate_skips_infrastructure_types(self):
        store = _make_store([
            ("e1", "objective", "objectives-agent", 0.9),
            ("pp1", "pdf_page", "pdf-parser", 1.0),
            ("cp1", "checkpoint", "checkpoint-agent", 1.0),
        ])
        self.agent.set_context_store(store)

        task = AgentTask(task_id="t1", agent_id="provenance",
                         task_type="provenance_generate", input_data={})
        result = self.agent.execute(task)
        assert result.success
        assert result.data["record_count"] == 1

    def test_generate_with_type_filter(self):
        store = _make_store([
            ("e1", "objective", "objectives-agent", 0.9),
            ("e2", "study_arm", "studydesign-agent", 0.85),
        ])
        self.agent.set_context_store(store)

        task = AgentTask(task_id="t1", agent_id="provenance",
                         task_type="provenance_generate",
                         input_data={"entity_types": ["objective"]})
        result = self.agent.execute(task)
        assert result.success
        assert result.data["record_count"] == 1

    def test_generate_writes_to_file(self):
        store = _make_store([
            ("e1", "objective", "objectives-agent", 0.9),
        ])
        self.agent.set_context_store(store)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "provenance.json")
            task = AgentTask(task_id="t1", agent_id="provenance",
                             task_type="provenance_generate",
                             input_data={"output_path": output_path})
            result = self.agent.execute(task)
            assert result.success
            assert os.path.exists(output_path)

            with open(output_path, "r") as f:
                data = json.load(f)
            assert "summary" in data
            assert "records" in data

    def test_query_all(self):
        store = _make_store([
            ("e1", "objective", "objectives-agent", 0.9),
            ("e2", "study_arm", "studydesign-agent", 0.85),
        ])
        self.agent.set_context_store(store)

        task = AgentTask(task_id="t1", agent_id="provenance",
                         task_type="provenance_query", input_data={})
        result = self.agent.execute(task)
        assert result.success
        assert result.data["record_count"] == 2

    def test_query_by_entity_ids(self):
        store = _make_store([
            ("e1", "objective", "objectives-agent", 0.9),
            ("e2", "study_arm", "studydesign-agent", 0.85),
        ])
        self.agent.set_context_store(store)

        task = AgentTask(task_id="t1", agent_id="provenance",
                         task_type="provenance_query",
                         input_data={"entity_ids": ["e1"]})
        result = self.agent.execute(task)
        assert result.success
        assert result.data["record_count"] == 1
        assert result.data["records"][0]["entity_id"] == "e1"

    def test_summary_statistics(self):
        store = _make_store([
            ("e1", "objective", "objectives-agent", 0.9),
            ("e2", "study_arm", "studydesign-agent", 0.3),  # Low confidence
        ])
        self.agent.set_context_store(store)

        task = AgentTask(task_id="t1", agent_id="provenance",
                         task_type="provenance_generate", input_data={})
        result = self.agent.execute(task)
        summary = result.data["summary"]
        assert summary["total_entities"] == 2
        assert summary["entities_with_provenance"] == 2
        assert summary["min_confidence"] < summary["max_confidence"]
        assert summary["low_confidence_count"] >= 1

    def test_source_type_detection_in_records(self):
        store = _make_store([
            ("e1", "soa_cell", "soa-vision-agent", 0.9),
            ("e2", "objective", "objectives-agent", 0.85),
        ])
        self.agent.set_context_store(store)

        task = AgentTask(task_id="t1", agent_id="provenance",
                         task_type="provenance_generate", input_data={})
        result = self.agent.execute(task)
        records = result.data["provenance"]["records"]
        source_types = {r["entity_id"]: r["source_type"] for r in records}
        assert source_types["e1"] == "vision"
        assert source_types["e2"] == "text"

    def test_provenance_metadata_in_result(self):
        store = _make_store([
            ("e1", "objective", "objectives-agent", 0.9),
        ])
        self.agent.set_context_store(store)

        task = AgentTask(task_id="t1", agent_id="provenance",
                         task_type="provenance_generate", input_data={})
        result = self.agent.execute(task)
        assert result.provenance is not None
        assert result.provenance["agent_id"] == "provenance"
        assert result.confidence_score == 1.0
