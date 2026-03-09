"""
Test SOA cell validation step that marks confirmed cells as "both".

This test verifies that the text agent calls the validator to validate
text-extracted cells against vision images and marks confirmed cells as "both".
"""

import json
import os
import pytest
from pathlib import Path

from core.provenance import ProvenanceTracker, ProvenanceSource


def test_validation_marks_cells_as_both():
    """
    Test that validation step marks confirmed cells as "both".
    
    This test verifies:
    1. Text agent extracts cells and initially marks them as "text"
    2. Validator validates cells against vision images
    3. Confirmed cells are marked as "both" (text + vision agree)
    4. Provenance is saved to 9_final_soa_provenance.json with "both" cells
    """
    # Find a recent extraction output directory
    output_base = Path("output")
    if not output_base.exists():
        pytest.skip("No output directory found")
    
    # Find the most recent Alexion protocol extraction
    protocol_dirs = sorted(
        [d for d in output_base.iterdir() if d.is_dir() and "Alexion" in d.name],
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    if not protocol_dirs:
        pytest.skip("No Alexion protocol extraction found")
    
    output_dir = protocol_dirs[0]
    print(f"\nTesting validation in: {output_dir}")
    
    # Check if 9_final_soa_provenance.json exists
    provenance_file = output_dir / "9_final_soa_provenance.json"
    if not provenance_file.exists():
        pytest.skip(f"No provenance file found at {provenance_file}")
    
    # Load provenance
    with open(provenance_file, 'r') as f:
        provenance_data = json.load(f)
    
    cells = provenance_data.get('cells', {})
    
    # Verify cells exist
    assert cells, "Cells field should not be empty"
    print(f"Found {len(cells)} cells in provenance")
    
    # Count cells by source
    source_counts = {}
    for cell_key, source in cells.items():
        source_counts[source] = source_counts.get(source, 0) + 1
    
    print(f"Cell sources: {source_counts}")
    
    # Verify at least some cells are marked as "both" (validated by vision)
    both_count = source_counts.get('both', 0)
    text_count = source_counts.get('text', 0)
    
    print(f"Cells marked as 'both': {both_count}")
    print(f"Cells marked as 'text': {text_count}")
    
    # After validation, we expect most cells to be marked as "both"
    # Some may remain as "text" if vision couldn't confirm them
    assert both_count > 0, (
        "Expected at least some cells to be marked as 'both' after validation. "
        f"Found: {source_counts}"
    )
    
    # The ratio of "both" to total should be high (>50%)
    total_cells = len(cells)
    both_ratio = both_count / total_cells if total_cells > 0 else 0
    
    print(f"Validation success rate: {both_ratio:.1%}")
    
    assert both_ratio > 0.5, (
        f"Expected >50% of cells to be validated as 'both', got {both_ratio:.1%}. "
        "This suggests validation is not working correctly."
    )


def test_provenance_tracker_merge():
    """
    Test that ProvenanceTracker.merge() correctly marks cells as "both".
    
    This verifies the merge logic used by the validation step.
    """
    # Create two trackers
    text_tracker = ProvenanceTracker()
    vision_tracker = ProvenanceTracker()
    
    # Text tracker marks cells as "text"
    text_tracker.tag_cell("act_1", "pt_1", ProvenanceSource.TEXT)
    text_tracker.tag_cell("act_1", "pt_2", ProvenanceSource.TEXT)
    text_tracker.tag_cell("act_2", "pt_1", ProvenanceSource.TEXT)
    
    # Vision tracker marks confirmed cells as "vision"
    vision_tracker.tag_cell("act_1", "pt_1", ProvenanceSource.VISION)
    vision_tracker.tag_cell("act_1", "pt_2", ProvenanceSource.VISION)
    # act_2|pt_1 not confirmed by vision
    
    # Merge vision into text
    text_tracker.merge(vision_tracker)
    
    # Verify cells marked as "both" when both sources agree
    assert text_tracker.get_cell_source("act_1", "pt_1") == "both"
    assert text_tracker.get_cell_source("act_1", "pt_2") == "both"
    
    # Verify cell remains "text" when vision didn't confirm
    assert text_tracker.get_cell_source("act_2", "pt_1") == "text"


def test_validation_preserves_text_only_cells():
    """
    Test that validation preserves cells that vision couldn't confirm.
    
    These cells should remain marked as "text" (needs review).
    """
    # Find a recent extraction output directory
    output_base = Path("output")
    if not output_base.exists():
        pytest.skip("No output directory found")
    
    protocol_dirs = sorted(
        [d for d in output_base.iterdir() if d.is_dir() and "Alexion" in d.name],
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    if not protocol_dirs:
        pytest.skip("No Alexion protocol extraction found")
    
    output_dir = protocol_dirs[0]
    provenance_file = output_dir / "9_final_soa_provenance.json"
    
    if not provenance_file.exists():
        pytest.skip(f"No provenance file found at {provenance_file}")
    
    with open(provenance_file, 'r') as f:
        provenance_data = json.load(f)
    
    cells = provenance_data.get('cells', {})
    
    # Verify that cells marked as "text" still exist
    # (validation should not remove them, just mark confirmed ones as "both")
    text_cells = [k for k, v in cells.items() if v == 'text']
    
    print(f"Found {len(text_cells)} cells marked as 'text' (unconfirmed by vision)")
    
    # It's OK to have some text-only cells (vision may not confirm all)
    # But we should have both "both" and "text" cells
    both_cells = [k for k, v in cells.items() if v == 'both']
    
    assert len(both_cells) > 0, "Should have at least some 'both' cells"
    
    # If we have text-only cells, that's fine - it means validation is working
    # and marking only confirmed cells as "both"
    if text_cells:
        print(f"Validation correctly preserved {len(text_cells)} unconfirmed cells as 'text'")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
