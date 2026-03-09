"""
Preservation Property Tests for Reconciliation Encounter Merge Bug Fix

IMPORTANT: Follow observation-first methodology.
These tests observe and capture the CURRENT behavior on UNFIXED code for non-encounter entities.

Expected Outcome: Tests PASS on unfixed code (confirms baseline behavior to preserve).

After the fix is implemented, these tests must STILL PASS to ensure no regressions.

Property 2: Preservation - Non-Encounter Duplicate Detection Unchanged
- For all non-encounter entity pairs with fuzzy score >= 0.85, they are merged
- For all encounter pairs with identical timepoints and fuzzy score >= 0.85, they are merged
- For all encounter pairs without timepoint indicators and fuzzy score >= 0.85, they are merged

Validates Requirements: 3.1, 3.2, 3.3, 3.4
"""

import sys
import os

# Add project root to path for standalone execution
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from typing import Dict, Any, List

from agents.quality.reconciliation_agent import (
    ReconciliationAgent,
    fuzzy_match_score,
)
from agents.base import AgentTask


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entity(
    entity_id: str,
    entity_type: str = "activity",
    name: str = "Blood Draw",
    source: str = "soa_vision_agent",
    confidence: float = 0.8,
    extra_data: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Create a test entity."""
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
    """Create a test task."""
    input_data = {"entities": entities}
    input_data.update(overrides)
    return AgentTask(
        task_id="task_recon",
        agent_id="reconciliation_agent",
        task_type="reconcile",
        input_data=input_data,
    )


# ---------------------------------------------------------------------------
# Property-Based Tests - Preservation
# ---------------------------------------------------------------------------

class TestPreservationNonEncounterEntities:
    """
    Property 2: Preservation - Non-Encounter Duplicate Detection
    
    Validates Requirements: 3.1, 3.3, 3.4
    
    For any pair of entities where at least one is NOT an encounter entity,
    the reconciliation agent SHALL apply the same fuzzy matching logic
    (threshold=0.85) as the original code, producing identical duplicate
    detection results and preserving all existing merge behavior.
    """
    
    def test_activity_entities_with_similar_names_are_merged(self):
        """
        Concrete test: Activity entities with fuzzy score >= 0.85 are merged.
        
        Validates Requirement 3.1: Non-encounter entities continue to use fuzzy matching.
        """
        entities = [
            _make_entity("e1", entity_type="activity", name="Blood Draw", source="soa_vision_agent"),
            _make_entity("e2", entity_type="activity", name="Blood Draws", source="soa_text_agent"),
        ]
        
        # Verify fuzzy score is high
        score = fuzzy_match_score("Blood Draw", "Blood Draws")
        assert score >= 0.85, f"Test setup: fuzzy score should be >= 0.85, got {score:.2f}"
        
        # Run reconciliation
        agent = ReconciliationAgent()
        agent.initialize()
        task = _make_task(entities)
        result = agent.execute(task)
        
        # PRESERVATION CHECK: Activities should be merged
        assert result.success
        report = result.data["report"]
        assert report["duplicates_merged"] >= 1, "Activity entities should be merged"
        assert report["total_entities_after"] == 1, "Should have 1 activity after merge"
    
    def test_procedure_entities_with_similar_names_are_merged(self):
        """
        Concrete test: Procedure entities with fuzzy score >= 0.85 are merged.
        
        Validates Requirement 3.1: Non-encounter entities continue to use fuzzy matching.
        """
        entities = [
            _make_entity("e1", entity_type="procedure", name="ECG Recording", source="soa_vision_agent"),
            _make_entity("e2", entity_type="procedure", name="ECG Recordings", source="soa_text_agent"),
        ]
        
        # Verify fuzzy score is high
        score = fuzzy_match_score("ECG Recording", "ECG Recordings")
        assert score >= 0.85, f"Test setup: fuzzy score should be >= 0.85, got {score:.2f}"
        
        # Run reconciliation
        agent = ReconciliationAgent()
        agent.initialize()
        task = _make_task(entities)
        result = agent.execute(task)
        
        # PRESERVATION CHECK: Procedures should be merged
        assert result.success
        report = result.data["report"]
        assert report["duplicates_merged"] >= 1, "Procedure entities should be merged"
        assert report["total_entities_after"] == 1, "Should have 1 procedure after merge"
    
    def test_intervention_entities_with_similar_names_are_merged(self):
        """
        Concrete test: Intervention entities with fuzzy score >= 0.85 are merged.
        
        Validates Requirement 3.1: Non-encounter entities continue to use fuzzy matching.
        """
        entities = [
            _make_entity("e1", entity_type="intervention", name="Drug Administration", source="soa_vision_agent"),
            _make_entity("e2", entity_type="intervention", name="Drug Administrations", source="soa_text_agent"),
        ]
        
        # Verify fuzzy score is high
        score = fuzzy_match_score("Drug Administration", "Drug Administrations")
        assert score >= 0.85, f"Test setup: fuzzy score should be >= 0.85, got {score:.2f}"
        
        # Run reconciliation
        agent = ReconciliationAgent()
        agent.initialize()
        task = _make_task(entities)
        result = agent.execute(task)
        
        # PRESERVATION CHECK: Interventions should be merged
        assert result.success
        report = result.data["report"]
        assert report["duplicates_merged"] >= 1, "Intervention entities should be merged"
        assert report["total_entities_after"] == 1, "Should have 1 intervention after merge"
    
    def test_multiple_activity_variations_are_merged(self):
        """
        Property test: Multiple activity name variations with high fuzzy scores are merged.
        
        Tests various name patterns to ensure fuzzy matching works consistently.
        """
        test_cases = [
            ("Vital Signs", "Vital Sign"),
            ("Physical Examination", "Physical Examinations"),
            ("Laboratory Test", "Laboratory Tests"),
            ("Adverse Event Assessment", "Adverse Event Assessments"),
        ]
        
        for name_a, name_b in test_cases:
            score = fuzzy_match_score(name_a, name_b)
            if score >= 0.85:
                entities = [
                    _make_entity("e1", entity_type="activity", name=name_a, source="soa_vision_agent"),
                    _make_entity("e2", entity_type="activity", name=name_b, source="soa_text_agent"),
                ]
                
                agent = ReconciliationAgent()
                agent.initialize()
                task = _make_task(entities)
                result = agent.execute(task)
                
                assert result.success
                report = result.data["report"]
                assert report["duplicates_merged"] >= 1, (
                    f"Activities '{name_a}' and '{name_b}' with score {score:.2f} should be merged"
                )
                assert report["total_entities_after"] == 1


class TestPreservationEncounterIdenticalTimepoints:
    """
    Property 2: Preservation - Identical Encounter Merging
    
    Validates Requirement 3.2
    
    For any pair of encounter entities with identical names AND identical
    timepoint information from different extraction sources, the reconciliation
    agent SHALL continue to merge them as legitimate duplicates.
    """
    
    def test_encounters_with_identical_names_and_timepoints_are_merged(self):
        """
        Concrete test: Encounters with identical timepoints should be merged.
        
        Validates Requirement 3.2: Encounters with identical timepoint information
        are merged as legitimate duplicates.
        """
        entities = [
            _make_entity("e1", entity_type="encounter", name="OP (Day 1)", source="soa_vision_agent"),
            _make_entity("e2", entity_type="encounter", name="OP (Day 1)", source="soa_text_agent"),
        ]
        
        # Run reconciliation
        agent = ReconciliationAgent()
        agent.initialize()
        task = _make_task(entities)
        result = agent.execute(task)
        
        # PRESERVATION CHECK: Identical encounters should be merged
        assert result.success
        report = result.data["report"]
        assert report["duplicates_merged"] >= 1, (
            "Encounters with identical names and timepoints should be merged"
        )
        assert report["total_entities_after"] == 1, "Should have 1 encounter after merge"
    
    def test_encounters_with_identical_screening_timepoints_are_merged(self):
        """
        Concrete test: Screening encounters with identical timepoints should be merged.
        
        Validates Requirement 3.2: Encounters with identical timepoint information
        are merged as legitimate duplicates.
        """
        entities = [
            _make_entity("e1", entity_type="encounter", name="Screening (-21)", source="soa_vision_agent"),
            _make_entity("e2", entity_type="encounter", name="Screening (-21)", source="soa_text_agent"),
        ]
        
        # Run reconciliation
        agent = ReconciliationAgent()
        agent.initialize()
        task = _make_task(entities)
        result = agent.execute(task)
        
        # PRESERVATION CHECK: Identical screening encounters should be merged
        assert result.success
        report = result.data["report"]
        assert report["duplicates_merged"] >= 1, (
            "Screening encounters with identical timepoints should be merged"
        )
        assert report["total_entities_after"] == 1, "Should have 1 encounter after merge"


class TestPreservationEncounterNoTimepoints:
    """
    Property 2: Preservation - No-Timepoint Encounter Merging
    
    Validates Requirement 3.1, 3.3
    
    For any pair of encounter entities without timepoint indicators,
    the reconciliation agent SHALL continue to use fuzzy matching with
    threshold=0.85, preserving existing behavior.
    """
    
    def test_encounters_without_timepoints_use_fuzzy_matching(self):
        """
        Concrete test: Encounters without timepoint indicators use fuzzy matching.
        
        Validates Requirement 3.1, 3.3: Encounters without timepoint indicators
        continue to use existing fuzzy matching logic.
        """
        entities = [
            _make_entity("e1", entity_type="encounter", name="Baseline Visit", source="soa_vision_agent"),
            _make_entity("e2", entity_type="encounter", name="Baseline Visits", source="soa_text_agent"),
        ]
        
        # Verify fuzzy score is high
        score = fuzzy_match_score("Baseline Visit", "Baseline Visits")
        assert score >= 0.85, f"Test setup: fuzzy score should be >= 0.85, got {score:.2f}"
        
        # Run reconciliation
        agent = ReconciliationAgent()
        agent.initialize()
        task = _make_task(entities)
        result = agent.execute(task)
        
        # PRESERVATION CHECK: Encounters without timepoints should use fuzzy matching
        assert result.success
        report = result.data["report"]
        assert report["duplicates_merged"] >= 1, (
            "Encounters without timepoint indicators should be merged via fuzzy matching"
        )
        assert report["total_entities_after"] == 1, "Should have 1 encounter after merge"
    
    def test_encounters_without_timepoints_similar_names_merged(self):
        """
        Concrete test: Encounters without timepoints and similar names are merged.
        
        Validates Requirement 3.1, 3.3: Encounters without timepoint indicators
        continue to use existing fuzzy matching logic.
        """
        entities = [
            _make_entity("e1", entity_type="encounter", name="Follow-up", source="soa_vision_agent"),
            _make_entity("e2", entity_type="encounter", name="Follow-ups", source="soa_text_agent"),
        ]
        
        # Verify fuzzy score is high
        score = fuzzy_match_score("Follow-up", "Follow-ups")
        assert score >= 0.85, f"Test setup: fuzzy score should be >= 0.85, got {score:.2f}"
        
        # Run reconciliation
        agent = ReconciliationAgent()
        agent.initialize()
        task = _make_task(entities)
        result = agent.execute(task)
        
        # PRESERVATION CHECK: Encounters without timepoints should be merged
        assert result.success
        report = result.data["report"]
        assert report["duplicates_merged"] >= 1, (
            "Encounters without timepoint indicators should be merged via fuzzy matching"
        )
        assert report["total_entities_after"] == 1, "Should have 1 encounter after merge"


# ---------------------------------------------------------------------------
# Run tests manually
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("="*80)
    print("Preservation Property Tests")
    print("="*80)
    print("\nThese tests observe CURRENT behavior on UNFIXED code.")
    print("Expected: All tests PASS (confirms baseline behavior to preserve)")
    print("="*80)
    
    # Run concrete tests
    test_class_1 = TestPreservationNonEncounterEntities()
    test_class_2 = TestPreservationEncounterIdenticalTimepoints()
    test_class_3 = TestPreservationEncounterNoTimepoints()
    
    print("\n--- Non-Encounter Entity Preservation Tests ---")
    try:
        test_class_1.test_activity_entities_with_similar_names_are_merged()
        print("✓ Activity entities with similar names are merged")
    except AssertionError as e:
        print(f"✗ Activity test failed: {e}")
    
    try:
        test_class_1.test_procedure_entities_with_similar_names_are_merged()
        print("✓ Procedure entities with similar names are merged")
    except AssertionError as e:
        print(f"✗ Procedure test failed: {e}")
    
    try:
        test_class_1.test_intervention_entities_with_similar_names_are_merged()
        print("✓ Intervention entities with similar names are merged")
    except AssertionError as e:
        print(f"✗ Intervention test failed: {e}")
    
    try:
        test_class_1.test_multiple_activity_variations_are_merged()
        print("✓ Multiple activity variations are merged")
    except AssertionError as e:
        print(f"✗ Multiple variations test failed: {e}")
    
    print("\n--- Identical Encounter Timepoint Preservation Tests ---")
    try:
        test_class_2.test_encounters_with_identical_names_and_timepoints_are_merged()
        print("✓ Encounters with identical timepoints are merged")
    except AssertionError as e:
        print(f"✗ Identical timepoint test failed: {e}")
    
    try:
        test_class_2.test_encounters_with_identical_screening_timepoints_are_merged()
        print("✓ Screening encounters with identical timepoints are merged")
    except AssertionError as e:
        print(f"✗ Screening timepoint test failed: {e}")
    
    print("\n--- No-Timepoint Encounter Preservation Tests ---")
    try:
        test_class_3.test_encounters_without_timepoints_use_fuzzy_matching()
        print("✓ Encounters without timepoints use fuzzy matching")
    except AssertionError as e:
        print(f"✗ No-timepoint test 1 failed: {e}")
    
    try:
        test_class_3.test_encounters_without_timepoints_similar_names_merged()
        print("✓ Encounters without timepoints with similar names are merged")
    except AssertionError as e:
        print(f"✗ No-timepoint test 2 failed: {e}")
    
    print("\n" + "="*80)
    print("Preservation tests complete.")
    print("All tests should PASS on unfixed code (baseline behavior).")
    print("="*80)
