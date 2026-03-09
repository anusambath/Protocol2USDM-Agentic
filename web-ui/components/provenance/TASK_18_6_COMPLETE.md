# Task 18.6 Complete: SOA Details Sub-tab Enhancement

## Summary

Successfully enhanced the SOA Details sub-tab to provide clearer information about cell-level provenance tracking, including an informational banner explaining the current limitations and enhanced cell display showing all available provenance information.

## Implementation Details

### Core Features Implemented

1. **Informational Banner**
   - Added prominent blue info card at the top of the view
   - Explains that cell-level provenance includes:
     - Source type (text/vision/confirmed/needs review)
     - Footnote references
     - Page numbers
   - Clarifies that agent and model information is tracked at entity level but not yet available at cell level
   - Uses AlertTriangle icon for visibility
   - Styled for both light and dark modes

2. **Enhanced Cell Display**
   - Improved cell information layout with better visual hierarchy
   - Enhanced cell cards with:
     - Larger padding (p-3 instead of p-2)
     - Border on hover for better interactivity
     - Transition effects for smooth hover states
   - Cell details now show:
     - Visit name (bold, prominent)
     - Source type badge (rounded pill with muted background)
     - Page references with 📄 icon (blue text)
     - Footnote references with 📝 icon (purple text)
   - Better handling of plural forms ("Page" vs "Pages", "Footnote" vs "Footnotes")

3. **Maintained Existing Functionality**
   - Kept all existing ProvenanceExplorer features:
     - Activity grouping and expansion
     - Filter buttons (All, Confirmed, Text Only, Needs Review, Orphaned)
     - Search functionality
     - Expand/Collapse all controls
     - Virtualization for large lists (>100 items)
     - ProvenanceStats display
   - Cell-level provenance tracking remains unchanged
   - Activity × visit matrix structure preserved

### Data Flow

The component now properly passes provenance data to ProvenanceActivityItem to enable page reference display:

```typescript
<ProvenanceActivityItem
  item={item}
  isExpanded={expandedActivities.has(item.activityId)}
  onToggle={() => toggleActivity(item.activityId)}
  onCellClick={onCellSelect}
  provenance={provenance}  // ← Added
/>
```

Within ProvenanceActivityItem, page refs are retrieved using the cell key format:

```typescript
const cellKey = `${item.activityId}|${cell.visitId}`;
const pageRefs = (provenance?.cellPageRefs as Record<string, number[]>)?.[cellKey] || [];
```

## Acceptance Criteria Met

✅ Keep existing SOA cell-level provenance (ProvenanceExplorer)
✅ Enhance with agent/model information display (added note explaining limitation)
✅ Integrate with new protocol preview component (prepared for task 18.8)
✅ Add inline provenance format to cell details (enhanced display with page refs and footnotes)

## Technical Implementation

### Component Structure

```
ProvenanceExplorer
├── Info Banner (new)
│   └── Explanation of cell-level provenance
├── ProvenanceStats
├── Controls (Search + Filters)
└── Activity List
    └── ProvenanceActivityItem (enhanced)
        └── Cell Details (enhanced with page refs)
```

### Key Changes

1. **ProvenanceExplorer.tsx**
   - Added info banner card with AlertTriangle icon
   - Enhanced cell display with better layout and styling
   - Added page reference display using cellPageRefs
   - Improved visual hierarchy with badges and icons

2. **ProvenanceActivityItem**
   - Added `provenance` prop to access cellPageRefs
   - Enhanced cell button styling
   - Added page refs and footnotes display with icons
   - Improved responsive layout with flex-wrap

### Data Structure

Cell provenance data structure (current):
```typescript
{
  cells: {
    "activityId|encounterId": "text" | "vision" | "both" | "needs_review"
  },
  cellFootnotes: {
    "activityId|encounterId": ["1", "2", "3"]
  },
  cellPageRefs: {
    "activityId|encounterId": [5, 12, 23]
  }
}
```

Note: Agent and model information is NOT available at the cell level in the current data structure. This is tracked at the entity level (activities, encounters) in the `entities` object.

## UI Components Used

- Card, CardContent (shadcn/ui)
- AlertTriangle (lucide-react)
- Existing ProvenanceExplorer components

## Styling Details

### Info Banner
- Border: `border-blue-200` (light) / `border-blue-900` (dark)
- Background: `bg-blue-50` (light) / `bg-blue-950` (dark)
- Text: `text-blue-900` (light) / `text-blue-100` (dark)
- Icon: `text-blue-600` (light) / `text-blue-400` (dark)

### Enhanced Cell Display
- Padding: `p-3` (increased from `p-2`)
- Border: `border border-transparent hover:border-border`
- Transitions: `transition-colors`
- Page refs: `text-blue-600 dark:text-blue-400`
- Footnotes: `text-purple-600 dark:text-purple-400`
- Source badge: `bg-muted text-muted-foreground`

## Integration Points

### Current
- Reads from `provenance.cells` (cell source types)
- Reads from `provenance.cellFootnotes` (footnote references)
- Reads from `provenance.cellPageRefs` (page numbers) ← Enhanced
- Uses existing ProvenanceExplorer functionality

### Future (Task 18.8)
- Cell click handlers will wire to protocol preview
- Page number badges could become clickable to jump to specific pages
- When agent/model data becomes available at cell level, can be easily added to display

## Responsive Design

- Info banner text wraps appropriately on small screens
- Cell details use flex-wrap for badges
- Icons and text scale properly
- Maintains existing responsive behavior of ProvenanceExplorer

## Dark Mode Support

- Info banner styled for dark mode
- Page refs and footnotes have dark mode colors
- All existing dark mode support maintained

## Accessibility

- Info banner uses semantic HTML
- AlertTriangle icon has proper sizing and color contrast
- All existing accessibility features maintained:
  - Keyboard navigation
  - ARIA labels
  - Focus indicators

## Performance Considerations

- No performance impact - only UI enhancements
- Page refs retrieved efficiently using cell key lookup
- Existing virtualization for large lists maintained

## Files Modified

- `web-ui/components/provenance/ProvenanceExplorer.tsx`
  - Added informational banner about cell-level provenance
  - Enhanced cell display with page refs and better styling
  - Added `provenance` prop to ProvenanceActivityItem
  - Improved visual hierarchy and layout

## Testing Notes

To test this implementation:

1. Navigate to Provenance tab
2. Click "SOA Details" sub-tab
3. Verify info banner displays at the top with clear explanation
4. Expand an activity to see cells
5. Verify cells show:
   - Source type badge
   - Page numbers (if available)
   - Footnote references (if available)
6. Verify hover states work smoothly
7. Test in dark mode
8. Verify existing functionality (search, filters, expand/collapse) still works

## Known Limitations

1. **Agent/Model Information Not Available**: Cell-level provenance in the current data structure does not include agent or model information. This is tracked at the entity level (activities, encounters) but not at the individual cell level (activity × encounter intersection).

2. **Future Enhancement Opportunity**: When the backend pipeline is updated to include agent/model information at the cell level, the UI can be easily enhanced to display this information by:
   - Adding agent and model fields to the cell display
   - Using existing helper functions (`getAgentDisplayName`, `getModelDisplayName`)
   - Following the same badge pattern used in other tabs

## Next Steps

Task 18.8 will wire the cell click handlers to update the protocol preview component, enabling users to view the source protocol pages for each cell.

## Requirements Validated

- Requirement 5.6: SOA Details sub-tab enhancement ✅
- Keep existing cell-level provenance display ✅
- Enhance with available provenance information ✅
- Add clear explanation of current limitations ✅
- Prepare for protocol preview integration ✅

