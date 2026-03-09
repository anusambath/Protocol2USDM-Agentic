"""Unit tests for _extract_timepoint() helper function."""

import pytest
from agents.quality.reconciliation_agent import _extract_timepoint


class TestExtractTimepoint:
    """Test the _extract_timepoint() helper function."""

    def test_single_day_number(self):
        """Test extraction of single day numbers."""
        assert _extract_timepoint("OP (Day 2)") == "day_2"
        assert _extract_timepoint("Screening Day 1") == "day_1"
        assert _extract_timepoint("Visit Day 10") == "day_10"
        
    def test_negative_day_number(self):
        """Test extraction of negative day numbers."""
        assert _extract_timepoint("Screening (Day -42)") == "day_-42"
        assert _extract_timepoint("Baseline Day -7") == "day_-7"
        
    def test_day_range(self):
        """Test extraction of day ranges."""
        assert _extract_timepoint("Screening (Day -42 to -9)") == "day_range_-42_to_-9"
        assert _extract_timepoint("Treatment Day 1 to 5") == "day_range_1_to_5"
        assert _extract_timepoint("Inpatient Period Day 23 to 40") == "day_range_23_to_40"
        
    def test_week_number(self):
        """Test extraction of week numbers."""
        assert _extract_timepoint("Follow-up Week 4") == "week_4"
        assert _extract_timepoint("Treatment Week 12") == "week_12"
        
    def test_parenthetical_number_without_day(self):
        """Test extraction of parenthetical numbers without 'Day' keyword."""
        assert _extract_timepoint("Screening (-42)") == "day_-42"
        assert _extract_timepoint("Visit (2)") == "day_2"
        
    def test_case_insensitive(self):
        """Test that matching is case-insensitive."""
        assert _extract_timepoint("OP (day 2)") == "day_2"
        assert _extract_timepoint("OP (DAY 2)") == "day_2"
        assert _extract_timepoint("Follow-up week 4") == "week_4"
        assert _extract_timepoint("Follow-up WEEK 4") == "week_4"
        
    def test_no_timepoint(self):
        """Test that None is returned when no timepoint is found."""
        assert _extract_timepoint("Screening") is None
        assert _extract_timepoint("Follow-up Visit") is None
        assert _extract_timepoint("Baseline Assessment") is None
        
    def test_empty_or_none_input(self):
        """Test edge cases with empty or None input."""
        assert _extract_timepoint("") is None
        assert _extract_timepoint(None) is None
        
    def test_malformed_patterns(self):
        """Test that malformed patterns return None."""
        assert _extract_timepoint("Day") is None  # No number
        assert _extract_timepoint("Week") is None  # No number
        assert _extract_timepoint("Day abc") is None  # Non-numeric
        assert _extract_timepoint("(Day)") is None  # No number
        
    def test_multiple_timepoints_first_match(self):
        """Test that when multiple patterns exist, the first match is returned."""
        # Day range should match before single day
        result = _extract_timepoint("Visit Day 1 to 5 (Day 3)")
        assert result == "day_range_1_to_5"
        
    def test_real_world_examples(self):
        """Test with real-world encounter names from NCT04573309."""
        assert _extract_timepoint("OP (Day 1)") == "day_1"
        assert _extract_timepoint("OP (Day 2)") == "day_2"
        assert _extract_timepoint("OP (Day 22)") == "day_22"
        assert _extract_timepoint("Inpatient Period 2 (Day 23)") == "day_23"
        assert _extract_timepoint("Inpatient Period 2 (Day 40)") == "day_40"
        assert _extract_timepoint("Screening (-42 to -9)") == "day_range_-42_to_-9"
        assert _extract_timepoint("Screening (-21)") == "day_-21"
        assert _extract_timepoint("Screening (-8)") == "day_-8"
        assert _extract_timepoint("Screening (-7)") == "day_-7"
