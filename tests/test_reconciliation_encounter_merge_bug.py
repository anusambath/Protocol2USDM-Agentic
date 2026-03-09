"""
Bug Condition Exploration Test for Reconciliation Encounter Merge Issue

This test MUST FAIL on unfixed code - failure confirms the bug exists.
DO NOT attempt to fix the test or the code when it fails.

The test encodes the expected behavior and will validate the fix when it passes after implementation.

Bug Description:
- Reconciliation agent incorrectly merges distinct encounters based solely on name similarity
- Encounters with similar name prefixes but different timepoint indicators are merged
- In NCT04573309: 30 encounters reduced to 7 (77% data loss)
- "OP (Day 1)" through "OP (Day 22)" merged into single "OP" encounter
- "Inpatient Period 2 (Day 23)" through "Inpatient Period 2 (Day 40)" merged into single encounter

Expected Behavior (what this test validates):
- Encounters with different timepoint indicators must be preserved as distinct entities
- "OP (Day N)" encounters should remain separate (9 distinct encounters)
- "Inpatient Period 2 (Day N)" encounters should remain separate (17 distinct encounters)
- "Screening" encounters with different timepoints should remain separate (4 distinct encounters)
"""

import json
import os
import pytest
from typing import Dict, List, Any


def load_context_store_entities(file_path: str) -> List[Dict[str, Any]]:
    """Load entities from a context store JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('data', {}).get('entities', [])


def test_op_encounters_not_merged():
    """
    Property 1: Bug Condition - OP Encounters with Different Day Numbers
    
    CRITICAL: This test MUST FAIL on unfixed code.
    
    For any pair of encounter entities where both have "OP" prefix and different day numbers,
    the reconciliation agent SHALL NOT merge them, preserving each encounter as a distinct
    entity regardless of fuzzy match score.
    
    Test Case 1: "OP (Day 1)" through "OP (Day 22)" should remain as 9 distinct encounters
    
    Validates Requirements: 2.1, 2.2, 2.3, 2.4
    """
    output_dir = "output/Alexion_NCT04573309_Wilsons_20260308_185157"
    
    # Load postprocessing output (before reconciliation)
    postproc_path = os.path.join(output_dir, "15_quality_postprocessing.json")
    assert os.path.exists(postproc_path), f"Postprocessing file not found: {postproc_path}"
    
    postproc_entities = load_context_store_entities(postproc_path)
    postproc_encounters = [e for e in postproc_entities if e.get('entity_type') == 'encounter']
    
    # Count OP encounters before reconciliation
    op_encounters_before = [
        e for e in postproc_encounters 
        if e.get('data', {}).get('name', '').startswith('OP')
    ]
    
    print(f"\nOP encounters before reconciliation: {len(op_encounters_before)}")
    for e in op_encounters_before:
        print(f"  {e.get('id')}: {e.get('data', {}).get('name')}")
    
    # Load reconciliation output
    recon_path = os.path.join(output_dir, "16_quality_reconciliation.json")
    assert os.path.exists(recon_path), f"Reconciliation file not found: {recon_path}"
    
    recon_entities = load_context_store_entities(recon_path)
    recon_encounters = [e for e in recon_entities if e.get('entity_type') == 'encounter']
    
    # Count OP encounters after reconciliation
    op_encounters_after = [
        e for e in recon_encounters 
        if e.get('data', {}).get('name', '').startswith('OP')
    ]
    
    print(f"\nOP encounters after reconciliation: {len(op_encounters_after)}")
    for e in op_encounters_after:
        print(f"  {e.get('id')}: {e.get('data', {}).get('name')}")
    
    # BUG CONDITION CHECK: OP encounters should NOT be merged
    # Expected: 9 distinct OP encounters (based on spec)
    # This will FAIL on unfixed code (expected - proves bug exists)
    assert len(op_encounters_before) > 1, "Should have multiple OP encounters before reconciliation"
    assert len(op_encounters_after) == len(op_encounters_before), (
        f"Bug confirmed: OP encounters were incorrectly merged. "
        f"Before: {len(op_encounters_before)}, After: {len(op_encounters_after)}. "
        f"Lost {len(op_encounters_before) - len(op_encounters_after)} encounters."
    )
    
    print("\n✓ All OP encounters with different day numbers preserved")


def test_inpatient_period_2_encounters_not_merged():
    """
    Property 1: Bug Condition - Inpatient Period 2 Encounters with Different Day Numbers
    
    CRITICAL: This test MUST FAIL on unfixed code.
    
    For any pair of encounter entities where both have "Inpatient Period 2" prefix and 
    different day numbers, the reconciliation agent SHALL NOT merge them.
    
    Test Case 2: "Inpatient Period 2 (Day 23)" through "Inpatient Period 2 (Day 40)" 
    should remain as 17 distinct encounters (not merged into 1)
    
    Validates Requirements: 2.1, 2.2, 2.3, 2.4
    """
    output_dir = "output/Alexion_NCT04573309_Wilsons_20260308_185157"
    
    # Load postprocessing output
    postproc_path = os.path.join(output_dir, "15_quality_postprocessing.json")
    postproc_entities = load_context_store_entities(postproc_path)
    postproc_encounters = [e for e in postproc_entities if e.get('entity_type') == 'encounter']
    
    # Count Inpatient Period 2 encounters before reconciliation
    ip2_encounters_before = [
        e for e in postproc_encounters 
        if 'Inpatient Period 2' in e.get('data', {}).get('name', '')
    ]
    
    print(f"\nInpatient Period 2 encounters before reconciliation: {len(ip2_encounters_before)}")
    for e in ip2_encounters_before:
        print(f"  {e.get('id')}: {e.get('data', {}).get('name')}")
    
    # Load reconciliation output
    recon_path = os.path.join(output_dir, "16_quality_reconciliation.json")
    recon_entities = load_context_store_entities(recon_path)
    recon_encounters = [e for e in recon_entities if e.get('entity_type') == 'encounter']
    
    # Count Inpatient Period 2 encounters after reconciliation
    ip2_encounters_after = [
        e for e in recon_encounters 
        if 'Inpatient Period' in e.get('data', {}).get('name', '')
    ]
    
    print(f"\nInpatient Period 2 encounters after reconciliation: {len(ip2_encounters_after)}")
    for e in ip2_encounters_after:
        print(f"  {e.get('id')}: {e.get('data', {}).get('name')}")
    
    # BUG CONDITION CHECK: Inpatient Period 2 encounters should NOT be merged
    # Expected: 13 distinct Inpatient Period 2 encounters (based on actual data)
    # This will FAIL on unfixed code (expected - proves bug exists)
    assert len(ip2_encounters_before) > 1, "Should have multiple Inpatient Period 2 encounters"
    assert len(ip2_encounters_after) == len(ip2_encounters_before), (
        f"Bug confirmed: Inpatient Period 2 encounters were incorrectly merged. "
        f"Before: {len(ip2_encounters_before)}, After: {len(ip2_encounters_after)}. "
        f"Lost {len(ip2_encounters_before) - len(ip2_encounters_after)} encounters."
    )
    
    print("\n✓ All Inpatient Period 2 encounters with different day numbers preserved")


def test_screening_encounters_not_merged():
    """
    Property 1: Bug Condition - Screening Encounters with Different Timepoints
    
    CRITICAL: This test MUST FAIL on unfixed code.
    
    For any pair of encounter entities where both have "Screening" prefix and different
    timepoint indicators, the reconciliation agent SHALL NOT merge them.
    
    Test Case 3: "Screening (-42 to -9)", "Screening (-21)", "Screening (-8)", "Screening (-7)"
    should remain as 4 distinct encounters
    
    Validates Requirements: 2.1, 2.2, 2.3, 2.4
    """
    output_dir = "output/Alexion_NCT04573309_Wilsons_20260308_185157"
    
    # Load postprocessing output
    postproc_path = os.path.join(output_dir, "15_quality_postprocessing.json")
    postproc_entities = load_context_store_entities(postproc_path)
    postproc_encounters = [e for e in postproc_entities if e.get('entity_type') == 'encounter']
    
    # Count Screening encounters before reconciliation
    screening_encounters_before = [
        e for e in postproc_encounters 
        if e.get('data', {}).get('name', '').startswith('Screening')
    ]
    
    print(f"\nScreening encounters before reconciliation: {len(screening_encounters_before)}")
    for e in screening_encounters_before:
        print(f"  {e.get('id')}: {e.get('data', {}).get('name')}")
    
    # Load reconciliation output
    recon_path = os.path.join(output_dir, "16_quality_reconciliation.json")
    recon_entities = load_context_store_entities(recon_path)
    recon_encounters = [e for e in recon_entities if e.get('entity_type') == 'encounter']
    
    # Count Screening encounters after reconciliation
    screening_encounters_after = [
        e for e in recon_encounters 
        if e.get('data', {}).get('name', '').startswith('Screening')
    ]
    
    print(f"\nScreening encounters after reconciliation: {len(screening_encounters_after)}")
    for e in screening_encounters_after:
        print(f"  {e.get('id')}: {e.get('data', {}).get('name')}")
    
    # BUG CONDITION CHECK: Screening encounters should NOT be merged
    # Expected: 4 distinct Screening encounters (based on spec)
    # This will FAIL on unfixed code (expected - proves bug exists)
    assert len(screening_encounters_before) >= 2, "Should have multiple Screening encounters"
    assert len(screening_encounters_after) == len(screening_encounters_before), (
        f"Bug confirmed: Screening encounters were incorrectly merged. "
        f"Before: {len(screening_encounters_before)}, After: {len(screening_encounters_after)}. "
        f"Lost {len(screening_encounters_before) - len(screening_encounters_after)} encounters."
    )
    
    print("\n✓ All Screening encounters with different timepoints preserved")


def test_total_encounter_preservation():
    """
    Property 1: Bug Condition - Total Encounter Count Preservation
    
    CRITICAL: This test MUST FAIL on unfixed code.
    
    The reconciliation agent SHALL preserve all encounters with different timepoint indicators,
    maintaining the total encounter count from postprocessing through reconciliation.
    
    Overall Test: 30 encounters should be preserved (not reduced to 7)
    
    Validates Requirements: 2.1, 2.2, 2.3, 2.4
    """
    output_dir = "output/Alexion_NCT04573309_Wilsons_20260308_185157"
    
    # Load postprocessing output
    postproc_path = os.path.join(output_dir, "15_quality_postprocessing.json")
    postproc_entities = load_context_store_entities(postproc_path)
    postproc_encounters = [e for e in postproc_entities if e.get('entity_type') == 'encounter']
    
    print(f"\nTotal encounters before reconciliation: {len(postproc_encounters)}")
    
    # Load reconciliation output
    recon_path = os.path.join(output_dir, "16_quality_reconciliation.json")
    recon_entities = load_context_store_entities(recon_path)
    recon_encounters = [e for e in recon_entities if e.get('entity_type') == 'encounter']
    
    print(f"Total encounters after reconciliation: {len(recon_encounters)}")
    
    encounters_lost = len(postproc_encounters) - len(recon_encounters)
    if encounters_lost > 0:
        print(f"\n⚠️  Lost {encounters_lost} encounters ({encounters_lost/len(postproc_encounters)*100:.1f}% data loss)")
    
    # BUG CONDITION CHECK: All encounters should be preserved
    # Expected: 30 encounters preserved
    # This will FAIL on unfixed code (expected - proves bug exists)
    assert len(recon_encounters) == len(postproc_encounters), (
        f"Bug confirmed: Encounters were incorrectly merged during reconciliation. "
        f"Before: {len(postproc_encounters)}, After: {len(recon_encounters)}. "
        f"Lost {encounters_lost} encounters ({encounters_lost/len(postproc_encounters)*100:.1f}% data loss)."
    )
    
    print("\n✓ All encounters preserved through reconciliation")


if __name__ == "__main__":
    # Run all tests to surface the bug
    print("="*80)
    print("Bug Condition Exploration Tests")
    print("="*80)
    
    try:
        test_op_encounters_not_merged()
    except AssertionError as e:
        print(f"\n❌ Test 1 FAILED (expected): {e}")
    
    print("\n" + "="*80)
    
    try:
        test_inpatient_period_2_encounters_not_merged()
    except AssertionError as e:
        print(f"\n❌ Test 2 FAILED (expected): {e}")
    
    print("\n" + "="*80)
    
    try:
        test_screening_encounters_not_merged()
    except AssertionError as e:
        print(f"\n❌ Test 3 FAILED (expected): {e}")
    
    print("\n" + "="*80)
    
    try:
        test_total_encounter_preservation()
    except AssertionError as e:
        print(f"\n❌ Test 4 FAILED (expected): {e}")
    
    print("\n" + "="*80)
    print("Bug exploration complete. All tests should fail on unfixed code.")
    print("="*80)
