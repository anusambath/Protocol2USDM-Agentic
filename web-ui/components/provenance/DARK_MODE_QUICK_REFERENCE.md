# Dark Mode Quick Reference

## Overview
All provenance components support dark mode automatically through semantic design tokens. No additional code is needed when building new components - just use the semantic tokens.

## Semantic Color Tokens

### Background Colors
```tsx
bg-background      // Main page background
bg-card           // Card/panel backgrounds
bg-muted          // Subtle backgrounds (loading skeletons, etc.)
bg-secondary      // Button backgrounds
bg-accent         // Hover backgrounds
```

### Text Colors
```tsx
text-foreground         // Primary text
text-muted-foreground   // Secondary text, labels
text-primary           // Interactive text, links
text-destructive       // Error text
text-card-foreground   // Text on cards
```

### Border Colors
```tsx
border-border     // All borders
```

### Interactive Colors
```tsx
// Buttons
bg-secondary text-foreground hover:bg-secondary/80

// Primary buttons
bg-primary text-primary-foreground hover:bg-primary/90

// Destructive buttons
bg-destructive text-destructive-foreground hover:bg-destructive/90

// Links
text-primary hover:text-primary/80

// Badges
text-primary bg-primary/10 hover:bg-primary/20
```

### Focus States
```tsx
focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2
```

## DO NOT Use

❌ Hardcoded colors:
```tsx
bg-white dark:bg-gray-800           // BAD
text-gray-900 dark:text-gray-100    // BAD
border-gray-200 dark:border-gray-700 // BAD
```

✅ Use semantic tokens instead:
```tsx
bg-background      // GOOD
text-foreground    // GOOD
border-border      // GOOD
```

## Special Cases

### Backdrop (Semi-transparent)
The sidebar backdrop is the only component with an explicit dark variant:
```tsx
bg-black/20 dark:bg-black/40
```

### Confidence Indicators
Color-coded indicators use direct colors (sufficient contrast in both modes):
```tsx
bg-green-500   // High confidence
bg-yellow-500  // Medium confidence
bg-red-500     // Low confidence
```

### Protocol Images
Protocol page images have white backgrounds (rendered by backend) and use:
```tsx
shadow-lg rounded-md  // Provides visibility in dark mode
```

## Testing Dark Mode

### Enable Dark Mode
```javascript
// In browser console
document.documentElement.classList.add('dark')
```

### Disable Dark Mode
```javascript
// In browser console
document.documentElement.classList.remove('dark')
```

### Toggle Dark Mode
```javascript
// In browser console
document.documentElement.classList.toggle('dark')
```

## WCAG AA Contrast Requirements

| Text Type | Minimum Contrast | Our Implementation |
|-----------|------------------|-------------------|
| Normal text (< 18pt) | 4.5:1 | 8.2:1 - 18.5:1 ✅ |
| Large text (≥ 18pt) | 3:1 | 18.5:1 ✅ |
| UI components | 3:1 | 5.2:1+ ✅ |

## Component Checklist

When building new components, ensure:
- [ ] Use semantic tokens for all colors
- [ ] No hardcoded `dark:` variants (except backdrop)
- [ ] Test in both light and dark modes
- [ ] Verify text contrast with DevTools
- [ ] Check hover states in both modes
- [ ] Verify focus indicators are visible

## Resources

- **Test Page:** `web-ui/components/provenance/DARK_MODE_TEST.html`
- **Manual Testing Guide:** `web-ui/components/provenance/TASK_15_2_DARK_MODE_VERIFICATION.md`
- **Automated Tests:** `web-ui/components/provenance/__tests__/dark-mode.test.tsx`
- **CSS Variables:** `web-ui/app/globals.css`

## Common Patterns

### Card with Content
```tsx
<div className="p-4 bg-card border border-border rounded-lg">
  <h3 className="text-lg font-semibold text-foreground">Title</h3>
  <p className="text-sm text-muted-foreground">Description</p>
</div>
```

### Button
```tsx
<button className="px-3 py-1.5 text-sm font-medium text-foreground bg-secondary rounded-md hover:bg-secondary/80 transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-ring">
  Click Me
</button>
```

### Badge
```tsx
<span className="px-2 py-1 text-xs font-medium text-primary bg-primary/10 rounded-md hover:bg-primary/20 transition-all duration-150">
  Badge
</span>
```

### Link
```tsx
<a href="#" className="text-primary hover:text-primary/80 transition-all duration-150">
  Link Text
</a>
```

### Error State
```tsx
<div className="p-4 text-destructive">
  <div className="font-semibold">Error Title</div>
  <div className="text-sm text-destructive/80">Error message</div>
  <button className="mt-2 px-3 py-1.5 text-sm bg-destructive text-destructive-foreground rounded-md hover:bg-destructive/90">
    Retry
  </button>
</div>
```

### Loading Skeleton
```tsx
<div className="animate-pulse bg-muted rounded-md w-full h-32" />
```

## Quick Verification

To verify a component supports dark mode:

1. Open component in browser
2. Open DevTools console
3. Run: `document.documentElement.classList.add('dark')`
4. Check:
   - [ ] All text is readable
   - [ ] Backgrounds change appropriately
   - [ ] Borders are visible
   - [ ] Interactive elements are clear
   - [ ] No white flashes or unstyled content

## Support

For questions or issues with dark mode:
1. Check this quick reference
2. Review `TASK_15_2_DARK_MODE_VERIFICATION.md`
3. Test with `DARK_MODE_TEST.html`
4. Verify CSS variables in `globals.css`
