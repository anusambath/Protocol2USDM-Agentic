'use client';

import { FolderTree, Search, CheckCircle2 } from 'lucide-react';
import { ActivityBarMode } from '@/stores/layoutStore';
import { cn } from '@/lib/utils';

export interface ActivityBarProps {
  activeMode: ActivityBarMode;
  onModeChange: (mode: ActivityBarMode) => void;
  onToggleSidebar: () => void;
}

interface ActivityBarButton {
  mode: ActivityBarMode;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
}

const ACTIVITY_BAR_BUTTONS: ActivityBarButton[] = [
  {
    mode: 'explorer',
    icon: FolderTree,
    label: 'Explorer',
  },
  {
    mode: 'search',
    icon: Search,
    label: 'Search',
  },
  {
    mode: 'quality',
    icon: CheckCircle2,
    label: 'Quality',
  },
];

export function ActivityBar({ activeMode, onModeChange, onToggleSidebar }: ActivityBarProps) {
  const handleButtonClick = (mode: ActivityBarMode) => {
    if (mode === activeMode) {
      // Clicking active mode toggles sidebar collapse
      onToggleSidebar();
    } else {
      // Clicking inactive mode switches to that mode
      onModeChange(mode);
    }
  };

  return (
    <div
      role="toolbar"
      aria-label="Activity Bar"
      className="w-12 h-full bg-muted/40 border-r border-border flex flex-col items-center py-2 gap-1"
    >
      {ACTIVITY_BAR_BUTTONS.map(({ mode, icon: Icon, label }) => {
        const isActive = mode === activeMode;

        return (
          <button
            key={mode}
            onClick={() => handleButtonClick(mode)}
            aria-label={label}
            aria-pressed={isActive}
            className={cn(
              'w-10 h-10 flex items-center justify-center rounded-md transition-colors',
              'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1',
              isActive
                ? 'bg-accent text-accent-foreground'
                : 'text-muted-foreground hover:text-foreground hover:bg-accent/50'
            )}
          >
            <Icon className="h-5 w-5" aria-hidden="true" />
          </button>
        );
      })}
    </div>
  );
}
