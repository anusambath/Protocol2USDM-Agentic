# ThemeProvider Integration Guide

This guide shows how to integrate the ThemeProvider into the Protocol2USDM application.

## Step 1: Update Providers

Modify `app/providers.tsx` to include the ThemeProvider:

```tsx
'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';
import { ThemeProvider } from '@/components/theme';

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000, // 1 minute
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        {children}
      </ThemeProvider>
    </QueryClientProvider>
  );
}
```

## Step 2: Verify Layout Configuration

Ensure `app/layout.tsx` has `suppressHydrationWarning` on both `<html>` and `<body>` tags:

```tsx
export default function RootLayout({ children }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className} suppressHydrationWarning>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

✅ This is already configured correctly in the current layout.

## Step 3: Add Theme Toggle to UI

Add the ThemeToggle component to your Status Bar or any other location:

```tsx
import { ThemeToggle } from '@/components/theme';

export function StatusBar() {
  return (
    <div className="status-bar">
      {/* Other status bar content */}
      <ThemeToggle />
    </div>
  );
}
```

## Step 4: Use Theme in Components

Any component can access the theme using the `useTheme` hook:

```tsx
import { useTheme } from '@/hooks/useTheme';

export function MyComponent() {
  const { theme, toggleTheme } = useTheme();
  
  return (
    <div>
      <p>Current theme: {theme}</p>
      <button onClick={toggleTheme}>Toggle</button>
    </div>
  );
}
```

## Step 5: Verify CSS Variables

The theme system uses CSS variables from `app/globals.css`. Ensure all components use Tailwind utilities that reference these variables:

✅ Already configured:
- `:root` - Light mode variables
- `.dark` - Dark mode variables

## Step 6: Test the Integration

1. Start the development server: `npm run dev`
2. Open the application in a browser
3. Verify the default theme is dark
4. Click the theme toggle button
5. Verify the theme switches to light
6. Refresh the page
7. Verify the theme persists (stays light)
8. Check localStorage in DevTools - should see `p2u-theme: "light"`

## AG Grid Integration

AG Grid will automatically use the theme CSS variables. No additional configuration needed.

The existing CSS in `globals.css` already has AG Grid theme overrides:

```css
.ag-theme-alpine {
  --ag-header-background-color: hsl(var(--muted));
  --ag-odd-row-background-color: hsl(var(--background));
  --ag-row-hover-color: hsl(var(--accent));
}
```

## Cytoscape Integration

For Cytoscape, you'll need to update the styles when the theme changes. Example:

```tsx
import { useTheme } from '@/hooks/useTheme';
import { useEffect } from 'react';

export function TimelineView() {
  const { theme } = useTheme();
  const cyRef = useRef<cytoscape.Core | null>(null);
  
  useEffect(() => {
    if (cyRef.current) {
      // Apply theme-specific styles
      const styles = theme === 'dark' ? getDarkStyles() : getLightStyles();
      cyRef.current.style().fromJson(styles).update();
    }
  }, [theme]);
  
  // ... rest of component
}
```

## Command Palette Integration

Add theme toggle as a command in the Command Palette:

```tsx
const commands = [
  // ... other commands
  {
    id: 'toggle-theme',
    label: 'Toggle Theme',
    category: 'action',
    icon: 'Palette',
    execute: () => toggleTheme(),
  },
];
```

## Troubleshooting

### Flash of Unstyled Content (FOUC)

If you see a flash of light theme before dark theme loads:

1. Verify `suppressHydrationWarning` is on `<html>` and `<body>`
2. Ensure ThemeProvider returns `null` until mounted
3. Check that localStorage is being read in the initial useEffect

### Theme Not Persisting

If theme doesn't persist across page reloads:

1. Check browser DevTools → Application → Local Storage
2. Verify `p2u-theme` key exists
3. Check for localStorage quota errors in console
4. Ensure localStorage is not disabled in browser settings

### Theme Not Applying to Components

If some components don't respond to theme changes:

1. Verify they use Tailwind utilities (not hardcoded colors)
2. Check that CSS variables are defined in globals.css
3. Ensure components are within the ThemeProvider tree
4. For third-party components, check if they need manual theme updates

## Next Steps

After integration:

1. Add ThemeToggle to the Status Bar (Task 1.8)
2. Add theme toggle command to Command Palette (Task 1.9)
3. Update Cytoscape styles to be theme-aware (Task 2.x)
4. Test theme changes across all views
5. Verify accessibility (contrast ratios in both themes)
