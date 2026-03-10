"""Eval: SoA Vision agent — encounters, epoch mapping, activities."""
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


class TestEncounters:
    def test_encounter_count(self, golden_design, pipeline_design):
        expected = len(golden_design.get("encounters", []))
        actual = len(pipeline_design.get("encounters", []))
        score = count_match_score(expected, actual)
        assert score >= 0.4, (
            f"Encounters: expected {expected}, got {actual} (score={score:.2f})"
        )

    def test_encounters_have_names(self, pipeline_design):
        encounters = pipeline_design.get("encounters", [])
        unnamed = [e for e in encounters if not e.get("name", "").strip()]
        assert len(unnamed) == 0, f"{len(unnamed)} encounters have no name"

    def test_no_duplicate_encounter_names(self, pipeline_design):
        encounters = pipeline_design.get("encounters", [])
        names = [e.get("name", "") for e in encounters]
        dupes = [n for n in names if names.count(n) > 1]
        assert len(set(dupes)) == 0, f"Duplicate encounter names: {set(dupes)}"


class TestEpochEncounterMapping:
    """Verify encounters are properly linked to epochs."""

    def test_encounters_have_epoch_references(self, pipeline_design):
        """Check that encounters reference epochs via scheduledInstances or epochId."""
        encounters = pipeline_design.get("encounters", [])
        epochs = pipeline_design.get("epochs", [])
        epoch_ids = {e.get("id") for e in epochs}

        # Check via scheduleTimelines → instances → epochId
        timelines = pipeline_design.get("scheduleTimelines", [])
        encounter_ids_with_epoch = set()
        for tl in timelines:
            for inst in tl.get("instances", []):
                enc_id = inst.get("encounterId")
                epoch_id = inst.get("epochId")
                if enc_id and epoch_id and epoch_id in epoch_ids:
                    encounter_ids_with_epoch.add(enc_id)

        # Also check direct epochId on encounter
        for enc in encounters:
            if enc.get("epochId") and enc["epochId"] in epoch_ids:
                encounter_ids_with_epoch.add(enc.get("id"))

        coverage = len(encounter_ids_with_epoch) / max(len(encounters), 1)
        assert coverage >= 0.5, (
            f"Only {len(encounter_ids_with_epoch)}/{len(encounters)} "
            f"encounters mapped to epochs ({coverage:.0%})"
        )


class TestActivities:
    def test_activity_count(self, golden_design, pipeline_design):
        expected = len(golden_design.get("activities", []))
        actual = len(pipeline_design.get("activities", []))
        score = count_match_score(expected, actual)
        assert score >= 0.5, (
            f"Activities: expected {expected}, got {actual} (score={score:.2f})"
        )

    def test_activities_have_names(self, pipeline_design):
        activities = pipeline_design.get("activities", [])
        unnamed = [a for a in activities if not a.get("name", "").strip()]
        pct = len(unnamed) / max(len(activities), 1)
        assert pct <= 0.1, (
            f"{len(unnamed)}/{len(activities)} activities have no name"
        )


class TestScheduleTimelines:
    def test_timeline_exists(self, pipeline_design):
        timelines = pipeline_design.get("scheduleTimelines", [])
        assert len(timelines) > 0, "Should have at least one schedule timeline"

    def test_timeline_count(self, golden_design, pipeline_design):
        expected = len(golden_design.get("scheduleTimelines", []))
        actual = len(pipeline_design.get("scheduleTimelines", []))
        score = count_match_score(expected, actual)
        assert score >= 0.3, (
            f"Timelines: expected {expected}, got {actual} (score={score:.2f})"
        )

    def test_main_timeline_has_instances(self, pipeline_design):
        timelines = pipeline_design.get("scheduleTimelines", [])
        if not timelines:
            pytest.skip("No timelines")
        # Find the one with most instances (likely main)
        main = max(timelines, key=lambda t: len(t.get("instances", [])))
        inst_count = len(main.get("instances", []))
        assert inst_count >= 5, (
            f"Main timeline has only {inst_count} instances"
        )
