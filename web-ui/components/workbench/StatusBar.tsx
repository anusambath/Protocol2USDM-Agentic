"use client"

import * as React from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { AlertCircle, Save, Upload, RotateCcw } from "lucide-react"
import { cn } from "@/lib/utils"

export interface StatusBarProps {
  protocolId: string
  usdmVersion: string | undefined
  isDirty: boolean
  overlayStatus: 'draft' | 'published'
  validationIssueCount: number
  onSaveDraft: () => void
  onPublish: () => void
  onResetToPublished: () => void
}

export function StatusBar({
  protocolId,
  usdmVersion,
  isDirty,
  overlayStatus,
  validationIssueCount,
  onSaveDraft,
  onPublish,
  onResetToPublished,
}: StatusBarProps) {
  return (
    <TooltipProvider>
      <footer
        className="fixed bottom-0 left-0 right-0 h-8 border-t bg-muted/40 flex items-center justify-between px-4 text-xs z-40"
        role="contentinfo"
        aria-label="Status Bar"
      >
        {/* Left section: Protocol metadata and status indicators */}
        <div className="flex items-center gap-4">
          {/* Protocol ID */}
          <span className="font-medium text-foreground">
            {protocolId}
          </span>

          {/* USDM Version */}
          {usdmVersion && (
            <>
              <span className="text-muted-foreground">|</span>
              <span className="text-muted-foreground">
                USDM {usdmVersion}
              </span>
            </>
          )}

          {/* Overlay Status Badge */}
          <Badge
            variant={overlayStatus === 'published' ? 'default' : 'secondary'}
            className={cn(
              "text-xs",
              overlayStatus === 'published'
                ? "bg-green-600 hover:bg-green-600/80"
                : "bg-orange-500 hover:bg-orange-500/80"
            )}
          >
            {overlayStatus === 'published' ? 'Published' : 'Draft'}
          </Badge>

          {/* Dirty Indicator */}
          {isDirty && (
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="flex items-center gap-1.5">
                  <div className="w-2 h-2 rounded-full bg-orange-500 animate-pulse" />
                  <span className="text-muted-foreground">Unsaved changes</span>
                </div>
              </TooltipTrigger>
              <TooltipContent>
                <p>You have unsaved changes in the draft overlay</p>
              </TooltipContent>
            </Tooltip>
          )}

          {/* Validation Issue Count */}
          {validationIssueCount > 0 && (
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  className="flex items-center gap-1.5 text-destructive hover:text-destructive/80 transition-colors"
                  aria-label={`${validationIssueCount} validation issues`}
                >
                  <AlertCircle className="w-3.5 h-3.5" />
                  <span className="font-medium">{validationIssueCount}</span>
                </button>
              </TooltipTrigger>
              <TooltipContent>
                <div className="space-y-1">
                  <p className="font-semibold">Validation Issues</p>
                  <p className="text-muted-foreground">
                    {validationIssueCount} issue{validationIssueCount !== 1 ? 's' : ''} found
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Click to view details in the Quality panel
                  </p>
                </div>
              </TooltipContent>
            </Tooltip>
          )}
        </div>

        {/* Right section: Action buttons */}
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={onSaveDraft}
            disabled={!isDirty}
            className="h-6 px-2 text-xs"
          >
            <Save className="w-3 h-3 mr-1.5" />
            Save Draft
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={onPublish}
            className="h-6 px-2 text-xs"
          >
            <Upload className="w-3 h-3 mr-1.5" />
            Publish
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={onResetToPublished}
            disabled={overlayStatus === 'published' && !isDirty}
            className="h-6 px-2 text-xs"
          >
            <RotateCcw className="w-3 h-3 mr-1.5" />
            Reset
          </Button>
        </div>
      </footer>
    </TooltipProvider>
  )
}
