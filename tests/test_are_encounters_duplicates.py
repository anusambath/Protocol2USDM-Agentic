"""Unit tests for _are_encounters_duplicates function."""

import pytest
from agents.quality.reconciliation_agent import _are_encounters_duplicates


class TestAreEncountersDuplicates:
    """Test the _are_encounters_duplicates function."""
    
    def test_different_timepoints_not_duplicates(self):
        """Encounters with different timepoints should NOT be duplicates."""
        # Even with high fuzzy match score, different timepoints mean not duplicates
        assert not _are_encounters_duplicates("OP (Day 2)", "OP (Day 3)", 0.85)
        assert not _are_encounters_duplicates("Inpatient Period 2 (Day 24)", "Inpatient Period 2 (Day 25)", 0.85)
        assert not _are_encounters_duplicates("Screening (-42 to -9)", "Screening (-21)", 0.85)
    
    def test_same_timepoints_uses_fuzzy_matching(self):
        """Encounters with same timepoints should use fuzzy matching."""
        # Same timepoint, identical names -> duplicates
        assert _are_encounters_duplicates("OP (Day 2)", "OP (Day 2)", 0.85)
        
        # Same timepoint, similar names with lower threshold -> duplicates
        assert _are_encounters_duplicates("Outpatient (Day 2)", "OP (Day 2)", 0.70)
        
        # Same timepoint, low similarity -> not duplicates
        assert not _are_encounters_duplicates("Screening (Day 2)", "Treatment (Day 2)", 0.85)
    
    def test_no_timepoints_uses_fuzzy_matching(self):
        """Encounters without timepoints should use fuzzy matching."""
        # High similarity -> duplicates (using lower threshold that matches actual score)
        assert _are_encounters_duplicates("Screening Visit", "Screening", 0.70)
        
        # Low similarity -> not duplicates
        assert not _are_encounters_duplicates("Screening", "Treatment", 0.85)
    
    def test_one_timepoint_one_without_uses_fuzzy_matching(self):
        """When only one encounter has a timepoint, use fuzzy matching."""
        # Similar names but score too low for 0.85 threshold -> not duplicates
        assert not _are_encounters_duplicates("OP (Day 2)", "OP", 0.85)
        
        # With lower threshold -> duplicates
        assert _are_encounters_duplicates("OP (Day 2)", "OP", 0.30)
        
        # Low similarity -> not duplicates
        assert not _are_encounters_duplicates("Screening (Day 2)", "Treatment", 0.85)
    
    def test_edge_cases(self):
        """Test edge cases."""
        # Empty strings
        assert not _are_encounters_duplicates("", "", 0.85)
        assert not _are_encounters_duplicates("OP (Day 2)", "", 0.85)
        
        # Identical strings
        assert _are_encounters_duplicates("OP (Day 2)", "OP (Day 2)", 0.85)
        
        # Different threshold values (using realistic score of 0.4)
        assert _are_encounters_duplicates("OP Visit", "OP", 0.30)
        assert not _are_encounters_duplicates("OP Visit", "OP", 0.50)
