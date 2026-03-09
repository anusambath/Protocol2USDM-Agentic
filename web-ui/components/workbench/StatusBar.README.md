# StatusBar Component

A fixed status bar component that displays protocol metadata, overlay status, and draft/publish actions at the bottom of the viewport.

## Features

- Fixed 32px height bar at viewport bottom
- Protocol ID and USDM version display
- Overlay status badge (draft/published) with color coding
- Dirty indicator with pulse animation for unsaved changes
- Validation issue count with hover tooltip
- Draft/publish action buttons (Save Draft, Publish, Reset)

## Usage

```tsx
import { StatusBar } from '@/components/workbench/StatusBar'

function MyWorkbench() {
  const handleSaveDraft = () => {
    // Save draft logic
  }

  const handlePublish = () => {
    // Publish logic
  }

  const handleReset = () => {
    // Reset to published logic
  }

  return (
    <StatusBar
      protocolId="PROTO-001"
      usdmVersion="3.0.0"
      isDirty={true}
      overlayStatus="draft"
      validationIssueCount={3}
      onSaveDraft={handleSaveDraft}
      onPublish={handlePublish}
      onResetToPublished={handleReset}
    />
  )
}
```

## Props

### `protocolId` (required)
- Type: `string`
- Description: The protocol identifier to display

### `usdmVersion` (optional)
- Type: `string | undefined`
- Description: The USDM version number to display

### `isDirty` (required)
- Type: `boolean`
- Description: Whether there are unsaved changes in the draft overlay

### `overlayStatus` (required)
- Type: `'draft' | 'published'`
- Description: The current overlay status
- Visual: Green badge for published, orange badge for draft

### `validationIssueCount` (required)
- Type: `number`
- Description: The number of validation issues found
- Visual: Red alert icon with count, shows tooltip on hover

### `onSaveDraft` (required)
- Type: `() => void`
- Description: Callback when Save Draft button is clicked
- Note: Button is disabled when `isDirty` is false

### `onPublish` (required)
- Type: `() => void`
- Description: Callback when Publish button is clicked

### `onResetToPublished` (required)
- Type: `() => void`
- Description: Callback when Reset button is clicked
- Note: Button is disabled when status is published and not dirty

## Visual Design

### Layout
```
┌─────────────────────────────────────────────────────────────────┐
│ PROTO-001 | USDM 3.0.0 | [Draft] | ● Unsaved | ⚠ 3  [Actions] │
└─────────────────────────────────────────────────────────────────┘
```

### Color Coding
- Published badge: Green (`bg-green-600`)
- Draft badge: Orange (`bg-orange-500`)
- Dirty indicator: Orange dot with pulse animation
- Validation issues: Red alert icon

### Tooltips
- Dirty indicator: "You have unsaved changes in the draft overlay"
- Validation count: Shows issue breakdown and hint to view in Quality panel

## Accessibility

- Uses semantic `<footer>` element with `role="contentinfo"`
- Includes `aria-label` for screen readers
- Validation count button has descriptive `aria-label`
- All interactive elements are keyboard accessible
- Tooltips provide additional context

## Integration with Overlay Store

The StatusBar is designed to work with the `overlayStore`:

```tsx
import { useOverlayStore } from '@/stores/overlayStore'

function WorkbenchWithStatusBar() {
  const { isDirty, draft } = useOverlayStore()
  const overlayStatus = draft?.status ?? 'draft'

  return (
    <StatusBar
      protocolId="PROTO-001"
      usdmVersion="3.0.0"
      isDirty={isDirty}
      overlayStatus={overlayStatus}
      validationIssueCount={0}
      onSaveDraft={() => {
        // Call API to save draft
        useOverlayStore.getState().markClean()
      }}
      onPublish={() => {
        // Call API to publish
        useOverlayStore.getState().promoteDraftToPublished()
      }}
      onResetToPublished={() => {
        useOverlayStore.getState().resetToPublished()
      }}
    />
  )
}
```

## Requirements Validated

This component validates the following requirements from the Web UI Redesign spec:

- **8.1**: Displays protocol ID and USDM version
- **8.2**: Displays overlay status (Draft/Published)
- **8.3**: Displays dirty indicator when overlay is modified
- **8.4**: Displays validation issue count
- **8.5**: Shows tooltip on hover over validation count
- **8.6**: Remains fixed at bottom of viewport

## Related Components

- `Badge` - Used for status display
- `Button` - Used for action buttons
- `Tooltip` - Used for hover information
- `overlayStore` - Provides draft/publish state
