# useKeyboardShortcuts Hook

A React hook for managing global keyboard shortcuts in the Protocol2USDM web UI redesign.

## Overview

The `useKeyboardShortcuts` hook (Keyboard_Manager) provides a declarative way to register and manage keyboard shortcuts throughout the application. It automatically handles:

- Cross-platform modifier keys (Ctrl on Windows/Linux, Cmd on macOS)
- Input element exclusion (prevents shortcuts from firing in text inputs)
- Event prevention (calls `preventDefault()` to override browser defaults)
- Cleanup on unmount

## Usage

```tsx
import { useKeyboardShortcuts, ShortcutConfig } from '@/hooks/useKeyboardShortcuts';

function MyComponent() {
  const shortcuts: ShortcutConfig[] = [
    {
      key: 's',
      ctrl: true,
      action: handleSave,
      description: 'Save Draft',
    },
    {
      key: 'b',
      ctrl: true,
      action: toggleSidebar,
      description: 'Toggle Sidebar',
    },
  ];

  useKeyboardShortcuts(shortcuts);

  return <div>My Component</div>;
}
```

## API

### `useKeyboardShortcuts(shortcuts: ShortcutConfig[])`

Registers global keyboard shortcuts.

**Parameters:**
- `shortcuts`: Array of shortcut configurations

### `ShortcutConfig`

```typescript
interface ShortcutConfig {
  key: string;           // The key to match (e.g., 's', 'b', '1')
  ctrl?: boolean;        // Whether Ctrl (Windows/Linux) or Cmd (macOS) is required
  meta?: boolean;        // Alternative to ctrl for explicit meta key handling
  action: () => void;    // Function to execute when shortcut is triggered
  description: string;   // Human-readable description of the shortcut
}
```

## Behavior

### 1. Focus Context Check

The hook automatically skips interception when focus is in:
- `<input>` elements
- `<textarea>` elements
- Elements with `[data-ag-grid-editor]` attribute (AG Grid cell editors)
- Elements with `contentEditable` enabled

This ensures shortcuts don't interfere with normal text input.

### 2. Cross-Platform Modifier Keys

When `ctrl: true` is specified, the hook automatically uses:
- `Ctrl` key on Windows/Linux
- `Cmd` key on macOS

This provides a consistent user experience across platforms.

### 3. Event Prevention

When a shortcut matches, the hook calls `event.preventDefault()` to prevent the browser's default behavior (e.g., Ctrl+S normally opens the browser's save dialog).

### 4. Case-Insensitive Matching

Key matching is case-insensitive, so `key: 'S'` and `key: 's'` are equivalent.

## Standard Shortcuts

The following shortcuts are typically registered in the Workbench component:

| Shortcut | Action | Description |
|----------|--------|-------------|
| Ctrl/Cmd+S | Save Draft | Save the current draft overlay |
| Ctrl/Cmd+B | Toggle Sidebar | Show/hide the left sidebar |
| Ctrl/Cmd+J | Toggle Right Panel | Show/hide the right panel |
| Ctrl/Cmd+K | Command Palette | Open the command palette overlay |
| Ctrl/Cmd+W | Close Active Tab | Close the currently active tab |
| Ctrl/Cmd+1-9 | Switch to Tab | Switch to tab at ordinal position |

## Example: Workbench Integration

```tsx
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts';
import { useLayoutStore } from '@/stores/layoutStore';

function Workbench() {
  const {
    toggleSidebar,
    toggleRightPanel,
    closeTab,
    setActiveTab,
    activeTabId,
    openTabs,
  } = useLayoutStore();

  const shortcuts = [
    { key: 's', ctrl: true, action: handleSaveDraft, description: 'Save Draft' },
    { key: 'b', ctrl: true, action: toggleSidebar, description: 'Toggle Sidebar' },
    { key: 'j', ctrl: true, action: toggleRightPanel, description: 'Toggle Right Panel' },
    { key: 'k', ctrl: true, action: openCommandPalette, description: 'Command Palette' },
    { key: 'w', ctrl: true, action: () => activeTabId && closeTab(activeTabId), description: 'Close Active Tab' },
    
    // Ctrl/Cmd+1-9: Switch to tab
    ...Array.from({ length: 9 }, (_, i) => ({
      key: String(i + 1),
      ctrl: true,
      action: () => {
        const tab = openTabs[i];
        if (tab) setActiveTab(tab.id);
      },
      description: `Switch to tab ${i + 1}`,
    })),
  ];

  useKeyboardShortcuts(shortcuts);

  return <div>{/* Workbench content */}</div>;
}
```

## Requirements Validation

This hook validates the following requirements from the Web UI Redesign specification:

- **Requirement 10.1**: Register shortcuts for Save Draft, Toggle Sidebar, Toggle Right Panel, Command Palette, Close Active Tab
- **Requirement 10.2**: Execute corresponding action when shortcut is pressed
- **Requirement 10.3**: Prevent browser default behavior for registered shortcuts
- **Requirement 10.4**: Do not intercept shortcuts when focus is in text input, textarea, or AG Grid cell editor
- **Requirement 10.5**: Support Ctrl/Cmd+1-9 for switching to tab at ordinal position

## Testing

Unit tests are located in `__tests__/useKeyboardShortcuts.test.tsx` and cover:

- Shortcut execution
- `preventDefault()` behavior
- Input element exclusion (input, textarea, AG Grid editor, contentEditable)
- Multiple shortcuts
- Case-insensitive matching
- Missing modifier keys
- Cleanup on unmount

## Notes

- The hook uses `useEffect` with the `shortcuts` array as a dependency, so shortcuts can be dynamically updated
- Event listeners are properly cleaned up when the component unmounts
- The hook is designed to be used once per application (typically in the Workbench component)
- Multiple instances of the hook can coexist, but be careful of conflicting shortcuts
