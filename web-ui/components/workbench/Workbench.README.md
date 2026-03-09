# Workbench Component

## Overview

The `Workbench` component is the top-level application shell for the Protocol2USDM web UI redesign. It orchestrates the IDE/Workbench-style multi-panel interface, managing layout state, keyboard shortcuts, responsive behavior, and communication between child components.

## Architecture

The Workbench renders a full-viewport flex layout with the following structure:

```
┌──────┬────────────┬──────────────────────────┬──────────────┐
│      │            │                          │              │
│  AB  │  Sidebar   │      Center Panel        │  Right Panel │
│      │  (260px)   │      (flex: 1)           │  (320px)     │
│ 48px │  min:200   │      min: 400px          │  min:240     │
│      │  max:480   │                          │  max:600     │
│      │            │                          │              │
├──────┴────────────┴──────────────────────────┴──────────────┤
│                        Status Bar (32px)                     │
└──────────────────────────────────────────────────────────────┘
```

## Props

```typescript
interface WorkbenchProps {
  protocolId: string;
  usdm: Record<string, unknown>;
  provenance: ProvenanceData | null;
  intermediateFiles: Record<string, unknown> | null;
}
```

- `protocolId`: Unique identifier for the protocol
- `usdm`: USDM data object containing protocol information
- `provenance`: Provenance tracking data for extraction sources
- `intermediateFiles`: Intermediate files from the extraction pipeline

## Features

### 1. Layout Management

The Workbench reads layout state from `layoutStore` (Zustand) and manages:
- Panel sizes (sidebar width, right panel width)
- Collapsed states (sidebar collapsed, right panel collapsed)
- Open tabs and active tab in the center panel
- Activity bar mode (explorer, search, quality)
- Nav tree expanded groups
- Right panel active tab

All layout state is automatically persisted to localStorage via Zustand's persist middleware.

### 2. Panel Resizing

Users can resize panels by dragging the `PanelSplitter` components:
- **Left Splitter**: Resizes sidebar (200-480px) and center panel
- **Right Splitter**: Resizes right panel (240-600px) and center panel
- **Double-click**: Toggles adjacent panel collapse/expand
- **Keyboard**: Arrow keys adjust width by 10px increments

Constraints:
- Sidebar: min 200px, max 480px
- Right Panel: min 240px, max 600px
- Center Panel: min 400px (enforced by resize handlers)

### 3. Keyboard Shortcuts

The Workbench registers global keyboard shortcuts via `useKeyboardShortcuts`:

| Shortcut | Action |
|----------|--------|
| Ctrl/Cmd+S | Save Draft |
| Ctrl/Cmd+B | Toggle Sidebar |
| Ctrl/Cmd+J | Toggle Right Panel |
| Ctrl/Cmd+K | Open Command Palette |
| Ctrl/Cmd+W | Close Active Tab |
| Ctrl/Cmd+1-9 | Switch to tab at ordinal position |

Shortcuts are automatically skipped when focus is in text inputs, textareas, or AG Grid cell editors.

### 4. Responsive Behavior

The Workbench uses `useResponsiveLayout` to automatically adapt to viewport changes:
- **Viewport < 1024px**: Auto-collapse sidebar and right panel
- **Viewport >= 1024px**: Restore panels to persisted states

This ensures optimal space utilization on mobile and tablet devices.

### 5. Command Palette

The Command Palette (Ctrl/Cmd+K) provides quick access to:
- **Navigation commands**: All 20 views from the view registry
- **Action commands**: Save Draft, Publish, Reset, Toggle Panels, Export (CSV, JSON, PDF)

The palette uses fuzzy search to filter commands and supports keyboard navigation (Arrow Up/Down, Enter, Escape).

### 6. Selection State Management

The Workbench manages ephemeral selection state (not persisted):
- `selectedCellId`: Currently selected cell in the SoA table
- `selectedNodeId`: Currently selected node in the Timeline graph

Selection state is passed to the Right Panel to display contextual details (provenance, properties, footnotes).

### 7. ARIA Landmarks

The Workbench applies appropriate ARIA landmark roles for accessibility:
- **Sidebar**: `<nav>` (navigation)
- **Center Panel**: `<main>` (main content)
- **Right Panel**: `<aside>` (complementary)
- **Status Bar**: `<footer>` (contentinfo)

## Child Components

The Workbench orchestrates the following child components:

1. **ActivityBar**: 48px vertical icon strip for switching sidebar modes
2. **Sidebar**: Collapsible left panel with NavTree, SearchPanel, or QualityPanel
3. **PanelSplitter**: 4px draggable divider for resizing panels
4. **CenterPanel**: Main content area with tabbed views
5. **RightPanel**: Collapsible right panel with contextual details
6. **StatusBar**: 32px fixed bar at bottom with protocol metadata and actions
7. **CommandPalette**: Overlay for quick navigation and actions (rendered via portal)

## Data Flow

```
Workbench (layout orchestration)
    ↓
    ├─→ ActivityBar (mode selection)
    ├─→ Sidebar (navigation)
    │     └─→ NavTree (view selection) → handleNavigate() → openTab()
    ├─→ CenterPanel (view rendering)
    │     ├─→ PanelTabBar (tab management)
    │     └─→ ActiveView (usdm, provenance props)
    │           ├─→ onCellSelect() → setSelectedCellId()
    │           └─→ onNodeSelect() → setSelectedNodeId()
    ├─→ RightPanel (contextual details)
    │     └─→ ProvenancePanel / PropertiesPanel / FootnotesPanel
    │           (reads selectedCellId, selectedNodeId)
    ├─→ StatusBar (metadata, actions)
    └─→ CommandPalette (quick actions)
          └─→ handleCommandExecute() → handleNavigate() / toggleSidebar() / etc.
```

## Integration Points

### Draft/Publish Workflow

The Workbench provides handlers for draft/publish actions:
- `handleSaveDraft()`: TODO - Wire to `overlayStore.saveDraft()`
- `handlePublish()`: TODO - Wire to `overlayStore.publish()` with confirmation dialog
- `handleResetToPublished()`: TODO - Wire to `overlayStore.reset()` with confirmation dialog

Status Bar displays:
- `isDirty`: TODO - Wire to `overlayStore.isDirty`
- `overlayStatus`: TODO - Wire to `overlayStore.status`

### Export Functionality

The Workbench provides handlers for export actions:
- `handleExportCSV()`: TODO - Wire to `exportToCSV()`
- `handleExportJSON()`: TODO - Wire to `exportToJSON()`
- `handleExportPDF()`: TODO - Wire to `exportToPDF()`

### Validation Results

Status Bar displays validation issue count:
- `validationIssueCount`: TODO - Wire to validation results from quality store

## Requirements Validation

This component validates the following requirements from the Web UI Redesign specification:

- **Requirement 1.1**: Three-region layout (Sidebar, Center Panel, Right Panel)
- **Requirement 1.2**: Status Bar at bottom
- **Requirement 1.3**: Activity Bar on far-left edge
- **Requirement 1.4**: Restore panel sizes and collapsed states from Layout Store
- **Requirement 1.6**: Full viewport with no outer scrollbars
- **Requirement 2.7**: Persist panel sizes to localStorage on resize
- **Requirement 18.1**: ARIA landmarks (nav, main, aside, footer)

## Usage

```tsx
import { Workbench } from '@/components/workbench/Workbench';

function ProtocolDetailPage({ protocolId }: { protocolId: string }) {
  // Fetch protocol data
  const { usdm, provenance, intermediateFiles } = useProtocolData(protocolId);

  return (
    <Workbench
      protocolId={protocolId}
      usdm={usdm}
      provenance={provenance}
      intermediateFiles={intermediateFiles}
    />
  );
}
```

## Testing

Unit tests should cover:
- Panel resize and persistence
- Panel collapse/expand
- Keyboard shortcuts
- Responsive behavior
- Command execution
- Selection state management
- ARIA landmarks

Integration tests should cover:
- Draft/publish workflow
- Export functionality
- SoA cell selection → Right Panel update
- Timeline node selection → Right Panel update

## Future Enhancements

- Wire draft/publish handlers to actual API endpoints
- Wire export handlers to actual export functions
- Wire validation results to quality store
- Add confirmation dialogs for Publish and Reset actions
- Add error boundaries for layout store corruption
- Add performance optimizations (requestAnimationFrame for resize)
