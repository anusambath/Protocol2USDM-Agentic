/**
 * Zustand store for provenance sidebar state management
 * 
 * Manages:
 * - Sidebar visibility (open/closed)
 * - Pin state (pinned/unpinned)
 * - Selected entity for display
 * - Split pane ratio with localStorage persistence
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { SelectedEntity } from '../provenance/types';

interface ProvenanceSidebarState {
  // State
  isOpen: boolean;
  isPinned: boolean;
  selectedEntity: SelectedEntity | null;
  splitRatio: number; // 0-1, default 0.4 (40% provenance, 60% preview)
  currentTab: string; // Current active tab (e.g., "metadata", "soa-table")
  selectedPageIndex: number; // Index in the pageRefs array (0-based)

  // Actions
  open: (entity: SelectedEntity) => void;
  close: () => void;
  pin: () => void;
  unpin: () => void;
  setSplitRatio: (ratio: number) => void;
  setCurrentTab: (tab: string) => void;
  navigateToPage: (pageNumber: number) => void; // Navigate to specific page number
  
  // Computed
  shouldAutoShow: () => boolean;
  shouldAutoHide: () => boolean;
}

/**
 * Provenance sidebar store with localStorage persistence
 */
export const useProvenanceSidebarStore = create<ProvenanceSidebarState>()(
  persist(
    (set, get) => ({
      // Initial state
      isOpen: false,
      isPinned: false,
      selectedEntity: null,
      splitRatio: 0.4,
      currentTab: '',
      selectedPageIndex: 0,

      // Open sidebar with entity
      open: (entity: SelectedEntity) => {
        set({ isOpen: true, selectedEntity: entity, selectedPageIndex: 0 });
      },

      // Close sidebar
      close: () => {
        const { isPinned } = get();
        // Only close if not pinned
        if (!isPinned) {
          set({ isOpen: false, selectedEntity: null, selectedPageIndex: 0 });
        }
      },

      // Pin sidebar (keeps it open)
      pin: () => {
        set({ isPinned: true });
      },

      // Unpin sidebar (allows closing)
      unpin: () => {
        set({ isPinned: false });
      },

      // Set split pane ratio
      setSplitRatio: (ratio: number) => {
        // Clamp ratio between 0.2 and 0.8
        const clampedRatio = Math.max(0.2, Math.min(0.8, ratio));
        set({ splitRatio: clampedRatio });
      },

      // Set current tab
      setCurrentTab: (tab: string) => {
        const { isPinned, isOpen } = get();
        set({ currentTab: tab });

        // Auto-show on SOA tab
        if (tab === 'soa-table' && !isOpen) {
          set({ isOpen: true });
        }

        // Auto-hide on non-SOA tabs (unless pinned)
        if (tab !== 'soa-table' && isOpen && !isPinned) {
          set({ isOpen: false, selectedEntity: null, selectedPageIndex: 0 });
        }
      },

      // Navigate to a specific page number
      navigateToPage: (pageNumber: number) => {
        const { selectedEntity } = get();
        if (!selectedEntity || !selectedEntity.provenance.pageRefs) return;
        
        // Find the index of the page number in the pageRefs array
        const pageIndex = selectedEntity.provenance.pageRefs.indexOf(pageNumber);
        if (pageIndex !== -1) {
          set({ selectedPageIndex: pageIndex });
        }
      },

      // Check if sidebar should auto-show (SOA tab)
      shouldAutoShow: () => {
        const { currentTab } = get();
        return currentTab === 'soa-table';
      },

      // Check if sidebar should auto-hide (non-SOA tab, unpinned)
      shouldAutoHide: () => {
        const { currentTab, isPinned } = get();
        return currentTab !== 'soa-table' && !isPinned;
      },
    }),
    {
      name: 'provenance-sidebar-storage',
      // Only persist these fields
      partialize: (state) => ({
        isPinned: state.isPinned,
        splitRatio: state.splitRatio,
      }),
    }
  )
);
