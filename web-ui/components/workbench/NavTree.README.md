# NavTree Component

## Overview

The `NavTree` component is a hierarchical navigation tree that organizes protocol sections into collapsible groups. It's displayed in the Sidebar when in "explorer" mode and provides keyboard-accessible navigation to all protocol views.

## Features

- **Hierarchical Organization**: Groups protocol sections into 4 categories (Protocol, Advanced, Quality, Data)
- **Collapsible Groups**: Click group headers to expand/collapse child items
- **Active Item Highlighting**: Visually highlights the currently active tab
- **Keyboard Navigation**: Full arrow-key navigation support
- **ARIA Tree Pattern**: Implements proper accessibility with `role="tree"`, `role="treeitem"`, and `aria-expanded`
- **Icon Support**: Uses Lucide icons from the view registry

## Usage

```tsx
import { NavTree } from '@/components/workbench/NavTree';
import { useLayoutStore } from '@/stores/layoutStore';

function Sidebar() {
  const { activeTabId, navTreeExpandedGroups, openTab, toggleNavTreeGroup } = useLayoutStore();

  const handleNavigate = (viewType: ViewType) => {
    const entry = viewRegistry[viewType];
    if (entry) {
      openTab({
        id: viewType,
        viewType,
        label: entry.label,
        icon: entry.icon,
      });
    }
  };

  return (
    <NavTree
      activeTabId={activeTabId}
      expandedGroups={navTreeExpandedGroups}
      onNavigate={handleNavigate}
      onToggleGroup={toggleNavTreeGroup}
    />
  );
}
```

## Props

### `activeTabId`
- **Type**: `string | null`
- **Description**: The ID of the currently active tab in the Center Panel. Used to highlight the corresponding nav item.

### `expandedGroups`
- **Type**: `Record<string, boolean>`
- **Description**: Object mapping group IDs to their expanded state. Persisted in the layout store.

### `onNavigate`
- **Type**: `(viewType: ViewType) => void`
- **Description**: Callback fired when a nav item is clicked. Should open or focus the corresponding tab.

### `onToggleGroup`
- **Type**: `(groupId: string) => void`
- **Description**: Callback fired when a group header is clicked. Should toggle the group's expanded state.

## Static Group Definitions

The NavTree organizes views into 4 groups:

### Protocol
- Overview (Study Metadata)
- Eligibility Criteria
- Objectives & Endpoints
- Study Design
- Interventions
- Amendment History

### Advanced
- Extensions
- Advanced Entities
- Procedures & Devices
- Study Sites
- Footnotes
- Schedule Timeline
- Narrative

### Quality
- Quality Metrics
- Validation Results

### Data
- Document Structure
- SoA Images
- SoA Table
- Timeline
- Provenance

## Keyboard Navigation

The NavTree implements full keyboard navigation following the ARIA tree pattern:

- **Arrow Down**: Move focus to the next item
- **Arrow Up**: Move focus to the previous item
- **Arrow Right**: Expand a collapsed group (when focused on a group header)
- **Arrow Left**: Collapse an expanded group or move to parent group (when focused on a child item)
- **Enter / Space**: Activate the focused item (toggle group or navigate to view)

## Accessibility

The component implements the ARIA tree pattern with:

- `role="tree"` on the container
- `role="treeitem"` on groups and items
- `aria-expanded` on group headers
- `aria-current="page"` on the active item
- `aria-label` on all interactive elements
- Visible focus indicators via `focus:ring-2`

## Integration with View Registry

The NavTree uses the `viewRegistry` from `@/lib/viewRegistry.ts` to get the icon and label for each view type. This ensures consistency between the navigation tree and the actual views.

## Styling

The component uses Tailwind CSS with design system tokens:

- `bg-accent` for hover and active states
- `text-accent-foreground` for active item text
- `text-muted-foreground` for inactive items
- `focus:ring-ring` for focus indicators

## Requirements Validated

This component validates the following requirements from the spec:

- **4.1**: Organizes sections into Protocol, Advanced, Quality, Data groups
- **4.2**: Opens/focuses corresponding view on click
- **4.3**: Displays icon and label from view registry
- **4.4**: Hides child items when group is collapsed
- **4.5**: Shows child items when group is expanded
- **4.6**: Highlights active item matching activeTabId
- **4.7**: Restores group expanded/collapsed states from layout store
- **18.2**: Implements ARIA tree pattern with arrow-key navigation
