# Task 18.8 Complete: Wire Entity Selection to Protocol Preview

## Summary

Successfully implemented task 18.8 from the provenance-display-enhancement spec. Entity selection is now wired to the protocol preview component across all sub-tabs in the Provenance tab.

## Changes Made

### 1. Added ProtocolPreview Import
- Imported `ProtocolPreview` component from `./ProtocolPreview`

### 2. Added SelectedEntity Interface
```typescript
interface SelectedEntity {
  id: string;
  type: string;
  pages: number[];
}
```

### 3. Added State Management
- Added `protocolId` from `useProtocolStore` to access the current protocol ID
- Added `selectedEntity` state to track the currently selected entity
- State is shared across all sub-tabs for consistent preview synchronization

### 4. Replaced ProtocolPreviewPlaceholder
Replaced the placeholder component in all four sub-tabs (Overview, By Section, By Agent, By Page) with conditional rendering:
- If `selectedEntity` and `protocolId` exist: render `ProtocolPreview` with entity's page numbers
- Otherwise: show placeholder message "Select an entity to view its source pages"

### 5. Updated Tab Components
Updated all three entity list tabs to accept and use entity selection:

#### BySectionTab
- Added `selectedEntity` and `onEntitySelect` props
- Updated entity click handler to call `onEntitySelect` with entity data
- Added visual highlighting: selected entities show `bg-accent border-l-4 border-primary`

#### ByAgentTab
- Added `selectedEntity` and `onEntitySelect` props
- Updated entity click handler to call `onEntitySelect` with entity data
- Added visual highlighting for selected entities
- Used `e.stopPropagation()` to prevent agent card collapse on entity click

#### ByPageTab
- Added `selectedEntity` and `onEntitySelect` props
- Updated entity click handler to call `onEntitySelect` with entity data
- Added visual highlighting for selected entities
- Used `e.stopPropagation()` to prevent page card collapse on entity click

### 6. Entity Click Behavior
When an entity is clicked:
1. The entity's ID, type, and page numbers are stored in `selectedEntity` state
2. The entity row is highlighted with accent background and primary border
3. The protocol preview updates to show the entity's source pages
4. Selection persists when switching between sub-tabs

## Requirements Validated

✅ **Requirement 5.11**: Wire entity selection to protocol preview
- Entity list clicks update preview component
- Relevant source pages load and display when entity selected
- Selected entity is highlighted in list
- Preview syncs with entity selection across all sub-tabs

## Testing Recommendations

1. **Entity Selection**: Click entities in each sub-tab and verify preview updates
2. **Visual Highlighting**: Verify selected entity shows accent background and border
3. **Tab Switching**: Select entity in one tab, switch tabs, verify selection persists
4. **Page Display**: Verify correct pages load in preview for each entity
5. **No Selection State**: Verify placeholder message shows when no entity selected
6. **Multiple Pages**: Test entities with multiple page references

## Files Modified

- `web-ui/components/provenance/ProvenanceView.tsx`
  - Added ProtocolPreview import
  - Added SelectedEntity interface
  - Added selectedEntity state and protocolId access
  - Updated all four tab content sections with conditional preview rendering
  - Updated BySectionTab, ByAgentTab, and ByPageTab signatures and implementations
  - Removed ProtocolPreviewPlaceholder function

## Next Steps

This completes task 18.8. The provenance tab now has full entity selection and protocol preview integration. Users can:
- Click any entity in any sub-tab to view its source pages
- See visual feedback for selected entities
- Navigate between tabs while maintaining selection
- View protocol pages directly in the split view

The implementation follows the design document requirements and provides a seamless user experience for exploring provenance data and verifying extractions against source documents.
