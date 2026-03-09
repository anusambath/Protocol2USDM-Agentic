'use client';

import React from 'react';
import { Sidebar } from './Sidebar';
import { ActivityBarMode, ViewType } from '@/stores/layoutStore';

/**
 * Example usage of the Sidebar component
 * 
 * This example demonstrates how to use the Sidebar component with different modes:
 * - Explorer mode: Shows the NavTree for hierarchical navigation
 * - Search mode: Shows the SearchPanel (placeholder)
 * - Quality mode: Shows the QualityPanel (placeholder)
 */
export function SidebarExample() {
  const [mode, setMode] = React.useState<ActivityBarMode>('explorer');
  const [collapsed, setCollapsed] = React.useState(false);
  const [width] = React.useState(260);
  const [activeTabId, setActiveTabId] = React.useState<string | null>(null);
  const [expandedGroups, setExpandedGroups] = React.useState<Record<string, boolean>>({
    protocol: true,
    advanced: false,
    quality: false,
    data: false,
  });

  const handleNavigate = (viewType: ViewType) => {
    console.log('Navigate to:', viewType);
    setActiveTabId(viewType);
  };

  const handleToggleGroup = (groupId: string) => {
    setExpandedGroups((prev) => ({
      ...prev,
      [groupId]: !prev[groupId],
    }));
  };

  return (
    <div className="flex h-screen">
      {/* Mode selector */}
      <div className="flex flex-col gap-2 p-4 bg-muted">
        <button
          onClick={() => setMode('explorer')}
          className={`px-3 py-2 rounded ${mode === 'explorer' ? 'bg-primary text-primary-foreground' : 'bg-background'}`}
        >
          Explorer
        </button>
        <button
          onClick={() => setMode('search')}
          className={`px-3 py-2 rounded ${mode === 'search' ? 'bg-primary text-primary-foreground' : 'bg-background'}`}
        >
          Search
        </button>
        <button
          onClick={() => setMode('quality')}
          className={`px-3 py-2 rounded ${mode === 'quality' ? 'bg-primary text-primary-foreground' : 'bg-background'}`}
        >
          Quality
        </button>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="px-3 py-2 rounded bg-background mt-4"
        >
          {collapsed ? 'Expand' : 'Collapse'}
        </button>
      </div>

      {/* Sidebar */}
      <Sidebar
        mode={mode}
        collapsed={collapsed}
        width={width}
        activeTabId={activeTabId}
        expandedGroups={expandedGroups}
        onNavigate={handleNavigate}
        onToggleGroup={handleToggleGroup}
      />

      {/* Main content area */}
      <div className="flex-1 p-8 bg-background">
        <h1 className="text-2xl font-bold mb-4">Sidebar Example</h1>
        <p className="text-muted-foreground mb-4">
          Use the buttons on the left to switch between different sidebar modes and toggle collapse state.
        </p>
        {activeTabId && (
          <div className="p-4 bg-muted rounded">
            <p className="font-medium">Active Tab: {activeTabId}</p>
          </div>
        )}
      </div>
    </div>
  );
}
