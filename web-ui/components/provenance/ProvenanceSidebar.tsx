'use client';

/**
 * ProvenanceSidebar component
 * 
 * Slide-in panel displaying provenance details and protocol preview
 * 
 * Features:
 * - Smooth slide-in animation (200ms, 60fps)
 * - Split view (40% provenance, 60% preview)
 * - Pin button for persistent display
 * - Close button and Esc key handler
 * - Outside click handler (when unpinned)
 * - Draggable split pane divider
 */

import React, { useEffect, useRef, useState } from 'react';
import { useProvenanceSidebarStore } from '@/lib/stores/provenance-sidebar-store';
import { ProtocolPreview } from './ProtocolPreview';
import { ProvenanceDetails } from './ProvenanceDetails';
import { useKeyboardShortcuts } from '@/lib/hooks/useKeyboardShortcuts';
import { ErrorBoundary } from './ErrorBoundary';

interface ProvenanceSidebarProps {
  protocolId: string;
  totalPages?: number;
}

export function ProvenanceSidebar({ protocolId, totalPages }: ProvenanceSidebarProps) {
  const { isOpen, isPinned, selectedEntity, splitRatio, close, pin, unpin, setSplitRatio } =
    useProvenanceSidebarStore();
  
  const sidebarRef = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  // Keyboard shortcuts
  useKeyboardShortcuts({
    onEscape: isOpen && !isPinned ? close : undefined,
  });

  // Handle Esc key (legacy - now handled by useKeyboardShortcuts)
  // Keeping for backwards compatibility
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen && !isPinned) {
        close();
      }
    };

    document.addEventListener('keydown', handleEsc);
    return () => document.removeEventListener('keydown', handleEsc);
  }, [isOpen, isPinned, close]);

  // Handle outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        isOpen &&
        !isPinned &&
        sidebarRef.current &&
        !sidebarRef.current.contains(e.target as Node)
      ) {
        close();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen, isPinned, close]);

  // Handle split pane dragging
  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!sidebarRef.current) return;

      const sidebarRect = sidebarRef.current.getBoundingClientRect();
      const relativeY = e.clientY - sidebarRect.top;
      const newRatio = relativeY / sidebarRect.height;

      setSplitRatio(newRatio);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, setSplitRatio]);

  if (!isOpen || !selectedEntity) {
    return null;
  }

  const pageNumbers = selectedEntity.provenance.pageRefs || [];

  return (
    <>
      {/* Backdrop */}
      {!isPinned && (
        <div
          className="fixed inset-0 bg-black/20 dark:bg-black/40 z-40 transition-opacity duration-200 ease-out"
          aria-hidden="true"
          onClick={close}
        />
      )}

      {/* Sidebar */}
      <div
        ref={sidebarRef}
        className="fixed right-0 top-0 bottom-0 w-full md:w-[500px] lg:w-[600px] bg-background border-l border-border shadow-2xl z-50 flex flex-col will-change-transform touch-pan-y"
        style={{
          transform: isOpen ? 'translateX(0)' : 'translateX(100%)',
          transition: 'transform 200ms cubic-bezier(0.4, 0, 0.2, 1)',
        }}
        role="complementary"
        aria-label="Provenance sidebar"
        aria-hidden={!isOpen}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border bg-card">
          <h2 className="text-lg font-semibold text-foreground" id="sidebar-title">
            Provenance Details
          </h2>
          <div className="flex items-center gap-2">
            {/* Pin button */}
            <button
              onClick={isPinned ? unpin : pin}
              className={`p-2 rounded-md transition-all duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 touch-manipulation ${
                isPinned 
                  ? 'text-primary bg-primary/10 hover:bg-primary/20' 
                  : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
              }`}
              aria-label={isPinned ? 'Unpin sidebar' : 'Pin sidebar'}
              aria-pressed={isPinned}
              title={isPinned ? 'Unpin sidebar' : 'Pin sidebar'}
            >
              📌
            </button>

            {/* Close button */}
            <button
              onClick={close}
              className="p-2 text-muted-foreground hover:bg-accent hover:text-accent-foreground rounded-md transition-all duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 touch-manipulation"
              aria-label="Close sidebar (Esc)"
              title="Close sidebar (Esc)"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Split view */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Provenance details (top) */}
          <div
            className="overflow-auto border-b border-border"
            style={{ height: `${splitRatio * 100}%` }}
            role="region"
            aria-labelledby="sidebar-title"
          >
            <ErrorBoundary
              fallback={(error, retry) => (
                <div className="p-4 space-y-4">
                  <div className="text-destructive text-sm font-medium">
                    Failed to load provenance details
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {error.message}
                  </div>
                  <button
                    onClick={retry}
                    className="px-3 py-1.5 text-xs font-medium text-destructive-foreground bg-destructive hover:bg-destructive/90 rounded-md transition-all duration-150 ease-in-out"
                  >
                    Retry
                  </button>
                </div>
              )}
            >
              <ProvenanceDetails
                entityType={selectedEntity.type}
                entityId={selectedEntity.id}
                provenance={selectedEntity.provenance}
              />
            </ErrorBoundary>
          </div>

          {/* Draggable divider */}
          <div
            className="h-1 bg-border hover:bg-primary cursor-row-resize transition-all duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-ring"
            onMouseDown={handleMouseDown}
            role="separator"
            aria-label="Resize split pane. Drag to adjust the size of provenance details and protocol preview sections."
            aria-valuenow={Math.round(splitRatio * 100)}
            aria-valuemin={20}
            aria-valuemax={80}
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'ArrowUp') {
                e.preventDefault();
                setSplitRatio(Math.max(0.2, splitRatio - 0.05));
              } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                setSplitRatio(Math.min(0.8, splitRatio + 0.05));
              }
            }}
          />

          {/* Protocol preview (bottom) */}
          <div
            className="overflow-hidden"
            style={{ height: `${(1 - splitRatio) * 100}%` }}
          >
            <ErrorBoundary
              fallback={(error, retry) => (
                <div className="flex flex-col items-center justify-center h-full gap-4 p-4">
                  <div className="text-destructive text-sm font-medium">
                    Failed to load protocol preview
                  </div>
                  <div className="text-xs text-muted-foreground text-center max-w-md">
                    {error.message}
                  </div>
                  <button
                    onClick={retry}
                    className="px-3 py-1.5 text-xs font-medium text-destructive-foreground bg-destructive hover:bg-destructive/90 rounded-md transition-all duration-150 ease-in-out"
                  >
                    Retry
                  </button>
                </div>
              )}
            >
              {pageNumbers.length > 0 ? (
                <ProtocolPreview
                  protocolId={protocolId}
                  pageNumbers={pageNumbers}
                  totalPages={totalPages}
                />
              ) : (
                <div className="flex items-center justify-center h-full text-muted-foreground" role="status">
                  No protocol pages available
                </div>
              )}
            </ErrorBoundary>
          </div>
        </div>
      </div>
    </>
  );
}
