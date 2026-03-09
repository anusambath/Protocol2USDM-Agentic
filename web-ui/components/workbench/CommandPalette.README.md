# CommandPalette Component

A keyboard-activated command palette overlay for quick navigation and action execution in the Protocol2USDM web UI redesign.

## Overview

The `CommandPalette` component provides a centered overlay with fuzzy search for navigating to any protocol section or executing common actions. It is triggered by the Ctrl/Cmd+K keyboard shortcut and implements the ARIA combobox pattern for accessibility.

## Features

- **Fuzzy Search**: Filters commands using fuzzy matching against labels and keywords
- **Keyboard Navigation**: Arrow Up/Down to navigate, Enter to select, Escape to close
- **Categorized Results**: Groups commands into "Navigate to" and "Actions" sections
- **Shortcut Hints**: Displays keyboard shortcuts for commands that have them
- **Animated Entry/Exit**: Fade and scale animation using Framer Motion
- **Focus Trap**: Prevents focus from leaving the palette while open
- **ARIA Combobox Pattern**: Implements proper accessibility with aria-activedescendant

## Usage

```tsx
import { CommandPalette } from '@/components/workbench/CommandPalette';
import { useState } from 'react';

function Workbench() {
  const [isPaletteOpen, setIsPaletteOpen] = useState(false);

  const handleExecute = (commandId: string) => {
    // Handle command execution
    if (commandId.startsWith('nav-')) {
      // Navigate to view
      const viewType = commandId.replace('nav-', '');
      layoutStore.openTab({ id: viewType, viewType, label: '...', icon: '...' });
    } else if (commandId.startsWith('action-')) {
      // Execute action
      switch (commandId) {
        case 'action-save-draft':
          handleSaveDraft();
          break;
        case 'action-toggle-sidebar':
          layoutStore.toggleSidebar();
          break;
        // ... other actions
      }
    }
  };

  return (
    <>
      {/* Workbench content */}
      <CommandPalette
        isOpen={isPaletteOpen}
        onClose={() => setIsPaletteOpen(false)}
        onExecute={handleExecute}
      />
    </>
  );
}
```

## Props

### `CommandPaletteProps`

```typescript
interface CommandPaletteProps {
  isOpen: boolean;           // Whether the palette is currently open
  onClose: () => void;       // Callback when palette should close
  onExecute: (commandId: string) => void;  // Callback when a command is selected
}
```

## Command Registry

The palette uses the `commandRegistry` from `@/lib/commandRegistry`, which includes:

### Navigation Commands (20)
- Protocol group: Overview, Eligibility, Objectives, Design, Interventions, Amendments
- Advanced group: Extensions, Entities, Procedures, Sites, Footnotes, Schedule, Narrative
- Quality group: Quality Metrics, Validation Results
- Data group: Document Structure, Images, SoA Table, Timeline Graph, Provenance

### Action Commands (8)
- Save Draft (⌘S)
- Publish
- Reset to Published
- Toggle Sidebar (⌘B)
- Toggle Right Panel (⌘J)
- Export CSV
- Export JSON
- Export PDF

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Ctrl/Cmd+K | Open command palette |
| Arrow Up | Move selection up |
| Arrow Down | Move selection down |
| Enter | Execute selected command |
| Escape | Close palette |

## Accessibility

The component implements the ARIA combobox pattern:

- **role="combobox"**: Applied to the search input container
- **role="listbox"**: Applied to the results list
- **role="option"**: Applied to each result item
- **aria-activedescendant**: Points to the currently selected result
- **aria-expanded**: Indicates the listbox is expanded
- **aria-controls**: Links the input to the listbox
- **aria-selected**: Indicates the selected option

### Focus Management

- Input is automatically focused when palette opens
- Focus remains trapped within the palette (clicking backdrop closes it)
- Selected item scrolls into view automatically
- Body scroll is prevented while palette is open

## Styling

The component uses Tailwind CSS classes and respects the application theme (dark/light mode):

- **Backdrop**: Semi-transparent black with blur effect
- **Container**: Centered modal with shadow, max-width 2xl
- **Input**: Full-width with search icon and ESC hint
- **Results**: Scrollable list with max-height 400px
- **Footer**: Keyboard hint bar at bottom

## Animation

Uses Framer Motion for smooth entry/exit:

- **Backdrop**: Fade in/out (150ms)
- **Container**: Fade + scale + vertical slide (200ms)
- **Timing**: Respects `prefers-reduced-motion` setting

## Fuzzy Search Algorithm

The `searchCommands` function from `commandRegistry.ts` implements a simple fuzzy match:

1. Converts query and search text to lowercase
2. Checks if all query characters appear in order in the label or keywords
3. Scores matches by position (earlier matches score higher)
4. Sorts results by score ascending

**Example**: Query "soa" matches "Schedule of Activities" (s-o-a in order).

## Requirements Validation

This component validates the following requirements from the Web UI Redesign specification:

- **Requirement 9.1**: Opens as centered overlay with text input on Ctrl/Cmd+K
- **Requirement 9.2**: Lists all navigable sections filtered by fuzzy matching
- **Requirement 9.3**: Executes command and closes palette on selection
- **Requirement 9.4**: Lists available actions (Save Draft, Publish, etc.)
- **Requirement 9.5**: Closes on Escape without performing action
- **Requirement 9.6**: Supports keyboard navigation (Arrow Up/Down, Enter)
- **Requirement 18.4**: Implements ARIA combobox pattern with listbox and aria-activedescendant
- **Requirement 18.5**: Implements focus trap while open

## Testing

Unit tests are located in `__tests__/CommandPalette.test.tsx` and cover:

- Rendering and opening/closing
- Fuzzy search filtering
- Keyboard navigation (Arrow Up/Down, Enter, Escape)
- Command execution
- Focus management
- ARIA attributes
- Empty results state
- Category grouping

## Example: Integration with Workbench

```tsx
import { CommandPalette } from '@/components/workbench/CommandPalette';
import { useLayoutStore } from '@/stores/layoutStore';
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts';
import { useState } from 'react';

function Workbench() {
  const [isPaletteOpen, setIsPaletteOpen] = useState(false);
  const { openTab, toggleSidebar, toggleRightPanel } = useLayoutStore();

  // Register Ctrl/Cmd+K shortcut
  useKeyboardShortcuts([
    {
      key: 'k',
      ctrl: true,
      action: () => setIsPaletteOpen(true),
      description: 'Open Command Palette',
    },
  ]);

  const handleExecute = (commandId: string) => {
    if (commandId.startsWith('nav-')) {
      // Navigate to view
      const viewType = commandId.replace('nav-', '') as ViewType;
      const entry = viewRegistry[viewType];
      if (entry) {
        openTab({
          id: viewType,
          viewType,
          label: entry.label,
          icon: entry.icon,
        });
      }
    } else if (commandId === 'action-save-draft') {
      handleSaveDraft();
    } else if (commandId === 'action-toggle-sidebar') {
      toggleSidebar();
    } else if (commandId === 'action-toggle-right-panel') {
      toggleRightPanel();
    }
    // ... handle other actions
  };

  return (
    <>
      {/* Workbench content */}
      <CommandPalette
        isOpen={isPaletteOpen}
        onClose={() => setIsPaletteOpen(false)}
        onExecute={handleExecute}
      />
    </>
  );
}
```

## Notes

- The palette is rendered via a React portal in the actual Workbench implementation
- Query is cleared when palette opens to show all commands initially
- Results are grouped by category (navigation vs action) for better organization
- Shortcut hints are hidden on small screens (< sm breakpoint)
- The component prevents body scroll while open to avoid background scrolling
- Selected item automatically scrolls into view for long result lists
