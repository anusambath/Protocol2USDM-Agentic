# Integration Test Guide for SOA Cell Provenance Fix

## Overview

This guide explains how to run integration tests for the SOA cell provenance bugfix. The fix ensures that cell-level provenance data from SOA tables is properly populated in the final `protocol_usdm_provenance.json` file.

## Test Files

- `tests/test_soa_cell_provenance_integration.py` - Integration tests for tasks 4.1, 4.2, and 4.3
- `tests/test_soa_cell_provenance_preservation.py` - Preservation property tests (task 2)
- `tests/test_soa_cell_provenance_bug.py` - Bug condition exploration tests (task 1)

## Prerequisites

The integration tests require extraction output files to validate against. The fix has been implemented in `core/validation.py` (lines 602-622), but existing output directories were created before the fix was applied.

## Running Integration Tests

### Option 1: Test Against Existing Output (Limited)

Run the tests against existing output files:

```bash
python -m pytest tests/test_soa_cell_provenance_integration.py -v -s
```

**Expected Results:**
- **Test 4.1** (Full pipeline with SOA): SKIPPED - requires fresh extraction
- **Test 4.2** (Frontend display): SKIPPED - requires fresh extraction  
- **Test 4.3** (Non-SOA preservation): PASSED - validates entity-level provenance works

### Option 2: Run Fresh Extraction (Recommended)

To fully validate the fix, run a fresh extraction on a protocol with SOA table:

#### Step 1: Run Extraction

```bash
# Extract a protocol with SOA table (e.g., Alexion Wilson's disease protocol)
python run_extraction.py input/test_trials/Alexion_NCT04573309_Wilsons.pdf --model gemini-2.5-flash
```

This will create a new output directory with the fixed code applied.

#### Step 2: Run Integration Tests

```bash
python -m pytest tests/test_soa_cell_provenance_integration.py -v -s
```

**Expected Results:**
- **Test 4.1** (Full pipeline with SOA): PASSED
  - Verifies `cells` field is populated with UUID-based keys
  - Verifies cell values are valid provenance sources ("both", "text", "vision", "table")
  - Prints cell count and source distribution

- **Test 4.2** (Frontend display): PASSED
  - Verifies debug output shows `cellsCount > 0` and `hasCells: true`
  - Verifies cell colors map correctly (green for "both", blue for "text", etc.)
  - Confirms no cells would display as "orphaned"

- **Test 4.3** (Non-SOA preservation): PASSED
  - Verifies protocols without SOA work correctly
  - Verifies entity-level provenance is unchanged

## Test Details

### Task 4.1: Full Pipeline with SOA Protocol

**Validates Requirements:** 2.1, 2.2, 2.3

**What it tests:**
1. Loads the final `protocol_usdm_provenance.json` file
2. Verifies `cells` field exists and is populated
3. Verifies all cell keys match UUID format: `uuid|uuid`
4. Verifies all cell values are valid provenance sources
5. Prints summary statistics of cell provenance distribution

**Success Criteria:**
- `cells` field contains > 0 entries
- All cell keys match pattern: `[uuid]|[uuid]`
- All cell values are in: {"both", "text", "vision", "table"}

### Task 4.2: Frontend Display

**Validates Requirements:** 2.3

**What it tests:**
1. Simulates frontend debug output
2. Verifies `cellsCount > 0` and `hasCells: true`
3. Maps cell provenance sources to display colors
4. Verifies no cells would display as "orphaned" (gray)

**Success Criteria:**
- Debug output shows correct cell count
- All cells have valid color mappings
- No cells have "unknown" provenance source

**Color Mapping:**
- "both" → green
- "text" → blue
- "vision" → purple
- "table" → orange
- missing/orphaned → gray

### Task 4.3: Non-SOA Protocol Preservation

**Validates Requirements:** 3.1, 3.2, 3.3, 3.4

**What it tests:**
1. Loads provenance file from protocol without SOA
2. Verifies `cells` field is empty or doesn't exist (correct behavior)
3. Verifies entity-level provenance works correctly
4. Verifies provenance structure is intact

**Success Criteria:**
- No errors occur during extraction
- `cells` field is empty or absent
- Entity-level provenance has > 0 records
- All required fields present in provenance records

## Manual Frontend Verification

While the integration tests verify the data structure is correct, manual verification in the web UI is recommended:

### Step 1: Start the Web UI

```bash
cd web-ui
npm run dev
```

### Step 2: Load Protocol

1. Open http://localhost:3000
2. Load a protocol with SOA table (e.g., Alexion_NCT04573309_Wilsons)
3. Navigate to the SOA table tab

### Step 3: Verify Cell Colors

1. Check that SOA cells display with colors (not gray "orphaned")
2. Verify colors match provenance sources:
   - Green cells = "both" (text + vision)
   - Blue cells = "text" only
   - Purple cells = "vision" only
   - Orange cells = "table" only

### Step 4: Check Debug Output

Open browser console and verify:
- `cellsCount > 0`
- `hasCells: true`
- Cell provenance data is available

## Troubleshooting

### Tests Skip with "Output generated before fix"

**Cause:** The test is running against old output files created before the fix was applied.

**Solution:** Run a fresh extraction (see Option 2 above).

### No SOA Protocol Output Found

**Cause:** No extraction output directories contain SOA extraction files.

**Solution:** Run extraction on a protocol with SOA table:
```bash
python run_extraction.py input/test_trials/Alexion_NCT04573309_Wilsons.pdf
```

### Cells Field Empty Despite SOA Extraction

**Cause:** The intermediate `9_final_soa_provenance.json` file may not exist or may be empty.

**Solution:** 
1. Check if `9_final_soa_provenance.json` exists in the output directory
2. Verify it contains cell provenance data
3. Check logs for errors during SOA extraction

## Implementation Details

The fix is implemented in `core/validation.py` (lines 602-622):

1. **Load Intermediate Cell Provenance**: Loads `9_final_soa_provenance.json` containing cell data with simple IDs
2. **Merge Cell Data**: Merges cells and cellFootnotes into the provenance structure
3. **Convert IDs**: The existing `convert_provenance_to_uuids()` function converts cell keys from simple IDs to UUIDs
4. **Save Final File**: Writes `protocol_usdm_provenance.json` with populated cells field

## Related Files

- `core/validation.py` - Contains the fix implementation
- `core/provenance.py` - ProvenanceTracker class that tracks cell-level provenance
- `extraction/text_extractor.py` - Tags cells during text extraction
- `extraction/validator.py` - Tags cells during validation
- `agents/support/provenance_agent.py` - Generates entity-level provenance

## Summary

The integration tests verify that:
1. ✅ Cell provenance data is populated in final provenance file (Task 4.1)
2. ✅ Frontend can display cells with correct colors (Task 4.2)
3. ✅ Non-SOA protocols continue to work correctly (Task 4.3)

For complete validation, run a fresh extraction and verify both automated tests and manual UI display.
