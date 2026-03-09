"""
Test that postprocessing agent preserves timepoint information in encounter names.
"""
import pytest
from agents.quality.postprocessing_agent import SoAPostProcessingAgent


def test_encounter_names_preserve_timepoints():
    """Verify that encounter names with timepoint information are NOT normalized."""
    # Sample entities with encounters that have timepoint information
    entities = [
        {
            "id": "enc_1",
            "entity_type": "encounter",
            "data": {
                "name": "OP (Day 1)",
                "label": "OP (Day 1)"
            }
        },
        {
            "id": "enc_2",
            "entity_type": "encounter",
            "data": {
                "name": "OP (Day 2)",
                "label": "OP (Day 2)"
            }
        },
        {
            "id": "enc_3",
            "entity_type": "encounter",
            "data": {
                "name": "Screening (-42 to -9)",
                "label": "Screening (-42 to -9)"
            }
        },
        {
            "id": "enc_4",
            "entity_type": "encounter",
            "data": {
                "name": "Inpatient Period 2 (Day 23)",
                "label": "Inpatient Period 2 (Day 23)"
            }
        },
    ]
    
    # Apply normalization
    normalized_entities, fixes = SoAPostProcessingAgent._normalize_names(entities)
    
    # Verify encounter names are UNCHANGED
    assert normalized_entities[0]["data"]["name"] == "OP (Day 1)"
    assert normalized_entities[0]["data"]["label"] == "OP (Day 1)"
    
    assert normalized_entities[1]["data"]["name"] == "OP (Day 2)"
    assert normalized_entities[1]["data"]["label"] == "OP (Day 2)"
    
    assert normalized_entities[2]["data"]["name"] == "Screening (-42 to -9)"
    assert normalized_entities[2]["data"]["label"] == "Screening (-42 to -9)"
    
    assert normalized_entities[3]["data"]["name"] == "Inpatient Period 2 (Day 23)"
    assert normalized_entities[3]["data"]["label"] == "Inpatient Period 2 (Day 23)"
    
    # Verify NO fixes were applied to encounters
    encounter_fixes = [f for f in fixes if f.entity_type == "encounter"]
    assert len(encounter_fixes) == 0, "No normalization fixes should be applied to encounters"


def test_activity_names_still_normalized():
    """Verify that activity names with timepoint information ARE still normalized."""
    # Sample entities with activities that have timepoint information
    entities = [
        {
            "id": "act_1",
            "entity_type": "activity",
            "data": {
                "name": "Vital Signs (Day 1)",
                "label": "Vital Signs (Day 1)"
            }
        },
        {
            "id": "act_2",
            "entity_type": "activity",
            "data": {
                "name": "Blood Draw (Week 2)",
                "label": "Blood Draw (Week 2)"
            }
        },
    ]
    
    # Apply normalization
    normalized_entities, fixes = SoAPostProcessingAgent._normalize_names(entities)
    
    # Verify activity names ARE normalized (timepoint removed)
    assert normalized_entities[0]["data"]["name"] == "Vital Signs"
    assert normalized_entities[0]["data"]["label"] == "Vital Signs"
    
    assert normalized_entities[1]["data"]["name"] == "Blood Draw"
    assert normalized_entities[1]["data"]["label"] == "Blood Draw"
    
    # Verify fixes were applied to activities
    activity_fixes = [f for f in fixes if f.entity_type == "activity"]
    assert len(activity_fixes) == 4, "Normalization fixes should be applied to activities (2 entities x 2 fields)"


def test_mixed_entity_types():
    """Verify that normalization is applied selectively based on entity type."""
    entities = [
        {
            "id": "enc_1",
            "entity_type": "encounter",
            "data": {"name": "OP (Day 1)"}
        },
        {
            "id": "act_1",
            "entity_type": "activity",
            "data": {"name": "Vital Signs (Day 1)"}
        },
        {
            "id": "proc_1",
            "entity_type": "procedure",
            "data": {"name": "ECG (Week 2)"}
        },
    ]
    
    normalized_entities, fixes = SoAPostProcessingAgent._normalize_names(entities)
    
    # Encounter: timepoint preserved
    assert normalized_entities[0]["data"]["name"] == "OP (Day 1)"
    
    # Activity: timepoint removed
    assert normalized_entities[1]["data"]["name"] == "Vital Signs"
    
    # Procedure: timepoint removed
    assert normalized_entities[2]["data"]["name"] == "ECG"
    
    # Verify only non-encounter entities have fixes
    assert len(fixes) == 2
    assert all(f.entity_type != "encounter" for f in fixes)
