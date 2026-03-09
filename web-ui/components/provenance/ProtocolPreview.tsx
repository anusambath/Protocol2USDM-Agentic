'use client';

/**
 * ProtocolPreview component
 * 
 * Displays protocol page images with zoom and navigation controls
 * 
 * Features:
 * - PNG image display with zoom controls (50%, 75%, 100%, 125%, 150%, 200%)
 * - Previous/Next page navigation
 * - Fullscreen mode toggle
 * - Loading skeletons for async loading
 * - Cache-first loading with IndexedDB
 */

import React, { useState, useEffect } from 'react';
import { getProtocolPageCache } from '@/lib/cache/protocol-page-cache';
import { useKeyboardShortcuts } from '@/lib/hooks/useKeyboardShortcuts';
import { useProvenanceSidebarStore } from '@/lib/stores/provenance-sidebar-store';

interface ProtocolPreviewProps {
  protocolId: string;
  pageNumbers: number[];
  totalPages?: number;
  className?: string;
}

const ZOOM_LEVELS = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0];

export function ProtocolPreview({
  protocolId,
  pageNumbers,
  totalPages,
  className = '',
}: ProtocolPreviewProps) {
  const { selectedPageIndex, navigateToPage } = useProvenanceSidebarStore();
  const [zoomLevel, setZoomLevel] = useState(1.0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [errorType, setErrorType] = useState<'network' | 'not-found' | 'render-failed' | 'unknown' | null>(null);
  const [retryCount, setRetryCount] = useState(0);

  // Use selectedPageIndex from store, but clamp it to valid range
  const currentPageIndex = Math.max(0, Math.min(selectedPageIndex, pageNumbers.length - 1));
  const currentPageNum = pageNumbers[currentPageIndex];
  const cache = getProtocolPageCache();

  // Load page image with retry logic
  useEffect(() => {
    let isMounted = true;
    let objectUrl: string | null = null;
    const startTime = performance.now();

    const loadPage = async (attemptNumber = 0) => {
      setIsLoading(true);
      setError(null);
      setErrorType(null);

      try {
        // Try cache first
        const cached = await cache.get(protocolId, currentPageNum);
        
        if (cached && isMounted) {
          const loadTime = performance.now() - startTime;
          if (loadTime > 50) {
            console.warn(`Cached page load took ${loadTime.toFixed(2)}ms (target: <50ms)`);
          }
          
          objectUrl = URL.createObjectURL(cached.blob);
          setImageUrl(objectUrl);
          setIsLoading(false);
          setRetryCount(0); // Reset retry count on success
          
          // Preload adjacent pages
          if (totalPages) {
            cache.preloadAdjacentPages(protocolId, currentPageNum, totalPages);
          }
          
          return;
        }

        // Fetch from server
        const fetchStart = performance.now();
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000); // 10s timeout
        
        let response: Response;
        try {
          response = await fetch(`/api/protocols/${protocolId}/pages/${currentPageNum}`, {
            signal: controller.signal,
          });
        } catch (fetchError: any) {
          clearTimeout(timeoutId);
          
          // Network error or timeout
          if (fetchError.name === 'AbortError') {
            throw new Error('network:Request timed out. Please check your connection.');
          }
          throw new Error('network:Unable to connect to server. Please check your connection.');
        }
        
        clearTimeout(timeoutId);
        
        // Handle HTTP errors
        if (!response.ok) {
          if (response.status === 404) {
            throw new Error('not-found:Protocol file not available for preview');
          } else if (response.status === 500) {
            throw new Error('render-failed:Failed to render page. The PDF may be corrupted.');
          } else {
            throw new Error(`unknown:Failed to load page: ${response.statusText}`);
          }
        }

        const blob = await response.blob();
        const fetchTime = performance.now() - fetchStart;
        
        if (fetchTime > 500) {
          console.warn(`Uncached page load took ${fetchTime.toFixed(2)}ms (target: <500ms)`);
        }
        
        if (isMounted) {
          // Cache the page
          await cache.set(protocolId, currentPageNum, blob);
          
          // Check and evict if needed
          await cache.checkAndEvict();
          
          // Display the page
          objectUrl = URL.createObjectURL(blob);
          setImageUrl(objectUrl);
          setIsLoading(false);
          setRetryCount(0); // Reset retry count on success
          
          // Preload adjacent pages
          if (totalPages) {
            cache.preloadAdjacentPages(protocolId, currentPageNum, totalPages);
          }
        }
      } catch (err) {
        if (isMounted) {
          const errorMessage = err instanceof Error ? err.message : 'Failed to load page';
          const [type, message] = errorMessage.includes(':') 
            ? errorMessage.split(':', 2) as [string, string]
            : ['unknown', errorMessage];
          
          // Log error with context (serialize error properly)
          console.error('Failed to load protocol page:', {
            protocolId,
            pageNum: currentPageNum,
            error: message,
            errorType: type,
            attemptNumber,
            timestamp: new Date().toISOString(),
            rawError: err instanceof Error ? err.message : String(err),
          });
          
          // For network errors, implement exponential backoff retry
          if (type === 'network' && attemptNumber < 3) {
            const backoffDelay = Math.pow(2, attemptNumber) * 1000; // 1s, 2s, 4s
            console.log(`Retrying in ${backoffDelay}ms (attempt ${attemptNumber + 1}/3)...`);
            
            setTimeout(() => {
              if (isMounted) {
                loadPage(attemptNumber + 1);
              }
            }, backoffDelay);
            
            setError(`${message} Retrying in ${backoffDelay / 1000}s...`);
            setErrorType(type as any);
          } else {
            // Final error state
            setError(message);
            setErrorType(type as any);
            setIsLoading(false);
            setRetryCount(attemptNumber);
          }
        }
      }
    };

    loadPage();

    return () => {
      isMounted = false;
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [protocolId, currentPageNum, totalPages, cache]);

  const handleRetry = () => {
    // Force reload by updating a state that triggers the effect
    setImageUrl(null);
    setError(null);
    setErrorType(null);
    setIsLoading(true);
    // The effect will reload based on currentPageNum
  };

  const handlePrevPage = () => {
    if (currentPageIndex > 0) {
      const prevPageNum = pageNumbers[currentPageIndex - 1];
      navigateToPage(prevPageNum);
    }
  };

  const handleNextPage = () => {
    if (currentPageIndex < pageNumbers.length - 1) {
      const nextPageNum = pageNumbers[currentPageIndex + 1];
      navigateToPage(nextPageNum);
    }
  };

  const handleZoomIn = () => {
    const currentIndex = ZOOM_LEVELS.indexOf(zoomLevel);
    if (currentIndex < ZOOM_LEVELS.length - 1) {
      setZoomLevel(ZOOM_LEVELS[currentIndex + 1]);
    }
  };

  const handleZoomOut = () => {
    const currentIndex = ZOOM_LEVELS.indexOf(zoomLevel);
    if (currentIndex > 0) {
      setZoomLevel(ZOOM_LEVELS[currentIndex - 1]);
    }
  };

  const handleZoomReset = () => {
    setZoomLevel(1.0);
  };

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  const canZoomIn = ZOOM_LEVELS.indexOf(zoomLevel) < ZOOM_LEVELS.length - 1;
  const canZoomOut = ZOOM_LEVELS.indexOf(zoomLevel) > 0;

  // Keyboard shortcuts for navigation and zoom
  useKeyboardShortcuts({
    onArrowLeft: handlePrevPage,
    onArrowRight: handleNextPage,
    onZoomIn: canZoomIn ? handleZoomIn : undefined,
    onZoomOut: canZoomOut ? handleZoomOut : undefined,
  });

  return (
    <div
      className={`flex flex-col h-full bg-muted ${className} ${
        isFullscreen ? 'fixed inset-0 z-50' : ''
      }`}
      role="region"
      aria-label="Protocol page preview"
    >
      {/* Controls */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 sm:gap-0 p-3 border-b border-border bg-card">
        {/* Page navigation */}
        <div className="flex items-center gap-2" role="group" aria-label="Page navigation">
          <button
            onClick={handlePrevPage}
            disabled={currentPageIndex === 0}
            className="px-3 py-1.5 text-sm font-medium text-foreground bg-secondary rounded-md hover:bg-secondary/80 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 touch-manipulation"
            aria-label="Previous page"
            title="Previous page (Left arrow)"
          >
            ← Prev
          </button>
          <span className="text-sm text-muted-foreground whitespace-nowrap" aria-live="polite">
            Page {currentPageNum} ({currentPageIndex + 1} of {pageNumbers.length})
          </span>
          <button
            onClick={handleNextPage}
            disabled={currentPageIndex === pageNumbers.length - 1}
            className="px-3 py-1.5 text-sm font-medium text-foreground bg-secondary rounded-md hover:bg-secondary/80 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 touch-manipulation"
            aria-label="Next page"
            title="Next page (Right arrow)"
          >
            Next →
          </button>
        </div>

        {/* Zoom controls */}
        <div className="flex items-center gap-2" role="group" aria-label="Zoom controls">
          <button
            onClick={handleZoomOut}
            disabled={!canZoomOut}
            className="px-2 py-1.5 text-sm font-medium text-foreground bg-secondary rounded-md hover:bg-secondary/80 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 touch-manipulation"
            aria-label="Zoom out"
            title="Zoom out (- key)"
          >
            −
          </button>
          <button
            onClick={handleZoomReset}
            className="px-3 py-1.5 text-sm font-medium text-foreground bg-secondary rounded-md hover:bg-secondary/80 transition-all duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 touch-manipulation"
            aria-label={`Reset zoom to 100%. Current zoom: ${Math.round(zoomLevel * 100)}%`}
            title="Reset zoom"
          >
            {Math.round(zoomLevel * 100)}%
          </button>
          <button
            onClick={handleZoomIn}
            disabled={!canZoomIn}
            className="px-2 py-1.5 text-sm font-medium text-foreground bg-secondary rounded-md hover:bg-secondary/80 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 touch-manipulation"
            aria-label="Zoom in"
            title="Zoom in (+ key)"
          >
            +
          </button>
        </div>

        {/* Fullscreen toggle */}
        <button
          onClick={toggleFullscreen}
          className="px-3 py-1.5 text-sm font-medium text-foreground bg-secondary rounded-md hover:bg-secondary/80 transition-all duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 touch-manipulation"
          aria-label={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
          aria-pressed={isFullscreen}
        >
          {isFullscreen ? '⊗ Exit' : '⛶ Fullscreen'}
        </button>
      </div>

      {/* Image display */}
      <div className="flex-1 overflow-auto p-4" role="main">
        {isLoading && (
          <div className="flex items-center justify-center h-full" role="status" aria-live="polite">
            <div className="w-full max-w-4xl space-y-4">
              {/* Loading skeleton that matches page aspect ratio */}
              <div className="animate-pulse bg-muted rounded-md w-full aspect-[8.5/11]" aria-hidden="true" />
              <div className="text-center text-sm text-muted-foreground">
                Loading page {currentPageNum}...
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="flex flex-col items-center justify-center h-full gap-4" role="alert" aria-live="assertive">
            {/* Error icon based on type */}
            <div className="text-6xl" aria-hidden="true">
              {errorType === 'not-found' && '📄'}
              {errorType === 'render-failed' && '⚠️'}
              {errorType === 'network' && '🌐'}
              {errorType === 'unknown' && '❌'}
            </div>
            
            {/* Error message */}
            <div className="text-destructive text-lg font-semibold text-center max-w-md">
              {errorType === 'not-found' && 'Protocol File Not Available'}
              {errorType === 'render-failed' && 'Failed to Render Page'}
              {errorType === 'network' && 'Unable to Connect'}
              {errorType === 'unknown' && 'Error Loading Page'}
            </div>
            
            <div className="text-destructive/80 text-sm text-center max-w-md">
              {error}
            </div>
            
            {/* Retry button - only show for retryable errors */}
            {errorType !== 'not-found' && (
              <button
                onClick={handleRetry}
                className="px-4 py-2 text-sm font-medium text-destructive-foreground bg-destructive hover:bg-destructive/90 rounded-md transition-all duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                aria-label="Retry loading page"
              >
                Try Again
              </button>
            )}
            
            {/* Additional help text */}
            {errorType === 'network' && (
              <div className="text-xs text-muted-foreground text-center max-w-md">
                Check your internet connection and try again.
                {retryCount > 0 && ` (Attempt ${retryCount + 1})`}
              </div>
            )}
            
            {errorType === 'not-found' && (
              <div className="text-xs text-muted-foreground text-center max-w-md">
                The protocol PDF file is not available. Preview functionality is disabled.
              </div>
            )}
          </div>
        )}

        {!isLoading && !error && imageUrl && (
          <div className="flex justify-center">
            <img
              src={imageUrl}
              alt={`Protocol page ${currentPageNum} showing source content for provenance verification`}
              style={{ 
                transform: `scale(${zoomLevel})`, 
                transformOrigin: 'top center',
                willChange: 'transform',
              }}
              className="max-w-full h-auto shadow-lg rounded-md transition-transform duration-200 ease-in-out"
              loading="eager"
              role="img"
            />
          </div>
        )}
      </div>
    </div>
  );
}
