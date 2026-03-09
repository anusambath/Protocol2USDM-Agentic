# useResponsiveLayout Hook

## Overview

The `useResponsiveLayout` hook provides automatic responsive behavior for the workbench layout by detecting viewport changes and managing panel collapse/expand states. It ensures optimal space utilization on different screen sizes while preserving user preferences.

## Requirements

**Validates Requirements:**
- 17.1: Auto-collapse Sidebar when viewport < 1024px
- 17.2: Auto-collapse Right Panel when viewport < 1024px  
- 17.3: Restore persisted states when viewport >= 1024px

## Usage

```typescript
import { useResponsiveLayout } from '@/hooks/useResponsiveLayout';

function Workbench() {
  // Enable responsive layout behavior
  useResponsiveLayout();

  return (
    <div className="workbench">
      {/* Your layout components */}
    </div>
  );
}
```

## Behavior

### Mobile/Tablet (viewport < 1024px)
- **Sidebar**: Automatically collapses to show only Activity Bar
- **Right Panel**: Automatically collapses to hidden
- **Center Panel**: Expands to maximize available space
- **User State**: Current panel states are saved for restoration

### Desktop (viewport >= 1024px)
- **Sidebar**: Restores to user's persisted state (collapsed or expanded)
- **Right Panel**: Restores to user's persisted state (collapsed or expanded)
- **Layout**: Returns to user's preferred configuration

## Technical Implementation

### Performance Optimizations

1. **matchMedia API**: Uses `window.matchMedia('(max-width: 1023px)')` instead of window resize events
   - More efficient than polling window dimensions
   - Native browser optimization
   - Better battery life on mobile devices

2. **Debouncing**: 100ms debounce on viewport changes
   - Prevents rapid toggle calls during resize
   - Reduces layout thrashing
   - Improves animation smoothness

3. **State Preservation**: Saves panel states before auto-collapse
   - Stores original collapsed states in ref
   - Restores exact states on viewport expansion
   - Works seamlessly with localStorage persistence

### Event Handling

```typescript
// Listens for viewport changes
const mediaQuery = window.matchMedia('(max-width: 1023px)');
mediaQuery.addEventListener('change', handleResize);

// Performs initial check on mount
handleResize(mediaQuery);

// Cleans up on unmount
return () => {
  mediaQuery.removeEventListener('change', handleResize);
  clearTimeout(debounceTimer);
};
```

## Integration with layoutStore

The hook integrates with Zustand's `layoutStore` to manage panel states:

```typescript
const toggleSidebar = useLayoutStore((state) => state.toggleSidebar);
const toggleRightPanel = useLayoutStore((state) => state.toggleRightPanel);
const sidebarCollapsed = useLayoutStore((state) => state.sidebarCollapsed);
const rightPanelCollapsed = useLayoutStore((state) => state.rightPanelCollapsed);
```

All state changes are automatically persisted to localStorage via Zustand's persist middleware.

## Manual Overrides

Users can still manually toggle panels even on mobile viewports. The hook only auto-collapses when crossing the 1024px breakpoint threshold, not on every resize event.

```typescript
// Manual toggle still works
const toggleSidebar = useLayoutStore((state) => state.toggleSidebar);

<button onClick={toggleSidebar}>
  Toggle Sidebar
</button>
```

## Edge Cases Handled

1. **Already Collapsed Panels**: Doesn't toggle panels that are already in the target state
2. **Rapid Resizing**: Debounces to prevent multiple rapid toggles
3. **State Restoration**: Only restores states if they were auto-collapsed (not manually collapsed)
4. **Cleanup**: Properly removes listeners and clears timers on unmount

## Testing

The hook includes comprehensive unit tests covering:
- Auto-collapse on viewport < 1024px
- State restoration on viewport >= 1024px
- Debouncing behavior (100ms)
- Avoiding redundant toggles
- Event listener cleanup
- Initial check on mount

See `__tests__/useResponsiveLayout.test.tsx` for test implementation.

## Design Decisions

### Why 1024px breakpoint?
- Standard tablet/desktop breakpoint
- Matches common CSS frameworks (Tailwind's `lg` breakpoint)
- Provides enough space for comfortable multi-panel layout

### Why 100ms debounce?
- Balance between responsiveness and performance
- Prevents thrashing during window resize
- Allows smooth animations to complete

### Why matchMedia over resize events?
- More efficient (browser-optimized)
- Fires only on breakpoint crossing, not every pixel
- Better for battery life on mobile devices
- Cleaner API with boolean matches property

## Related Components

- `layoutStore`: Manages panel state and persistence
- `Workbench`: Main layout component that uses this hook
- `Sidebar`: Left panel that auto-collapses
- `RightPanel`: Right panel that auto-collapses
- `CenterPanel`: Always visible, expands to fill space

## Future Enhancements

Potential improvements for future iterations:
- Configurable breakpoint via props
- Configurable debounce duration
- Support for multiple breakpoints (mobile, tablet, desktop)
- Animation coordination with Framer Motion
- Prefers-reduced-motion support
