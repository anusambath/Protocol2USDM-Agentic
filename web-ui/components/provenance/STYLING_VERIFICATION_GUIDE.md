# Provenance Component Styling Verification Guide

## Quick Visual Checklist

This guide helps verify that all styling changes are correctly applied and consistent across components.

## 1. ProvenanceSidebar

### Visual Checks
- [ ] **Background:** Sidebar uses white background in light mode, dark background in dark mode (matches main app)
- [ ] **Border:** Left border is subtle and matches other panel borders
- [ ] **Header:** Header has card background with proper border-bottom
- [ ] **Pin Button:** 
  - Unpinned: Gray icon with hover effect
  - Pinned: Blue icon with blue background tint
- [ ] **Close Button:** Gray X with hover effect
- [ ] **Divider:** Horizontal divider between sections, turns blue on hover
- [ ] **Animation:** Sidebar slides in from right smoothly (200ms)

### Color Tokens to Verify
```tsx
// Sidebar container
className="bg-background border-l border-border"

// Header
className="bg-card border-b border-border"

// Pin button (pinned)
className="text-primary bg-primary/10 hover:bg-primary/20"

// Pin button (unpinned)
className="text-muted-foreground hover:bg-accent"

// Divider
className="bg-border hover:bg-primary"
```

## 2. ProvenanceDetails

### Visual Checks
- [ ] **Labels:** All field labels are uppercase, small, and muted gray
- [ ] **Values:** All field values are readable foreground color
- [ ] **Entity Header:** Clear separation with border-bottom
- [ ] **Confidence Bar:**
  - Background is muted gray
  - Fill color matches confidence level (green/yellow/red)
  - Animates smoothly when changing
- [ ] **Page Badges:**
  - Blue background with darker blue text
  - Hover effect shows darker background
  - Subtle shadow on hover
- [ ] **Missing Data:** Shows "Not available" in muted gray, not error red

### Color Tokens to Verify
```tsx
// Labels
className="text-xs text-muted-foreground uppercase tracking-wide"

// Values
className="text-sm text-foreground"

// Page badges
className="text-primary bg-primary/10 hover:bg-primary/20"

// Confidence bar background
className="bg-muted"

// Confidence bar fill
className="bg-green-500 transition-all duration-300 ease-in-out"
```

## 3. ProtocolPreview

### Visual Checks
- [ ] **Background:** Subtle muted background (not stark white/black)
- [ ] **Controls Bar:** Card background with border
- [ ] **Buttons:**
  - Secondary background (light gray in light mode)
  - Hover effect darkens slightly
  - Disabled buttons are faded
- [ ] **Page Info:** Muted text color for page numbers
- [ ] **Loading Skeleton:** Animated pulse with muted background
- [ ] **Error States:**
  - Red text for error messages
  - Red button for retry
  - Appropriate icon for error type
- [ ] **Image:** Smooth zoom transition (200ms)

### Color Tokens to Verify
```tsx
// Container
className="bg-muted"

// Controls bar
className="bg-card border-b border-border"

// Buttons
className="bg-secondary hover:bg-secondary/80"

// Page info
className="text-muted-foreground"

// Error message
className="text-destructive"
```

## 4. ProvenanceInline

### Visual Checks
- [ ] **Info Icon:** Blue color (primary)
- [ ] **Text:** Clear hierarchy with bold agent name
- [ ] **Separators:** Muted gray bullets between items
- [ ] **Confidence:** Color-coded (green/yellow/red) based on value
- [ ] **Preview Button:**
  - Blue text with border
  - Hover shows light blue background
  - Disabled state is faded
- [ ] **View All Link:** Blue text with underline on hover

### Color Tokens to Verify
```tsx
// Info icon
className="text-primary"

// Agent name
className="font-medium text-foreground"

// Separators
className="text-muted-foreground"

// Preview button
className="text-primary border-border hover:bg-accent"

// View All link
className="text-primary hover:text-primary/80"
```

## 5. ErrorBoundary

### Visual Checks
- [ ] **Container:** Light red background with red border
- [ ] **Title:** Red text with warning emoji
- [ ] **Message:** Slightly lighter red text
- [ ] **Button:** Red background with white text
- [ ] **Hover:** Button darkens on hover

### Color Tokens to Verify
```tsx
// Container
className="bg-destructive/10 border-destructive/20"

// Title
className="text-destructive"

// Message
className="text-destructive/80"

// Button
className="bg-destructive hover:bg-destructive/90"
```

## Animation Verification

### Sidebar Animation
1. Open sidebar by clicking preview button
2. **Expected:** Smooth slide-in from right (200ms)
3. **Check:** No jank, maintains 60fps
4. Close sidebar with Esc or close button
5. **Expected:** Smooth slide-out to right (200ms)

### Button Hover Animations
1. Hover over any button
2. **Expected:** Background color changes smoothly (150ms)
3. **Check:** No abrupt color changes
4. Move mouse away
5. **Expected:** Returns to original state smoothly

### Confidence Bar Animation
1. Navigate between entities with different confidence scores
2. **Expected:** Bar width animates smoothly (300ms)
3. **Check:** No jumpy transitions

### Page Badge Hover
1. Hover over page badge
2. **Expected:** Background darkens and shadow appears (150ms)
3. **Check:** Smooth transition

## Dark Mode Verification

### Toggle Dark Mode
1. Switch to dark mode using system/app toggle
2. **Check all components:**
   - [ ] Backgrounds are dark but not pure black
   - [ ] Text is light but readable
   - [ ] Borders are visible but subtle
   - [ ] Interactive elements (buttons, links) are clearly visible
   - [ ] Hover states work correctly
   - [ ] No hardcoded light colors remain

### Specific Dark Mode Checks
- [ ] **Sidebar:** Dark background, light text
- [ ] **Details:** Labels are muted but readable
- [ ] **Preview:** Controls bar is dark, buttons are visible
- [ ] **Inline:** Info icon is bright blue, text is readable
- [ ] **Errors:** Red colors are adjusted for dark mode

## Spacing Verification

### Consistent Padding
- [ ] **Sidebar header:** 16px padding (p-4)
- [ ] **Details sections:** 16px padding (p-4)
- [ ] **Preview controls:** 12px padding (p-3)
- [ ] **Inline component:** 8px gap (gap-2)

### Consistent Gaps
- [ ] **Details fields:** 16px vertical spacing (space-y-4)
- [ ] **Inline items:** 6px gap (gap-1.5)
- [ ] **Button groups:** 8px gap (gap-2)

## Typography Verification

### Font Sizes
- [ ] **Labels:** 10px (text-xs)
- [ ] **Body text:** 14px (text-sm)
- [ ] **Headers:** 18px (text-lg)

### Font Weights
- [ ] **Labels:** Normal weight
- [ ] **Values:** Normal weight
- [ ] **Entity names:** Medium weight (font-medium)
- [ ] **Headers:** Semibold (font-semibold)

### Text Transforms
- [ ] **Labels:** Uppercase with tracking (uppercase tracking-wide)
- [ ] **Values:** Normal case

## Focus State Verification

### Keyboard Navigation
1. Press Tab to navigate through interactive elements
2. **Check each element:**
   - [ ] Focus ring appears (2px blue ring)
   - [ ] Ring has offset for visibility
   - [ ] Ring color matches design system
   - [ ] Focus order is logical

### Specific Focus Checks
- [ ] **Preview button:** Blue focus ring
- [ ] **Page badges:** Blue focus ring
- [ ] **Sidebar buttons:** Blue focus ring
- [ ] **Protocol controls:** Blue focus ring

## Accessibility Verification

### Color Contrast
- [ ] **Light mode:** All text meets WCAG AA contrast (4.5:1)
- [ ] **Dark mode:** All text meets WCAG AA contrast (4.5:1)
- [ ] **Interactive elements:** Clear visual distinction

### Hover States
- [ ] All interactive elements have visible hover states
- [ ] Hover states don't rely solely on color
- [ ] Cursor changes to pointer for clickable elements

## Common Issues to Watch For

### ❌ Issues to Avoid
1. **Hardcoded colors:** No `text-gray-500` or `bg-blue-600`
2. **Missing transitions:** All state changes should animate
3. **Inconsistent spacing:** Use design system scale
4. **Abrupt animations:** All transitions should be smooth
5. **Poor dark mode:** Colors should adapt, not just invert

### ✅ What Good Looks Like
1. **Semantic tokens:** Uses `text-foreground`, `bg-background`, etc.
2. **Smooth transitions:** 150-300ms with easing functions
3. **Consistent spacing:** 4px, 8px, 12px, 16px scale
4. **Proper hierarchy:** Clear visual distinction between elements
5. **Accessible:** High contrast, clear focus states

## Browser Testing

Test in multiple browsers to ensure consistency:
- [ ] **Chrome:** All animations smooth, colors correct
- [ ] **Firefox:** All animations smooth, colors correct
- [ ] **Safari:** All animations smooth, colors correct
- [ ] **Edge:** All animations smooth, colors correct

## Performance Checks

### Animation Performance
1. Open DevTools Performance tab
2. Record while opening/closing sidebar
3. **Check:** Maintains 60fps (16.67ms per frame)
4. **Check:** No layout thrashing

### Rendering Performance
1. Navigate between different provenance views
2. **Check:** No visible lag or jank
3. **Check:** Smooth scrolling
4. **Check:** Quick hover responses

## Sign-off Checklist

Before marking task complete, verify:
- [ ] All components use design system tokens
- [ ] All animations are smooth with proper easing
- [ ] Dark mode works correctly
- [ ] Spacing is consistent
- [ ] Typography is consistent
- [ ] Focus states are visible
- [ ] Hover states work correctly
- [ ] No console errors
- [ ] No visual regressions
- [ ] Accessibility requirements met

## Notes

- This is a visual verification guide for manual testing
- Automated tests should be added when testing infrastructure is set up
- Report any issues or inconsistencies found during verification
- Take screenshots of any problems for documentation
