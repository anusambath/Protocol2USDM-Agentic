'use client';

import { useState, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { useLayoutStore } from '@/stores/layoutStore';
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts';
import { useResponsiveLayout } from '@/hooks/useResponsiveLayout';
import { viewRegistry } from '@/lib/viewRegistry';
import { ProvenanceDataExtended } from '@/lib/provenance/types';
import { ActivityBar } from './ActivityBar';
import { Sidebar } from './Sidebar';
import { CenterPanel } from './CenterPanel';
import { RightPanel } from './RightPanel';
import { StatusBar } from './StatusBar';
import { CommandPalette } from './CommandPalette';
import { PanelSplitter } from './PanelSplitter';
import { ProvenanceSidebar } from '@/components/provenance/ProvenanceSidebar';

export interface WorkbenchProps {
  protocolId: string;
  usdm: Record<string, unknown>;
  provenance: ProvenanceDataExtended | null;
  idMapping: Record<string, string> | null;
  intermediateFiles: Record<string, unknown> | null;
}

export function Workbench({
  protocolId,
  usdm,
  provenance,
  idMapping,
  intermediateFiles,
}: WorkbenchProps) {
  // Layout store state
  const {
    sidebarWidth,
    rightPanelWidth,
    sidebarCollapsed,
    rightPanelCollapsed,
    openTabs,
    activeTabId,
    activityBarMode,
    navTreeExpandedGroups,
    rightPanelActiveTab,
    setSidebarWidth,
    setRightPanelWidth,
    toggleSidebar,
    toggleRightPanel,
    openTab,
    closeTab,
    setActiveTab,
    setActivityBarMode,
    toggleNavTreeGroup,
    setRightPanelActiveTab,
  } = useLayoutStore();

  // Local selection state (ephemeral, not persisted)
  const [selectedCellId, setSelectedCellId] = useState<string | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // Command palette state
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);

  // Panel resize handlers
  const handleLeftSplitterResize = useCallback(
    (delta: number) => {
      const newWidth = Math.max(200, Math.min(480, sidebarWidth + delta));
      setSidebarWidth(newWidth);
    },
    [sidebarWidth, setSidebarWidth]
  );

  const handleRightSplitterResize = useCallback(
    (delta: number) => {
      // For right splitter, positive delta means dragging right (decreasing right panel width)
      const newWidth = Math.max(240, Math.min(600, rightPanelWidth - delta));
      setRightPanelWidth(newWidth);
    },
    [rightPanelWidth, setRightPanelWidth]
  );

  // Navigation handler - opens a tab for the given view type
  const handleNavigate = useCallback(
    (viewType: string) => {
      const viewEntry = viewRegistry[viewType as keyof typeof viewRegistry];
      if (!viewEntry) {
        console.error(`View type "${viewType}" not found in view registry`);
        return;
      }

      // Create a new tab
      const newTab = {
        id: `${viewType}-${Date.now()}`,
        viewType: viewEntry.viewType,
        label: viewEntry.label,
        icon: viewEntry.icon,
      };

      openTab(newTab);
    },
    [openTab]
  );

  // Command execution handler
  const handleCommandExecute = useCallback(
    (commandId: string) => {
      // Navigation commands
      if (commandId.startsWith('nav-')) {
        const viewType = commandId.replace('nav-', '');
        handleNavigate(viewType);
        return;
      }

      // Action commands
      switch (commandId) {
        case 'action-save-draft':
          handleSaveDraft();
          break;
        case 'action-publish':
          handlePublish();
          break;
        case 'action-reset':
          handleResetToPublished();
          break;
        case 'action-toggle-sidebar':
          toggleSidebar();
          break;
        case 'action-toggle-right-panel':
          toggleRightPanel();
          break;
        case 'action-export-csv':
          handleExportCSV();
          break;
        case 'action-export-json':
          handleExportJSON();
          break;
        case 'action-export-pdf':
          handleExportPDF();
          break;
        default:
          console.warn(`Unknown command: ${commandId}`);
      }
    },
    [handleNavigate, toggleSidebar, toggleRightPanel]
  );

  // Draft/publish handlers (placeholders - will be wired to actual API)
  const handleSaveDraft = useCallback(() => {
    console.log('Save draft action triggered');
    // TODO: Wire to overlayStore.saveDraft()
  }, []);

  const handlePublish = useCallback(() => {
    console.log('Publish action triggered');
    // TODO: Show confirmation dialog, then wire to overlayStore.publish()
  }, []);

  const handleResetToPublished = useCallback(() => {
    console.log('Reset to published action triggered');
    // TODO: Show confirmation dialog, then wire to overlayStore.reset()
  }, []);

  // Export handlers (placeholders - will be wired to actual export functions)
  const handleExportCSV = useCallback(() => {
    console.log('Export CSV action triggered');
    // TODO: Wire to exportToCSV()
  }, []);

  const handleExportJSON = useCallback(() => {
    console.log('Export JSON action triggered');
    // TODO: Wire to exportToJSON()
  }, []);

  const handleExportPDF = useCallback(() => {
    console.log('Export PDF action triggered');
    // TODO: Wire to exportToPDF()
  }, []);

  // Keyboard shortcuts
  useKeyboardShortcuts([
    {
      key: 's',
      ctrl: true,
      action: handleSaveDraft,
      description: 'Save Draft',
    },
    {
      key: 'b',
      ctrl: true,
      action: toggleSidebar,
      description: 'Toggle Sidebar',
    },
    {
      key: 'j',
      ctrl: true,
      action: toggleRightPanel,
      description: 'Toggle Right Panel',
    },
    {
      key: 'k',
      ctrl: true,
      action: () => setIsCommandPaletteOpen(true),
      description: 'Command Palette',
    },
    {
      key: 'w',
      ctrl: true,
      action: () => activeTabId && closeTab(activeTabId),
      description: 'Close Active Tab',
    },
    // Ctrl/Cmd+1-9: Switch to tab at ordinal position
    ...Array.from({ length: 9 }, (_, i) => ({
      key: String(i + 1),
      ctrl: true,
      action: () => {
        const tab = openTabs[i];
        if (tab) setActiveTab(tab.id);
      },
      description: `Switch to tab ${i + 1}`,
    })),
  ]);

  // Responsive layout behavior
  useResponsiveLayout();

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-background">
      {/* Main content area: ActivityBar | Sidebar | Splitter | CenterPanel | Splitter | RightPanel */}
      <div className="flex flex-row flex-1 overflow-hidden">
        {/* Activity Bar (48px fixed width) */}
        <ActivityBar
          activeMode={activityBarMode}
          onModeChange={setActivityBarMode}
          onToggleSidebar={toggleSidebar}
        />

        {/* Sidebar (collapsible, animated width) */}
        <Sidebar
          mode={activityBarMode}
          collapsed={sidebarCollapsed}
          width={sidebarWidth}
          activeTabId={activeTabId}
          expandedGroups={navTreeExpandedGroups}
          onNavigate={handleNavigate}
          onToggleGroup={toggleNavTreeGroup}
        />

        {/* Left Panel Splitter */}
        {!sidebarCollapsed && (
          <PanelSplitter
            position="left"
            onResize={handleLeftSplitterResize}
            onDoubleClick={toggleSidebar}
          />
        )}

        {/* Center Panel (main content area) */}
        <CenterPanel
          openTabs={openTabs}
          activeTabId={activeTabId}
          onTabChange={setActiveTab}
          onTabClose={closeTab}
          usdm={usdm}
          protocolId={protocolId}
          provenance={provenance}
          idMapping={idMapping}
          intermediateFiles={intermediateFiles}
          onCellSelect={setSelectedCellId}
          onNodeSelect={setSelectedNodeId}
        />

        {/* Right Panel Splitter */}
        {!rightPanelCollapsed && (
          <PanelSplitter
            position="right"
            onResize={handleRightSplitterResize}
            onDoubleClick={toggleRightPanel}
          />
        )}

        {/* Right Panel (collapsible, animated width) */}
        <RightPanel
          collapsed={rightPanelCollapsed}
          width={rightPanelWidth}
          activeTab={rightPanelActiveTab}
          onTabChange={setRightPanelActiveTab}
          selectedCellId={selectedCellId}
          selectedNodeId={selectedNodeId}
          usdm={usdm}
          provenance={provenance}
        />
      </div>

      {/* Status Bar (32px fixed height at bottom) */}
      <StatusBar
        protocolId={protocolId}
        usdmVersion={(usdm?.version as string) || undefined}
        isDirty={false} // TODO: Wire to overlayStore.isDirty
        overlayStatus="draft" // TODO: Wire to overlayStore.status
        validationIssueCount={0} // TODO: Wire to validation results
        onSaveDraft={handleSaveDraft}
        onPublish={handlePublish}
        onResetToPublished={handleResetToPublished}
      />

      {/* Command Palette (overlay, rendered via portal) */}
      {typeof window !== 'undefined' &&
        createPortal(
          <CommandPalette
            isOpen={isCommandPaletteOpen}
            onClose={() => setIsCommandPaletteOpen(false)}
            onExecute={handleCommandExecute}
          />,
          document.body
        )}

      {/* Provenance Sidebar (overlay, rendered via portal) */}
      {typeof window !== 'undefined' &&
        createPortal(
          <ProvenanceSidebar
            protocolId={protocolId}
          />,
          document.body
        )}
    </div>
  );
}
