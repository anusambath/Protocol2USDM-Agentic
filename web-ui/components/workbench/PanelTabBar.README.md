# PanelTabBar Component

A reusable horizontal tab strip component for the workbench interface that displays tabs with icons, labels, and optional close buttons. Implements the ARIA tablist pattern with full keyboard navigation support.

## Features

- **Horizontal Tab Strip**: Displays tabs in a horizontal layout with overflow scroll when tabs exceed available width
- **Icon + Label**: Each tab shows a Lucide icon and text label
- **Optional Close Button**: Tabs can be closable with an X button that appears on hover or when active
- **ARIA Tablist Pattern**: Implements proper accessibility with `role="tablist"`, `role="tab"`, and `aria-selected`
- **Keyboard Navigation**: Full arrow-key navigation between tabs (Left/Right arrows, Home/End keys)
- **Active Tab Highlighting**: Visually distinguishes the active tab with background and shadow
- **Responsive**: Horizontal scroll for overflow tabs with custom scrollbar styling

## Usage

```tsx
import { PanelTabBar } from '@/components/workbench';

function MyPanel() {
  const [activeTabId, setActiveTabId] = useState('tab1');
  
  const tabs = [
    { id: 'tab1', label: 'Overview', icon: 'FileText', closable: true },
    { id: 'tab2', label: 'Timeline', icon: 'Clock', closable: true },
    { id: 'tab3', label: 'Schedule', icon: 'Calendar', closable: false },
  ];

  return (
    <PanelTabBar
      tabs={tabs}
      activeTabId={activeTabId}
      onTabChange={setActiveTabId}
      onTabClose={(tabId) => {
        // Handle tab close
        console.log('Closing tab:', tabId);
      }}
    />
  );
}
```

## Props

### `tabs`
- **Type**: `Array<{ id: string; label: string; icon: string; closable?: boolean }>`
- **Required**: Yes
- **Description**: Array of tab objects to display. Each tab must have:
  - `id`: Unique identifier for the tab
  - `label`: Display text for the tab
  - `icon`: Name of a Lucide icon (e.g., 'FileText', 'Clock', 'Calendar')
  - `closable`: Optional boolean indicating if the tab can be closed (defaults to false)

### `activeTabId`
- **Type**: `string | null`
- **Required**: Yes
- **Description**: The ID of the currently active tab. Set to `null` if no tab is active.

### `onTabChange`
- **Type**: `(tabId: string) => void`
- **Required**: Yes
- **Description**: Callback function called when a tab is clicked or navigated to via keyboard.

### `onTabClose`
- **Type**: `(tabId: string) => void`
- **Required**: No
- **Description**: Callback function called when a tab's close button is clicked. If not provided, close buttons will not be rendered even if `closable: true`.

## Keyboard Navigation

The component supports full keyboard navigation:

- **Arrow Left**: Move focus to the previous tab (wraps to last tab)
- **Arrow Right**: Move focus to the next tab (wraps to first tab)
- **Home**: Move focus to the first tab
- **End**: Move focus to the last tab
- **Tab**: Move focus into/out of the tab list (standard browser behavior)

## Accessibility

The component implements the ARIA tablist pattern:

- `role="tablist"` on the container
- `role="tab"` on each tab button
- `aria-selected="true"` on the active tab
- `aria-controls` linking each tab to its panel
- `tabIndex={0}` on the active tab, `tabIndex={-1}` on inactive tabs
- Focus ring indicators for keyboard navigation
- Descriptive `aria-label` on close buttons

## Styling

The component uses Tailwind CSS with design tokens from the theme system:

- **Active Tab**: `bg-background` with `shadow-sm`
- **Inactive Tab**: `text-muted-foreground` with hover effects
- **Close Button**: Appears on hover or when tab is active
- **Scrollbar**: Custom thin scrollbar styling for overflow
- **Focus Indicators**: Ring-based focus indicators for accessibility

## Integration with Workbench

This component is used by both `CenterPanel` and `RightPanel` to display their respective tabs:

```tsx
// In CenterPanel
<PanelTabBar
  tabs={openTabs}
  activeTabId={activeTabId}
  onTabChange={handleTabChange}
  onTabClose={handleTabClose}
/>

// In RightPanel
<PanelTabBar
  tabs={contextualTabs}
  activeTabId={activeContextualTab}
  onTabChange={handleContextualTabChange}
  // No onTabClose - right panel tabs are not closable
/>
```

## Design Decisions

1. **Icon Fallback**: If an icon name is not found in Lucide, falls back to `FileText` icon
2. **Close Button Visibility**: Close buttons are hidden by default and appear on hover or when the tab is active
3. **Max Label Width**: Tab labels are truncated at 120px to prevent excessive tab width
4. **Overflow Scroll**: Uses horizontal scroll instead of dropdown or virtualization for simplicity
5. **Focus Management**: Maintains internal focus index for keyboard navigation separate from active tab

## Requirements Validation

This component validates the following requirements from the Web UI Redesign spec:

- **Requirement 6.1**: Panel Tab Bar displays tabs with icon and label
- **Requirement 6.2**: Clicking a tab activates it
- **Requirement 6.3**: Close button removes the tab
- **Requirement 6.5**: Horizontal scrolling for overflow tabs
- **Requirement 18.3**: ARIA tablist pattern with arrow-key navigation
