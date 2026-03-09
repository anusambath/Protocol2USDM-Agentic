'use client';

import React from 'react';
import { NavTree } from './NavTree';
import { ViewType } from '@/stores/layoutStore';

/**
 * Example: Basic NavTree with controlled state
 */
export function BasicNavTreeExample() {
  const [activeTabId, setActiveTabId] = React.useState<string | null>('overview');
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
    <div className="w-64 h-screen border-r bg-background">
      <div className="p-4 border-b">
        <h2 className="text-lg font-semibold">Navigation</h2>
      </div>
      <NavTree
        activeTabId={activeTabId}
        expandedGroups={expandedGroups}
        onNavigate={handleNavigate}
        onToggleGroup={handleToggleGroup}
      />
    </div>
  );
}

/**
 * Example: NavTree with all groups expanded
 */
export function ExpandedNavTreeExample() {
  const [activeTabId, setActiveTabId] = React.useState<string | null>('soa');
  const [expandedGroups] = React.useState<Record<string, boolean>>({
    protocol: true,
    advanced: true,
    quality: true,
    data: true,
  });

  const handleNavigate = (viewType: ViewType) => {
    console.log('Navigate to:', viewType);
    setActiveTabId(viewType);
  };

  const handleToggleGroup = (groupId: string) => {
    console.log('Toggle group:', groupId);
  };

  return (
    <div className="w-64 h-screen border-r bg-background">
      <div className="p-4 border-b">
        <h2 className="text-lg font-semibold">All Groups Expanded</h2>
      </div>
      <NavTree
        activeTabId={activeTabId}
        expandedGroups={expandedGroups}
        onNavigate={handleNavigate}
        onToggleGroup={handleToggleGroup}
      />
    </div>
  );
}

/**
 * Example: NavTree with no active item
 */
export function NoActiveItemExample() {
  const [expandedGroups, setExpandedGroups] = React.useState<Record<string, boolean>>({
    protocol: true,
    advanced: false,
    quality: false,
    data: true,
  });

  const handleNavigate = (viewType: ViewType) => {
    console.log('Navigate to:', viewType);
  };

  const handleToggleGroup = (groupId: string) => {
    setExpandedGroups((prev) => ({
      ...prev,
      [groupId]: !prev[groupId],
    }));
  };

  return (
    <div className="w-64 h-screen border-r bg-background">
      <div className="p-4 border-b">
        <h2 className="text-lg font-semibold">No Active Item</h2>
      </div>
      <NavTree
        activeTabId={null}
        expandedGroups={expandedGroups}
        onNavigate={handleNavigate}
        onToggleGroup={handleToggleGroup}
      />
    </div>
  );
}

/**
 * Example: NavTree with keyboard navigation demo
 */
export function KeyboardNavigationExample() {
  const [activeTabId, setActiveTabId] = React.useState<string | null>('timeline');
  const [expandedGroups, setExpandedGroups] = React.useState<Record<string, boolean>>({
    protocol: false,
    advanced: false,
    quality: false,
    data: true,
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
    <div className="w-64 h-screen border-r bg-background">
      <div className="p-4 border-b">
        <h2 className="text-lg font-semibold">Keyboard Navigation</h2>
        <p className="text-xs text-muted-foreground mt-2">
          Use arrow keys to navigate, Enter/Space to activate
        </p>
      </div>
      <NavTree
        activeTabId={activeTabId}
        expandedGroups={expandedGroups}
        onNavigate={handleNavigate}
        onToggleGroup={handleToggleGroup}
      />
    </div>
  );
}
