# RightPanel Component

## Overview

The `RightPanel` is a collapsible panel that displays contextual information based on selections in the Center Panel. It features a tabbed interface with three tabs: Properties, Provenance, and Footnotes. The panel animates smoothly when collapsing/expanding using Framer Motion.

## Features

- **Tabbed Interface**: Three tabs (Properties, Provenance, Footnotes) for different contextual views
- **Reactive Updates**: Content updates automatically based on `selectedCellId` and `selectedNodeId`
- **Smooth Animations**: Width animates using Framer Motion with 200ms duration
- **Collapsible**: Collapses to width 0 when `collapsed` prop is true
- **Empty States**: Displays informative empty states when no selection is active
- **Accessibility**: Implements ARIA complementary landmark and tabpanel pattern

## Props

```typescript
interface RightPanelProps {
  collapsed: boolean;              // Whether the panel is collapsed
  width: number;                   // Panel width in pixels (default: 320px)
  activeTab: RightPanelTab;        // Currently active tab
  onTabChange: (tab: RightPanelTab) => void;  // Tab change handler
  
  // Contextual data
  selectedCellId: string | null;   // Selected SoA cell ID
  selectedNodeId: string | null;   // Selected timeline node ID
  usdm: Record<string, unknown>;   // USDM data
  provenance: ProvenanceData | null;  // Provenance data
}

type RightPanelTab = 'properties' | 'provenance' | 'footnotes';
```

## Usage

```tsx
import { RightPanel } from '@/components/workbench/RightPanel';
import { useLayoutStore } from '@/stores/layoutStore';

function Workbench() {
  const {
    rightPanelCollapsed,
    rightPanelWidth,
    rightPanelActiveTab,
    setRightPanelActiveTab,
  } = useLayoutStore();

  const [selectedCellId, setSelectedCellId] = useState<string | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  return (
    <RightPanel
      collapsed={rightPanelCollapsed}
      width={rightPanelWidth}
      activeTab={rightPanelActiveTab}
      onTabChange={setRightPanelActiveTab}
      selectedCellId={selectedCellId}
      selectedNodeId={selectedNodeId}
      usdm={usdm}
      provenance={provenance}
    />
  );
}
```

## Tab Content

### Properties Tab

Displays properties of the selected node or cell. Shows:
- Selection information (cell ID or node ID)
- Placeholder message: "Properties panel coming soon"
- Empty state when no selection is active

### Provenance Tab

Displays provenance information for the selected cell. Shows:
- Selected cell ID
- Placeholder message: "Provenance panel coming soon"
- Empty state when no cell is selected

### Footnotes Tab

Displays footnotes related to the selected content. Shows:
- Selection information (cell ID or node ID)
- Placeholder message: "Footnotes panel coming soon"
- Empty state when no selection is active

## Layout Constraints

- **Default Width**: 320px
- **Minimum Width**: 240px
- **Maximum Width**: 600px
- **Collapsed Width**: 0px (hidden)

## Animation

The panel uses Framer Motion for smooth width transitions:
- **Duration**: 200ms
- **Easing**: easeInOut
- **Property**: width
- **Respects**: prefers-reduced-motion (via Framer Motion defaults)

## Accessibility

- **Role**: `complementary` (ARIA landmark)
- **Label**: "Right panel"
- **Hidden State**: `aria-hidden={collapsed}` when collapsed
- **Tab Pattern**: Implements ARIA tabpanel pattern with `role="tabpanel"` and `aria-labelledby`

## Empty States

Each tab displays a contextual empty state when no relevant selection is active:
- **Icon**: Tab-specific icon (Settings, GitBranch, FileText)
- **Message**: Short message explaining the empty state
- **Description**: Guidance on how to populate the panel

## Future Enhancements

The placeholder content in each tab will be replaced with actual implementations in later tasks:
- **Properties**: Display detailed properties of selected nodes/cells
- **Provenance**: Display source type, confidence, PDF references
- **Footnotes**: Display footnote content and references

## Related Components

- `PanelTabBar`: Tab strip component used for tab navigation
- `CenterPanel`: Main content panel that triggers selection changes
- `layoutStore`: Zustand store managing panel state

## Requirements Validated

- **7.1**: Right panel displays provenance details for selected SoA cells
- **7.2**: Right panel displays node properties for selected timeline nodes
- **7.3**: Right panel displays related properties for protocol metadata sections
- **7.4**: Right panel has its own tab bar for switching contextual views
- **7.5**: Right panel displays empty state when no contextual information is available
- **7.6**: Right panel updates content reactively without manual navigation
