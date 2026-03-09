import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

// ViewType enum matching existing TabId values
export type ViewType =
  | 'overview'
  | 'eligibility'
  | 'objectives'
  | 'design'
  | 'interventions'
  | 'amendments'
  | 'extensions'
  | 'entities'
  | 'procedures'
  | 'sites'
  | 'footnotes'
  | 'schedule'
  | 'narrative'
  | 'quality'
  | 'validation'
  | 'document'
  | 'images'
  | 'soa'
  | 'timeline'
  | 'provenance';

export type ActivityBarMode = 'explorer' | 'search' | 'quality';

export type RightPanelTab = 'properties' | 'provenance' | 'footnotes';

export interface LayoutTab {
  id: string; // e.g. 'overview', 'soa', 'timeline'
  viewType: ViewType;
  label: string;
  icon: string; // Lucide icon name
}

interface LayoutState {
  // Panel sizes
  sidebarWidth: number; // default 260, min 200, max 480
  rightPanelWidth: number; // default 320, min 240, max 600

  // Collapsed states
  sidebarCollapsed: boolean;
  rightPanelCollapsed: boolean;

  // Center panel tabs
  openTabs: LayoutTab[];
  activeTabId: string | null;
  tabHistory: string[]; // MRU stack for close-tab fallback

  // Right panel tabs
  rightPanelActiveTab: RightPanelTab;

  // Nav tree
  navTreeExpandedGroups: Record<string, boolean>;

  // Activity bar
  activityBarMode: ActivityBarMode;

  // Actions
  setSidebarWidth: (width: number) => void;
  setRightPanelWidth: (width: number) => void;
  toggleSidebar: () => void;
  toggleRightPanel: () => void;
  openTab: (tab: LayoutTab) => void;
  closeTab: (tabId: string) => void;
  setActiveTab: (tabId: string) => void;
  setActivityBarMode: (mode: ActivityBarMode) => void;
  toggleNavTreeGroup: (groupId: string) => void;
  setRightPanelActiveTab: (tab: RightPanelTab) => void;
  resetToDefaults: () => void;
}

// Default values
const DEFAULT_SIDEBAR_WIDTH = 260;
const DEFAULT_RIGHT_PANEL_WIDTH = 320;
const DEFAULT_SIDEBAR_COLLAPSED = false;
const DEFAULT_RIGHT_PANEL_COLLAPSED = false;
const DEFAULT_OPEN_TABS: LayoutTab[] = [];
const DEFAULT_ACTIVE_TAB_ID: string | null = null;
const DEFAULT_TAB_HISTORY: string[] = [];
const DEFAULT_RIGHT_PANEL_ACTIVE_TAB: RightPanelTab = 'properties';
const DEFAULT_NAV_TREE_EXPANDED_GROUPS: Record<string, boolean> = {};
const DEFAULT_ACTIVITY_BAR_MODE: ActivityBarMode = 'explorer';

export const useLayoutStore = create<LayoutState>()(
  persist(
    (set, get) => ({
      // Initial state
      sidebarWidth: DEFAULT_SIDEBAR_WIDTH,
      rightPanelWidth: DEFAULT_RIGHT_PANEL_WIDTH,
      sidebarCollapsed: DEFAULT_SIDEBAR_COLLAPSED,
      rightPanelCollapsed: DEFAULT_RIGHT_PANEL_COLLAPSED,
      openTabs: DEFAULT_OPEN_TABS,
      activeTabId: DEFAULT_ACTIVE_TAB_ID,
      tabHistory: DEFAULT_TAB_HISTORY,
      rightPanelActiveTab: DEFAULT_RIGHT_PANEL_ACTIVE_TAB,
      navTreeExpandedGroups: DEFAULT_NAV_TREE_EXPANDED_GROUPS,
      activityBarMode: DEFAULT_ACTIVITY_BAR_MODE,

      // Actions
      setSidebarWidth: (width: number) => {
        set({ sidebarWidth: width });
      },

      setRightPanelWidth: (width: number) => {
        set({ rightPanelWidth: width });
      },

      toggleSidebar: () => {
        set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed }));
      },

      toggleRightPanel: () => {
        set((state) => ({ rightPanelCollapsed: !state.rightPanelCollapsed }));
      },

      openTab: (tab: LayoutTab) => {
        const { openTabs, tabHistory } = get();

        // Check if tab already exists (idempotent)
        const existingTab = openTabs.find((t) => t.viewType === tab.viewType);
        if (existingTab) {
          // Focus existing tab
          set({
            activeTabId: existingTab.id,
            tabHistory: [
              existingTab.id,
              ...tabHistory.filter((id) => id !== existingTab.id),
            ],
          });
          return;
        }

        // Add new tab
        const newOpenTabs = [...openTabs, tab];
        const newTabHistory = [tab.id, ...tabHistory];

        set({
          openTabs: newOpenTabs,
          activeTabId: tab.id,
          tabHistory: newTabHistory,
        });
      },

      closeTab: (tabId: string) => {
        const { openTabs, activeTabId, tabHistory } = get();

        // Remove tab from openTabs
        const newOpenTabs = openTabs.filter((t) => t.id !== tabId);

        // Remove from tabHistory
        const newTabHistory = tabHistory.filter((id) => id !== tabId);

        // If closed tab was active, activate most recent tab
        let newActiveTabId = activeTabId;
        if (activeTabId === tabId) {
          newActiveTabId = newTabHistory[0] ?? null;
        }

        set({
          openTabs: newOpenTabs,
          activeTabId: newActiveTabId,
          tabHistory: newTabHistory,
        });
      },

      setActiveTab: (tabId: string) => {
        const { tabHistory } = get();

        // Move tab to front of history (MRU)
        const newTabHistory = [
          tabId,
          ...tabHistory.filter((id) => id !== tabId),
        ];

        set({
          activeTabId: tabId,
          tabHistory: newTabHistory,
        });
      },

      setActivityBarMode: (mode: ActivityBarMode) => {
        set({ activityBarMode: mode });
      },

      toggleNavTreeGroup: (groupId: string) => {
        set((state) => ({
          navTreeExpandedGroups: {
            ...state.navTreeExpandedGroups,
            [groupId]: !state.navTreeExpandedGroups[groupId],
          },
        }));
      },

      setRightPanelActiveTab: (tab: RightPanelTab) => {
        set({ rightPanelActiveTab: tab });
      },

      resetToDefaults: () => {
        set({
          sidebarWidth: DEFAULT_SIDEBAR_WIDTH,
          rightPanelWidth: DEFAULT_RIGHT_PANEL_WIDTH,
          sidebarCollapsed: DEFAULT_SIDEBAR_COLLAPSED,
          rightPanelCollapsed: DEFAULT_RIGHT_PANEL_COLLAPSED,
          openTabs: DEFAULT_OPEN_TABS,
          activeTabId: DEFAULT_ACTIVE_TAB_ID,
          tabHistory: DEFAULT_TAB_HISTORY,
          rightPanelActiveTab: DEFAULT_RIGHT_PANEL_ACTIVE_TAB,
          navTreeExpandedGroups: DEFAULT_NAV_TREE_EXPANDED_GROUPS,
          activityBarMode: DEFAULT_ACTIVITY_BAR_MODE,
        });
      },
    }),
    {
      name: 'p2u-layout', // localStorage key
      storage: createJSONStorage(() => localStorage),
      version: 1,
      // Partialize to exclude action functions from persistence
      partialize: (state) => ({
        sidebarWidth: state.sidebarWidth,
        rightPanelWidth: state.rightPanelWidth,
        sidebarCollapsed: state.sidebarCollapsed,
        rightPanelCollapsed: state.rightPanelCollapsed,
        openTabs: state.openTabs,
        activeTabId: state.activeTabId,
        tabHistory: state.tabHistory,
        rightPanelActiveTab: state.rightPanelActiveTab,
        navTreeExpandedGroups: state.navTreeExpandedGroups,
        activityBarMode: state.activityBarMode,
      }),
      // Handle corrupted data with resetToDefaults fallback
      onRehydrateStorage: () => (state, error) => {
        if (error) {
          console.warn(
            'Failed to hydrate layout store from localStorage, resetting to defaults:',
            error
          );
          // Reset to defaults on error
          state?.resetToDefaults();
        }
      },
    }
  )
);
