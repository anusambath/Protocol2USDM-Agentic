"""
Test that provenance includes entity names for SOA-only encounters/activities.
"""
import json
import os
import pytest


def test_provenance_includes_soa_only_entity_names():
    """
    Verify that provenance file includes entity names for SOA-only encounters/activities
    that aren't in the USDM model but appear in the SOA table.
    """
    # Find the most recent extraction output
    output_dirs = [d for d in os.listdir('output') if d.startswith('Alexion_NCT04573309_Wilsons_2026')]
    if not output_dirs:
        pytest.skip("No extraction output found")
    
    latest_output = sorted(output_dirs)[-1]
    output_dir = os.path.join('output', latest_output)
    
    # Load provenance file
    provenance_path = os.path.join(output_dir, 'Alexion_NCT04573309_Wilsons_provenance.json')
    if not os.path.exists(provenance_path):
        pytest.skip(f"Provenance file not found: {provenance_path}")
    
    with open(provenance_path, encoding='utf-8') as f:
        provenance = json.load(f)
    
    # Load USDM model
    usdm_path = os.path.join(output_dir, 'Alexion_NCT04573309_Wilsons_usdm.json')
    with open(usdm_path, encoding='utf-8') as f:
        usdm = json.load(f)
    
    # Load SOA data
    soa_path = os.path.join(output_dir, '9_final_soa.json')
    with open(soa_path, encoding='utf-8') as f:
        soa = json.load(f)
    
    # Get entity counts
    usdm_encounters = usdm.get('study', {}).get('versions', [{}])[0].get('studyDesigns', [{}])[0].get('encounters', [])
    soa_encounters = [e for e in soa.get('entities', []) if e.get('entity_type') == 'encounter']
    
    provenance_encounters = provenance.get('entities', {}).get('encounters', {})
    provenance_activities = provenance.get('entities', {}).get('activities', {})
    
    print(f"\nEncounter counts:")
    print(f"  USDM model: {len(usdm_encounters)}")
    print(f"  SOA table: {len(soa_encounters)}")
    print(f"  Provenance entities: {len(provenance_encounters)}")
    
    # Verify provenance has at least as many encounters as SOA
    # (SOA encounters + any USDM-only encounters)
    assert len(provenance_encounters) >= len(soa_encounters), \
        f"Provenance should include all SOA encounters: {len(provenance_encounters)} < {len(soa_encounters)}"
    
    # Verify no "Unknown" values in provenance entities
    unknown_encounters = [uuid for uuid, name in provenance_encounters.items() if name == "Unknown"]
    assert len(unknown_encounters) == 0, \
        f"Found {len(unknown_encounters)} encounters with 'Unknown' names in provenance"
    
    unknown_activities = [uuid for uuid, name in provenance_activities.items() if name == "Unknown"]
    assert len(unknown_activities) == 0, \
        f"Found {len(unknown_activities)} activities with 'Unknown' names in provenance"
    
    # Verify all cell keys can be resolved to entity names
    cells = provenance.get('cells', {})
    for cell_key in cells.keys():
        parts = cell_key.split('|')
        assert len(parts) == 2, f"Invalid cell key format: {cell_key}"
        
        activity_uuid, encounter_uuid = parts
        
        # Check if activity UUID has a name
        assert activity_uuid in provenance_activities, \
            f"Activity UUID {activity_uuid} not found in provenance entities"
        assert provenance_activities[activity_uuid] != "Unknown", \
            f"Activity UUID {activity_uuid} has 'Unknown' name"
        
        # Check if encounter UUID has a name
        assert encounter_uuid in provenance_encounters, \
            f"Encounter UUID {encounter_uuid} not found in provenance entities"
        assert provenance_encounters[encounter_uuid] != "Unknown", \
            f"Encounter UUID {encounter_uuid} has 'Unknown' name"
    
    print(f"\n✓ All {len(cells)} cell keys can be resolved to entity names")
    print(f"✓ No 'Unknown' entity names found")


if __name__ == "__main__":
    test_provenance_includes_soa_only_entity_names()
