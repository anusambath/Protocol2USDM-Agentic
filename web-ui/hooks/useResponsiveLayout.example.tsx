/**
 * useResponsiveLayout Hook - Usage Example
 * 
 * This hook automatically manages panel collapse/expand behavior based on viewport width.
 * It uses window.matchMedia for efficient viewport detection and debounces changes by 100ms.
 */

import React from 'react';
import { useResponsiveLayout } from './useResponsiveLayout';
import { useLayoutStore } from '@/stores/layoutStore';

/**
 * Example 1: Basic usage in Workbench component
 * 
 * Simply call the hook at the top level of your component.
 * It will automatically handle panel collapse/expand based on viewport changes.
 */
export function WorkbenchExample() {
  // Enable responsive layout behavior
  useResponsiveLayout();

  // Access layout state for rendering
  const sidebarCollapsed = useLayoutStore((state) => state.sidebarCollapsed);
  const rightPanelCollapsed = useLayoutStore((state) => state.rightPanelCollapsed);

  return (
    <div className="workbench">
      <aside className={sidebarCollapsed ? 'collapsed' : 'expanded'}>
        Sidebar
      </aside>
      <main>Center Panel</main>
      <aside className={rightPanelCollapsed ? 'collapsed' : 'expanded'}>
        Right Panel
      </aside>
    </div>
  );
}

/**
 * Example 2: Understanding the behavior
 * 
 * Viewport < 1024px (mobile/tablet):
 * - Sidebar auto-collapses
 * - Right Panel auto-collapses
 * - Center Panel maximizes to full width
 * - User's persisted panel states are saved
 * 
 * Viewport >= 1024px (desktop):
 * - Sidebar restores to persisted state
 * - Right Panel restores to persisted state
 * - Layout returns to user's preferred configuration
 */
export function ResponsiveBehaviorExample() {
  useResponsiveLayout();

  const sidebarCollapsed = useLayoutStore((state) => state.sidebarCollapsed);
  const rightPanelCollapsed = useLayoutStore((state) => state.rightPanelCollapsed);

  return (
    <div className="flex h-screen">
      {/* Activity Bar - always visible */}
      <div className="w-12 bg-gray-900">Activity Bar</div>

      {/* Sidebar - auto-collapses on mobile */}
      {!sidebarCollapsed && (
        <aside className="w-64 bg-gray-800 transition-all duration-300">
          Navigation Tree
        </aside>
      )}

      {/* Center Panel - always visible, takes remaining space */}
      <main className="flex-1 bg-white">
        Content Area
      </main>

      {/* Right Panel - auto-collapses on mobile */}
      {!rightPanelCollapsed && (
        <aside className="w-80 bg-gray-800 transition-all duration-300">
          Contextual Details
        </aside>
      )}
    </div>
  );
}

/**
 * Example 3: Manual override still works
 * 
 * Users can still manually toggle panels even on mobile.
 * The hook only auto-collapses when crossing the 1024px threshold.
 */
export function ManualToggleExample() {
  useResponsiveLayout();

  const toggleSidebar = useLayoutStore((state) => state.toggleSidebar);
  const toggleRightPanel = useLayoutStore((state) => state.toggleRightPanel);
  const sidebarCollapsed = useLayoutStore((state) => state.sidebarCollapsed);
  const rightPanelCollapsed = useLayoutStore((state) => state.rightPanelCollapsed);

  return (
    <div className="workbench">
      <header className="flex gap-2 p-2">
        <button onClick={toggleSidebar}>
          {sidebarCollapsed ? 'Show' : 'Hide'} Sidebar
        </button>
        <button onClick={toggleRightPanel}>
          {rightPanelCollapsed ? 'Show' : 'Hide'} Right Panel
        </button>
      </header>

      <div className="flex flex-1">
        {!sidebarCollapsed && <aside>Sidebar</aside>}
        <main className="flex-1">Center Panel</main>
        {!rightPanelCollapsed && <aside>Right Panel</aside>}
      </div>
    </div>
  );
}

/**
 * Technical Details:
 * 
 * 1. Uses window.matchMedia('(max-width: 1023px)') for efficient viewport detection
 *    - More performant than window.resize events
 *    - Native browser API with better optimization
 * 
 * 2. Debounces changes by 100ms to avoid thrashing
 *    - Prevents rapid toggle calls during resize
 *    - Improves performance and user experience
 * 
 * 3. Preserves user preferences
 *    - Saves panel states before auto-collapse
 *    - Restores exact states when returning to desktop
 *    - Works seamlessly with layoutStore persistence
 * 
 * 4. Cleanup on unmount
 *    - Removes event listeners
 *    - Clears debounce timers
 *    - No memory leaks
 */
