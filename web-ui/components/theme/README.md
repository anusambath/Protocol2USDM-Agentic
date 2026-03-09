# Theme System

This directory contains the theme management system for Protocol2USDM, implementing dark mode first with light mode option.

## Components

### ThemeProvider

The main provider component that manages theme state and persistence.

**Features:**
- Defaults to dark mode on first visit
- Persists theme preference to localStorage (key: `p2u-theme`)
- Applies/removes `dark` class on `document.documentElement`
- Provides theme context to all child components

**Usage:**

```tsx
import { ThemeProvider } from '@/components/theme';

export function RootLayout({ children }) {
  return (
    <html>
      <body>
        <ThemeProvider>
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
```

### useTheme Hook

Hook to access the current theme and toggle function.

**Usage:**

```tsx
import { useTheme } from '@/hooks/useTheme';

function MyComponent() {
  const { theme, toggleTheme } = useTheme();
  
  return (
    <div>
      <p>Current theme: {theme}</p>
      <button onClick={toggleTheme}>
        Toggle Theme
      </button>
    </div>
  );
}
```

### ThemeToggle Component

A pre-built button component for toggling themes with icons.

**Usage:**

```tsx
import { ThemeToggle } from '@/components/theme';

function StatusBar() {
  return (
    <div className="status-bar">
      <ThemeToggle />
    </div>
  );
}
```

## Requirements Satisfied

This implementation satisfies the following requirements from the Web UI Redesign spec:

- **11.1**: Apply dark color scheme as default theme on first visit
- **11.2**: Toggle between dark and light modes
- **11.3**: Persist theme selection to localStorage
- **11.4**: Restore persisted theme preference from localStorage
- **11.5**: Default to dark mode if no persisted preference exists

## CSS Variables

The theme system uses CSS custom properties defined in `app/globals.css`:

- `:root` - Light mode variables
- `.dark` - Dark mode variables

All components should use these variables via Tailwind utilities:
- `bg-background` - Background color
- `text-foreground` - Text color
- `bg-card` - Card background
- `text-card-foreground` - Card text
- etc.

## Integration with AG Grid and Cytoscape

The theme changes automatically propagate to:
- **AG Grid**: Uses CSS variables from globals.css
- **Cytoscape**: Will use theme-aware styles from `styles/cytoscape-theme.ts`

No manual intervention required - theme changes apply without page reload.

## Testing

Unit tests are located in `__tests__/ThemeProvider.test.tsx` and verify:
- Default theme behavior
- Theme persistence
- Theme restoration
- Toggle functionality
- Document class application

Run tests with:
```bash
npm test
```

## Architecture Notes

- **Storage Key**: `p2u-theme`
- **Default Theme**: `dark`
- **Valid Values**: `'dark' | 'light'`
- **Persistence**: localStorage
- **SSR Handling**: Component doesn't render until mounted to prevent hydration mismatch
