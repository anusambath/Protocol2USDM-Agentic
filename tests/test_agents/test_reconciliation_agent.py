"""
Unit tests for ReconciliationAgent.

Covers:
- Lifecycle (init, initialize, terminate, capabilities)
- Entity name cleaning (footnotes, whitespace)
- Duplicate entity detection (exact and fuzzy matching)
- Entity merging with priority rules
- Reference updates after reconciliation
- SoA cell-level reconciliation (vision vs text)
- Conflict resolution strategies (tick marks, numeric, source priority)
- Confidence boosting (agreement) and reduction (conflicts)
- Reconciliation report generation
- Context Store integration
- 30 parametrised SoA vision/text reconciliation scenarios
"""

import pytest
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.base import AgentCapabilities, AgentResult, AgentState, AgentTask
from agents.context_store import ContextEntity, ContextStore, EntityProvenance
from agents.quality.reconciliation_agent import (
    ConflictDetail,
    DuplicateGroup,
    ReconciliationAgent,
    ReconciliationReport,
    clean_entity_name,
    fuzzy_match_score,
    get_source_priority,
    SOURCE_PRIORITY,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entity(
    entity_id: str,
    entity_type: str = "activity",
    name: str = "Blood Draw",
    source: str = "soa_vision_agent",
    confidence: float = 0.8,
    extra_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    data = {"name": name}
    if extra_data:
        data.update(extra_data)
    return {
        "id": entity_id,
        "entity_type": entity_type,
        "data": data,
        "relationships": {},
        "provenance": {
            "source_agent_id": source,
            "confidence_score": confidence,
        },
    }


def _make_task(entities: List[Dict[str, Any]], **overrides) -> AgentTask:
    input_data = {"entities": entities}
    input_data.update(overrides)
    return AgentTask(
        task_id="task_recon",
        agent_id="reconciliation_agent",
        task_type="reconcile",
        input_data=input_data,
    )


def _make_context_entity(
    entity_type: str, name: str, entity_id: Optional[str] = None, source: str = "soa_vision_agent"
) -> ContextEntity:
    eid = entity_id or f"{entity_type}_{name.lower().replace(' ', '_')}"
    return ContextEntity(
        id=eid,
        entity_type=entity_type,
        data={"name": name},
        provenance=EntityProvenance(
            entity_id=eid,
            source_agent_id=source,
            confidence_score=0.8,
            source_pages=[1],
            model_used="gpt-4",
        ),
    )


@pytest.fixture
def agent():
    a = ReconciliationAgent()
    a.initialize()
    return a


@pytest.fixture
def context_store():
    return ContextStore()


# ===================================================================
# Lifecycle tests
# ===================================================================

class TestReconciliationAgentLifecycle:
    def test_init_default(self):
        a = ReconciliationAgent()
        assert a.agent_id == "reconciliation_agent"
        assert a.state == AgentState.INITIALIZING

    def test_initialize_sets_ready(self, agent):
        assert agent.state == AgentState.READY

    def test_terminate_sets_terminated(self, agent):
        agent.terminate()
        assert agent.state == AgentState.TERMINATED

    def test_capabilities(self, agent):
        caps = agent.get_capabilities()
        assert caps.agent_type == "reconciliation"
        assert "context_data" in caps.input_types
        assert "reconciled_entities" in caps.output_types
        assert caps.supports_parallel is False

    def test_custom_agent_id(self):
        a = ReconciliationAgent(agent_id="custom_recon")
        assert a.agent_id == "custom_recon"

    def test_custom_config(self):
        a = ReconciliationAgent(config={"fuzzy_threshold": 0.9, "confidence_boost": 0.2})
        assert a._fuzzy_threshold == 0.9
        assert a._confidence_boost == 0.2


# ===================================================================
# Entity name cleaning tests
# ===================================================================

class TestEntityNameCleaning:
    def test_clean_trailing_asterisk(self):
        assert clean_entity_name("Blood Draw*") == "Blood Draw"

    def test_clean_trailing_dagger(self):
        assert clean_entity_name("Vital Signs†") == "Vital Signs"

    def test_clean_trailing_bracket_number(self):
        assert clean_entity_name("ECG [1]") == "ECG"

    def test_clean_trailing_paren_number(self):
        assert clean_entity_name("Urinalysis (2)") == "Urinalysis"

    def test_clean_multiple_spaces(self):
        assert clean_entity_name("Blood   Draw") == "Blood Draw"

    def test_clean_leading_trailing_whitespace(self):
        assert clean_entity_name("  Blood Draw  ") == "Blood Draw"

    def test_clean_combined(self):
        assert clean_entity_name("  Blood  Draw * ") == "Blood Draw"

    def test_clean_empty_string(self):
        assert clean_entity_name("") == ""

    def test_clean_no_change_needed(self):
        assert clean_entity_name("Blood Draw") == "Blood Draw"

    def test_clean_inline_footnote_symbols(self):
        assert clean_entity_name("Blood†Draw") == "BloodDraw"

    def test_agent_cleans_all_names(self, agent):
        entities = [
            _make_entity("e1", name="Activity A*"),
            _make_entity("e2", name="Activity B [1]"),
            _make_entity("e3", name="Activity C"),
        ]
        task = _make_task(entities)
        result = agent.execute(task)
        assert result.success
        report = result.data["report"]
        assert report["names_cleaned"] >= 2


# ===================================================================
# Fuzzy matching tests
# ===================================================================

class TestFuzzyMatching:
    def test_exact_match(self):
        assert fuzzy_match_score("Blood Draw", "Blood Draw") == 1.0

    def test_case_insensitive_match(self):
        assert fuzzy_match_score("Blood Draw", "blood draw") == 1.0

    def test_similar_names(self):
        score = fuzzy_match_score("Blood Draw", "Blood Draws")
        assert score > 0.8

    def test_different_names(self):
        score = fuzzy_match_score("Blood Draw", "ECG")
        assert score < 0.5

    def test_empty_string(self):
        assert fuzzy_match_score("", "Blood Draw") == 0.0
        assert fuzzy_match_score("Blood Draw", "") == 0.0

    def test_footnote_normalised(self):
        score = fuzzy_match_score("Blood Draw*", "Blood Draw")
        assert score == 1.0

    def test_source_priority_order(self):
        assert get_source_priority("execution_agent") > get_source_priority("procedures_agent")
        assert get_source_priority("procedures_agent") > get_source_priority("soa_vision_agent")
        assert get_source_priority("soa_vision_agent") > get_source_priority("soa_text_agent")
        assert get_source_priority("unknown_agent") == 1


# ===================================================================
# Duplicate detection tests
# ===================================================================

class TestDuplicateDetection:
    def test_exact_duplicates_detected(self, agent):
        entities = [
            _make_entity("e1", name="Blood Draw", source="soa_vision_agent"),
            _make_entity("e2", name="Blood Draw", source="soa_text_agent"),
        ]
        task = _make_task(entities)
        result = agent.execute(task)
        assert result.success
        report = result.data["report"]
        assert report["duplicates_merged"] >= 1

    def test_fuzzy_duplicates_detected(self, agent):
        entities = [
            _make_entity("e1", name="Blood Draw", source="soa_vision_agent"),
            _make_entity("e2", name="Blood Draws", source="soa_text_agent"),
        ]
        task = _make_task(entities)
        result = agent.execute(task)
        assert result.success
        assert result.data["report"]["duplicates_merged"] >= 1

    def test_different_types_not_merged(self, agent):
        entities = [
            _make_entity("e1", entity_type="activity", name="Screening"),
            _make_entity("e2", entity_type="epoch", name="Screening"),
        ]
        task = _make_task(entities)
        result = agent.execute(task)
        assert result.success
        # Different types should not be merged
        assert result.data["report"]["duplicates_merged"] == 0

    def test_no_duplicates(self, agent):
        entities = [
            _make_entity("e1", name="Blood Draw"),
            _make_entity("e2", name="ECG"),
        ]
        task = _make_task(entities)
        result = agent.execute(task)
        assert result.success
        assert result.data["report"]["duplicates_merged"] == 0

    def test_custom_threshold(self, agent):
        entities = [
            _make_entity("e1", name="Blood Draw"),
            _make_entity("e2", name="Blood Draws"),
        ]
        # Very high threshold should prevent merging
        task = _make_task(entities, fuzzy_threshold=0.99)
        result = agent.execute(task)
        assert result.success
        assert result.data["report"]["duplicates_merged"] == 0


# ===================================================================
# Entity merging tests
# ===================================================================

class TestEntityMerging:
    def test_higher_priority_source_wins(self, agent):
        entities = [
            _make_entity("e1", name="Blood Draw", source="soa_text_agent",
                         extra_data={"timing": "Day 1"}),
            _make_entity("e2", name="Blood Draw", source="execution_agent",
                         extra_data={"timing": "Day 2"}),
        ]
        task = _make_task(entities)
        result = agent.execute(task)
        assert result.success
        merged = result.data["entities"]
        # execution_agent has higher priority, so its entity should be primary
        primary = merged[0]
        assert primary["data"]["timing"] == "Day 2"

    def test_merged_entity_has_sources(self, agent):
        entities = [
            _make_entity("e1", name="Blood Draw", source="soa_vision_agent"),
            _make_entity("e2", name="Blood Draw", source="soa_text_agent"),
        ]
        task = _make_task(entities)
        result = agent.execute(task)
        merged = result.data["entities"]
        primary = merged[0]
        assert "_sources" in primary["data"]
        assert len(primary["data"]["_sources"]) == 2

    def test_merged_entity_marked_reconciled(self, agent):
        entities = [
            _make_entity("e1", name="Blood Draw", source="soa_vision_agent"),
            _make_entity("e2", name="Blood Draw", source="soa_text_agent"),
        ]
        task = _make_task(entities)
        result = agent.execute(task)
        merged = result.data["entities"]
        assert merged[0]["data"]["_reconciled"] is True

    def test_secondary_data_fills_gaps(self, agent):
        entities = [
            _make_entity("e1", name="Blood Draw", source="execution_agent",
                         extra_data={}),
            _make_entity("e2", name="Blood Draw", source="soa_text_agent",
                         extra_data={"description": "Venous blood draw"}),
        ]
        task = _make_task(entities)
        result = agent.execute(task)
        merged = result.data["entities"]
        # Primary (execution_agent) should get description from secondary
        assert merged[0]["data"].get("description") == "Venous blood draw"

    def test_id_mapping_returned(self, agent):
        entities = [
            _make_entity("e1", name="Blood Draw", source="soa_vision_agent"),
            _make_entity("e2", name="Blood Draw", source="soa_text_agent"),
        ]
        task = _make_task(entities)
        result = agent.execute(task)
        mapping = result.data["id_mapping"]
        assert len(mapping) == 1
        # One of the IDs should map to the other
        assert "e2" in mapping or "e1" in mapping


# ===================================================================
# Reference update tests
# ===================================================================

class TestReferenceUpdates:
    def test_references_rewritten(self, agent):
        entities = [
            _make_entity("e1", name="Blood Draw", source="soa_vision_agent"),
            _make_entity("e2", name="Blood Draw", source="soa_text_agent"),
            _make_entity("e3", entity_type="encounter", name="Visit 1",
                         extra_data={"activity_refs": ["e2"]}),
        ]
        task = _make_task(entities)
        result = agent.execute(task)
        assert result.success
        # e2 should be merged into e1 (vision has higher priority)
        mapping = result.data["id_mapping"]
        merged = result.data["entities"]
        # Find the encounter entity
        encounter = [e for e in merged if e["entity_type"] == "encounter"][0]
        refs = encounter["data"]["activity_refs"]
        # The reference should now point to the merged entity
        for ref in refs:
            assert ref not in mapping  # old IDs should be replaced

    def test_no_references_no_error(self, agent):
        entities = [
            _make_entity("e1", name="Blood Draw"),
        ]
        task = _make_task(entities)
        result = agent.execute(task)
        assert result.success
        assert result.data["report"]["references_updated"] == 0

    def test_relationship_references_rewritten(self, agent):
        entities = [
            _make_entity("e1", name="Blood Draw", source="soa_vision_agent"),
            _make_entity("e2", name="Blood Draw", source="soa_text_agent"),
        ]
        # Add a third entity with a relationship pointing to e2
        e3 = _make_entity("e3", entity_type="encounter", name="Visit 1")
        e3["relationships"] = {"activities": ["e2"]}
        entities.append(e3)

        task = _make_task(entities)
        result = agent.execute(task)
        merged = result.data["entities"]
        encounter = [e for e in merged if e["entity_type"] == "encounter"][0]
        # Relationship should point to merged ID
        assert "e2" not in encounter["relationships"].get("activities", [])


# ===================================================================
# SoA cell-level reconciliation tests
# ===================================================================

class TestSoACellReconciliation:
    def test_agreement_boosts_confidence(self, agent):
        entities = [
            _make_entity("e1", name="Activity A", extra_data={
                "cells": [
                    {"vision_value": "X", "text_value": "X",
                     "vision_confidence": 0.8, "text_confidence": 0.7}
                ]
            }),
        ]
        task = _make_task(entities)
        result = agent.execute(task)
        assert result.success
        report = result.data["report"]
        assert report["confidence_boosts"] >= 1
        cell = result.data["entities"][0]["data"]["cells"][0]
        assert cell["resolved_value"] == "X"
        assert cell["resolved_confidence"] > 0.8

    def test_conflict_reduces_confidence(self, agent):
        entities = [
            _make_entity("e1", name="Activity A", extra_data={
                "cells": [
                    {"vision_value": "X", "text_value": "",
                     "vision_confidence": 0.6, "text_confidence": 0.7}
                ]
            }),
        ]
        task = _make_task(entities)
        result = agent.execute(task)
        report = result.data["report"]
        assert report["confidence_reductions"] >= 1
        assert report["conflict_count"] >= 1

    def test_single_source_no_conflict(self, agent):
        entities = [
            _make_entity("e1", name="Activity A", extra_data={
                "cells": [
                    {"vision_value": "X", "vision_confidence": 0.8}
                ]
            }),
        ]
        task = _make_task(entities)
        result = agent.execute(task)
        report = result.data["report"]
        assert report["conflict_count"] == 0
        cell = result.data["entities"][0]["data"]["cells"][0]
        assert cell["resolved_value"] == "X"

    def test_dict_cells_format(self, agent):
        entities = [
            _make_entity("e1", name="Activity A", extra_data={
                "cells": {
                    "V1": {"vision_value": "X", "text_value": "X",
                           "vision_confidence": 0.9, "text_confidence": 0.9},
                }
            }),
        ]
        task = _make_task(entities)
        result = agent.execute(task)
        assert result.success
        assert result.data["report"]["confidence_boosts"] >= 1


# ===================================================================
# Conflict resolution strategy tests
# ===================================================================

class TestConflictResolution:
    def test_tick_marks_agree(self):
        assert ReconciliationAgent._values_agree("X", "✓")
        assert ReconciliationAgent._values_agree("x", "Y")
        assert ReconciliationAgent._values_agree("Yes", "yes")

    def test_empty_values_agree(self):
        assert ReconciliationAgent._values_agree("", "-")
        assert ReconciliationAgent._values_agree("-", "—")
        assert ReconciliationAgent._values_agree("No", "no")

    def test_numeric_values_agree(self):
        assert ReconciliationAgent._values_agree("3.0", "3.0")
        assert ReconciliationAgent._values_agree("42", "42")

    def test_tick_vs_empty_disagree(self):
        assert not ReconciliationAgent._values_agree("X", "")
        assert not ReconciliationAgent._values_agree("✓", "-")

    def test_different_numbers_disagree(self):
        assert not ReconciliationAgent._values_agree("3.0", "4.0")

    def test_tick_present_over_absent(self, agent):
        resolved, strategy = agent._resolve_cell_conflict("X", 0.8, "", 0.7)
        assert resolved == "X"
        assert strategy == "tick_present_over_absent"

    def test_tick_present_over_absent_text(self, agent):
        resolved, strategy = agent._resolve_cell_conflict("-", 0.8, "✓", 0.7)
        assert resolved == "✓"
        assert strategy == "tick_present_over_absent"

    def test_numeric_higher_confidence_wins(self, agent):
        resolved, strategy = agent._resolve_cell_conflict("3.0", 0.9, "4.0", 0.7)
        assert resolved == "3.0"
        assert strategy == "numeric_higher_confidence"

    def test_numeric_text_higher_confidence(self, agent):
        resolved, strategy = agent._resolve_cell_conflict("3.0", 0.5, "4.0", 0.9)
        assert resolved == "4.0"
        assert strategy == "numeric_higher_confidence"

    def test_source_priority_fallback(self, agent):
        resolved, strategy = agent._resolve_cell_conflict("abc", 0.8, "def", 0.8)
        assert strategy == "source_priority"
        # Vision has higher priority than text
        assert resolved == "abc"


# ===================================================================
# Confidence boosting / reduction tests
# ===================================================================

class TestConfidenceAdjustment:
    def test_boost_increases_confidence(self, agent):
        entity = _make_entity("e1", confidence=0.7)
        agent._boost_entity_confidence(entity)
        assert entity["provenance"]["confidence_score"] == pytest.approx(0.8, abs=0.01)

    def test_boost_caps_at_1(self, agent):
        entity = _make_entity("e1", confidence=0.95)
        agent._boost_entity_confidence(entity)
        assert entity["provenance"]["confidence_score"] <= 1.0

    def test_reduce_decreases_confidence(self, agent):
        entity = _make_entity("e1", confidence=0.7)
        agent._reduce_entity_confidence(entity)
        assert entity["provenance"]["confidence_score"] == pytest.approx(0.55, abs=0.01)

    def test_reduce_floors_at_0(self, agent):
        entity = _make_entity("e1", confidence=0.05)
        agent._reduce_entity_confidence(entity)
        assert entity["provenance"]["confidence_score"] >= 0.0

    def test_field_agreement_boosts(self, agent):
        entities = [
            _make_entity("e1", name="Activity A", confidence=0.7, extra_data={
                "_source_values": {
                    "timing": {"soa_vision_agent": "Day 1", "soa_text_agent": "Day 1"}
                }
            }),
        ]
        task = _make_task(entities)
        result = agent.execute(task)
        assert result.data["report"]["confidence_boosts"] >= 1

    def test_field_conflict_reduces(self, agent):
        entities = [
            _make_entity("e1", name="Activity A", confidence=0.7, extra_data={
                "_source_values": {
                    "timing": {"soa_vision_agent": "Day 1", "execution_agent": "Day 2"}
                }
            }),
        ]
        task = _make_task(entities)
        result = agent.execute(task)
        assert result.data["report"]["confidence_reductions"] >= 1
        # execution_agent should win
        merged = result.data["entities"][0]
        assert merged["data"]["timing"] == "Day 2"


# ===================================================================
# Reconciliation report tests
# ===================================================================

class TestReconciliationReport:
    def test_report_generated(self, agent):
        entities = [
            _make_entity("e1", name="Blood Draw", source="soa_vision_agent"),
            _make_entity("e2", name="Blood Draw", source="soa_text_agent"),
        ]
        task = _make_task(entities)
        result = agent.execute(task)
        report = result.data["report"]
        assert report["total_entities_before"] == 2
        assert report["total_entities_after"] == 1
        assert report["duplicates_merged"] == 1

    def test_report_stored_in_agent(self, agent):
        entities = [_make_entity("e1", name="Blood Draw")]
        task = _make_task(entities)
        agent.execute(task)
        reports = agent.get_reports()
        assert len(reports) == 1

    def test_report_to_dict(self):
        report = ReconciliationReport(
            total_entities_before=10,
            total_entities_after=8,
            names_cleaned=3,
            references_updated=2,
        )
        d = report.to_dict()
        assert d["total_entities_before"] == 10
        assert d["total_entities_after"] == 8
        assert d["names_cleaned"] == 3
        assert d["references_updated"] == 2

    def test_report_conflict_details(self, agent):
        entities = [
            _make_entity("e1", name="Activity A", extra_data={
                "cells": [
                    {"vision_value": "X", "text_value": "",
                     "vision_confidence": 0.8, "text_confidence": 0.7}
                ]
            }),
        ]
        task = _make_task(entities)
        result = agent.execute(task)
        report = result.data["report"]
        assert len(report["conflicts"]) >= 1
        conflict = report["conflicts"][0]
        assert "soa_vision_agent" in conflict["values"]
        assert "soa_text_agent" in conflict["values"]

    def test_duplicate_group_to_dict(self):
        g = DuplicateGroup(
            canonical_name="Blood Draw",
            entity_type="activity",
            entity_ids=["e1", "e2"],
            sources=["soa_vision_agent", "soa_text_agent"],
            merged_id="e1",
        )
        d = g.to_dict()
        assert d["canonical_name"] == "Blood Draw"
        assert d["merged_id"] == "e1"

    def test_conflict_detail_to_dict(self):
        c = ConflictDetail(
            field_name="cell_value",
            entity_id="e1",
            entity_type="activity",
            values={"soa_vision_agent": "X", "soa_text_agent": ""},
            resolved_value="X",
            resolution_strategy="tick_present_over_absent",
        )
        d = c.to_dict()
        assert d["resolution_strategy"] == "tick_present_over_absent"


# ===================================================================
# Context Store integration tests
# ===================================================================

class TestContextStoreIntegration:
    def test_execute_from_context_store(self, agent, context_store):
        context_store.add_entity(_make_context_entity("activity", "Blood Draw", "e1", "soa_vision_agent"))
        context_store.add_entity(_make_context_entity("activity", "Blood Draw", "e2", "soa_text_agent"))
        agent.set_context_store(context_store)

        task = AgentTask(
            task_id="task_recon",
            agent_id="reconciliation_agent",
            task_type="reconcile",
            input_data={},
        )
        result = agent.execute(task)
        assert result.success
        assert result.data["report"]["duplicates_merged"] >= 1

    def test_context_store_updated_after_reconciliation(self, agent, context_store):
        context_store.add_entity(_make_context_entity("activity", "Blood Draw", "e1", "soa_vision_agent"))
        context_store.add_entity(_make_context_entity("activity", "Blood Draw", "e2", "soa_text_agent"))
        agent.set_context_store(context_store)

        task = AgentTask(
            task_id="task_recon",
            agent_id="reconciliation_agent",
            task_type="reconcile",
            input_data={},
        )
        result = agent.execute(task)
        assert result.success
        # Merged-away entity should be removed
        mapping = result.data["id_mapping"]
        for old_id in mapping:
            assert context_store.get_entity(old_id) is None

    def test_no_entities_returns_error(self, agent):
        task = AgentTask(
            task_id="task_recon",
            agent_id="reconciliation_agent",
            task_type="reconcile",
            input_data={},
        )
        result = agent.execute(task)
        assert not result.success
        assert "No entities" in result.error


# ===================================================================
# Execute integration tests
# ===================================================================

class TestExecuteIntegration:
    def test_full_pipeline(self, agent):
        """Test the full reconciliation pipeline end-to-end."""
        entities = [
            _make_entity("e1", entity_type="activity", name="Blood Draw*",
                         source="soa_vision_agent", extra_data={
                             "cells": [{"vision_value": "X", "text_value": "X",
                                        "vision_confidence": 0.8, "text_confidence": 0.7}]
                         }),
            _make_entity("e2", entity_type="activity", name="Blood Draw",
                         source="soa_text_agent"),
            _make_entity("e3", entity_type="encounter", name="Visit 1",
                         extra_data={"activity_refs": ["e2"]}),
        ]
        task = _make_task(entities)
        result = agent.execute(task)
        assert result.success
        report = result.data["report"]
        assert report["names_cleaned"] >= 1
        assert report["duplicates_merged"] >= 1
        assert report["total_entities_after"] < report["total_entities_before"]

    def test_confidence_score_in_result(self, agent):
        entities = [_make_entity("e1", name="Activity A")]
        task = _make_task(entities)
        result = agent.execute(task)
        assert result.confidence_score is not None
        assert 0.0 <= result.confidence_score <= 1.0


# ===================================================================
# 30 parametrised SoA vision/text reconciliation scenarios
# ===================================================================

def _soa_scenario(
    scenario_id: str,
    vision_entities: List[Dict[str, Any]],
    text_entities: List[Dict[str, Any]],
    expected_merged_count: int,
    expected_conflicts: int,
    expected_boosts: int,
    description: str = "",
) -> Dict[str, Any]:
    return {
        "id": scenario_id,
        "vision": vision_entities,
        "text": text_entities,
        "expected_merged_count": expected_merged_count,
        "expected_conflicts": expected_conflicts,
        "expected_boosts": expected_boosts,
        "description": description,
    }


def _v(eid, name, cells=None, etype="activity"):
    """Create a vision entity."""
    data = {"name": name}
    if cells:
        data["cells"] = cells
    return _make_entity(eid, entity_type=etype, name=name, source="soa_vision_agent",
                        extra_data=data if cells else None)


def _t(eid, name, cells=None, etype="activity"):
    """Create a text entity."""
    data = {"name": name}
    if cells:
        data["cells"] = cells
    return _make_entity(eid, entity_type=etype, name=name, source="soa_text_agent",
                        extra_data=data if cells else None)


SOA_SCENARIOS = [
    # 1: Both agree on tick mark
    _soa_scenario("P01", [_v("v1", "Blood Draw", [{"vision_value": "X", "text_value": "X", "vision_confidence": 0.9, "text_confidence": 0.8}])],
                  [_t("t1", "Blood Draw")], 1, 0, 1, "Both agree on tick"),
    # 2: Vision tick, text empty
    _soa_scenario("P02", [_v("v1", "ECG", [{"vision_value": "X", "text_value": "", "vision_confidence": 0.8, "text_confidence": 0.7}])],
                  [_t("t1", "ECG")], 1, 1, 0, "Vision tick, text empty"),
    # 3: Text tick, vision empty
    _soa_scenario("P03", [_v("v1", "Urinalysis", [{"vision_value": "", "text_value": "✓", "vision_confidence": 0.7, "text_confidence": 0.8}])],
                  [_t("t1", "Urinalysis")], 1, 1, 0, "Text tick, vision empty"),
    # 4: Both agree on numeric value
    _soa_scenario("P04", [_v("v1", "Vital Signs", [{"vision_value": "3", "text_value": "3", "vision_confidence": 0.9, "text_confidence": 0.9}])],
                  [_t("t1", "Vital Signs")], 1, 0, 1, "Both agree on number"),
    # 5: Numeric conflict
    _soa_scenario("P05", [_v("v1", "Lab Test", [{"vision_value": "2", "text_value": "3", "vision_confidence": 0.9, "text_confidence": 0.7}])],
                  [_t("t1", "Lab Test")], 1, 1, 0, "Numeric conflict"),
    # 6: Exact name match, no cells
    _soa_scenario("P06", [_v("v1", "Physical Exam")], [_t("t1", "Physical Exam")], 1, 0, 0, "Exact name match, no cells"),
    # 7: Fuzzy name match
    _soa_scenario("P07", [_v("v1", "Blood Pressure")], [_t("t1", "Blood Pressures")], 1, 0, 0, "Fuzzy name match"),
    # 8: No match — different activities
    _soa_scenario("P08", [_v("v1", "ECG")], [_t("t1", "MRI")], 0, 0, 0, "No match"),
    # 9: Footnote in vision name
    _soa_scenario("P09", [_v("v1", "Blood Draw*")], [_t("t1", "Blood Draw")], 1, 0, 0, "Footnote cleaned"),
    # 10: Multiple activities, partial overlap
    _soa_scenario("P10",
                  [_v("v1", "ECG"), _v("v2", "Blood Draw")],
                  [_t("t1", "ECG"), _t("t2", "Urinalysis")],
                  1, 0, 0, "Partial overlap"),
    # 11: Encounter match
    _soa_scenario("P11", [_v("v1", "Screening", etype="encounter")],
                  [_t("t1", "Screening", etype="encounter")], 1, 0, 0, "Encounter match"),
    # 12: Epoch match
    _soa_scenario("P12", [_v("v1", "Treatment Period", etype="epoch")],
                  [_t("t1", "Treatment Period", etype="epoch")], 1, 0, 0, "Epoch match"),
    # 13: Both agree on empty cell
    _soa_scenario("P13", [_v("v1", "Activity A", [{"vision_value": "", "text_value": "", "vision_confidence": 0.9, "text_confidence": 0.9}])],
                  [_t("t1", "Activity A")], 1, 0, 1, "Both agree empty"),
    # 14: Vision only source
    _soa_scenario("P14", [_v("v1", "Activity B", [{"vision_value": "X", "vision_confidence": 0.8}])],
                  [], 0, 0, 0, "Vision only"),
    # 15: Text only source
    _soa_scenario("P15", [], [_t("t1", "Activity C", [{"text_value": "X", "text_confidence": 0.8}])],
                  0, 0, 0, "Text only"),
    # 16: Multiple cells, mixed agreement
    _soa_scenario("P16", [_v("v1", "Activity D", [
        {"vision_value": "X", "text_value": "X", "vision_confidence": 0.9, "text_confidence": 0.8},
        {"vision_value": "X", "text_value": "", "vision_confidence": 0.7, "text_confidence": 0.6},
    ])], [_t("t1", "Activity D")], 1, 1, 1, "Mixed cells"),
    # 17: Three duplicates from different sources
    _soa_scenario("P17",
                  [_v("v1", "Blood Draw")],
                  [_t("t1", "Blood Draw"), _t("t2", "Blood Draw")],
                  2, 0, 0, "Three duplicates"),
    # 18: Case difference in names
    _soa_scenario("P18", [_v("v1", "blood draw")], [_t("t1", "Blood Draw")], 1, 0, 0, "Case difference"),
    # 19: Whitespace difference
    _soa_scenario("P19", [_v("v1", "Blood  Draw")], [_t("t1", "Blood Draw")], 1, 0, 0, "Whitespace diff"),
    # 20: Tick mark variants agree
    _soa_scenario("P20", [_v("v1", "Activity E", [{"vision_value": "✓", "text_value": "Y", "vision_confidence": 0.8, "text_confidence": 0.8}])],
                  [_t("t1", "Activity E")], 1, 0, 1, "Tick variants agree"),
    # 21: String conflict (non-numeric, non-tick)
    _soa_scenario("P21", [_v("v1", "Activity F", [{"vision_value": "abc", "text_value": "def", "vision_confidence": 0.8, "text_confidence": 0.8}])],
                  [_t("t1", "Activity F")], 1, 1, 0, "String conflict"),
    # 22: High confidence text, low confidence vision
    _soa_scenario("P22", [_v("v1", "Activity G", [{"vision_value": "2", "text_value": "5", "vision_confidence": 0.3, "text_confidence": 0.95}])],
                  [_t("t1", "Activity G")], 1, 1, 0, "Text higher confidence numeric"),
    # 23: Both No/no agree
    _soa_scenario("P23", [_v("v1", "Activity H", [{"vision_value": "No", "text_value": "no", "vision_confidence": 0.9, "text_confidence": 0.9}])],
                  [_t("t1", "Activity H")], 1, 0, 1, "No/no agree"),
    # 24: Dash vs empty agree
    _soa_scenario("P24", [_v("v1", "Activity I", [{"vision_value": "-", "text_value": "", "vision_confidence": 0.8, "text_confidence": 0.8}])],
                  [_t("t1", "Activity I")], 1, 0, 1, "Dash vs empty agree"),
    # 25: Large protocol — 5 activities, all matching
    _soa_scenario("P25",
                  [_v(f"v{i}", f"Activity {i}") for i in range(5)],
                  [_t(f"t{i}", f"Activity {i}") for i in range(5)],
                  5, 0, 0, "5 activities all match"),
    # 26: Large protocol — 5 activities, none matching
    _soa_scenario("P26",
                  [_v(f"v{i}", f"Vision Act {i}") for i in range(5)],
                  [_t(f"t{i}", f"Text Act {i}") for i in range(5)],
                  0, 0, 0, "5 activities none match"),
    # 27: Encounter with footnote
    _soa_scenario("P27", [_v("v1", "Visit 1 [1]", etype="encounter")],
                  [_t("t1", "Visit 1", etype="encounter")], 1, 0, 0, "Encounter footnote"),
    # 28: Activity with trailing paren number
    _soa_scenario("P28", [_v("v1", "Blood Draw (1)")], [_t("t1", "Blood Draw")], 1, 0, 0, "Paren footnote"),
    # 29: Numeric agreement float
    _soa_scenario("P29", [_v("v1", "Activity J", [{"vision_value": "3.0", "text_value": "3.0", "vision_confidence": 0.85, "text_confidence": 0.85}])],
                  [_t("t1", "Activity J")], 1, 0, 1, "Float agreement"),
    # 30: Complex — multiple entities, cells, conflicts
    _soa_scenario("P30",
                  [_v("v1", "Blood Draw", [
                      {"vision_value": "X", "text_value": "X", "vision_confidence": 0.9, "text_confidence": 0.8},
                      {"vision_value": "3", "text_value": "4", "vision_confidence": 0.7, "text_confidence": 0.9},
                  ]),
                   _v("v2", "ECG")],
                  [_t("t1", "Blood Draw"), _t("t2", "ECG")],
                  2, 1, 1, "Complex mixed scenario"),
]


@pytest.mark.parametrize(
    "scenario",
    SOA_SCENARIOS,
    ids=[s["id"] for s in SOA_SCENARIOS],
)
class TestSoAVisionTextReconciliation:
    """30 parametrised SoA vision/text reconciliation scenarios."""

    def test_reconciliation(self, agent, scenario):
        all_entities = scenario["vision"] + scenario["text"]
        if not all_entities:
            pytest.skip("Empty scenario")

        task = _make_task(all_entities)
        result = agent.execute(task)
        assert result.success

        report = result.data["report"]
        assert report["duplicates_merged"] >= scenario["expected_merged_count"], (
            f"Scenario {scenario['id']}: expected >= {scenario['expected_merged_count']} merges, "
            f"got {report['duplicates_merged']}. {scenario['description']}"
        )

    def test_conflict_count(self, agent, scenario):
        all_entities = scenario["vision"] + scenario["text"]
        if not all_entities:
            pytest.skip("Empty scenario")

        task = _make_task(all_entities)
        result = agent.execute(task)
        report = result.data["report"]
        assert report["conflict_count"] >= scenario["expected_conflicts"], (
            f"Scenario {scenario['id']}: expected >= {scenario['expected_conflicts']} conflicts, "
            f"got {report['conflict_count']}. {scenario['description']}"
        )

    def test_boost_count(self, agent, scenario):
        all_entities = scenario["vision"] + scenario["text"]
        if not all_entities:
            pytest.skip("Empty scenario")

        task = _make_task(all_entities)
        result = agent.execute(task)
        report = result.data["report"]
        assert report["confidence_boosts"] >= scenario["expected_boosts"], (
            f"Scenario {scenario['id']}: expected >= {scenario['expected_boosts']} boosts, "
            f"got {report['confidence_boosts']}. {scenario['description']}"
        )
