'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { ActivityBarMode, ViewType } from '@/stores/layoutStore';
import { NavTree } from './NavTree';
import { SearchPanel } from './SearchPanel';
import { QualityPanel } from './QualityPanel';

interface SidebarProps {
  mode: ActivityBarMode;
  collapsed: boolean;
  width: number;
  activeTabId: string | null;
  expandedGroups: Record<string, boolean>;
  onNavigate: (viewType: ViewType) => void;
  onToggleGroup: (groupId: string) => void;
}

export function Sidebar({
  mode,
  collapsed,
  width,
  activeTabId,
  expandedGroups,
  onNavigate,
  onToggleGroup,
}: SidebarProps) {
  // Determine which content to render based on mode
  const renderContent = () => {
    switch (mode) {
      case 'explorer':
        return (
          <NavTree
            activeTabId={activeTabId}
            expandedGroups={expandedGroups}
            onNavigate={onNavigate}
            onToggleGroup={onToggleGroup}
          />
        );
      case 'search':
        return <SearchPanel onNavigate={onNavigate} />;
      case 'quality':
        return <QualityPanel />;
      default:
        return null;
    }
  };

  return (
    <motion.aside
      initial={false}
      animate={{ width: collapsed ? 0 : width }}
      transition={{
        duration: 0.2,
        ease: 'easeInOut',
      }}
      className="flex flex-col bg-background border-r border-border overflow-hidden"
      style={{ minWidth: collapsed ? 0 : undefined }}
    >
      {!collapsed && (
        <div className="flex flex-col h-full overflow-hidden">
          {/* Sidebar Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-border">
            <h2 className="text-sm font-semibold text-foreground">
              {mode === 'explorer' && 'Explorer'}
              {mode === 'search' && 'Search'}
              {mode === 'quality' && 'Quality'}
            </h2>
          </div>

          {/* Sidebar Content */}
          <div className="flex-1 overflow-y-auto">
            {renderContent()}
          </div>
        </div>
      )}
    </motion.aside>
  );
}
