# PanelSplitter Component

A 4px draggable divider component for resizing adjacent panels in the workbench layout.

## Features

- **Mouse Drag**: Click and drag to resize adjacent panels
- **Double-Click**: Toggle the adjacent panel between collapsed and expanded states
- **Keyboard Support**: Use arrow keys to adjust width by 10px increments
- **Accessibility**: Implements ARIA separator pattern with keyboard navigation
- **Visual Feedback**: Shows hover state and focus ring for keyboard users

## Props

```typescript
interface PanelSplitterProps {
  position: 'left' | 'right';
  onResize: (delta: number) => void;
  onDoubleClick: () => void;
}
```

### `position`
- Type: `'left' | 'right'`
- Description: Indicates which side of the workbench the splitter is on
- Used for: Determining arrow key behavior

### `onResize`
- Type: `(delta: number) => void`
- Description: Callback fired during drag with pixel delta from initial position
- Parameters:
  - `delta`: Positive values increase panel width, negative values decrease

### `onDoubleClick`
- Type: `() => void`
- Description: Callback fired when user double-clicks the splitter
- Used for: Toggling the adjacent panel's collapsed state

## Usage Example

```tsx
import { PanelSplitter } from '@/components/workbench';
import { useLayoutStore } from '@/stores/layoutStore';

function Workbench() {
  const { sidebarWidth, setSidebarWidth, toggleSidebar } = useLayoutStore();

  const handleLeftSplitterResize = (delta: number) => {
    const newWidth = Math.max(200, Math.min(480, sidebarWidth + delta));
    setSidebarWidth(newWidth);
  };

  return (
    <div className="flex">
      <Sidebar width={sidebarWidth} />
      
      <PanelSplitter
        position="left"
        onResize={handleLeftSplitterResize}
        onDoubleClick={toggleSidebar}
      />
      
      <CenterPanel />
    </div>
  );
}
```

## Keyboard Navigation

When the splitter has focus:
- **Arrow Left**: Decrease panel width by 10px
- **Arrow Right**: Increase panel width by 10px
- **Tab**: Move focus to next interactive element
- **Shift+Tab**: Move focus to previous interactive element

## Accessibility

- Uses `role="separator"` with `aria-orientation="vertical"`
- Includes descriptive `aria-label` based on position
- Keyboard focusable with visible focus indicator
- Supports keyboard-only operation

## Implementation Details

### Mouse Drag Behavior

1. On `mousedown`: Record initial X position and set dragging state
2. On `mousemove` (while dragging): Calculate delta and call `onResize`
3. On `mouseup`: Clear dragging state and remove global listeners

### Constraints

The component itself does not enforce min/max width constraints. The parent component should handle constraints in the `onResize` callback:

```tsx
const handleResize = (delta: number) => {
  const newWidth = Math.max(MIN_WIDTH, Math.min(MAX_WIDTH, currentWidth + delta));
  setWidth(newWidth);
};
```

### Styling

- Width: 4px (w-1 in Tailwind)
- Cursor: `col-resize` on hover
- Background: Uses theme border color with accent on hover
- Focus: 2px ring with offset for visibility

## Requirements Validated

- **Requirement 2.1**: Draggable divider between panels
- **Requirement 2.2**: Real-time resize during drag
- **Requirement 2.3**: Keyboard support for accessibility
- **Requirement 3.6**: Double-click to toggle adjacent panel
