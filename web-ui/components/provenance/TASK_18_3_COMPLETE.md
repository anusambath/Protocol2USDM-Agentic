# Task 18.3 Complete: By Section Sub-tab Implementation

## Summary

Implemented the **By Section** sub-tab in the Provenance tab with full functionality for grouping, filtering, and displaying entity provenance data.

## Implementation Details

### 1. Component Structure

**File**: `web-ui/components/provenance/ProvenanceView.tsx`

The `BySectionTab` component replaces the placeholder with a complete implementation that:
- Groups entities by logical sections (Study Metadata, Eligibility Criteria, etc.)
- Displays entity counts per section
- Provides expand/collapse functionality for sections
- Shows detailed entity information
- Includes search and filtering capabilities

### 2. Section Mappings

Entities are grouped into the following sections:

- **Study Metadata**: study_title, study_identifier, study_phase, organization, etc.
- **Eligibility Criteria**: eligibility_criterion, inclusion_criterion, exclusion_criterion
- **Objectives & Endpoints**: objective, endpoint
- **Study Design**: study_design, epoch, arm, population
- **Interventions**: study_intervention, intervention
- **Procedures & Devices**: procedure, medical_device
- **Advanced Entities**: indication, biomedical_concept, estimand, analysis_population
- **Narrative**: narrative_content
- **SOA**: activities, encounters, plannedTimepoints

### 3. Features Implemented

#### Entity Grouping
- Automatically groups entities by their type into logical sections
- Displays entity count badge for each section
- Shows total entity count across all sections

#### Expand/Collapse
- Sections are collapsed by default
- Click section header to expand/collapse
- Chevron icon rotates to indicate state
- Smooth transitions with hover effects

#### Entity Display
Each entity shows:
- **ID**: Entity identifier
- **Type**: Entity type badge
- **Agent**: Display name of the agent that extracted it
- **Model**: Display name of the model used (Gemini 2.5 Flash, Claude Opus 4, etc.)
- **Pages**: Page references in readable format
- **Confidence**: Percentage with color-coded badge (High/Medium/Low)
- **Source**: Source type label (Text Only, Vision Only, Confirmed, Derived)

#### Search Functionality
- Real-time search across entity IDs, types, and agent names
- Case-insensitive matching
- Filters sections to show only matching entities
- Shows "no entities match" message when no results

#### Confidence Filter
- Filter by confidence level:
  - **All Confidence**: Show all entities
  - **High (>75%)**: Show only high-confidence entities
  - **Medium (50-75%)**: Show only medium-confidence entities
  - **Low (<50%)**: Show only low-confidence entities

#### Source Type Filter
- Filter by source type:
  - **All Sources**: Show all entities
  - **Text Only**: Show only text-extracted entities
  - **Vision Only**: Show only vision-extracted entities
  - **Both**: Show only entities extracted by both methods
  - **Derived**: Show only derived entities

#### Entity Click Handler
- Clicking an entity logs it to console (placeholder for task 18.8)
- Will be wired to protocol preview in future task

### 4. UI Components Created

#### Input Component
**File**: `web-ui/components/ui/input.tsx`

Standard input component with:
- Consistent styling with design system
- Focus states and ring effects
- Placeholder text support
- Disabled state support

#### Select Component
**File**: `web-ui/components/ui/select.tsx`

Radix UI-based select component with:
- Dropdown menu with options
- Check indicator for selected item
- Keyboard navigation support
- Smooth animations
- Portal rendering for proper z-index

### 5. Dependencies Added

```json
{
  "@radix-ui/react-select": "^2.2.6"
}
```

### 6. Empty States

The component handles empty states gracefully:
- Shows message when no entity provenance data is available
- Shows message when search/filters return no results
- Provides helpful context about why data might be missing

### 7. Styling

- Uses Tailwind CSS for consistent styling
- Follows existing design system patterns
- Responsive layout with proper spacing
- Hover states for interactive elements
- Color-coded confidence badges:
  - High: Default variant (primary color)
  - Medium: Secondary variant
  - Low: Destructive variant (red)

### 8. Data Flow

```
ProvenanceData (from props)
  ↓
Extract entities from provenance.entities
  ↓
Group by section using SECTION_MAPPINGS
  ↓
Apply search filter (if query exists)
  ↓
Apply confidence filter (if selected)
  ↓
Apply source type filter (if selected)
  ↓
Render sections with entity lists
```

### 9. Helper Functions Used

From `web-ui/lib/provenance/types.ts`:
- `getAgentDisplayName()`: Formats agent ID to display name
- `getModelDisplayName()`: Formats model string to display name
- `formatPageRefs()`: Formats page array to readable string
- `formatConfidence()`: Formats confidence to percentage
- `getConfidenceLevel()`: Determines confidence level (high/medium/low)
- `getSourceTypeLabel()`: Gets display label for source type

## Testing

### Manual Testing Checklist

- [x] Component renders without errors
- [x] Sections are grouped correctly
- [x] Entity counts are displayed
- [x] Expand/collapse works
- [x] Search filters entities correctly
- [x] Confidence filter works
- [x] Source type filter works
- [x] Entity details are displayed correctly
- [x] Empty states show appropriate messages
- [x] Hover states work
- [x] TypeScript compiles without errors

### Test Data Requirements

To test this component, provenance data must include:
```typescript
{
  entities: {
    metadata: {
      'entity-id': {
        source: 'text' | 'vision' | 'both' | 'derived',
        agent: 'agent_name',
        model: 'model-name',
        confidence: 0.95,
        pageRefs: [1, 2, 3],
        timestamp: '2024-01-01T00:00:00Z'
      }
    },
    // ... other entity types
  }
}
```

## Requirements Validated

**Requirement 5.3**: By Section sub-tab
- ✅ Groups entities by tab/section
- ✅ Displays entity count per section
- ✅ Sections are expandable/collapsible
- ✅ Shows entity details (ID, type, agent, model, pages, confidence)
- ✅ Entity click handler (placeholder for task 18.8)
- ✅ Filter and search within sections

## Next Steps

**Task 18.8**: Wire entity click to protocol preview
- Update entity click handler to open protocol preview
- Pass selected entity to sidebar
- Display source pages in preview pane

## Files Modified

1. `web-ui/components/provenance/ProvenanceView.tsx`
   - Replaced `BySectionTab` placeholder with full implementation
   - Added imports for new UI components and helper functions
   - Added section mappings constant
   - Added entity grouping logic
   - Added search and filter functionality

2. `web-ui/components/ui/input.tsx` (created)
   - Standard input component

3. `web-ui/components/ui/select.tsx` (created)
   - Radix UI-based select component

4. `web-ui/components/provenance/__tests__/provenance-view-tabs.test.tsx`
   - Updated tests to reflect new implementation
   - Changed expected text from "coming soon" to "no entity provenance data"

5. `web-ui/package.json`
   - Added @radix-ui/react-select dependency

## Screenshots/Demo

To see the component in action:
1. Navigate to a protocol with provenance data
2. Click on the "Provenance" tab
3. Click on the "By Section" sub-tab
4. Expand sections to see entities
5. Use search and filters to narrow down results

## Notes

- The component uses the extended provenance format with `entities` object
- If provenance data doesn't include the `entities` field, an empty state is shown
- Entity click currently logs to console; will be wired to preview in task 18.8
- All TypeScript types are properly defined and validated
- Component follows existing patterns from other provenance components
