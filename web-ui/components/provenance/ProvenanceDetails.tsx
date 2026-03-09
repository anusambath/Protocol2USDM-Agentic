'use client';

/**
 * ProvenanceDetails component
 * 
 * Displays comprehensive provenance information for an entity
 * 
 * Features:
 * - All provenance fields: agent, model, confidence, source, pages, footnotes, timestamp
 * - Model icon (Gemini/Claude)
 * - Confidence as percentage with visual indicator
 * - Page numbers as clickable badges
 * - Relative timestamp formatting
 * - Graceful handling of missing fields
 */

import React from 'react';
import { EntityProvenanceExtended } from '@/lib/provenance/types';
import {
  getAgentDisplayName,
  getModelDisplayName,
  getModelType,
  formatConfidence,
  getConfidenceLevel,
  formatRelativeTime,
  getSourceTypeLabel,
} from '@/lib/provenance/types';
import { useProvenanceSidebarStore } from '@/lib/stores/provenance-sidebar-store';

interface ProvenanceDetailsProps {
  entityType: string;
  entityId: string;
  provenance: EntityProvenanceExtended | null;
}

export function ProvenanceDetails({
  entityType,
  entityId,
  provenance,
}: ProvenanceDetailsProps) {
  const { navigateToPage } = useProvenanceSidebarStore();
  
  // Handle missing provenance data
  if (!provenance) {
    return (
      <div className="p-4">
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <div className="text-4xl mb-3" aria-hidden="true">📋</div>
          <div className="text-foreground font-medium mb-1">
            No Provenance Data
          </div>
          <div className="text-sm text-muted-foreground">
            Provenance information is not available for this entity.
          </div>
        </div>
      </div>
    );
  }

  const agentName = getAgentDisplayName(provenance.agent);
  const modelName = getModelDisplayName(provenance.model);
  const modelType = getModelType(provenance.model);
  const confidence = formatConfidence(provenance.confidence);
  const confidenceLevel = getConfidenceLevel(provenance.confidence);
  const sourceLabel = getSourceTypeLabel(provenance.source);
  const relativeTime = formatRelativeTime(provenance.timestamp);

  // Model icon
  const modelIcon = modelType === 'gemini' ? '🔷' : modelType === 'claude' ? '🟣' : '❓';

  // Confidence color and bar width
  const confidenceColor = {
    high: 'bg-green-500',
    medium: 'bg-yellow-500',
    low: 'bg-red-500',
    unknown: 'bg-gray-400',
  }[confidenceLevel];

  const confidenceWidth = provenance.confidence !== undefined 
    ? `${provenance.confidence * 100}%` 
    : '0%';

  const handlePageClick = (pageNum: number) => {
    // Navigate to the page in the preview below
    navigateToPage(pageNum);
  };

  const handlePageKeyDown = (e: React.KeyboardEvent, pageNum: number) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handlePageClick(pageNum);
    }
  };

  return (
    <div className="p-4">
      {/* Two-column grid layout */}
      <div className="grid grid-cols-2 gap-x-6 gap-y-4">
        {/* Left Column */}
        <div className="space-y-4">
          {/* Agent */}
          <div>
            <div className="text-xs text-muted-foreground uppercase tracking-wide mb-1">
              Agent
            </div>
            <div className="text-sm text-foreground">
              {provenance.agent ? agentName : <span className="text-muted-foreground">Not available</span>}
            </div>
          </div>

          {/* Model */}
          <div>
            <div className="text-xs text-muted-foreground uppercase tracking-wide mb-1">
              Model
            </div>
            <div className="flex items-center gap-2 text-sm text-foreground">
              <span className="text-lg">{modelIcon}</span>
              {provenance.model ? modelName : <span className="text-muted-foreground">Not available</span>}
            </div>
          </div>

          {/* Source type */}
          <div>
            <div className="text-xs text-muted-foreground uppercase tracking-wide mb-1">
              Source
            </div>
            <div className="text-sm text-foreground">{sourceLabel}</div>
          </div>

          {/* Timestamp */}
          <div>
            <div className="text-xs text-muted-foreground uppercase tracking-wide mb-1">
              Extracted
            </div>
            <div className="text-sm text-foreground">
              {provenance.timestamp ? relativeTime : <span className="text-muted-foreground">Unknown</span>}
            </div>
          </div>
        </div>

        {/* Right Column */}
        <div className="space-y-4">
          {/* Confidence */}
          <div>
            <div className="text-xs text-muted-foreground uppercase tracking-wide mb-1">
              Confidence
            </div>
            {provenance.confidence !== undefined ? (
              <div className="space-y-2">
                <div className="text-sm text-foreground">{confidence}</div>
                <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                  <div
                    className={`h-full ${confidenceColor} transition-all duration-300 ease-in-out`}
                    style={{ width: confidenceWidth }}
                  />
                </div>
              </div>
            ) : (
              <div className="text-sm text-muted-foreground">Not available</div>
            )}
          </div>

          {/* Page references */}
          <div>
            <div className="text-xs text-muted-foreground uppercase tracking-wide mb-1">
              Protocol Pages
            </div>
            {provenance.pageRefs && provenance.pageRefs.length > 0 ? (
              <div className="flex flex-wrap gap-2" role="list" aria-label="Protocol page references">
                {provenance.pageRefs.map((page) => (
                  <button
                    key={page}
                    onClick={() => handlePageClick(page)}
                    onKeyDown={(e) => handlePageKeyDown(e, page)}
                    className="inline-flex items-center px-2 py-1 text-xs font-medium text-primary bg-primary/10 rounded-md hover:bg-primary/20 transition-all duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 touch-manipulation hover:shadow-sm"
                    role="listitem"
                    aria-label={`Jump to page ${page}`}
                  >
                    Page {page}
                  </button>
                ))}
              </div>
            ) : (
              <div className="text-sm text-muted-foreground italic">
                Page tracking not available for this entity
              </div>
            )}
          </div>

          {/* Footnotes (for SOA cells) */}
          {provenance.footnoteRefs && provenance.footnoteRefs.length > 0 && (
            <div>
              <div className="text-xs text-muted-foreground uppercase tracking-wide mb-1">
                Footnotes
              </div>
              <div className="space-y-1">
                {provenance.footnoteRefs.map((footnote, index) => (
                  <div key={index} className="text-sm text-foreground">
                    {footnote}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
