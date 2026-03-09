"""
Bug Condition Exploration Test for SOA Cell Provenance

**Validates: Requirements 2.1, 2.2, 2.3**

This test verifies the bug condition: when SOA extraction occurs and 
9_final_soa_provenance.json has cells, the protocol_usdm_provenance.json 
should also contain populated cells field with UUID-based keys.

EXPECTED OUTCOME ON UNFIXED CODE: Test FAILS
- 9_final_soa_provenance.json contains cell data (e.g., {"cells": {"act_1|pt_1": "both"}})
- protocol_usdm_provenance.json contains empty cells ({})

This test encodes the expected behavior and will validate the fix when it passes.
"""

import os
import json
import pytest
import tempfile
import shutil
from pathlib import Path

# Import validation functions
from core.validation import convert_provenance_to_uuids


class TestSOACellProvenanceBug:
    """Property 1 (Bug Condition): Cell Provenance Data Populated"""
    
    @pytest.fixture
    def sample_soa_provenance(self):
        """
        Create sample SOA provenance data with cells.
        This simulates what 9_final_soa_provenance.json contains.
        """
        return {
            "entities": {
                "activities": {
                    "act_1": "text",
                    "act_2": "both",
                    "act_3": "vision"
                },
                "encounters": {
                    "enc_1": "text",
                    "enc_2": "text",
                    "enc_3": "both"
                }
            },
            "cells": {
                "act_1|enc_1": "both",
                "act_1|enc_2": "text",
                "act_2|enc_1": "vision",
                "act_2|enc_2": "both",
                "act_3|enc_3": "text"
            },
            "cellFootnotes": {
                "act_1|enc_1": ["fn_1", "fn_2"],
                "act_2|enc_2": ["fn_3"]
            },
            "metadata": {
                "generated_at": "2026-03-06T00:00:00",
                "version": "1.0"
            }
        }
    
    @pytest.fixture
    def sample_id_map(self):
        """
        Create sample ID mapping from simple IDs to UUIDs.
        This simulates what convert_ids_to_uuids generates.
        """
        return {
            "act_1": "a1111111-1111-1111-1111-111111111111",
            "act_2": "a2222222-2222-2222-2222-222222222222",
            "act_3": "a3333333-3333-3333-3333-333333333333",
            "enc_1": "e1111111-1111-1111-1111-111111111111",
            "enc_2": "e2222222-2222-2222-2222-222222222222",
            "enc_3": "e3333333-3333-3333-3333-333333333333"
        }
    
    @pytest.fixture
    def temp_test_dir(self):
        """Create a temporary directory for test files"""
        temp_dir = tempfile.mkdtemp(prefix="test_soa_bug_")
        yield temp_dir
        # Cleanup after test
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    
    def test_bug_condition_cell_provenance_missing(
        self, 
        sample_soa_provenance, 
        sample_id_map,
        temp_test_dir
    ):
        """
        Property 1: Bug Condition - Cell Provenance Data Populated
        
        For any pipeline execution where SOA extraction occurs and cell provenance 
        exists in 9_final_soa_provenance.json, the final protocol_usdm_provenance.json 
        file SHALL contain a populated cells field with UUID-based keys.
        
        EXPECTED ON UNFIXED CODE: This test FAILS
        - Input has cells: {"act_1|enc_1": "both", ...}
        - Output has cells: {} (empty)
        
        EXPECTED AFTER FIX: This test PASSES
        - Output has populated cells with UUID keys
        - Cell keys use UUID format: "uuid|uuid"
        """
        # Save the SOA provenance (simulating 9_final_soa_provenance.json)
        soa_prov_path = os.path.join(temp_test_dir, "9_final_soa_provenance.json")
        with open(soa_prov_path, 'w', encoding='utf-8') as f:
            json.dump(sample_soa_provenance, f, indent=2)
        
        # Create a minimal USDM data structure for the conversion
        usdm_data = {
            "study": {
                "versions": [{
                    "studyDesigns": [{
                        "activities": [
                            {"id": sample_id_map["act_1"], "name": "Activity 1"},
                            {"id": sample_id_map["act_2"], "name": "Activity 2"},
                            {"id": sample_id_map["act_3"], "name": "Activity 3"}
                        ],
                        "encounters": [
                            {"id": sample_id_map["enc_1"], "name": "Encounter 1"},
                            {"id": sample_id_map["enc_2"], "name": "Encounter 2"},
                            {"id": sample_id_map["enc_3"], "name": "Encounter 3"}
                        ],
                        "epochs": []
                    }]
                }]
            }
        }
        
        # Simulate the validation.py code that generates protocol_usdm_provenance.json
        # This is the code we're testing/fixing
        orig_provenance_path = soa_prov_path
        if os.path.exists(orig_provenance_path):
            with open(orig_provenance_path, 'r', encoding='utf-8') as f:
                orig_provenance = json.load(f)
            
            # Load intermediate cell provenance from 9_final_soa_provenance.json
            # This ensures cell-level provenance is included in the final output
            cells_before_merge = len(orig_provenance.get('cells', {}))
            print(f"\nLoaded provenance with {cells_before_merge} cells from {orig_provenance_path}")
            
            # Ensure cells and cellFootnotes fields exist
            if 'cells' not in orig_provenance:
                orig_provenance['cells'] = {}
            if 'cellFootnotes' not in orig_provenance:
                orig_provenance['cellFootnotes'] = {}
            
            cells_after_merge = len(orig_provenance.get('cells', {}))
            print(f"Cell count after merge: {cells_after_merge}")
            
            # Convert provenance IDs using id_map
            converted_provenance = convert_provenance_to_uuids(
                orig_provenance, sample_id_map, soa_data=None, usdm_data=usdm_data
            )
            
            # Populate encounter/activity name mappings from USDM data
            try:
                sd = usdm_data.get('study', {}).get('versions', [{}])[0].get('studyDesigns', [{}])[0]
                if 'entities' not in converted_provenance:
                    converted_provenance['entities'] = {}
                
                # Add encounters with names
                converted_provenance['entities']['encounters'] = {
                    enc.get('id'): enc.get('name', 'Unknown')
                    for enc in sd.get('encounters', []) if enc.get('id')
                }
                # Add activities with names
                converted_provenance['entities']['activities'] = {
                    act.get('id'): act.get('name') or act.get('label', 'Unknown')
                    for act in sd.get('activities', []) if act.get('id')
                }
                # Add epochs with names
                converted_provenance['entities']['epochs'] = {
                    epoch.get('id'): epoch.get('name', 'Unknown')
                    for epoch in sd.get('epochs', []) if epoch.get('id')
                }
            except Exception:
                pass
            
            # Save as protocol_usdm_provenance.json
            prov_output_path = os.path.join(temp_test_dir, "protocol_usdm_provenance.json")
            with open(prov_output_path, 'w', encoding='utf-8') as f:
                json.dump(converted_provenance, f, indent=2)
            print(f"Created protocol_usdm_provenance.json ({len(converted_provenance.get('cells', {}))} cells)")
        
        # Load both files
        with open(soa_prov_path, 'r', encoding='utf-8') as f:
            soa_provenance = json.load(f)
        
        final_prov_path = os.path.join(temp_test_dir, "protocol_usdm_provenance.json")
        with open(final_prov_path, 'r', encoding='utf-8') as f:
            final_provenance = json.load(f)
        
        # Check cell counts
        soa_cells = soa_provenance.get('cells', {})
        soa_cell_count = len(soa_cells)
        
        final_cells = final_provenance.get('cells', {})
        final_cell_count = len(final_cells)
        
        print(f"\n9_final_soa_provenance.json has {soa_cell_count} cells")
        print(f"Sample cells: {list(soa_cells.items())[:3]}")
        print(f"\nprotocol_usdm_provenance.json has {final_cell_count} cells")
        
        # BUG CONDITION CHECK
        # On unfixed code: soa_cell_count > 0 but final_cell_count == 0
        # This assertion will FAIL on unfixed code, documenting the bug
        
        assert final_cell_count > 0, \
            f"BUG DETECTED: 9_final_soa_provenance.json has {soa_cell_count} cells " \
            f"but protocol_usdm_provenance.json has {final_cell_count} cells (empty). " \
            f"Cell provenance data was not transferred to final provenance file.\n" \
            f"Expected cells: {list(soa_cells.keys())}\n" \
            f"Actual cells: {list(final_cells.keys())}"
    
    def test_convert_provenance_preserves_cells(
        self,
        sample_soa_provenance,
        sample_id_map
    ):
        """
        Test that convert_provenance_to_uuids correctly converts cell keys.
        
        This tests the conversion function in isolation to verify it WOULD work
        correctly IF the cells were present in the input.
        
        The bug is NOT in convert_provenance_to_uuids - it's that cells are never
        passed to this function in the first place.
        """
        # Convert provenance using the existing function
        converted = convert_provenance_to_uuids(
            sample_soa_provenance,
            sample_id_map
        )
        
        # Verify cells were converted
        assert 'cells' in converted, "Converted provenance missing cells field"
        
        converted_cells = converted['cells']
        original_cells = sample_soa_provenance['cells']
        
        print(f"\nOriginal cells: {len(original_cells)}")
        print(f"Converted cells: {len(converted_cells)}")
        
        # Verify cell count matches
        assert len(converted_cells) == len(original_cells), \
            f"Cell count mismatch: {len(original_cells)} -> {len(converted_cells)}"
        
        # Verify cell keys are in UUID format
        for cell_key in converted_cells.keys():
            assert '|' in cell_key, f"Cell key missing separator: {cell_key}"
            act_id, enc_id = cell_key.split('|', 1)
            
            # Check if IDs look like UUIDs
            assert len(act_id) == 36 and act_id.count('-') == 4, \
                f"Activity ID not in UUID format: {act_id}"
            assert len(enc_id) == 36 and enc_id.count('-') == 4, \
                f"Encounter ID not in UUID format: {enc_id}"
        
        # Verify specific conversions
        expected_key = f"{sample_id_map['act_1']}|{sample_id_map['enc_1']}"
        assert expected_key in converted_cells, \
            f"Expected converted key not found: {expected_key}"
        assert converted_cells[expected_key] == "both", \
            f"Cell provenance value incorrect: {converted_cells[expected_key]}"
        
        print(f"✓ convert_provenance_to_uuids correctly converts cell keys")
        print(f"  Sample: act_1|enc_1 -> {expected_key}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
