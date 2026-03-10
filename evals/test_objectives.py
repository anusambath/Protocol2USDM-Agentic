"""Eval: Objectives agent — objective/endpoint counts and levels."""
import pytest
from evals.helpers import (
    load_usdm, get_study_design, count_match_score, normalize,
)


@pytest.fixture(scope="module")
def golden_design(golden):
    return get_study_design(golden)


@pytest.fixture(scope="module")
def pipeline_design(pipeline_output_dir):
    return get_study_design(load_usdm(pipeline_output_dir))


def _decode(obj) -> str:
    if not obj:
        return ""
    if isinstance(obj, str):
        return obj
    if "standardCode" in obj:
        return obj["standardCode"].get("decode", "")
    return obj.get("decode", "")


class TestObjectiveCounts:
    def test_objective_count(self, golden_design, pipeline_design):
        expected = len(golden_design.get("objectives", []))
        actual = len(pipeline_design.get("objectives", []))
        score = count_match_score(expected, actual)
        assert score >= 0.5, (
            f"Objectives: expected {expected}, got {actual} (score={score:.2f})"
        )

    def test_has_primary_objective(self, pipeline_design):
        objs = pipeline_design.get("objectives", [])
        has_primary = any(
            "primary" in _decode(o.get("level", {})).lower()
            for o in objs
        )
        assert has_primary, "Should have at least one primary objective"

    def test_has_secondary_objective(self, golden_design, pipeline_design):
        g_sec = [o for o in golden_design.get("objectives", [])
                 if "secondary" in _decode(o.get("level", {})).lower()]
        if not g_sec:
            pytest.skip("Golden has no secondary objectives")
        p_sec = [o for o in pipeline_design.get("objectives", [])
                 if "secondary" in _decode(o.get("level", {})).lower()]
        assert len(p_sec) > 0, "Should have secondary objectives"


class TestEndpoints:
    def test_endpoints_present(self, pipeline_design):
        """Objectives should have associated endpoints."""
        objs = pipeline_design.get("objectives", [])
        with_endpoints = sum(1 for o in objs if o.get("objectiveEndpoints"))
        pct = with_endpoints / max(len(objs), 1)
        assert pct >= 0.3, (
            f"Only {with_endpoints}/{len(objs)} objectives have endpoints"
        )


class TestEstimands:
    def test_estimand_count(self, golden_design, pipeline_design):
        expected = len(golden_design.get("estimands", []))
        actual = len(pipeline_design.get("estimands", []))
        if expected == 0:
            pytest.skip("Golden has no estimands")
        score = count_match_score(expected, actual)
        # Estimands are hard to extract, so lower threshold
        assert score >= 0.3, (
            f"Estimands: expected {expected}, got {actual} (score={score:.2f})"
        )
