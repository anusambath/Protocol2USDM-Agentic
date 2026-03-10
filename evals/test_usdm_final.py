"""Eval: End-to-end USDM output — schema completeness and structural checks."""
import pytest
from evals.helpers import load_usdm, get_study_design, get_study_version


@pytest.fixture(scope="module")
def pipeline_usdm(pipeline_output_dir):
    return load_usdm(pipeline_output_dir)


@pytest.fixture(scope="module")
def pipeline_design(pipeline_usdm):
    return get_study_design(pipeline_usdm)


@pytest.fixture(scope="module")
def pipeline_version(pipeline_usdm):
    return get_study_version(pipeline_usdm)


class TestUSDMStructure:
    def test_has_study(self, pipeline_usdm):
        assert "study" in pipeline_usdm, "USDM must have 'study' key"

    def test_has_versions(self, pipeline_usdm):
        versions = pipeline_usdm["study"].get("versions", [])
        assert len(versions) > 0, "Study must have at least one version"

    def test_has_study_designs(self, pipeline_version):
        designs = pipeline_version.get("studyDesigns", [])
        assert len(designs) > 0, "Version must have at least one studyDesign"

    def test_usdm_version_present(self, pipeline_usdm):
        version = pipeline_usdm.get("usdmVersion", "")
        assert version, "usdmVersion should be present"


class TestRequiredSections:
    """Verify all major USDM sections are populated."""

    REQUIRED_SECTIONS = [
        ("epochs", 1),
        ("encounters", 1),
        ("activities", 1),
        ("objectives", 1),
        ("eligibilityCriteria", 1),
        ("scheduleTimelines", 1),
    ]

    @pytest.mark.parametrize("section,min_count", REQUIRED_SECTIONS)
    def test_section_populated(self, pipeline_design, section, min_count):
        items = pipeline_design.get(section, [])
        assert len(items) >= min_count, (
            f"Section '{section}' has {len(items)} items, expected >= {min_count}"
        )

    OPTIONAL_SECTIONS = [
        "indications",
        "estimands",
        "elements",
        "studyCells",
        "population",
    ]

    @pytest.mark.parametrize("section", OPTIONAL_SECTIONS)
    def test_optional_section_exists(self, pipeline_design, section):
        """Optional sections should at least exist as keys (even if empty)."""
        assert section in pipeline_design, f"Section '{section}' missing from studyDesign"


class TestIDIntegrity:
    """Verify internal ID references are consistent."""

    def test_epoch_ids_unique(self, pipeline_design):
        epochs = pipeline_design.get("epochs", [])
        ids = [e.get("id") for e in epochs if e.get("id")]
        assert len(ids) == len(set(ids)), f"Duplicate epoch IDs: {ids}"

    def test_encounter_ids_unique(self, pipeline_design):
        encounters = pipeline_design.get("encounters", [])
        ids = [e.get("id") for e in encounters if e.get("id")]
        assert len(ids) == len(set(ids)), f"Duplicate encounter IDs: {ids}"

    def test_activity_ids_unique(self, pipeline_design):
        activities = pipeline_design.get("activities", [])
        ids = [a.get("id") for a in activities if a.get("id")]
        assert len(ids) == len(set(ids)), f"Duplicate activity IDs: {ids}"

    def test_timeline_epoch_refs_valid(self, pipeline_design):
        """Epoch IDs referenced in timeline instances should exist."""
        epoch_ids = {e.get("id") for e in pipeline_design.get("epochs", [])}
        timelines = pipeline_design.get("scheduleTimelines", [])
        bad_refs = []
        for tl in timelines:
            for inst in tl.get("instances", []):
                eid = inst.get("epochId")
                if eid and eid not in epoch_ids:
                    bad_refs.append(eid)
        assert len(bad_refs) == 0, (
            f"Timeline instances reference non-existent epoch IDs: {set(bad_refs)}"
        )

    def test_timeline_encounter_refs_valid(self, pipeline_design):
        """Encounter IDs referenced in timeline instances should exist."""
        enc_ids = {e.get("id") for e in pipeline_design.get("encounters", [])}
        timelines = pipeline_design.get("scheduleTimelines", [])
        bad_refs = []
        for tl in timelines:
            for inst in tl.get("instances", []):
                eid = inst.get("encounterId")
                if eid and eid not in enc_ids:
                    bad_refs.append(eid)
        assert len(bad_refs) == 0, (
            f"Timeline instances reference non-existent encounter IDs: {set(bad_refs)}"
        )
