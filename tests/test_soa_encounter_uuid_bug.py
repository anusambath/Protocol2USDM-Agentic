"""
Bug Condition Exploration Test for SOA Encounter UUID Mapping Issue

This test MUST FAIL on unfixed code - failure confirms the bug exists.
DO NOT attempt to fix the test or the code when it fails.

The test encodes the expected behavior and will validate the fix when it passes after implementation.

Bug Description:
- SOA encounters extracted from PDF but not in final USDM lack UUID mappings
- Cell keys in provenance remain partially unconverted (e.g., "uuid|encounter_v_18")
- Web UI displays these cells as "Unknown"

Expected Behavior (what this test validates):
- All SOA encounters should have UUID mappings in id_mapping.json
- All cell keys should be in full UUID format (uuid|uuid)
- No cell keys should contain unconverted encounter IDs like "encounter_v_18"
"""

import json
import os
import pytest
import re


def test_soa_encounter_uuid_mappings_complete():
    """
    Property 1: Bug Condition - Complete UUID Conversion for All SOA Encounters
    
    CRITICAL: This test MUST FAIL on unfixed code.
    
    For any SOA encounter referenced in cell provenance (exists in 9_final_soa_provenance.json),
    the system SHALL generate a UUID mapping for that encounter, enabling complete
    UUID conversion of all cell keys to full UUID format (uuid|uuid).
    
    Validates Requirements: 2.1, 2.2, 2.3, 2.4
    """
    # Use the latest extraction output directory
    output_dir = "output/Alexion_NCT04573309_Wilsons_20260307_215101"
    
    # Load SOA provenance to get all encounter IDs referenced in cells
    soa_prov_path = os.path.join(output_dir, "9_final_soa_provenance.json")
    assert os.path.exists(soa_prov_path), f"SOA provenance file not found: {soa_prov_path}"
    
    with open(soa_prov_path, 'r', encoding='utf-8') as f:
        soa_provenance = json.load(f)
    
    # Extract all encounter IDs from cell keys
    soa_encounters = set()
    cells = soa_provenance.get('cells', {})
    for cell_key in cells.keys():
        if '|' in cell_key:
            parts = cell_key.split('|', 1)
            encounter_id = parts[1]
            # Collect encounter IDs (should be encounter_v_N format)
            if encounter_id.startswith('encounter_v_'):
                soa_encounters.add(encounter_id)
    
    assert len(soa_encounters) > 0, "No SOA encounters found in provenance cell keys"
    print(f"\nFound {len(soa_encounters)} encounters in SOA data")
    
    # Load ID mapping
    id_map_path = os.path.join(output_dir, "id_mapping.json")
    assert os.path.exists(id_map_path), f"ID mapping file not found: {id_map_path}"
    
    with open(id_map_path, 'r', encoding='utf-8') as f:
        id_map = json.load(f)
    
    # Check which SOA encounters have UUID mappings
    mapped_encounters = set()
    missing_encounters = set()
    
    for enc_id in soa_encounters:
        if enc_id in id_map:
            mapped_encounters.add(enc_id)
        else:
            missing_encounters.add(enc_id)
    
    print(f"Encounters with UUID mappings: {len(mapped_encounters)}")
    print(f"Encounters WITHOUT UUID mappings: {len(missing_encounters)}")
    
    if missing_encounters:
        print(f"\nMissing UUID mappings for: {sorted(missing_encounters)}")
    
    # BUG CONDITION CHECK: All SOA encounters should have UUID mappings
    # This will FAIL on unfixed code (expected - proves bug exists)
    assert len(missing_encounters) == 0, (
        f"Bug confirmed: {len(missing_encounters)} SOA encounters lack UUID mappings. "
        f"Missing: {sorted(missing_encounters)}"
    )
    
    # Load final provenance file
    protocol_id = "Alexion_NCT04573309_Wilsons"
    prov_path = os.path.join(output_dir, f"{protocol_id}_provenance.json")
    assert os.path.exists(prov_path), f"Provenance file not found: {prov_path}"
    
    with open(prov_path, 'r', encoding='utf-8') as f:
        provenance = json.load(f)
    
    # Check cell keys for unconverted encounter IDs
    cells = provenance.get('cells', {})
    uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
    
    unconverted_cells = []
    partially_converted_cells = []
    fully_converted_cells = []
    
    for cell_key in cells.keys():
        if '|' in cell_key:
            parts = cell_key.split('|', 1)
            activity_id = parts[0]
            encounter_id = parts[1]
            
            activity_is_uuid = bool(uuid_pattern.match(activity_id))
            encounter_is_uuid = bool(uuid_pattern.match(encounter_id))
            
            if activity_is_uuid and encounter_is_uuid:
                fully_converted_cells.append(cell_key)
            elif activity_is_uuid and not encounter_is_uuid:
                partially_converted_cells.append(cell_key)
            else:
                unconverted_cells.append(cell_key)
    
    print(f"\nCell key conversion status:")
    print(f"  Fully converted (uuid|uuid): {len(fully_converted_cells)}")
    print(f"  Partially converted (uuid|encounter_v_N): {len(partially_converted_cells)}")
    print(f"  Unconverted (activity_t_N|encounter_v_N): {len(unconverted_cells)}")
    
    if partially_converted_cells:
        print(f"\nExample partially converted cells: {partially_converted_cells[:5]}")
    
    if unconverted_cells:
        print(f"\nExample unconverted cells: {unconverted_cells[:5]}")
    
    # BUG CONDITION CHECK: All cell keys should be fully converted
    # This will FAIL on unfixed code (expected - proves bug exists)
    assert len(partially_converted_cells) == 0, (
        f"Bug confirmed: {len(partially_converted_cells)} cell keys are partially converted. "
        f"Examples: {partially_converted_cells[:5]}"
    )
    
    assert len(unconverted_cells) == 0, (
        f"Bug confirmed: {len(unconverted_cells)} cell keys are unconverted. "
        f"Examples: {unconverted_cells[:5]}"
    )
    
    print("\n✓ All SOA encounters have UUID mappings")
    print("✓ All cell keys are in full UUID format")


if __name__ == "__main__":
    # Run the test to surface the bug
    test_soa_encounter_uuid_mappings_complete()
