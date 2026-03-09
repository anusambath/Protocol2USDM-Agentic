# ActivityBar Component

A vertical icon strip on the far left of the workbench that allows users to switch between sidebar modes (Explorer, Search, Quality).

## Features

- **48px-wide vertical strip** with icon buttons
- **Three modes**: Explorer (FolderTree), Search, Quality (CheckCircle2)
- **Active mode highlighting** with accent background
- **Toggle sidebar collapse** when clicking the active mode icon
- **Switch modes** when clicking an inactive mode icon
- **Accessible** with ARIA toolbar pattern and proper labels

## Usage

```tsx
import { ActivityBar } from '@/components/workbench/ActivityBar';
import { useLayoutStore } from '@/stores/layoutStore';

function Workbench() {
  const activityBarMode = useLayoutStore((state) => state.activityBarMode);
  const setActivityBarMode = useLayoutStore((state) => state.setActivityBarMode);
  const toggleSidebar = useLayoutStore((state) => state.toggleSidebar);

  return (
    <ActivityBar
      activeMode={activityBarMode}
      onModeChange={setActivityBarMode}
      onToggleSidebar={toggleSidebar}
    />
  );
}
```

## Props

### `activeMode`
- **Type**: `ActivityBarMode` (`'explorer' | 'search' | 'quality'`)
- **Required**: Yes
- **Description**: The currently active sidebar mode

### `onModeChange`
- **Type**: `(mode: ActivityBarMode) => void`
- **Required**: Yes
- **Description**: Callback when user clicks an inactive mode icon to switch modes

### `onToggleSidebar`
- **Type**: `() => void`
- **Required**: Yes
- **Description**: Callback when user clicks the active mode icon to toggle sidebar collapse

## Behavior

1. **Clicking an inactive mode icon**: Switches the sidebar to display that mode's content and highlights the clicked icon
2. **Clicking the active mode icon**: Toggles the sidebar between collapsed and expanded states
3. **Visual feedback**: Active mode has accent background, inactive modes show hover effects

## Accessibility

- Uses `role="toolbar"` with `aria-label="Activity Bar"`
- Each button has `aria-label` with the mode name
- Each button has `aria-pressed` to indicate active state
- Keyboard accessible with focus indicators

## Design Specifications

- **Width**: 48px (12 in Tailwind units)
- **Icon size**: 20px (h-5 w-5)
- **Button size**: 40px (w-10 h-10)
- **Active background**: `bg-accent`
- **Inactive hover**: `hover:bg-accent/50`
- **Icons**: FolderTree (Explorer), Search, CheckCircle2 (Quality)

## Requirements Validated

- **5.1**: Displays icon buttons for Explorer, Search, and Quality modes
- **5.2**: Switches sidebar content when clicking mode icons
- **5.3**: Visually indicates the currently active mode
- **5.4**: Toggles sidebar collapse when clicking active mode icon
- **5.5**: Remains visible at all times
