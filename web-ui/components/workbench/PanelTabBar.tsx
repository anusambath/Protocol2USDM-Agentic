'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import * as LucideIcons from 'lucide-react';
import { cn } from '@/lib/utils';

interface PanelTabBarProps {
  tabs: { id: string; label: string; icon: string; closable?: boolean }[];
  activeTabId: string | null;
  onTabChange: (tabId: string) => void;
  onTabClose?: (tabId: string) => void;
}

export function PanelTabBar({ tabs, activeTabId, onTabChange, onTabClose }: PanelTabBarProps) {
  const tabListRef = useRef<HTMLDivElement>(null);
  const [focusedIndex, setFocusedIndex] = useState<number>(-1);

  // Get the Lucide icon component by name
  const getIcon = (iconName: string) => {
    const Icon = (LucideIcons as any)[iconName];
    return Icon || LucideIcons.FileText; // Fallback to FileText if icon not found
  };

  // Handle keyboard navigation between tabs
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (tabs.length === 0) return;

      const currentIndex = focusedIndex >= 0 ? focusedIndex : tabs.findIndex((tab) => tab.id === activeTabId);

      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        const newIndex = currentIndex > 0 ? currentIndex - 1 : tabs.length - 1;
        setFocusedIndex(newIndex);
        onTabChange(tabs[newIndex].id);
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        const newIndex = currentIndex < tabs.length - 1 ? currentIndex + 1 : 0;
        setFocusedIndex(newIndex);
        onTabChange(tabs[newIndex].id);
      } else if (e.key === 'Home') {
        e.preventDefault();
        setFocusedIndex(0);
        onTabChange(tabs[0].id);
      } else if (e.key === 'End') {
        e.preventDefault();
        const lastIndex = tabs.length - 1;
        setFocusedIndex(lastIndex);
        onTabChange(tabs[lastIndex].id);
      }
    },
    [tabs, activeTabId, focusedIndex, onTabChange]
  );

  // Handle tab click
  const handleTabClick = useCallback(
    (tabId: string, index: number) => {
      setFocusedIndex(index);
      onTabChange(tabId);
    },
    [onTabChange]
  );

  // Handle close button click
  const handleCloseClick = useCallback(
    (e: React.MouseEvent, tabId: string) => {
      e.stopPropagation(); // Prevent tab activation
      onTabClose?.(tabId);
    },
    [onTabClose]
  );

  // Reset focused index when tabs change
  useEffect(() => {
    if (focusedIndex >= tabs.length) {
      setFocusedIndex(tabs.length - 1);
    }
  }, [tabs.length, focusedIndex]);

  if (tabs.length === 0) {
    return null;
  }

  return (
    <div
      ref={tabListRef}
      role="tablist"
      aria-label="Panel tabs"
      className="flex items-center gap-0.5 overflow-x-auto overflow-y-hidden bg-muted/30 border-b border-border px-1 py-1 scrollbar-thin scrollbar-thumb-border scrollbar-track-transparent"
      onKeyDown={handleKeyDown}
    >
      {tabs.map((tab, index) => {
        const Icon = getIcon(tab.icon);
        const isActive = tab.id === activeTabId;
        const isFocused = index === focusedIndex;

        return (
          <div
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            aria-controls={`panel-${tab.id}`}
            tabIndex={isActive ? 0 : -1}
            className={cn(
              'group relative flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-md transition-colors whitespace-nowrap cursor-pointer',
              'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1',
              isActive
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
            )}
            onClick={() => handleTabClick(tab.id, index)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleTabClick(tab.id, index);
              }
            }}
          >
            <Icon className="h-4 w-4 flex-shrink-0" />
            <span className="truncate max-w-[120px]">{tab.label}</span>
            {tab.closable && onTabClose && (
              <button
                aria-label={`Close ${tab.label}`}
                className={cn(
                  'ml-1 flex-shrink-0 rounded-sm p-0.5 transition-colors',
                  'hover:bg-muted-foreground/20 focus:outline-none focus:ring-1 focus:ring-ring',
                  'opacity-0 group-hover:opacity-100',
                  isActive && 'opacity-100'
                )}
                onClick={(e) => handleCloseClick(e, tab.id)}
              >
                <LucideIcons.X className="h-3 w-3" />
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}
