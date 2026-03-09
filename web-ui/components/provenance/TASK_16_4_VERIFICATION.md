# Task 16.4 Verification: Wire Provenance Data to All Components

## Task Requirements
- Load provenance JSON on app initialization ✅
- Pass provenance data to all tabs ✅
- Ensure data flows correctly to inline components ✅
- Validates Requirements: 10.4, 10.5 ✅

## Data Flow Analysis

### 1. API Layer (✅ Complete)
**File**: `web-ui/app/api/protocols/[id]/usdm/route.ts`

The API endpoint loads provenance data and returns it in the response:

```typescript
// Line 200+
return NextResponse.json({
  usdm,
  revision,
  provenance,  // ← Provenance data included
  intermediateFiles,
  generatedAt: usdm.generatedAt,
});
```

**Provenance Data Structure**:
- `cells`: Map of "activityId|encounterId" → CellSource ('text', 'vision', 'both', 'needs_review')
- `cellPageRefs`: Map of cell keys → page numbers array
- `footnotes`: Array of footnote strings
- `entities`: (Optional) Entity-level provenance with agent/model/confidence data

**Derivation Logic**:
The API derives cell-level provenance from:
1. USDM `scheduleTimelines.instances` (activityIds + encounterId in UUID space)
2. Provenance records (entity_id in pre-UUID space, source_type)
3. ID mapping (pre-UUID id → UUID)

### 2. Page Component (✅ Complete)
**File**: `web-ui/app/protocols/[id]/page.tsx`

The page component loads data and manages state:

```typescript
// Line 20: State declaration
const [provenance, setProvenance] = useState<ProvenanceData | null>(null);

// Line 33-38: Load from API
const { usdm, revision, provenance: provData, intermediateFiles: intFiles } = await usdmRes.json();
setProtocol(protocolId, usdm, revision);
setProvenance(provData);
setStoreProvenance(provData); // Also store in protocol store

// Line 75-79: Pass to Workbench
<Workbench
  protocolId={protocolId}
  usdm={usdm as Record<string, unknown>}
  provenance={provenance}  // ← Passed to Workbench
  i