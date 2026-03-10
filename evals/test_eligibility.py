"""Eval: Eligibility agent — criteria counts and category split."""
import pytest
from evals.helpers import (
    load_usdm, get_study_design, count_match_score, normalize,
)


@pytest.fixture(scope="module")
def golden_criteria(golden):
    return get_study_design(golden).get("eligibilityCriteria", [])


@pytest.fixture(scope="module")
def pipeline_criteria(pipeline_output_dir):
    usdm = load_usdm(pipeline_output_dir)
    return get_study_design(usdm).get("eligibilityCriteria", [])


def _split_criteria(criteria: list[dict]) -> tuple[list, list]:
    """Split criteria into inclusion and exclusion lists."""
    inclusion, exclusion = [], []
    for c in criteria:
        cat = c.get("category", {})
        if isinstance(cat, dict):
            decode = cat.get("decode", "")
        else:
            decode = str(cat)
        if "inclusion" in decode.lower():
            inclusion.append(c)
        elif "exclusion" in decode.lower():
            exclusion.append(c)
    return inclusion, exclusion


class TestCriteriaCounts:
    def test_total_count(self, golden_criteria, pipeline_criteria):
        expected = len(golden_criteria)
        actual = len(pipeline_criteria)
        score = count_match_score(expected, actual)
        assert score >= 0.7, (
            f"Total criteria: expected {expected}, got {actual} (score={score:.2f})"
        )

    def test_inclusion_count(self, golden_criteria, pipeline_criteria):
        g_inc, _ = _split_criteria(golden_criteria)
        p_inc, _ = _split_criteria(pipeline_criteria)
        expected = len(g_inc)
        actual = len(p_inc)
        score = count_match_score(expected, actual)
        assert score >= 0.6, (
            f"Inclusion criteria: expected {expected}, got {actual} (score={score:.2f})"
        )

    def test_exclusion_count(self, golden_criteria, pipeline_criteria):
        _, g_exc = _split_criteria(golden_criteria)
        _, p_exc = _split_criteria(pipeline_criteria)
        expected = len(g_exc)
        actual = len(p_exc)
        score = count_match_score(expected, actual)
        assert score >= 0.6, (
            f"Exclusion criteria: expected {expected}, got {actual} (score={score:.2f})"
        )


class TestCriteriaContent:
    def test_criteria_have_text(self, pipeline_criteria):
        """Every criterion should have non-empty text."""
        empty = []
        for c in pipeline_criteria:
            text = c.get("text", "") or c.get("description", "") or c.get("name", "")
            if not text.strip():
                empty.append(c.get("id", "unknown"))
        assert len(empty) == 0, f"Criteria with empty text: {empty}"

    def test_criteria_have_category(self, pipeline_criteria):
        """Every criterion should be categorized as inclusion or exclusion."""
        uncategorized = []
        for c in pipeline_criteria:
            cat = c.get("category", {})
            decode = cat.get("decode", "") if isinstance(cat, dict) else str(cat)
            if "inclusion" not in decode.lower() and "exclusion" not in decode.lower():
                uncategorized.append(c.get("id", "unknown"))
        pct = len(uncategorized) / max(len(pipeline_criteria), 1)
        assert pct <= 0.1, (
            f"{len(uncategorized)}/{len(pipeline_criteria)} criteria uncategorized"
        )
