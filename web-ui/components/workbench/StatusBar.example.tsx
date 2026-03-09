"use client"

import * as React from "react"
import { StatusBar } from "./StatusBar"

export default function StatusBarExample() {
  const [isDirty, setIsDirty] = React.useState(false)
  const [overlayStatus, setOverlayStatus] = React.useState<'draft' | 'published'>('draft')
  const [validationCount, setValidationCount] = React.useState(3)

  const handleSaveDraft = () => {
    console.log('Save Draft clicked')
    setIsDirty(false)
    alert('Draft saved!')
  }

  const handlePublish = () => {
    console.log('Publish clicked')
    const confirmed = confirm('Are you sure you want to publish?')
    if (confirmed) {
      setOverlayStatus('published')
      setIsDirty(false)
      alert('Published successfully!')
    }
  }

  const handleReset = () => {
    console.log('Reset clicked')
    const confirmed = confirm('Are you sure you want to reset to published version?')
    if (confirmed) {
      setIsDirty(false)
      alert('Reset to published version!')
    }
  }

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-4xl mx-auto space-y-8">
        <div>
          <h1 className="text-3xl font-bold mb-2">StatusBar Component Examples</h1>
          <p className="text-muted-foreground">
            The StatusBar displays protocol metadata, overlay status, and draft/publish actions.
          </p>
        </div>

        {/* Controls */}
        <div className="border rounded-lg p-6 space-y-4">
          <h2 className="text-xl font-semibold">Interactive Controls</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">
                Dirty State
              </label>
              <button
                onClick={() => setIsDirty(!isDirty)}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
              >
                Toggle Dirty: {isDirty ? 'Yes' : 'No'}
              </button>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">
                Overlay Status
              </label>
              <button
                onClick={() => setOverlayStatus(overlayStatus === 'draft' ? 'published' : 'draft')}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
              >
                Toggle Status: {overlayStatus}
              </button>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">
                Validation Issues
              </label>
              <div className="flex gap-2">
                <button
                  onClick={() => setValidationCount(Math.max(0, validationCount - 1))}
                  className="px-3 py-2 bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/80"
                >
                  -
                </button>
                <span className="px-4 py-2 border rounded-md">{validationCount}</span>
                <button
                  onClick={() => setValidationCount(validationCount + 1)}
                  className="px-3 py-2 bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/80"
                >
                  +
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Example 1: Draft with unsaved changes */}
        <div className="border rounded-lg p-6 space-y-4">
          <h2 className="text-xl font-semibold">Example 1: Draft with Unsaved Changes</h2>
          <p className="text-sm text-muted-foreground">
            Shows orange draft badge, pulsing dirty indicator, and validation issues.
          </p>
          <div className="relative h-32 border rounded-md bg-muted/20">
            <StatusBar
              protocolId="PROTO-2024-001"
              usdmVersion="3.0.0"
              isDirty={true}
              overlayStatus="draft"
              validationIssueCount={3}
              onSaveDraft={() => alert('Save Draft')}
              onPublish={() => alert('Publish')}
              onResetToPublished={() => alert('Reset')}
            />
          </div>
        </div>

        {/* Example 2: Published with no changes */}
        <div className="border rounded-lg p-6 space-y-4">
          <h2 className="text-xl font-semibold">Example 2: Published with No Changes</h2>
          <p className="text-sm text-muted-foreground">
            Shows green published badge, no dirty indicator, Save Draft button disabled.
          </p>
          <div className="relative h-32 border rounded-md bg-muted/20">
            <StatusBar
              protocolId="PROTO-2024-002"
              usdmVersion="3.0.1"
              isDirty={false}
              overlayStatus="published"
              validationIssueCount={0}
              onSaveDraft={() => alert('Save Draft')}
              onPublish={() => alert('Publish')}
              onResetToPublished={() => alert('Reset')}
            />
          </div>
        </div>

        {/* Example 3: No USDM version */}
        <div className="border rounded-lg p-6 space-y-4">
          <h2 className="text-xl font-semibold">Example 3: No USDM Version</h2>
          <p className="text-sm text-muted-foreground">
            Shows protocol ID only, without USDM version.
          </p>
          <div className="relative h-32 border rounded-md bg-muted/20">
            <StatusBar
              protocolId="PROTO-2024-003"
              usdmVersion={undefined}
              isDirty={false}
              overlayStatus="draft"
              validationIssueCount={0}
              onSaveDraft={() => alert('Save Draft')}
              onPublish={() => alert('Publish')}
              onResetToPublished={() => alert('Reset')}
            />
          </div>
        </div>

        {/* Example 4: Interactive (current state) */}
        <div className="border rounded-lg p-6 space-y-4">
          <h2 className="text-xl font-semibold">Example 4: Interactive Demo</h2>
          <p className="text-sm text-muted-foreground">
            Use the controls above to change the state. Try clicking the action buttons!
          </p>
          <div className="relative h-32 border rounded-md bg-muted/20">
            <StatusBar
              protocolId="PROTO-2024-INTERACTIVE"
              usdmVersion="3.0.2"
              isDirty={isDirty}
              overlayStatus={overlayStatus}
              validationIssueCount={validationCount}
              onSaveDraft={handleSaveDraft}
              onPublish={handlePublish}
              onResetToPublished={handleReset}
            />
          </div>
        </div>

        {/* Visual Guide */}
        <div className="border rounded-lg p-6 space-y-4">
          <h2 className="text-xl font-semibold">Visual Guide</h2>
          <div className="space-y-2 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-16 h-6 bg-green-600 rounded-full flex items-center justify-center text-white text-xs">
                Published
              </div>
              <span>Green badge indicates published status</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-16 h-6 bg-orange-500 rounded-full flex items-center justify-center text-white text-xs">
                Draft
              </div>
              <span>Orange badge indicates draft status</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-orange-500 animate-pulse" />
              <span>Orange pulsing dot indicates unsaved changes</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-destructive">⚠ 3</span>
              <span>Red alert icon shows validation issue count (hover for details)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
