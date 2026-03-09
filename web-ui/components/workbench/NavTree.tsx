'use client';

import React, { useRef, useEffect } from 'react';
import * as LucideIcons from 'lucide-react';
import { ViewType } from '@/stores/layoutStore';
import { viewRegistry } from '@/lib/viewRegistry';
import { ChevronRight } from 'lucide-react';

interface NavTreeProps {
  activeTabId: string | null;
  expandedGroups: Record<string, boolean>;
  onNavigate: (viewType: ViewType) => void;
  onToggleGroup: (groupId: string) => void;
}

interface NavGroup {
  id: string;
  label: string;
  icon: keyof typeof LucideIcons;
  items: ViewType[];
}

// Static group definitions matching requirements
const NAV_GROUPS: NavGroup[] = [
  {
    id: 'protocol',
    label: 'Protocol',
    icon: 'FileText',
    items: ['overview', 'eligibility', 'objectives', 'design', 'interventions', 'amendments'],
  },
  {
    id: 'advanced',
    label: 'Advanced',
    icon: 'Settings',
    items: ['extensions', 'entities', 'procedures', 'sites', 'footnotes', 'schedule', 'narrative'],
  },
  {
    id: 'quality',
    label: 'Quality',
    icon: 'CheckCircle2',
    items: ['quality', 'validation'],
  },
  {
    id: 'data',
    label: 'Data',
    icon: 'Database',
    items: ['document', 'images', 'soa', 'timeline', 'provenance'],
  },
];

export function NavTree({ activeTabId, expandedGroups, onNavigate, onToggleGroup }: NavTreeProps) {
  const treeRef = useRef<HTMLDivElement>(null);
  const [focusedIndex, setFocusedIndex] = React.useState<number>(-1);

  // Build flat list of all focusable items (groups + items) for keyboard navigation
  const focusableItems = React.useMemo(() => {
    const items: Array<{ type: 'group' | 'item'; id: string; groupId?: string; viewType?: ViewType }> = [];
    
    NAV_GROUPS.forEach((group) => {
      items.push({ type: 'group', id: group.id });
      if (expandedGroups[group.id]) {
        group.items.forEach((viewType) => {
          items.push({ type: 'item', id: viewType, groupId: group.id, viewType });
        });
      }
    });
    
    return items;
  }, [expandedGroups]);

  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!treeRef.current?.contains(document.activeElement)) return;

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setFocusedIndex((prev) => Math.min(prev + 1, focusableItems.length - 1));
          break;
        case 'ArrowUp':
          e.preventDefault();
          setFocusedIndex((prev) => Math.max(prev - 1, 0));
          break;
        case 'ArrowRight': {
          e.preventDefault();
          const item = focusableItems[focusedIndex];
          if (item?.type === 'group' && !expandedGroups[item.id]) {
            onToggleGroup(item.id);
          }
          break;
        }
        case 'ArrowLeft': {
          e.preventDefault();
          const item = focusableItems[focusedIndex];
          if (item?.type === 'group' && expandedGroups[item.id]) {
            onToggleGroup(item.id);
          } else if (item?.type === 'item' && item.groupId) {
            // Navigate to parent group
            const groupIndex = focusableItems.findIndex((i) => i.type === 'group' && i.id === item.groupId);
            if (groupIndex !== -1) {
              setFocusedIndex(groupIndex);
            }
          }
          break;
        }
        case 'Enter':
        case ' ': {
          e.preventDefault();
          const item = focusableItems[focusedIndex];
          if (item?.type === 'group') {
            onToggleGroup(item.id);
          } else if (item?.type === 'item' && item.viewType) {
            onNavigate(item.viewType);
          }
          break;
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [focusedIndex, focusableItems, expandedGroups, onToggleGroup, onNavigate]);

  // Auto-focus the focused item
  useEffect(() => {
    if (focusedIndex >= 0 && treeRef.current) {
      const focusableElements = treeRef.current.querySelectorAll('[data-focusable]');
      const element = focusableElements[focusedIndex] as HTMLElement;
      element?.focus();
    }
  }, [focusedIndex]);

  return (
    <nav
      ref={treeRef}
      role="tree"
      aria-label="Protocol navigation"
      className="flex flex-col gap-1 p-2 overflow-y-auto"
    >
      {NAV_GROUPS.map((group) => {
        const isExpanded = expandedGroups[group.id] ?? false;
        const GroupIcon = LucideIcons[group.icon] as React.ComponentType<{ className?: string }>;

        return (
          <div key={group.id} role="treeitem" aria-expanded={isExpanded}>
            {/* Group Header */}
            <button
              data-focusable
              onClick={() => onToggleGroup(group.id)}
              className="flex items-center gap-2 w-full px-2 py-1.5 text-sm font-medium rounded hover:bg-accent focus:outline-none focus:ring-2 focus:ring-ring"
              aria-label={`${group.label} group, ${isExpanded ? 'expanded' : 'collapsed'}`}
            >
              <ChevronRight
                className={`h-4 w-4 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
                aria-hidden="true"
              />
              <GroupIcon className="h-4 w-4" aria-hidden="true" />
              <span>{group.label}</span>
            </button>

            {/* Group Items */}
            {isExpanded && (
              <div role="group" className="ml-6 mt-1 flex flex-col gap-0.5">
                {group.items.map((viewType) => {
                  const entry = viewRegistry[viewType];
                  if (!entry) return null;

                  const ItemIcon = LucideIcons[entry.icon as keyof typeof LucideIcons] as React.ComponentType<{ className?: string }>;
                  const isActive = activeTabId === viewType;

                  return (
                    <button
                      key={viewType}
                      data-focusable
                      role="treeitem"
                      onClick={() => onNavigate(viewType)}
                      className={`flex items-center gap-2 w-full px-2 py-1.5 text-sm rounded transition-colors focus:outline-none focus:ring-2 focus:ring-ring ${
                        isActive
                          ? 'bg-accent text-accent-foreground font-medium'
                          : 'hover:bg-accent/50 text-muted-foreground hover:text-foreground'
                      }`}
                      aria-label={entry.label}
                      aria-current={isActive ? 'page' : undefined}
                    >
                      {ItemIcon && <ItemIcon className="h-4 w-4" aria-hidden="true" />}
                      <span>{entry.label}</span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
    </nav>
  );
}
