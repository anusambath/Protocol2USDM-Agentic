import { useEffect, useRef } from 'react';
import { useLayoutStore } from '@/stores/layoutStore';

/**
 * useResponsiveLayout Hook
 * 
 * Listens to viewport changes using window.matchMedia('(max-width: 1023px)')
 * and automatically collapses/restores panels based on viewport width.
 * 
 * Behavior:
 * - When viewport < 1024px: Auto-collapse Sidebar and Right Panel
 * - When viewport >= 1024px: Restore panels to their persisted states
 * 
 * Uses matchMedia.addEventListener('change') for better performance than
 * window resize events, with 100ms debouncing to avoid thrashing.
 * 
 * Requirements: 17.1, 17.2, 17.3
 */
export function useResponsiveLayout() {
  const toggleSidebar = useLayoutStore((state) => state.toggleSidebar);
  const toggleRightPanel = useLayoutStore((state) => state.toggleRightPanel);
  const sidebarCollapsed = useLayoutStore((state) => state.sidebarCollapsed);
  const rightPanelCollapsed = useLayoutStore((state) => state.rightPanelCollapsed);

  // Store the persisted states before auto-collapse
  const persistedStatesRef = useRef<{
    sidebar: boolean;
    rightPanel: boolean;
  } | null>(null);

  // Debounce timer ref
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(max-width: 1023px)');

    const handleResize = (e: MediaQueryListEvent | MediaQueryList) => {
      // Clear any pending debounce timer
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }

      // Debounce by 100ms to avoid thrashing
      debounceTimerRef.current = setTimeout(() => {
        if (e.matches) {
          // Viewport < 1024px: Save current states and auto-collapse panels
          if (!persistedStatesRef.current) {
            persistedStatesRef.current = {
              sidebar: sidebarCollapsed,
              rightPanel: rightPanelCollapsed,
            };
          }

          // Collapse both panels if not already collapsed
          if (!sidebarCollapsed) {
            toggleSidebar();
          }
          if (!rightPanelCollapsed) {
            toggleRightPanel();
          }
        } else {
          // Viewport >= 1024px: Restore persisted states
          if (persistedStatesRef.current) {
            const { sidebar, rightPanel } = persistedStatesRef.current;

            // Restore sidebar to persisted state
            if (sidebar !== sidebarCollapsed) {
              toggleSidebar();
            }

            // Restore right panel to persisted state
            if (rightPanel !== rightPanelCollapsed) {
              toggleRightPanel();
            }

            // Clear persisted states after restoration
            persistedStatesRef.current = null;
          }
        }
      }, 100);
    };

    // Initial check
    handleResize(mediaQuery);

    // Listen for viewport changes
    mediaQuery.addEventListener('change', handleResize);

    // Cleanup
    return () => {
      mediaQuery.removeEventListener('change', handleResize);
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [sidebarCollapsed, rightPanelCollapsed, toggleSidebar, toggleRightPanel]);
}
