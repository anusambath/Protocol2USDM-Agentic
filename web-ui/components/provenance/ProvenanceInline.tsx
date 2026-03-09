'use client';

/**
 * ProvenanceInline component
 * 
 * Displays compact provenance information inline with entity data
 * Format: "ℹ️ agent • model • pages • confidence"
 * 
 * Features:
 * - Preview button to open sidebar
 * - "View All" link to navigate to Provenance tab
 * - Hover tooltip with full details
 */

import React from 'react';
import { EntityProvenanceExtended } from '@/lib/provenance/types';
import {
  getAgentDisplayName,
  getModelDisplayName,
  formatPageRefs,
  formatConfidence,
  getConfidenceLevel,
  getSourceTypeLabel,
} from '@/lib/provenance/types';
import { useProvenanceSidebarStore } from '@/lib/stores/provenance-sidebar-store';
import { useLayoutStore } from '@/stores/layoutStore';

interface ProvenanceInlineProps {
  entityType: string;
  entityId: string;
  provenance: EntityProvenanceExtended | null;
  showViewAll?: boolean;
  className?: string;
  protocolAvailable?: boolean;
}

export function ProvenanceInline({
  entityType,
  entityId,
  provenance,
  showViewAll = true,
  protocolAvailable = true,
  className = '',
}: ProvenanceInlineProps) {
  const { open } = useProvenanceSidebarStore();
  const { setRightPanelActiveTab, toggleRightPanel, rightPanelCollapsed } = useLayoutStore();

  // Handle missing provenance data
  if (!provenance) {
    return (
      <div
        className={`flex items-center gap-2 text-sm text-muted-foreground italic ${className}`}
        role="region"
        aria-label="Provenance information"
      >
        <span className="text-muted-foreground" aria-hidden="true">
          ℹ️
        </span>
        <span>No provenance data available</span>
      </div>
    );
  }

  const handlePreviewClick = () => {
    if (!protocolAvailable) {
      console.warn('Protocol file not available for preview');
      return;
    }
    
    open({
      type: entityType,
      id: entityId,
      provenance,
    });
  };

  const handleViewAllClick = () => {
    // Switch to Provenance tab in the right panel
    setRightPanelActiveTab('provenance');
    
    // If right panel is collapsed, expand it
    if (rightPanelCollapsed) {
      toggleRightPanel();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Enter or Space activates the preview button
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handlePreviewClick();
    }
  };

  const agentName = getAgentDisplayName(provenance.agent);
  const modelName = getModelDisplayName(provenance.model);
  const pageRefs = formatPageRefs(provenance.pageRefs);
  const confidence = formatConfidence(provenance.confidence);
  const confidenceLevel = getConfidenceLevel(provenance.confidence);
  const sourceLabel = getSourceTypeLabel(provenance.source);

  // Check if page references are available
  const hasPageRefs = provenance.pageRefs && provenance.pageRefs.length > 0;
  const canPreview = protocolAvailable && hasPageRefs;

  // Confidence color classes
  const confidenceColorClass = {
    high: 'text-green-600 dark:text-green-400',
    medium: 'text-yellow-600 dark:text-yellow-400',
    low: 'text-red-600 dark:text-red-400',
    unknown: 'text-muted-foreground',
  }[confidenceLevel];

  return (
    <div
      className={`flex flex-wrap items-center gap-2 text-sm text-muted-foreground ${className}`}
      role="region"
      aria-label="Provenance information"
    >
      {/* Info icon */}
      <span className="text-primary" aria-hidden="true">
        ℹ️
      </span>

      {/* Compact provenance line */}
      <span className="flex flex-wrap items-center gap-1.5">
        <span className="font-medium text-foreground">{agentName}</span>
        <span className="text-muted-foreground" aria-hidden="true">•</span>
        <span className="text-foreground">{modelName}</span>
        <span className="text-muted-foreground" aria-hidden="true">•</span>
        <span className="text-foreground">{pageRefs}</span>
        {provenance.confidence !== undefined && (
          <>
            <span className="text-muted-foreground" aria-hidden="true">•</span>
            <span className={confidenceColorClass}>{confidence}</span>
          </>
        )}
      </span>

      {/* Preview button */}
      <button
        onClick={handlePreviewClick}
        onKeyDown={handleKeyDown}
        disabled={!canPreview}
        className="ml-2 px-2 py-0.5 text-xs font-medium text-primary hover:text-primary/80 border border-border rounded-md hover:bg-accent transition-all duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-transparent touch-manipulation hover:shadow-sm"
        aria-label={
          !protocolAvailable 
            ? 'Preview not available - protocol file missing'
            : !hasPageRefs
            ? 'Preview not available - no page references'
            : `Preview protocol pages ${pageRefs}`
        }
        title={
          !protocolAvailable 
            ? 'Protocol file not available'
            : !hasPageRefs
            ? 'No page references available'
            : undefined
        }
      >
        🔍 Preview
      </button>

      {/* View All link */}
      {showViewAll && (
        <button
          onClick={handleViewAllClick}
          className="ml-1 text-xs text-primary hover:text-primary/80 hover:underline focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 rounded transition-all duration-150 ease-in-out touch-manipulation"
          aria-label="View all provenance information in Provenance tab"
        >
          View All
        </button>
      )}
    </div>
  );
}
