'use client';

import { useState } from 'react';
import { PanelTabBar } from './PanelTabBar';

/**
 * Example 1: Basic tab bar with closable tabs
 */
export function BasicTabBarExample() {
  const [activeTabId, setActiveTabId] = useState('overview');
  const [tabs, setTabs] = useState([
    { id: 'overview', label: 'Overview', icon: 'FileText', closable: true },
    { id: 'timeline', label: 'Timeline', icon: 'Clock', closable: true },
    { id: 'schedule', label: 'Schedule', icon: 'Calendar', closable: true },
    { id: 'soa', label: 'Schedule of Activities', icon: 'Table', closable: true },
  ]);

  const handleTabClose = (tabId: string) => {
    const newTabs = tabs.filter((tab) => tab.id !== tabId);
    setTabs(newTabs);

    // If closing the active tab, switch to the first remaining tab
    if (tabId === activeTabId && newTabs.length > 0) {
      setActiveTabId(newTabs[0].id);
    } else if (newTabs.length === 0) {
      setActiveTabId('');
    }
  };

  return (
    <div className="w-full max-w-4xl border border-border rounded-lg overflow-hidden">
      <PanelTabBar
        tabs={tabs}
        activeTabId={activeTabId}
        onTabChange={setActiveTabId}
        onTabClose={handleTabClose}
      />
      <div className="p-4 bg-background">
        <p className="text-sm text-muted-foreground">
          Active Tab: <span className="font-medium text-foreground">{activeTabId || 'None'}</span>
        </p>
        <p className="text-xs text-muted-foreground mt-2">
          Try clicking tabs, using arrow keys to navigate, or closing tabs with the X button.
        </p>
      </div>
    </div>
  );
}

/**
 * Example 2: Tab bar without close buttons (non-closable tabs)
 */
export function NonClosableTabBarExample() {
  const [activeTabId, setActiveTabId] = useState('properties');

  const tabs = [
    { id: 'properties', label: 'Properties', icon: 'Settings' },
    { id: 'provenance', label: 'Provenance', icon: 'FileSearch' },
    { id: 'footnotes', label: 'Footnotes', icon: 'FileText' },
  ];

  return (
    <div className="w-full max-w-2xl border border-border rounded-lg overflow-hidden">
      <PanelTabBar
        tabs={tabs}
        activeTabId={activeTabId}
        onTabChange={setActiveTabId}
        // No onTabClose prop - close buttons won't render
      />
      <div className="p-4 bg-background">
        <p className="text-sm text-muted-foreground">
          Active Tab: <span className="font-medium text-foreground">{activeTabId}</span>
        </p>
        <p className="text-xs text-muted-foreground mt-2">
          These tabs cannot be closed (no X button).
        </p>
      </div>
    </div>
  );
}

/**
 * Example 3: Many tabs with overflow scroll
 */
export function OverflowTabBarExample() {
  const [activeTabId, setActiveTabId] = useState('tab1');

  const tabs = Array.from({ length: 15 }, (_, i) => ({
    id: `tab${i + 1}`,
    label: `Tab ${i + 1}`,
    icon: i % 3 === 0 ? 'FileText' : i % 3 === 1 ? 'Clock' : 'Calendar',
    closable: true,
  }));

  return (
    <div className="w-full max-w-3xl border border-border rounded-lg overflow-hidden">
      <PanelTabBar
        tabs={tabs}
        activeTabId={activeTabId}
        onTabChange={setActiveTabId}
        onTabClose={(tabId) => console.log('Close tab:', tabId)}
      />
      <div className="p-4 bg-background">
        <p className="text-sm text-muted-foreground">
          Active Tab: <span className="font-medium text-foreground">{activeTabId}</span>
        </p>
        <p className="text-xs text-muted-foreground mt-2">
          Scroll horizontally to see all tabs. Try using arrow keys to navigate.
        </p>
      </div>
    </div>
  );
}

/**
 * Example 4: Empty state (no tabs)
 */
export function EmptyTabBarExample() {
  return (
    <div className="w-full max-w-2xl border border-border rounded-lg overflow-hidden">
      <PanelTabBar tabs={[]} activeTabId={null} onTabChange={() => {}} />
      <div className="p-4 bg-background">
        <p className="text-sm text-muted-foreground">No tabs to display (component returns null).</p>
      </div>
    </div>
  );
}

/**
 * Example 5: Center Panel use case
 */
export function CenterPanelTabBarExample() {
  const [activeTabId, setActiveTabId] = useState('soa');
  const [tabs, setTabs] = useState([
    { id: 'overview', label: 'Overview', icon: 'FileText', closable: true },
    { id: 'soa', label: 'Schedule of Activities', icon: 'Table', closable: true },
    { id: 'timeline', label: 'Timeline', icon: 'Clock', closable: true },
    { id: 'quality', label: 'Quality Metrics', icon: 'BarChart3', closable: true },
  ]);

  const handleTabClose = (tabId: string) => {
    const closedIndex = tabs.findIndex((tab) => tab.id === tabId);
    const newTabs = tabs.filter((tab) => tab.id !== tabId);
    setTabs(newTabs);

    // MRU fallback: switch to the tab before the closed one, or the first tab
    if (tabId === activeTabId && newTabs.length > 0) {
      const newActiveIndex = Math.max(0, closedIndex - 1);
      setActiveTabId(newTabs[newActiveIndex].id);
    } else if (newTabs.length === 0) {
      setActiveTabId('');
    }
  };

  return (
    <div className="w-full max-w-4xl border border-border rounded-lg overflow-hidden bg-muted/30">
      <PanelTabBar
        tabs={tabs}
        activeTabId={activeTabId}
        onTabChange={setActiveTabId}
        onTabClose={handleTabClose}
      />
      <div className="p-8 bg-background min-h-[300px]">
        <h2 className="text-lg font-semibold mb-2">
          {tabs.find((tab) => tab.id === activeTabId)?.label || 'No Tab Selected'}
        </h2>
        <p className="text-sm text-muted-foreground">
          This simulates the Center Panel with multiple open views. Close tabs to see MRU fallback behavior.
        </p>
      </div>
    </div>
  );
}
