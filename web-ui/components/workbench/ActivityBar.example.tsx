'use client';

import { useState } from 'react';
import { ActivityBar } from './ActivityBar';
import { ActivityBarMode } from '@/stores/layoutStore';

export default function ActivityBarExample() {
  const [activeMode, setActiveMode] = useState<ActivityBarMode>('explorer');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const handleModeChange = (mode: ActivityBarMode) => {
    setActiveMode(mode);
    // Ensure sidebar is expanded when switching modes
    setSidebarCollapsed(false);
  };

  const handleToggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  return (
    <div className="h-screen flex">
      <ActivityBar
        activeMode={activeMode}
        onModeChange={handleModeChange}
        onToggleSidebar={handleToggleSidebar}
      />
      
      <div className="flex-1 p-8 bg-background">
        <div className="space-y-4">
          <h1 className="text-2xl font-bold">ActivityBar Example</h1>
          
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">
              Click the icons in the activity bar to switch modes or toggle the sidebar.
            </p>
            
            <div className="p-4 border rounded-lg space-y-2">
              <div className="flex items-center gap-2">
                <span className="font-medium">Active Mode:</span>
                <span className="px-2 py-1 bg-accent rounded text-sm">{activeMode}</span>
              </div>
              
              <div className="flex items-center gap-2">
                <span className="font-medium">Sidebar State:</span>
                <span className="px-2 py-1 bg-accent rounded text-sm">
                  {sidebarCollapsed ? 'Collapsed' : 'Expanded'}
                </span>
              </div>
            </div>
            
            <div className="space-y-2">
              <h2 className="font-semibold">Behavior:</h2>
              <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                <li>Click an inactive mode icon to switch to that mode (sidebar expands)</li>
                <li>Click the active mode icon to toggle sidebar collapse/expand</li>
                <li>Active mode is highlighted with accent background</li>
                <li>Inactive modes show hover effects</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
