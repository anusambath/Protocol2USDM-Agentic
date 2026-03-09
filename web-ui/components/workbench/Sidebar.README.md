# Sidebar Component

The Sidebar component is a collapsible panel that displays different content based on the activity bar mode. It's part of the IDE/Workbench-style layout redesign.

## Features

- **Multiple Modes**: Supports three modes - Explorer, Search, and Quality
- **Collapsible**: Animates width to 0 when collapsed using Framer Motion
- **Smooth Animations**: 200ms ease-in-out transitions for collapse/expand
- **Responsive**: Adapts to different viewport sizes
- **Accessible**: Proper ARIA landmarks and semantic HTML

## Props

```typescript
interface SidebarProps {
  mode: ActivityBarMode;              // Current sidebar mode: 'explorer' | 'search' | 'quality'
  collapsed: boolean;                 // Whether the sidebar is collapsed
  width: number;                      // Width in pixels when expanded (default: 260px)
  activeTabId: string | null;         // Currently active tab ID for highlighting
  expandedGroups: Record<string, boolean>; // Nav tree group expanded states
  onNavigate: (viewType: ViewType) => void; // Callback when user navigates to a view
  onToggleGroup: (groupId: string) => void; // Callback when user toggles a nav group
}
```

## Modes

### Explorer Mode
Displays the NavTree component with hierarchical navigation organized into groups:
- **Protocol**: Overview, Eligibility, Objectives, Design, Interventions, Amendments
- **Advanced**: Extensions, Entities, Procedures, Sites, Footnotes, Schedule, Narrative
- **Quality**: Quality Metrics, Validation
- **Data**: Document, Images, SoA Table, Timeline, Provenance

### Search Mode
Displays the SearchPanel component (placeholder for future implementation).
Will allow users to search across all protocol sections and navigate quickly to specific content.

### Quality Mode
Displays the QualityPanel component (placeholder for future implementation).
Will show validation summaries, quality metrics, and issue breakdowns.

## Usage

```tsx
import { Sidebar } from '@/components/workbench';
import { useLayoutStore } from '@/stores/layoutStore';

function MyWorkbench() {
  const {
    activityBarMode,
    sidebarCollapsed,
    sidebarWidth,
    activeTabId,
    navTreeExpandedGroups,
    openTab,
    toggleNavTreeGroup,
  } = useLayoutStore();

  const handleNavigate = (viewType: ViewType) => {
    // Open the view as a tab in the center panel
    openTab({
      id: viewType,
      viewType,
      label: viewRegistry[viewType].label,
      icon: viewRegistry[viewType].icon,
    });
  };

  return (
    <Sidebar
      mode={activityBarMode}
      collapsed={sidebarCollapsed}
      width={sidebarWidth}
      activeTabId={activeTabId}
      expandedGroups={navTreeExpandedGroups}
      onNavigate={handleNavigate}
      onToggleGroup={toggleNavTreeGroup}
    />
  );
}
```

## Animation Behavior

- **Expand**: Animates from width 0 to the specified width (e.g., 260px) over 200ms
- **Collapse**: Animates from current width to 0 over 200ms
- **Easing**: Uses ease-in-out for smooth transitions
- **Content**: Content is hidden when collapsed to avoid overflow

## Styling

The Sidebar uses Tailwind CSS classes and respects the theme (dark/light mode):
- Background: `bg-background`
- Border: `border-r border-border`
- Header: `border-b border-border`
- Text: `text-foreground` and `text-muted-foreground`

## Integration with Layout Store

The Sidebar is designed to work seamlessly with the `layoutStore`:
- Reads `activityBarMode` to determine which content to display
- Reads `sidebarCollapsed` to control collapse state
- Reads `sidebarWidth` for the expanded width
- Reads `navTreeExpandedGroups` for nav tree state
- Calls `openTab()` when user navigates to a view
- Calls `toggleNavTreeGroup()` when user expands/collapses groups

## Accessibility

- Uses `<aside>` semantic element
- Will be wrapped with `role="navigation"` in the Workbench
- NavTree implements ARIA tree pattern
- Keyboard navigation supported through NavTree component

## Requirements Validated

- **Requirement 3.1**: Sidebar animates to collapsed state
- **Requirement 3.3**: Sidebar animates back to previously persisted width
- **Requirement 4.1**: Sidebar displays NavTree with hierarchical navigation
- **Requirement 5.2**: Sidebar switches content based on activity bar mode

## Related Components

- **NavTree**: Hierarchical navigation tree (explorer mode)
- **SearchPanel**: Search functionality (placeholder)
- **QualityPanel**: Quality metrics and validation (placeholder)
- **ActivityBar**: Controls which mode is active
- **Workbench**: Parent component that orchestrates the layout

## Future Enhancements

1. **Search Panel**: Implement fuzzy search across all protocol sections
2. **Quality Panel**: Display validation summaries and quality metrics
3. **Resize Handle**: Allow users to resize the sidebar width
4. **Keyboard Shortcuts**: Add shortcuts to toggle sidebar (Ctrl/Cmd+B)
5. **Persistence**: Width and collapsed state are persisted via layoutStore
