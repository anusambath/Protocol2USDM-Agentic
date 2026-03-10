"""Eval: Metadata agent — study name, phase, type, identifiers."""
import pytest
from evals.helpers import (
    load_usdm, get_study_design, get_study_version,
    normalize, fuzzy_match, count_match_score,
)


@pytest.fixture(scope="module")
def golden_version(golden):
    return get_study_version(golden)


@pytest.fixture(scope="module")
def golden_design(golden):
    return get_study_design(golden)


@pytest.fixture(scope="module")
def pipeline_usdm(pipeline_output_dir):
    return load_usdm(pipeline_output_dir)


@pytest.fixture(scope="module")
def pipeline_version(pipeline_usdm):
    return get_study_version(pipeline_usdm)


@pytest.fixture(scope="module")
def pipeline_design(pipeline_usdm):
    return get_study_design(pipeline_usdm)


def _decode(obj) -> str:
    """Extract decode string from a Code or AliasCode object."""
    if not obj:
        return ""
    if isinstance(obj, str):
        return obj
    # AliasCode wraps standardCode
    if "standardCode" in obj:
        return obj["standardCode"].get("decode", "")
    return obj.get("decode", "")


class TestStudyName:
    def test_study_name_present(self, pipeline_usdm):
        name = pipeline_usdm["study"].get("name", "")
        assert name, "Study name should not be empty"

    def test_study_name_matches_golden(self, golden, pipeline_usdm):
        expected = normalize(golden["study"]["name"])
        actual = normalize(pipeline_usdm["study"]["name"])
        score = fuzzy_match(expected, actual)
        assert score >= 0.7, (
            f"Study name mismatch: expected '{golden['study']['name']}', "
            f"got '{pipeline_usdm['study']['name']}' (similarity={score:.2f})"
        )


class TestStudyIdentifiers:
    def test_identifier_count(self, golden_version, pipeline_version):
        expected = len(golden_version.get("studyIdentifiers", []))
        actual = len(pipeline_version.get("studyIdentifiers", []))
        score = count_match_score(expected, actual)
        assert score >= 0.5, (
            f"Identifier count: expected {expected}, got {actual} (score={score:.2f})"
        )

    def test_nct_number_present(self, pipeline_version):
        """The NCT number should be among the identifiers."""
        ids = pipeline_version.get("studyIdentifiers", [])
        texts = [i.get("text", "") for i in ids]
        has_nct = any("nct" in t.lower() for t in texts)
        assert has_nct, f"No NCT identifier found in: {texts}"


class TestStudyPhase:
    def test_phase_present(self, pipeline_design):
        phase = pipeline_design.get("studyPhase")
        assert phase, "Study phase should be present"

    def test_phase_matches_golden(self, golden_design, pipeline_design):
        expected = _decode(golden_design.get("studyPhase"))
        actual = _decode(pipeline_design.get("studyPhase"))
        if not expected:
            pytest.skip("Golden has no study phase")
        # Normalize phase representations: "Phase II Trial" ≈ "Phase 2"
        import re
        roman = {"i": "1", "ii": "2", "iii": "3", "iv": "4"}
        def norm_phase(s: str) -> str:
            s = s.lower().replace("trial", "").strip()
            for r, d in roman.items():
                s = re.sub(rf"\b{r}\b", d, s)
            return re.sub(r"\s+", " ", s).strip()
        score = fuzzy_match(norm_phase(expected), norm_phase(actual))
        assert score >= 0.6, (
            f"Phase mismatch: expected '{expected}', got '{actual}' (similarity={score:.2f})"
        )


class TestStudyType:
    def test_type_present(self, pipeline_design):
        stype = pipeline_design.get("studyType")
        assert stype, "Study type should be present"

    def test_type_matches_golden(self, golden_design, pipeline_design):
        expected = _decode(golden_design.get("studyType"))
        actual = _decode(pipeline_design.get("studyType"))
        if not expected:
            pytest.skip("Golden has no study type")
        score = fuzzy_match(expected, actual)
        assert score >= 0.6, (
            f"Type mismatch: expected '{expected}', got '{actual}' (similarity={score:.2f})"
        )
