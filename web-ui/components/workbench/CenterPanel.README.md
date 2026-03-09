# CenterPanel Component

## Overview

The `CenterPanel` is the main content area of the Workbench that displays protocol views in a tabbed interface. It supports multiple open tabs, lazy rendering for performance, and displays a welcome state when no tabs are open.

## Features

- **Tabbed Interface**: Displays multiple open views as tabs using `PanelTabBar`
- **Lazy Rendering**: Only mounts the active tab's component for optimal performance
- **Welcome State**: Shows quick-action links when no tabs are open
- **View Integration**: Renders any view from the `viewRegistry` with correct props
- **Accessibility**: Implements ARIA tabpanel pattern with proper roles and attributes

## Props

```typescript
interface CenterPanelProps {
  openTabs: LayoutTab[];              // Array of open tabs
  activeTabId: string | null;         // ID of the currently active tab
  onTabChange: (tabId: string) => void;  // Callback when tab is activated
  onTabClose: (tabId: string) => void;   // Callback when tab is closed
  
  // View rendering props (passed to all view components)
  usdm: Record<string, unknown>;
  protocolId: string;
  provenance: ProvenanceData | null;
  intermediateFiles: Record<string, unknown> | null;
  onCellSelect?: (cellId: string) => void;    // For SoA cell selection
  onNodeSelect?: (nodeId: string) => void;    // For Timeline node selection
}
```

## Usage

```tsx
import { CenterPanel } from '@/components/workbench/CenterPanel';
import { useLayoutStore } from '@/stores/layoutStore';

function Workbench() {
  const { openTabs, activeTabId, setActiveTab, closeTab } = useLayoutStore();
  
  return (
    <CenterPanel
      openTabs={openTabs}
      activeTabId={activeTabId}
      onTabChange={setActiveTab}
      onTabClose={closeTab}
      usdm={usdm}
      protocolId={protocolId}
      provenance={provenance}
      intermediateFiles={intermediateFiles}
      onCellSelect={handleCellSelect}
      onNodeSelect={handleNodeSelect}
    />
  );
}
```

## Welcome State

When `openTabs` is empty or `activeTabId` is null, the component displays a welcome screen with:

- Welcome message and description
- Quick-action cards for common views:
  - Study Metadata (Overview)
  - SoA Table
  - Timeline
  - Quality Metrics
- Keyboard shortcut hint for Command Palette (Ctrl+K)

Clicking a quick-action card calls `onTabChange` with the view ID, allowing the parent to open that tab.

## View Rendering

The component uses the `viewRegistry` to:

1. Look up the view component for the active tab's `viewType`
2. Render the component with standardized props
3. Handle missing view components gracefully (falls back to welcome state)

All view components receive these props:
- `usdm`: The USDM protocol data
- `protocolId`: The protocol identifier
- `provenance`: Provenance tracking data
- `intermediateFiles`: Intermediate extraction files
- `onNodeSelect`: Callback for timeline node selection
- `onCellSelect`: Callback for SoA cell selection

## Lazy Rendering

Only the active tab's component is mounted in the DOM. When switching tabs:

1. The previous tab's component is unmounted
2. The new tab's component is mounted
3. This prevents performance issues with heavy components (AG Grid, Cytoscape)

**Note**: This means scroll position and component state are lost when switching tabs. For views where state preservation is critical, consider implementing a keep-alive mechanism with `display: none` instead of unmounting.

## Accessibility

The component implements proper ARIA patterns:

- `role="main"` on the container
- `role="tabpanel"` on the active view container
- `id="panel-{tabId}"` for panel identification
- `aria-labelledby="tab-{tabId}"` linking to the tab button

The `PanelTabBar` implements the ARIA tablist pattern with keyboard navigation.

## Integration Points

### With Layout Store

The component receives tab state from `layoutStore`:
- `openTabs`: Array of open tabs
- `activeTabId`: Currently active tab ID

It calls store actions via callbacks:
- `onTabChange`: Updates active tab
- `onTabClose`: Removes tab from store

### With View Registry

The component uses `viewRegistry` to:
- Get the React component for each view type
- Get icons and labels for quick-action links
- Ensure all views receive correct props

### With Right Panel

Selection callbacks propagate to the Right Panel:
- `onCellSelect`: When user selects a SoA cell
- `onNodeSelect`: When user selects a Timeline node

The parent component (Workbench) manages this coordination.

## Error Handling

### Missing View Component

If a tab's `viewType` doesn't exist in the `viewRegistry`:
- The component renders the welcome state instead
- No error is thrown (graceful degradation)
- User can close the invalid tab

### Empty Tab List

When all tabs are closed:
- The welcome state is displayed automatically
- User can open new tabs via quick actions or sidebar

## Performance Considerations

1. **Lazy Rendering**: Only active tab is mounted
2. **Memoization**: View props are memoized to prevent unnecessary re-renders
3. **Tab Bar Optimization**: Tab list is converted to PanelTabBar format only when tabs change

## Testing

The component includes comprehensive unit tests covering:

- Welcome state rendering
- Quick-action link functionality
- Tab bar rendering with multiple tabs
- Active view rendering
- Lazy rendering (only active tab mounted)
- Tab switching
- Prop passing to view components
- Tab close functionality
- ARIA attributes
- Missing view component handling

Run tests with:
```bash
npm test -- CenterPanel.test.tsx --run
```

## Related Components

- **PanelTabBar**: Renders the tab strip at the top
- **Workbench**: Parent component that orchestrates all panels
- **RightPanel**: Displays contextual details based on CenterPanel selection
- **NavTree**: Sidebar navigation that opens tabs in CenterPanel

## Design Decisions

### Why Lazy Rendering?

Mounting all open tabs simultaneously would be expensive:
- AG Grid (SoA table) is heavy
- Cytoscape (Timeline) is heavy
- Multiple metadata views with complex rendering

Lazy rendering ensures only the visible content is rendered, improving performance.

### Why Welcome State?

The welcome state serves multiple purposes:
- Provides guidance for new users
- Offers quick access to common views
- Prevents empty/confusing UI when no tabs are open
- Reinforces the keyboard shortcut (Ctrl+K) for power users

### Why Separate onCellSelect and onNodeSelect?

These callbacks enable Right Panel integration:
- SoA cell selection → show provenance details
- Timeline node selection → show node properties

Keeping them separate allows the parent to handle each case differently.

## Future Enhancements

Potential improvements for future iterations:

1. **Keep-Alive Mode**: Option to preserve tab state with `display: none` instead of unmounting
2. **Tab Reordering**: Drag-and-drop to reorder tabs
3. **Tab Pinning**: Pin important tabs to prevent accidental closure
4. **Tab Groups**: Group related tabs together
5. **Split View**: Display two tabs side-by-side
6. **Tab Search**: Search through open tabs when many are open
7. **Recent Tabs**: Show recently closed tabs in welcome state

## Requirements Validation

This component validates the following requirements from the spec:

- **6.1**: Renders PanelTabBar at top with open tabs ✓
- **6.2**: Renders active view below based on activeTabId ✓
- **6.3**: Lazy-renders views (only mounts active tab component) ✓
- **6.4**: Shows welcome state with quick-action links when no tabs open ✓
- **6.6**: Passes usdm, protocolId, provenance, intermediateFiles props to views ✓
- **16.5**: Implements onCellSelect and onNodeSelect callbacks for Right Panel integration ✓
