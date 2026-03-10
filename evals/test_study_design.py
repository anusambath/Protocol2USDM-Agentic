"""Eval: Study Design agent — epochs, arms, cells, elements."""
import pytest
from evals.helpers import (
    load_usdm, get_study_design,
    count_match_score, name_set, fuzzy_set_match_score,
)


@pytest.fixture(scope="module")
def golden_design(golden):
    return get_study_design(golden)


@pytest.fixture(scope="module")
def pipeline_design(pipeline_output_dir):
    return get_study_design(load_usdm(pipeline_output_dir))


class TestEpochs:
    def test_epoch_count(self, golden_design, pipeline_design):
        expected = len(golden_design.get("epochs", []))
        actual = len(pipeline_design.get("epochs", []))
        score = count_match_score(expected, actual)
        assert score >= 0.8, (
            f"Epochs: expected {expected}, got {actual} (score={score:.2f})"
        )

    def test_epoch_names_match(self, golden_design, pipeline_design):
        expected = name_set(golden_design.get("epochs", []))
        actual = name_set(pipeline_design.get("epochs", []))
        score = fuzzy_set_match_score(expected, actual)
        assert score >= 0.7, (
            f"Epoch name match: {score:.2f} — "
            f"expected {expected}, got {actual}"
        )

    def test_epochs_have_names(self, pipeline_design):
        epochs = pipeline_design.get("epochs", [])
        unnamed = [e for e in epochs if not e.get("name", "").strip()]
        assert len(unnamed) == 0, f"{len(unnamed)} epochs have no name"


class TestStudyCells:
    def test_cell_count(self, golden_design, pipeline_design):
        expected = len(golden_design.get("studyCells", []))
        actual = len(pipeline_design.get("studyCells", []))
        if expected == 0:
            pytest.skip("Golden has no study cells")
        score = count_match_score(expected, actual)
        assert score >= 0.5, (
            f"Study cells: expected {expected}, got {actual} (score={score:.2f})"
        )


class TestStudyElements:
    def test_element_count(self, golden_design, pipeline_design):
        expected = len(golden_design.get("elements", []))
        actual = len(pipeline_design.get("elements", []))
        if expected == 0:
            pytest.skip("Golden has no study elements")
        score = count_match_score(expected, actual)
        assert score >= 0.5, (
            f"Study elements: expected {expected}, got {actual} (score={score:.2f})"
        )


class TestIndications:
    def test_indication_present(self, pipeline_design):
        indications = pipeline_design.get("indications", [])
        assert len(indications) > 0, "Should have at least one indication"

    def test_indication_count(self, golden_design, pipeline_design):
        expected = len(golden_design.get("indications", []))
        actual = len(pipeline_design.get("indications", []))
        score = count_match_score(expected, actual)
        assert score >= 0.8, (
            f"Indications: expected {expected}, got {actual} (score={score:.2f})"
        )
