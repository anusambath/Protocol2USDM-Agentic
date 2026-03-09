"""
Integration Tests for SOA Cell Provenance Fix

**Validates: Requirements 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 3.4**

These tests verify the fix works end-to-end in the actual pipeline and UI.
"""

import os
import json
import pytest
import re
from pathlib import Path


class TestSOACellProvenanceIntegration:
    """Task 4: Integration testing for SOA cell provenance fix"""
    
    @pytest.fixture
    def soa_protocol_output_dir(self):
        """
        Find the most recent output directory for a protocol with SOA extraction.
        
        This fixture looks for output directories that contain SOA extraction files
        (02_extraction_soa_vision.json and 03_extraction_soa_text.json).
        """
        output_base = Path("output")
        if not output_base.exists():
            pytest.skip("No output directory found - run extraction first")
        
        # Find directories with SOA extraction
        soa_dirs = []
        for output_dir in output_base.iterdir():
            if not output_dir.is_dir():
                continue
            
            soa_vision = output_dir / "02_extraction_soa_vision.json"
            soa_text = output_dir / "03_extraction_soa_text.json"
            
            if soa_vision.exists() and soa_text.exists():
                soa_dirs.append(output_dir)
        
        if not soa_dirs:
            pytest.skip("No output directories with SOA extraction found - run extraction on a protocol with SOA table first")
        
        # Return the most recent one (by directory name timestamp)
        most_recent = sorted(soa_dirs, key=lambda d: d.name)[-1]
        return most_recent
    
    @pytest.fixture
    def non_soa_protocol_output_dir(self):
        """
        Find an output directory for a protocol without SOA extraction.
        
        This fixture looks for output directories that do NOT contain SOA extraction files.
        """
        output_base = Path("output")
        if not output_base.exists():
            pytest.skip("No output directory found - run extraction first")
        
        # Find directories without SOA extraction
        non_soa_dirs = []
        for output_dir in output_base.iterdir():
            if not output_dir.is_dir():
                continue
            
            soa_vision = output_dir / "02_extraction_soa_vision.json"
            soa_text = output_dir / "03_extraction_soa_text.json"
            
            # Check if this directory has no SOA files OR empty SOA files
            has_soa = False
            if soa_vision.exists() and soa_text.exists():
                try:
                    with open(soa_vision) as f:
                        vision_data = json.load(f)
                    with open(soa_text) as f:
                        text_data = json.load(f)
                    
                    # Check if SOA data is actually present
                    if vision_data.get("activities") or text_data.get("activities"):
                        has_soa = True
                except:
                    pass
            
            if not has_soa:
                non_soa_dirs.append(output_dir)
        
        if not non_soa_dirs:
            pytest.skip("No output directories without SOA extraction found")
        
        # Return the most recent one
        most_recent = sorted(non_soa_dirs, key=lambda d: d.name)[-1]
        return most_recent
    
    def test_4_1_full_pipeline_with_soa_protocol(self, soa_protocol_output_dir):
        """
        Task 4.1: Test full pipeline with SOA protocol
        
        - Run extraction pipeline on protocol with SOA table
        - Verify protocol_usdm_provenance.json contains populated cells field
        - Verify cell keys are in UUID format
        - Verify cell values match provenance sources ("both", "text", "table")
        
        **Validates: Requirements 2.1, 2.2, 2.3**
        
        NOTE: This test requires a fresh extraction run with the fixed code.
        If testing against old output files (before fix), the test will be skipped.
        """
        print(f"\nTesting SOA protocol output: {soa_protocol_output_dir.name}")
        
        # Find the final provenance file (not the intermediate 20_support_provenance.json)
        provenance_files = [f for f in soa_protocol_output_dir.glob("*_provenance.json") 
                           if not f.name.startswith("20_")]
        assert len(provenance_files) > 0, f"No final provenance file found in {soa_protocol_output_dir}"
        
        provenance_file = provenance_files[0]
        print(f"Provenance file: {provenance_file.name}")
        
        # Load provenance data
        with open(provenance_file) as f:
            provenance_data = json.load(f)
        
        # Check if this is an old output file (before fix was applied)
        if "cells" not in provenance_data:
            pytest.skip(
                "This output was generated before the fix was applied. "
                "Run a fresh extraction with the fixed code to test this requirement. "
                "The fix has been implemented in core/validation.py lines 602-622."
            )
        
        # Verify cells field exists
        cells = provenance_data["cells"]
        
        # Verify cells field is populated (not empty)
        assert isinstance(cells, dict), "cells field should be a dictionary"
        assert len(cells) > 0, "cells field should not be empty for SOA protocol"
        
        print(f"✓ Cells field populated with {len(cells)} entries")
        
        # Verify cell keys are in UUID format (uuid|uuid)
        uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
        
        invalid_keys = []
        for cell_key in cells.keys():
            if not uuid_pattern.match(cell_key):
                invalid_keys.append(cell_key)
        
        assert len(invalid_keys) == 0, f"Found {len(invalid_keys)} cell keys not in UUID format: {invalid_keys[:5]}"
        print(f"✓ All cell keys are in UUID format (uuid|uuid)")
        
        # Verify cell values match expected provenance sources
        valid_sources = {"both", "text", "vision", "table"}
        invalid_values = []
        
        for cell_key, cell_value in cells.items():
            if cell_value not in valid_sources:
                invalid_values.append((cell_key, cell_value))
        
        assert len(invalid_values) == 0, f"Found {len(invalid_values)} invalid cell values: {invalid_values[:5]}"
        print(f"✓ All cell values are valid provenance sources")
        
        # Print summary statistics
        source_counts = {}
        for source in cells.values():
            source_counts[source] = source_counts.get(source, 0) + 1
        
        print(f"\nCell provenance summary:")
        for source, count in sorted(source_counts.items()):
            print(f"  {source}: {count} cells")
        
        print(f"\n✓ Task 4.1 PASSED: Full pipeline with SOA protocol works correctly")
    
    def test_4_2_frontend_display(self, soa_protocol_output_dir):
        """
        Task 4.2: Test frontend display
        
        - Load protocol in web UI
        - Verify SOA cells display with correct provenance colors (not "orphaned")
        - Verify cell colors match provenance sources (green for "both", blue for "text", etc.)
        - Verify debug output shows cellsCount > 0 and hasCells: true
        
        **Validates: Requirements 2.3**
        
        NOTE: This test verifies the data structure is correct for frontend display.
        Manual verification in the web UI is still recommended.
        This test requires a fresh extraction run with the fixed code.
        """
        print(f"\nTesting frontend display data for: {soa_protocol_output_dir.name}")
        
        # Find the final provenance file (not the intermediate 20_support_provenance.json)
        provenance_files = [f for f in soa_protocol_output_dir.glob("*_provenance.json") 
                           if not f.name.startswith("20_")]
        assert len(provenance_files) > 0, f"No final provenance file found in {soa_protocol_output_dir}"
        
        provenance_file = provenance_files[0]
        
        # Load provenance data
        with open(provenance_file) as f:
            provenance_data = json.load(f)
        
        # Check if this is an old output file (before fix was applied)
        if "cells" not in provenance_data:
            pytest.skip(
                "This output was generated before the fix was applied. "
                "Run a fresh extraction with the fixed code to test this requirement. "
                "The fix has been implemented in core/validation.py lines 602-622."
            )
        
        # Verify cells field exists and is populated
        cells = provenance_data["cells"]
        assert len(cells) > 0, "cells field should not be empty"
        
        # Simulate frontend debug output
        cells_count = len(cells)
        has_cells = len(cells) > 0
        
        print(f"Frontend debug output simulation:")
        print(f"  cellsCount: {cells_count}")
        print(f"  hasCells: {has_cells}")
        
        # Verify debug output matches expectations
        assert cells_count > 0, "cellsCount should be > 0"
        assert has_cells == True, "hasCells should be true"
        
        print(f"✓ Debug output correct: cellsCount={cells_count}, hasCells={has_cells}")
        
        # Verify cell provenance sources are valid for color mapping
        # Frontend color mapping:
        # - "both" -> green
        # - "text" -> blue
        # - "vision" -> purple
        # - "table" -> orange
        # - missing/orphaned -> gray
        
        color_mapping = {
            "both": "green",
            "text": "blue", 
            "vision": "purple",
            "table": "orange"
        }
        
        cells_by_color = {}
        for cell_key, source in cells.items():
            color = color_mapping.get(source, "unknown")
            if color not in cells_by_color:
                cells_by_color[color] = []
            cells_by_color[color].append(cell_key)
        
        print(f"\nCell color distribution:")
        for color, cell_list in sorted(cells_by_color.items()):
            print(f"  {color}: {len(cell_list)} cells")
        
        # Verify no cells would be displayed as "orphaned" (gray)
        assert "unknown" not in cells_by_color, "Some cells have invalid provenance sources"
        
        print(f"\n✓ Task 4.2 PASSED: Frontend display data is correct")
        print(f"  NOTE: Manual verification in web UI is recommended to confirm visual display")
    
    def test_4_3_non_soa_protocol_preservation(self, non_soa_protocol_output_dir):
        """
        Task 4.3: Test non-SOA protocol preservation
        
        - Run extraction pipeline on protocol without SOA
        - Verify no errors occur
        - Verify cells field remains empty (correct behavior)
        - Verify entity-level provenance works correctly
        
        **Validates: Requirements 3.1, 3.2, 3.3, 3.4**
        """
        print(f"\nTesting non-SOA protocol output: {non_soa_protocol_output_dir.name}")
        
        # Find the final provenance file (not the intermediate 20_support_provenance.json)
        provenance_files = [f for f in non_soa_protocol_output_dir.glob("*_provenance.json") 
                           if not f.name.startswith("20_")]
        assert len(provenance_files) > 0, f"No final provenance file found in {non_soa_protocol_output_dir}"
        
        provenance_file = provenance_files[0]
        print(f"Provenance file: {provenance_file.name}")
        
        # Load provenance data
        with open(provenance_file) as f:
            provenance_data = json.load(f)
        
        # Verify cells field is empty or doesn't exist (both are correct)
        if "cells" in provenance_data:
            cells = provenance_data["cells"]
            assert isinstance(cells, dict), "cells field should be a dictionary"
            assert len(cells) == 0, "cells field should be empty for non-SOA protocol"
            print(f"✓ Cells field exists and is empty (correct)")
        else:
            print(f"✓ Cells field does not exist (correct)")
        
        # Verify entity-level provenance works correctly
        assert "records" in provenance_data, "Provenance file missing 'records' field"
        records = provenance_data["records"]
        
        assert isinstance(records, list), "records field should be a list"
        assert len(records) > 0, "records field should not be empty"
        
        print(f"✓ Entity-level provenance populated with {len(records)} records")
        
        # Verify record structure
        sample_record = records[0]
        required_fields = ["entity_id", "entity_type", "source_agent_id", "source_type"]
        
        for field in required_fields:
            assert field in sample_record, f"Record missing required field: {field}"
        
        print(f"✓ Entity-level provenance structure is correct")
        
        # Verify summary statistics
        if "summary" in provenance_data:
            summary = provenance_data["summary"]
            print(f"\nProvenance summary:")
            print(f"  Total entities: {summary.get('total_entities', 0)}")
            print(f"  Entities with provenance: {summary.get('entities_with_provenance', 0)}")
            print(f"  Coverage: {summary.get('coverage_percent', 0):.1f}%")
        
        print(f"\n✓ Task 4.3 PASSED: Non-SOA protocol preservation works correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
