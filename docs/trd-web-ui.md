# Technical Requirements Document (TRD)
# Protocol2USDM Web UI

**Version:** 1.0  
**Date:** February 27, 2026  
**Status:** Final  
**Author:** Protocol2USDM Team

---

## Executive Summary

This Technical Requirements Document (TRD) provides detailed technical specifications for implementing the Protocol2USDM Web UI. It covers architecture, data models, component specifications, API endpoints, and implementation guidelines necessary to recreate the web application.

---

## 1. System Architecture

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              Protocol2USDM Web UI Architecture               │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Browser Layer                              │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐            │ │
│  │  │  React   │  │ AG Grid  │  │Cytoscape │            │ │
│  │  │Components│  │Enterprise│  │   .js    │            │ │
│  │  └──────────┘  └──────────┘  └──────────┘            │ │
│  └────────────────────────────────────────────────────────┘ │
│                            │                                 │
│                            ▼                                 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              State Management                           │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐            │ │
│  │  │ Zustand  │  │  React   │  │Component │            │ │
│  │  │  Global  │  │  Query   │  │  Local   │            │ │
│  │  └──────────┘  └──────────┘  └──────────┘            │ │
│  └────────────────────────────────────────────────────────┘ │
│                            │                                 │
│                            ▼                                 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Next.js Server                             │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐            │ │
│  │  │   App    │  │   API    │  │  Server  │            │ │
│  │  │  Router  │  │  Routes  │  │Components│            │ │
│  │  └──────────┘  └──────────┘  └──────────┘            │ │
│  └────────────────────────────────────────────────────────┘ │
│                            │                                 │
│                            ▼                                 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Data Layer                                 │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐            │ │
│  │  │ Adapters │  │  Schema  │  │   File   │            │ │
│  │  │(USDM→VM) │  │Validation│  │  System  │            │ │
│  │  └──────────┘  └──────────┘  └──────────┘            │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Technology Stack

**Frontend:**
- Next.js 16.1.6 (React framework with App Router)
- React 19.0.0 (UI library)
- TypeScript 5.7.2 (type safety)
- Tailwind CSS 3.4.16 (styling)
- shadcn/ui (component library)

**Data Visualization:**
- AG Grid Enterprise 32.3.3 (SoA table)
- Cytoscape.js 3.30.4 (timeline graph)

**State Management:**
- Zustand 5.0.2 (global state)
- TanStack React Query 5.62.8 (server state)
- Immer 10.1.1 (immutable updates)

**UI Components:**
- Radix UI (accessible primitives)
- Lucide React 0.468.0 (icons)
- Framer Motion 11.15.0 (animations)

**Validation:**
- Zod 3.24.1 (schema validation)

**Virtualization:**
- react-window 2.2.7 (windowed list rendering)

### 1.3 Project Structure


```
web-ui/
├── app/                          # Next.js App Router
│   ├── layout.tsx                # Root layout with providers
│   ├── page.tsx                  # Protocol list page
│   ├── globals.css               # Global styles
│   ├── api/                      # API routes
│   │   └── protocols/
│   │       ├── route.ts          # GET /api/protocols
│   │       └── [id]/
│   │           ├── ars/
│   │           │   └── route.ts  # GET /api/protocols/[id]/ars
│   │           ├── id-mapping/
│   │           │   └── route.ts  # GET /api/protocols/[id]/id-mapping
│   │           ├── images/
│   │           │   ├── route.ts  # GET /api/protocols/[id]/images
│   │           │   └── [filename]/
│   │           │       └── route.ts
│   │           ├── overlay/
│   │           │   ├── draft/    # PUT /api/protocols/[id]/overlay/draft
│   │           │   ├── publish/  # POST /api/protocols/[id]/overlay/publish
│   │           │   └── published/ # GET /api/protocols/[id]/overlay/published
│   │           ├── pages/
│   │           │   ├── [pageNum]/
│   │           │   │   └── route.ts
│   │           │   └── range/
│   │           │       └── route.ts
│   │           ├── provenance/
│   │           │   └── route.ts  # GET /api/protocols/[id]/provenance
│   │           ├── usdm/
│   │           │   └── route.ts  # GET /api/protocols/[id]/usdm
│   │           └── validation/
│   │               └── route.ts  # GET /api/protocols/[id]/validation
│   └── protocols/
│       └── [id]/
│           └── page.tsx          # Protocol detail page
│
├── components/                   # React components
│   ├── workbench/                # VS Code-style workbench layout
│   │   ├── Workbench.tsx         # Main workbench container
│   │   ├── ActivityBar.tsx       # Left icon bar for navigation
│   │   ├── Sidebar.tsx           # Collapsible sidebar panel
│   │   ├── CenterPanel.tsx       # Main content area
│   │   ├── RightPanel.tsx        # Right detail panel
│   │   ├── StatusBar.tsx         # Bottom status bar
│   │   ├── CommandPalette.tsx    # Keyboard-driven command palette
│   │   ├── PanelSplitter.tsx     # Resizable panel dividers
│   │   ├── PanelTabBar.tsx       # Tab bar for panels
│   │   ├── NavTree.tsx           # Navigation tree component
│   │   ├── SearchPanel.tsx       # Search panel
│   │   └── QualityPanel.tsx      # Quality metrics panel
│   ├── soa/                      # SoA table components
│   │   ├── SoAView.tsx           # Main SoA view
│   │   ├── SoAGrid.tsx           # AG Grid wrapper
│   │   ├── SoAToolbar.tsx        # Table toolbar
│   │   ├── ProvenanceCellRenderer.tsx  # Custom cell renderer
│   │   └── FootnotePanel.tsx     # Footnote display
│   ├── timeline/                 # Timeline components
│   │   ├── TimelineView.tsx      # Main timeline view
│   │   ├── TimelineCanvas.tsx    # Cytoscape wrapper
│   │   ├── TimelineToolbar.tsx   # Graph controls
│   │   ├── NodeDetailsPanel.tsx  # Node details
│   │   ├── ExecutionModelView.tsx # Execution model tabs
│   │   ├── SAPDataView.tsx       # SAP data view
│   │   └── ARSDataView.tsx       # ARS data view
│   ├── protocol/                 # Protocol section views
│   │   ├── StudyMetadataView.tsx
│   │   ├── EligibilityCriteriaView.tsx
│   │   ├── ObjectivesEndpointsView.tsx
│   │   ├── StudyDesignView.tsx
│   │   ├── InterventionsView.tsx
│   │   ├── ProceduresDevicesView.tsx
│   │   ├── NarrativeView.tsx
│   │   ├── AdvancedEntitiesView.tsx
│   │   ├── StudySitesView.tsx
│   │   ├── AmendmentHistoryView.tsx
│   │   ├── FootnotesView.tsx
│   │   ├── ExtensionsView.tsx
│   │   └── ScheduleTimelineView.tsx
│   ├── provenance/               # Provenance components
│   │   ├── ProvenanceView.tsx    # Main provenance view
│   │   ├── ProvenanceExplorer.tsx # Entity provenance list
│   │   ├── ProvenanceStats.tsx   # Statistics dashboard
│   │   ├── ProvenanceSidebar.tsx # Sidebar provenance panel
│   │   ├── ProvenanceInline.tsx  # Inline provenance display
│   │   ├── ProvenanceDetails.tsx # Detailed provenance view
│   │   ├── ProtocolPreview.tsx   # Protocol preview component
│   │   ├── ErrorBoundary.tsx     # Error boundary
│   │   └── SkipLink.tsx          # Accessibility skip link
│   ├── quality/                  # Quality components
│   │   ├── QualityMetricsDashboard.tsx
│   │   └── ValidationResultsView.tsx
│   ├── intermediate/             # Intermediate file viewers
│   │   ├── ExtractionOutputView.tsx
│   │   ├── SoAImagesViewer.tsx
│   │   └── DocumentStructureView.tsx
│   ├── overlay/                  # Overlay/draft components
│   │   ├── DraftPublishControls.tsx
│   │   └── OverlayDebugPanel.tsx
│   ├── theme/                    # Theme components
│   │   ├── ThemeProvider.tsx
│   │   └── ThemeToggle.tsx
│   └── ui/                       # Base UI components (shadcn)
│       ├── button.tsx
│       ├── card.tsx
│       ├── tabs.tsx
│       ├── badge.tsx
│       ├── hover-card.tsx
│       ├── progress.tsx
│       └── export-button.tsx
│
├── lib/                          # Core libraries
│   ├── adapters/                 # Data adapters
│   │   ├── soa-adapter.ts        # USDM → SoA table model
│   │   ├── timeline-adapter.ts   # USDM → graph model
│   │   ├── provenance-adapter.ts # Provenance → stats
│   │   └── quality-adapter.ts    # USDM → quality metrics
│   ├── cache/                    # Caching utilities
│   ├── export/                   # Export utilities
│   ├── hooks/                    # React hooks
│   ├── overlay/                  # Overlay schema
│   │   ├── schema.ts             # Overlay type definitions
│   │   └── validator.ts          # Overlay validation
│   ├── performance/              # Performance utilities
│   ├── provenance/               # Provenance types
│   │   └── types.ts              # Provenance data models
│   ├── stores/                   # Additional stores
│   │   └── provenance-sidebar-store.ts
│   ├── commandRegistry.ts        # Command palette registry
│   ├── viewRegistry.tsx          # View registry
│   └── utils.ts                  # Utility functions
│
├── stores/                       # Zustand stores
│   ├── protocolStore.ts          # Protocol state
│   ├── overlayStore.ts           # Overlay state
│   └── layoutStore.ts            # Layout/workbench state
│
├── styles/                       # Styles
│   └── ag-grid-theme.css         # AG Grid custom theme
│
├── public/                       # Static assets
│   └── icons/                    # Custom icons
│
├── next.config.mjs               # Next.js configuration
├── tailwind.config.ts            # Tailwind configuration
├── tsconfig.json                 # TypeScript configuration
├── package.json                  # Dependencies
└── .env.example                  # Environment variables template
```

---

## 2. Data Models

### 2.1 USDM Data Model (Read-Only)

The UI reads USDM v4.0 JSON structure. Key entities:

```typescript
// USDM Root Structure
interface USDMDocument {
  study: Study;
  version: string;
  systemName: string;
  systemVersion: string;
}

interface Study {
  id: string;
  name: string;
  studyTitle: string;
  studyPhase?: Code;
  studyType?: Code;
  studyIdentifiers: StudyIdentifier[];
  studyProtocolVersions: StudyProtocolVersion[];
  studyDesigns: StudyDesign[];
  objectives: Objective[];
  studyInterventions: StudyIntervention[];
  activities: Activity[];
  encounters: Encounter[];
  epochs: Epoch[];
  biomedicalConcepts: BiomedicalConcept[];
  eligibilityCriteria: EligibilityCriterion[];
  // ... other entities
}

interface Activity {
  id: string;
  name: string;
  description?: string;
  label?: string;
  studyInterventionIds?: string[];
  biomedicalConceptIds?: string[];
  definedProcedures?: Procedure[];
  instanceType: "Activity";
}

interface Encounter {
  id: string;
  name: string;
  description?: string;
  label?: string;
  encounterType?: Code;
  transitionStartRule?: TransitionRule;
  transitionEndRule?: TransitionRule;
  epochId?: string;
  previousId?: string;
  nextId?: string;
  instanceType: "Encounter";
}

interface Epoch {
  id: string;
  name: string;
  description?: string;
  label?: string;
  epochType?: Code;
  sequenceInStudy?: number;
  previousId?: string;
  nextId?: string;
  instanceType: "Epoch";
}

interface ScheduledActivityInstance {
  id: string;
  activityIds: string[];
  encounterId: string;
  defaultConditionId?: string;
  instanceType: "ScheduledActivityInstance";
}
```

### 2.2 Provenance Data Model

```typescript
interface ProvenanceDocument {
  version: string;
  protocolId: string;
  timestamp: string;
  entries: ProvenanceEntry[];
}

interface ProvenanceEntry {
  entityId: string;              // USDM entity ID
  entityType: string;            // "Activity", "Encounter", etc.
  fieldName: string;             // "name", "description", etc.
  source: ProvenanceSource;      // "text", "vision", "both"
  confidence: number;            // 0.0-1.0
  extractionMethod: string;      // "llm_text", "llm_vision", "manual"
  modelName?: string;            // LLM model used
  timestamp: string;             // ISO 8601
  pageNumber?: number;           // Source PDF page
  boundingBox?: BoundingBox;     // Vision bounding box
}

type ProvenanceSource = "text" | "vision" | "both" | "orphaned";

interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

// Provenance Statistics (computed)
interface ProvenanceStats {
  totalEntities: number;
  confirmed: number;           // both
  textOnly: number;
  visionOnly: number;
  orphaned: number;
  confirmedPercentage: number;
  textOnlyPercentage: number;
  visionOnlyPercentage: number;
  orphanedPercentage: number;
}
```

### 2.3 Overlay Data Model (Future)

```typescript
interface OverlayDocument {
  version: number;
  protocolId: string;
  usdmRevision: string;
  status: "draft" | "published";
  updatedAt: string;
  updatedBy: string;
  basePublishedId?: string;
  payload: OverlayPayload;
}

interface OverlayPayload {
  diagram: DiagramOverlay;
  table: TableOverlay;
}

interface DiagramOverlay {
  nodes: Record<string, NodePosition>;
  edges?: Record<string, EdgeStyle>;
  globals?: {
    snapGrid?: number;
    zoom?: number;
    pan?: { x: number; y: number };
  };
}

interface NodePosition {
  x: number;
  y: number;
  locked?: boolean;
  highlight?: boolean;
  icon?: string;
}

interface EdgeStyle {
  style?: string;
  color?: string;
  width?: number;
}

interface TableOverlay {
  rowOrder?: string[];          // Activity IDs
  columnOrder?: string[];       // Encounter IDs
  rowGroups?: RowGroup[];
  columnGroups?: ColumnGroup[];
  hiddenColumns?: string[];
}

interface RowGroup {
  label: string;
  activityIds: string[];
}

interface ColumnGroup {
  label: string;
  visitIds: string[];
}
```

### 2.4 View Models (Adapter Output)

```typescript
// SoA Table View Model
interface SoATableModel {
  rows: SoARow[];
  columns: SoAColumn[];
  cells: SoACell[][];
  epochs: EpochGroup[];
}

interface SoARow {
  id: string;
  activityId: string;
  activityName: string;
  category?: string;
  order: number;
}

interface SoAColumn {
  id: string;
  encounterId: string;
  encounterName: string;
  day?: number;
  week?: number;
  epochId?: string;
  order: number;
}

interface SoACell {
  rowId: string;
  columnId: string;
  hasTick: boolean;
  tickSymbol?: string;          // "X", "Xa", "Xb"
  provenance?: ProvenanceSource;
  confidence?: number;
  footnotes?: string[];
}

interface EpochGroup {
  epochId: string;
  epochName: string;
  columnIds: string[];
}

// Timeline Graph View Model
interface TimelineGraphModel {
  nodes: GraphNode[];
  edges: GraphEdge[];
  layout?: LayoutPreset;
}

interface GraphNode {
  id: string;
  label: string;
  type: NodeType;
  data: any;                    // Original USDM entity
  position?: { x: number; y: number };
  locked?: boolean;
}

type NodeType = "epoch" | "encounter" | "activity" | "timing" | "condition";

interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: EdgeType;
  label?: string;
}

type EdgeType = "scheduled" | "timing" | "conditional" | "traversal";

interface LayoutPreset {
  name: string;
  positions: Record<string, { x: number; y: number }>;
}
```

---

## 3. API Specifications

### 3.1 Protocol List API

```typescript
// GET /api/protocols
// Returns list of all protocols

interface ProtocolListResponse {
  protocols: ProtocolSummary[];
  total: number;
}

interface ProtocolSummary {
  id: string;
  title: string;
  protocolId: string;
  nctNumber?: string;
  extractionDate: string;
  status: "complete" | "partial" | "failed";
  hasProvenance: boolean;
  hasExecutionModel: boolean;
  hasSAP: boolean;
  hasSites: boolean;
}

// Implementation
export async function GET() {
  const outputDir = process.env.PROTOCOL_OUTPUT_DIR || './output';
  const protocols = await scanProtocolDirectory(outputDir);
  
  return NextResponse.json({
    protocols,
    total: protocols.length
  });
}
```

### 3.2 USDM API

```typescript
// GET /api/protocols/[id]/usdm
// Returns USDM JSON + Provenance + intermediate files metadata

interface USDMResponse {
  usdm: USDMDocument;
  provenance?: ProvenanceDocument;
  intermediateFiles: IntermediateFileMetadata;
  metadata: {
    extractionDate: string;
    pipelineVersion: string;
    model: string;
  };
}

interface IntermediateFileMetadata {
  executionModel?: {
    path: string;
    size: number;
    data?: any;
  };
  sapPopulations?: {
    path: string;
    size: number;
    data?: any;
  };
  siteList?: {
    path: string;
    size: number;
    data?: any;
  };
  soaImages?: {
    path: string;
    count: number;
  };
}

// Implementation
export async function GET(
  request: Request,
  { params }: { params: { id: string } }
) {
  const protocolDir = path.join(
    process.env.PROTOCOL_OUTPUT_DIR || './output',
    params.id
  );
  
  // Load USDM
  const usdmPath = path.join(protocolDir, 'protocol_usdm.json');
  const usdm = JSON.parse(await fs.readFile(usdmPath, 'utf-8'));
  
  // Load provenance (if exists)
  const provenancePath = path.join(protocolDir, 'provenance.json');
  let provenance = null;
  if (await fs.exists(provenancePath)) {
    provenance = JSON.parse(await fs.readFile(provenancePath, 'utf-8'));
  }
  
  // Scan intermediate files
  const intermediateFiles = await scanIntermediateFiles(protocolDir);
  
  return NextResponse.json({
    usdm,
    Provenance,
    intermediateFiles,
    metadata: {
      extractionDate: usdm.metadata?.extractionDate || '',
      pipelineVersion: usdm.systemVersion || '',
      model: usdm.metadata?.model || ''
    }
  });
}
```

### 3.3 Intermediate Files API

```typescript
// GET /api/protocols/[id]/intermediate?file=<filename>
// Returns specific intermediate file content

interface IntermediateFileResponse {
  filename: string;
  content: any;
  contentType: string;
}

// Implementation
export async function GET(
  request: Request,
  { params }: { params: { id: string } }
) {
  const { searchParams } = new URL(request.url);
  const filename = searchParams.get('file');
  
  if (!filename) {
    return NextResponse.json({ error: 'Missing file parameter' }, { status: 400 });
  }
  
  const protocolDir = path.join(
    process.env.PROTOCOL_OUTPUT_DIR || './output',
    params.id
  );
  
  const filePath = path.join(protocolDir, filename);
  
  // Security: ensure file is within protocol directory
  if (!filePath.startsWith(protocolDir)) {
    return NextResponse.json({ error: 'Invalid file path' }, { status: 403 });
  }
  
  const content = await fs.readFile(filePath, 'utf-8');
  const parsed = JSON.parse(content);
  
  return NextResponse.json({
    filename,
    content: parsed,
    contentType: 'application/json'
  });
}
```

### 3.4 Overlay API

```typescript
// GET /api/protocols/[id]/overlay/published
// Returns published overlay

interface OverlayResponse {
  overlay: OverlayDocument | null;
}

// PUT /api/protocols/[id]/overlay/draft
// Save draft overlay

interface SaveDraftRequest {
  overlay: OverlayDocument;
}

interface SaveDraftResponse {
  success: boolean;
  draftId: string;
}

// POST /api/protocols/[id]/overlay/publish
// Promote draft to published

interface PublishRequest {
  draftId: string;
}

interface PublishResponse {
  success: boolean;
  publishedId: string;
}
```

---

## 4. Data Adapters

### 4.1 SoA Table Adapter

```typescript
/**
 * Convert USDM + Provenance + overlay to SoA table view model
 */
export function toSoATableModel(
  usdm: USDMDocument,
  provenance?: ProvenanceDocument,
  overlay?: OverlayDocument
): SoATableModel {
  const study = usdm.study;
  
  // Extract activities (rows)
  const activities = study.activities || [];
  const rows: SoARow[] = activities.map((activity, index) => ({
    id: `row_${activity.id}`,
    activityId: activity.id,
    activityName: activity.name,
    category: extractActivityCategory(activity),
    order: overlay?.payload.table.rowOrder?.indexOf(activity.id) ?? index
  }));
  
  // Extract encounters (columns)
  const encounters = study.encounters || [];
  const columns: SoAColumn[] = encounters.map((encounter, index) => ({
    id: `col_${encounter.id}`,
    encounterId: encounter.id,
    encounterName: encounter.name,
    day: extractDay(encounter),
    week: extractWeek(encounter),
    epochId: encounter.epochId,
    order: overlay?.payload.table.columnOrder?.indexOf(encounter.id) ?? index
  }));
  
  // Extract scheduled instances (cells)
  const instances = study.scheduledActivityInstances || [];
  const cells: SoACell[][] = rows.map(row => 
    columns.map(col => {
      const instance = instances.find(inst =>
        inst.activityIds.includes(row.activityId) &&
        inst.encounterId === col.encounterId
      );
      
      if (!instance) {
        return {
          rowId: row.id,
          columnId: col.id,
          hasTick: false
        };
      }
      
      // Get Provenance for this cell
      const cellProvenance = getProvenanceForCell(
        Provenance,
        row.activityId,
        col.encounterId
      );
      
      return {
        rowId: row.id,
        columnId: col.id,
        hasTick: true,
        tickSymbol: extractTickSymbol(instance),
        provenance: cellProvenance?.source,
        confidence: cellProvenance?.confidence,
        footnotes: extractFootnotes(instance)
      };
    })
  );
  
  // Extract epoch groups
  const epochs = study.epochs || [];
  const epochGroups: EpochGroup[] = epochs.map(epoch => ({
    epochId: epoch.id,
    epochName: epoch.name,
    columnIds: columns
      .filter(col => col.epochId === epoch.id)
      .map(col => col.id)
  }));
  
  return {
    rows: rows.sort((a, b) => a.order - b.order),
    columns: columns.sort((a, b) => a.order - b.order),
    cells,
    epochs: epochGroups
  };
}

function getProvenanceForCell(
  provenance: ProvenanceDocument | undefined,
  activityId: string,
  encounterId: string
): ProvenanceEntry | undefined {
  if (!provenance) return undefined;
  
  // Look for provenance entry for this activity-encounter pair
  const cellId = `${activityId}_${encounterId}`;
  return provenance.entries.find(entry =>
    entry.entityId === cellId &&
    entry.entityType === "ScheduledActivityInstance"
  );
}
```

### 4.2 Timeline Graph Adapter


```typescript
/**
 * Convert USDM + overlay to timeline graph view model
 */
export function toTimelineGraphModel(
  usdm: USDMDocument,
  overlay?: OverlayDocument
): TimelineGraphModel {
  const study = usdm.study;
  const nodes: GraphNode[] = [];
  const edges: GraphEdge[] = [];
  
  // Add epoch nodes
  const epochs = study.epochs || [];
  epochs.forEach(epoch => {
    nodes.push({
      id: epoch.id,
      label: epoch.name,
      type: "epoch",
      data: epoch,
      position: overlay?.payload.diagram.nodes[epoch.id],
      locked: overlay?.payload.diagram.nodes[epoch.id]?.locked
    });
    
    // Add traversal edges (previousId/nextId)
    if (epoch.nextId) {
      edges.push({
        id: `${epoch.id}_${epoch.nextId}`,
        source: epoch.id,
        target: epoch.nextId,
        type: "traversal",
        label: "next"
      });
    }
  });
  
  // Add encounter nodes
  const encounters = study.encounters || [];
  encounters.forEach(encounter => {
    nodes.push({
      id: encounter.id,
      label: encounter.name,
      type: "encounter",
      data: encounter,
      position: overlay?.payload.diagram.nodes[encounter.id],
      locked: overlay?.payload.diagram.nodes[encounter.id]?.locked
    });
    
    // Add epoch-encounter edges
    if (encounter.epochId) {
      edges.push({
        id: `${encounter.epochId}_${encounter.id}`,
        source: encounter.epochId,
        target: encounter.id,
        type: "scheduled"
      });
    }
    
    // Add traversal edges
    if (encounter.nextId) {
      edges.push({
        id: `${encounter.id}_${encounter.nextId}`,
        source: encounter.id,
        target: encounter.nextId,
        type: "traversal",
        label: "next"
      });
    }
  });
  
  // Add activity nodes (from scheduled instances)
  const instances = study.scheduledActivityInstances || [];
  const activities = study.activities || [];
  
  instances.forEach(instance => {
    instance.activityIds.forEach(activityId => {
      const activity = activities.find(a => a.id === activityId);
      if (!activity) return;
      
      // Add activity node (if not already added)
      if (!nodes.find(n => n.id === activityId)) {
        nodes.push({
          id: activityId,
          label: activity.name,
          type: "activity",
          data: activity,
          position: overlay?.payload.diagram.nodes[activityId],
          locked: overlay?.payload.diagram.nodes[activityId]?.locked
        });
      }
      
      // Add encounter-activity edge
      edges.push({
        id: `${instance.encounterId}_${activityId}`,
        source: instance.encounterId,
        target: activityId,
        type: "scheduled"
      });
    });
  });
  
  return {
    nodes,
    edges,
    layout: overlay?.payload.diagram.globals ? {
      name: "preset",
      positions: Object.fromEntries(
        Object.entries(overlay.payload.diagram.nodes).map(([id, pos]) => [
          id,
          { x: pos.x, y: pos.y }
        ])
      )
    } : undefined
  };
}
```

### 4.3 Provenance Statistics Adapter

```typescript
/**
 * Calculate Provenance statistics
 */
export function toProvenanceStats(
  provenance: ProvenanceDocument
): ProvenanceStats {
  const entries = provenance.entries;
  const total = entries.length;
  
  const confirmed = entries.filter(e => e.source === "both").length;
  const textOnly = entries.filter(e => e.source === "text").length;
  const visionOnly = entries.filter(e => e.source === "vision").length;
  const orphaned = entries.filter(e => e.source === "orphaned").length;
  
  return {
    totalEntities: total,
    confirmed,
    textOnly,
    visionOnly,
    orphaned,
    confirmedPercentage: total > 0 ? (confirmed / total) * 100 : 0,
    textOnlyPercentage: total > 0 ? (textOnly / total) * 100 : 0,
    visionOnlyPercentage: total > 0 ? (visionOnly / total) * 100 : 0,
    orphanedPercentage: total > 0 ? (orphaned / total) * 100 : 0
  };
}
```

### 4.4 Quality Metrics Adapter

```typescript
/**
 * Calculate quality metrics from USDM
 */
export function toQualityMetrics(
  usdm: USDMDocument,
  provenance?: ProvenanceDocument
): QualityMetrics {
  const study = usdm.study;
  
  // Entity counts
  const entityCounts = {
    activities: study.activities?.length || 0,
    encounters: study.encounters?.length || 0,
    epochs: study.epochs?.length || 0,
    objectives: study.objectives?.length || 0,
    endpoints: study.endpoints?.length || 0,
    interventions: study.studyInterventions?.length || 0,
    eligibilityCriteria: study.eligibilityCriteria?.length || 0,
    organizations: study.organizations?.length || 0
  };
  
  // Provenance stats
  const ProvenanceStats = Provenance ? toProvenanceStats(Provenance) : null;
  
  // Validation results (if available)
  const validationResults = extractValidationResults(usdm);
  
  // Calculate quality score (0-100)
  const qualityScore = calculateQualityScore(
    entityCounts,
    ProvenanceStats,
    validationResults
  );
  
  return {
    entityCounts,
    ProvenanceStats,
    validationResults,
    qualityScore
  };
}

function calculateQualityScore(
  entityCounts: any,
  ProvenanceStats: ProvenanceStats | null,
  validationResults: any
): number {
  let score = 100;
  
  // Deduct for missing entities
  if (entityCounts.activities === 0) score -= 20;
  if (entityCounts.encounters === 0) score -= 20;
  if (entityCounts.epochs === 0) score -= 10;
  
  // Deduct for low Provenance confirmation
  if (ProvenanceStats) {
    if (ProvenanceStats.confirmedPercentage < 80) {
      score -= (80 - ProvenanceStats.confirmedPercentage) * 0.5;
    }
    if (ProvenanceStats.orphanedPercentage > 5) {
      score -= (ProvenanceStats.orphanedPercentage - 5) * 2;
    }
  }
  
  // Deduct for validation errors
  if (validationResults?.errors > 0) {
    score -= validationResults.errors * 5;
  }
  
  return Math.max(0, Math.min(100, score));
}
```

---

## 5. Component Specifications

### 5.1 SoA Grid Component (AG Grid)

```typescript
// components/soa/SoAGrid.tsx

import { AgGridReact } from 'ag-grid-react';
import { ProvenanceCellRenderer } from './ProvenanceCellRenderer';

interface SoAGridProps {
  model: SoATableModel;
  onCellClick?: (cell: SoACell) => void;
  onExport?: () => void;
}

export function SoAGrid({ model, onCellClick, onExport }: SoAGridProps) {
  // Build column definitions
  const columnDefs = [
    {
      headerName: 'Activity',
      field: 'activityName',
      pinned: 'left',
      width: 200,
      cellClass: 'activity-cell'
    },
    ...model.columns.map(col => ({
      headerName: col.encounterName,
      field: col.id,
      width: 100,
      cellRenderer: ProvenanceCellRenderer,
      cellRendererParams: {
        onClick: onCellClick
      }
    }))
  ];
  
  // Build row data
  const rowData = model.rows.map((row, rowIndex) => {
    const rowObj: any = {
      activityName: row.activityName,
      category: row.category
    };
    
    model.columns.forEach((col, colIndex) => {
      const cell = model.cells[rowIndex][colIndex];
      rowObj[col.id] = cell;
    });
    
    return rowObj;
  });
  
  // Column grouping for epochs
  const columnGroupDefs = model.epochs.map(epoch => ({
    headerName: epoch.epochName,
    children: epoch.columnIds.map(colId => 
      columnDefs.find(def => def.field === colId)
    ).filter(Boolean)
  }));
  
  return (
    <div className="ag-theme-alpine" style={{ height: '600px', width: '100%' }}>
      <AgGridReact
        columnDefs={columnDefs}
        rowData={rowData}
        columnGroupDefs={columnGroupDefs}
        defaultColDef={{
          sortable: true,
          filter: true,
          resizable: true
        }}
        enableRangeSelection={true}
        suppressMovableColumns={false}
        onGridReady={(params) => {
          params.api.sizeColumnsToFit();
        }}
      />
    </div>
  );
}
```

### 5.2 Provenance Cell Renderer

```typescript
// components/soa/ProvenanceCellRenderer.tsx

import { ICellRendererParams } from 'ag-grid-community';

export function ProvenanceCellRenderer(params: ICellRendererParams) {
  const cell: SoACell = params.value;
  
  if (!cell || !cell.hasTick) {
    return null;
  }
  
  // Determine color based on Provenance
  const getProvenanceColor = (source?: ProvenanceSource) => {
    switch (source) {
      case 'both': return 'bg-green-100 text-green-800';
      case 'text': return 'bg-blue-100 text-blue-800';
      case 'vision': return 'bg-orange-100 text-orange-800';
      case 'orphaned': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };
  
  const colorClass = getProvenanceColor(cell.Provenance);
  
  return (
    <div
      className={`flex items-center justify-center h-full ${colorClass} cursor-pointer`}
      onClick={() => params.onClick?.(cell)}
      title={`Source: ${cell.Provenance || 'unknown'}\nConfidence: ${cell.confidence?.toFixed(2) || 'N/A'}`}
    >
      <span className="font-semibold">{cell.tickSymbol || 'X'}</span>
      {cell.footnotes && cell.footnotes.length > 0 && (
        <sup className="ml-1 text-xs">{cell.footnotes.join(',')}</sup>
      )}
    </div>
  );
}
```

### 5.3 Timeline Canvas Component (Cytoscape)

```typescript
// components/timeline/TimelineCanvas.tsx

import { useEffect, useRef } from 'react';
import cytoscape, { Core } from 'cytoscape';

interface TimelineCanvasProps {
  model: TimelineGraphModel;
  onNodeClick?: (node: GraphNode) => void;
  onNodeDrag?: (nodeId: string, position: { x: number; y: number }) => void;
}

export function TimelineCanvas({ model, onNodeClick, onNodeDrag }: TimelineCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  
  useEffect(() => {
    if (!containerRef.current) return;
    
    // Initialize Cytoscape
    const cy = cytoscape({
      container: containerRef.current,
      elements: [
        // Nodes
        ...model.nodes.map(node => ({
          data: {
            id: node.id,
            label: node.label,
            type: node.type,
            ...node.data
          },
          position: node.position || { x: 0, y: 0 },
          locked: node.locked || false
        })),
        // Edges
        ...model.edges.map(edge => ({
          data: {
            id: edge.id,
            source: edge.source,
            target: edge.target,
            type: edge.type,
            label: edge.label
          }
        }))
      ],
      style: [
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'text-valign': 'center',
            'text-halign': 'center',
            'background-color': '#4299e1',
            'color': '#fff',
            'font-size': '12px',
            'width': '80px',
            'height': '40px',
            'shape': 'roundrectangle'
          }
        },
        {
          selector: 'node[type="epoch"]',
          style: {
            'background-color': '#805ad5',
            'shape': 'rectangle'
          }
        },
        {
          selector: 'node[type="encounter"]',
          style: {
            'background-color': '#4299e1'
          }
        },
        {
          selector: 'node[type="activity"]',
          style: {
            'background-color': '#48bb78',
            'shape': 'ellipse'
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 2,
            'line-color': '#cbd5e0',
            'target-arrow-color': '#cbd5e0',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'label': 'data(label)',
            'font-size': '10px'
          }
        },
        {
          selector: 'edge[type="traversal"]',
          style: {
            'line-style': 'dashed',
            'line-color': '#f56565'
          }
        }
      ],
      layout: model.layout ? {
        name: 'preset',
        positions: model.layout.positions
      } : {
        name: 'breadthfirst',
        directed: true,
        spacingFactor: 1.5
      }
    });
    
    // Event handlers
    cy.on('tap', 'node', (evt) => {
      const node = evt.target;
      const nodeData = model.nodes.find(n => n.id === node.id());
      if (nodeData && onNodeClick) {
        onNodeClick(nodeData);
      }
    });
    
    cy.on('dragfree', 'node', (evt) => {
      const node = evt.target;
      const position = node.position();
      if (onNodeDrag) {
        onNodeDrag(node.id(), position);
      }
    });
    
    cyRef.current = cy;
    
    return () => {
      cy.destroy();
    };
  }, [model]);
  
  return (
    <div
      ref={containerRef}
      className="w-full h-full border border-gray-300 rounded"
      style={{ minHeight: '600px' }}
    />
  );
}
```

### 5.4 Provenance Explorer Component

```typescript
// components/Provenance/ProvenanceExplorer.tsx

import { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';

interface ProvenanceExplorerProps {
  provenance: ProvenanceDocument;
}

export function ProvenanceExplorer({ Provenance }: ProvenanceExplorerProps) {
  const [filter, setFilter] = useState<ProvenanceSource | 'all'>('all');
  const [sortBy, setSortBy] = useState<'confidence' | 'entityType'>('confidence');
  
  // Filter entries
  const filteredEntries = provenance.entries.filter(entry =>
    filter === 'all' || entry.source === filter
  );
  
  // Sort entries
  const sortedEntries = [...filteredEntries].sort((a, b) => {
    if (sortBy === 'confidence') {
      return (b.confidence || 0) - (a.confidence || 0);
    } else {
      return a.entityType.localeCompare(b.entityType);
    }
  });
  
  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex gap-2">
        <button
          onClick={() => setFilter('all')}
          className={`px-3 py-1 rounded ${filter === 'all' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
        >
          All
        </button>
        <button
          onClick={() => setFilter('both')}
          className={`px-3 py-1 rounded ${filter === 'both' ? 'bg-green-500 text-white' : 'bg-gray-200'}`}
        >
          Confirmed
        </button>
        <button
          onClick={() => setFilter('text')}
          className={`px-3 py-1 rounded ${filter === 'text' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
        >
          Text Only
        </button>
        <button
          onClick={() => setFilter('vision')}
          className={`px-3 py-1 rounded ${filter === 'vision' ? 'bg-orange-500 text-white' : 'bg-gray-200'}`}
        >
          Vision Only
        </button>
        <button
          onClick={() => setFilter('orphaned')}
          className={`px-3 py-1 rounded ${filter === 'orphaned' ? 'bg-red-500 text-white' : 'bg-gray-200'}`}
        >
          Orphaned
        </button>
      </div>
      
      {/* Sort */}
      <div className="flex gap-2">
        <label>Sort by:</label>
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as any)}
          className="px-2 py-1 border rounded"
        >
          <option value="confidence">Confidence</option>
          <option value="entityType">Entity Type</option>
        </select>
      </div>
      
      {/* Entry list */}
      <div className="space-y-2">
        {sortedEntries.map((entry, index) => (
          <Card key={index} className="p-4">
            <div className="flex justify-between items-start">
              <div>
                <div className="font-semibold">{entry.entityType}</div>
                <div className="text-sm text-gray-600">ID: {entry.entityId}</div>
                <div className="text-sm text-gray-600">Field: {entry.fieldName}</div>
              </div>
              <div className="text-right">
                <Badge variant={getProvenanceBadgeVariant(entry.source)}>
                  {entry.source}
                </Badge>
                <div className="text-sm mt-1">
                  Confidence: {(entry.confidence * 100).toFixed(0)}%
                </div>
                {entry.pageNumber && (
                  <div className="text-sm text-gray-600">
                    Page: {entry.pageNumber}
                  </div>
                )}
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

function getProvenanceBadgeVariant(source: ProvenanceSource) {
  switch (source) {
    case 'both': return 'success';
    case 'text': return 'info';
    case 'vision': return 'warning';
    case 'orphaned': return 'destructive';
    default: return 'secondary';
  }
}
```

---

## 6. State Management

### 6.1 Zustand Store

```typescript
// stores/protocol-store.ts

import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';

interface ProtocolState {
  // Current protocol
  currentProtocol: ProtocolSummary | null;
  usdm: USDMDocument | null;
  provenance: ProvenanceDocument | null;
  intermediateFiles: IntermediateFileMetadata | null;
  
  // UI state
  activeTab: string;
  selectedCell: SoACell | null;
  selectedNode: GraphNode | null;
  
  // Actions
  setCurrentProtocol: (protocol: ProtocolSummary) => void;
  setUSDM: (usdm: USDMDocument) => void;
  setProvenance: (provenance: ProvenanceDocument) => void;
  setIntermediateFiles: (files: IntermediateFileMetadata) => void;
  setActiveTab: (tab: string) => void;
  setSelectedCell: (cell: SoACell | null) => void;
  setSelectedNode: (node: GraphNode | null) => void;
  reset: () => void;
}

export const useProtocolStore = create<ProtocolState>()(
  immer((set) => ({
    // Initial state
    currentProtocol: null,
    usdm: null,
    provenance: null,
    intermediateFiles: null,
    activeTab: 'overview',
    selectedCell: null,
    selectedNode: null,
    
    // Actions
    setCurrentProtocol: (protocol) => set({ currentProtocol: protocol }),
    setUSDM: (usdm) => set({ usdm }),
    setProvenance: (provenance) => set({ provenance }),
    setIntermediateFiles: (files) => set({ intermediateFiles: files }),
    setActiveTab: (tab) => set({ activeTab: tab }),
    setSelectedCell: (cell) => set({ selectedCell: cell }),
    setSelectedNode: (node) => set({ selectedNode: node }),
    reset: () => set({
      currentProtocol: null,
      usdm: null,
      provenance: null,
      intermediateFiles: null,
      activeTab: 'overview',
      selectedCell: null,
      selectedNode: null
    })
  }))
);
```

### 6.2 React Query Integration

```typescript
// lib/api/protocols.ts

import { useQuery, useMutation } from '@tanstack/react-query';

export function useProtocols() {
  return useQuery({
    queryKey: ['protocols'],
    queryFn: async () => {
      const response = await fetch('/api/protocols');
      if (!response.ok) throw new Error('Failed to fetch protocols');
      return response.json() as Promise<ProtocolListResponse>;
    }
  });
}

export function useProtocolUSDM(protocolId: string) {
  return useQuery({
    queryKey: ['protocol', protocolId, 'usdm'],
    queryFn: async () => {
      const response = await fetch(`/api/protocols/${protocolId}/usdm`);
      if (!response.ok) throw new Error('Failed to fetch USDM');
      return response.json() as Promise<USDMResponse>;
    },
    enabled: !!protocolId
  });
}

export function useIntermediateFile(protocolId: string, filename: string) {
  return useQuery({
    queryKey: ['protocol', protocolId, 'intermediate', filename],
    queryFn: async () => {
      const response = await fetch(
        `/api/protocols/${protocolId}/intermediate?file=${filename}`
      );
      if (!response.ok) throw new Error('Failed to fetch file');
      return response.json() as Promise<IntermediateFileResponse>;
    },
    enabled: !!protocolId && !!filename
  });
}
```

---

## 7. Deployment

### 7.1 Development Setup

```bash
# Install dependencies
cd web-ui
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local with PROTOCOL_OUTPUT_DIR

# Start development server
npm run dev

# Open http://localhost:3000
```

### 7.2 Production Build

```bash
# Build for production
npm run build

# Start production server
npm run start
```

### 7.3 Docker Deployment

**Dockerfile:**
```dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

COPY --from=builder /app/next.config.mjs ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

EXPOSE 3000

CMD ["npm", "start"]
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

```typescript
// __tests__/adapters/soa-adapter.test.ts

import { toSoATableModel } from '@/lib/adapters/soa-adapter';

describe('SoA Adapter', () => {
  it('should convert USDM to SoA table model', () => {
    const usdm = createMockUSDM();
    const model = toSoATableModel(usdm);
    
    expect(model.rows).toHaveLength(10);
    expect(model.columns).toHaveLength(5);
    expect(model.cells).toHaveLength(10);
    expect(model.cells[0]).toHaveLength(5);
  });
  
  it('should apply provenance colors', () => {
    const usdm = createMockUSDM();
    const provenance = createMockProvenance();
    const model = toSoATableModel(usdm, provenance);
    
    const cell = model.cells[0][0];
    expect(cell.Provenance).toBe('both');
    expect(cell.confidence).toBeGreaterThan(0.8);
  });
});
```

### 8.2 Integration Tests

```typescript
// __tests__/api/protocols.test.ts

import { GET } from '@/app/api/protocols/route';

describe('Protocol API', () => {
  it('should return protocol list', async () => {
    const response = await GET();
    const data = await response.json();
    
    expect(data.protocols).toBeInstanceOf(Array);
    expect(data.total).toBeGreaterThan(0);
  });
});
```

### 8.3 Component Tests

```typescript
// __tests__/components/SoAGrid.test.tsx

import { render, screen } from '@testing-library/react';
import { SoAGrid } from '@/components/soa/SoAGrid';

describe('SoAGrid', () => {
  it('should render table with activities and visits', () => {
    const model = createMockSoATableModel();
    render(<SoAGrid model={model} />);
    
    expect(screen.getByText('Physical Exam')).toBeInTheDocument();
    expect(screen.getByText('Screening Visit')).toBeInTheDocument();
  });
});
```

---

## 9. Performance Optimization

### 9.1 Code Splitting

```typescript
// Use dynamic imports for large components
import dynamic from 'next/dynamic';

const TimelineCanvas = dynamic(
  () => import('@/components/timeline/TimelineCanvas'),
  { ssr: false, loading: () => <div>Loading timeline...</div> }
);

const SoAGrid = dynamic(
  () => import('@/components/soa/SoAGrid'),
  { ssr: false, loading: () => <div>Loading table...</div> }
);
```

### 9.2 Data Caching

```typescript
// Use React Query caching
export function useProtocolUSDM(protocolId: string) {
  return useQuery({
    queryKey: ['protocol', protocolId, 'usdm'],
    queryFn: fetchUSDM,
    staleTime: 5 * 60 * 1000,  // 5 minutes
    cacheTime: 30 * 60 * 1000  // 30 minutes
  });
}
```

### 9.3 Virtualization

```typescript
// Use AG Grid virtualization for large tables
<AgGridReact
  rowBuffer={10}
  rowModelType="clientSide"
  cacheBlockSize={100}
  maxBlocksInCache={10}
/>
```

---

## 10. Appendices

### 10.1 Environment Variables

```bash
# .env.local

# Path to Protocol2USDM output directory
PROTOCOL_OUTPUT_DIR=/path/to/output

# Optional: AG Grid license key
AG_GRID_LICENSE_KEY=your-license-key

# Optional: Node environment
NODE_ENV=development
```

### 10.2 Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

### 10.3 Dependencies

See `package.json` for complete dependency list.

---

**Document Control:**
- Version: 1.0
- Last Updated: February 27, 2026
- Next Review: March 27, 2026
- Owner: Protocol2USDM Team

