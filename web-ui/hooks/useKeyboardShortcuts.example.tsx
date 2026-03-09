/**
 * Example usage of useKeyboardShortcuts hook in Workbench component
 * 
 * This file demonstrates how to integrate the keyboard shortcuts
 * into the main Workbench component.
 */

import { useKeyboardShortcuts, ShortcutConfig } from './useKeyboardShortcuts';
import { useLayoutStore } from '@/stores/layoutStore';

export function WorkbenchExample() {
  const {
    toggleSidebar,
    toggleRightPanel,
    closeTab,
    setActiveTab,
    activeTabId,
    openTabs,
  } = useLayoutStore();

  // Define keyboard shortcuts
  const shortcuts: ShortcutConfig[] = [
    // Ctrl/Cmd+S: Save Draft
    {
      key: 's',
      ctrl: true,
      action: () => {
        console.log('Save Draft');
        // Call save draft API
      },
      description: 'Save Draft',
    },
    
    // Ctrl/Cmd+B: Toggle Sidebar
    {
      key: 'b',
      ctrl: true,
      action: toggleSidebar,
      description: 'Toggle Sidebar',
    },
    
    // Ctrl/Cmd+J: Toggle Right Panel
    {
      key: 'j',
      ctrl: true,
      action: toggleRightPanel,
      description: 'Toggle Right Panel',
    },
    
    // Ctrl/Cmd+K: Command Palette
    {
      key: 'k',
      ctrl: true,
      action: () => {
        console.log('Open Command Palette');
        // Open command palette
      },
      description: 'Command Palette',
    },
    
    // Ctrl/Cmd+W: Close Active Tab
    {
      key: 'w',
      ctrl: true,
      action: () => {
        if (activeTabId) {
          closeTab(activeTabId);
        }
      },
      description: 'Close Active Tab',
    },
    
    // Ctrl/Cmd+1-9: Switch to tab at ordinal position
    ...Array.from({ length: 9 }, (_, i) => ({
      key: String(i + 1),
      ctrl: true,
      action: () => {
        const tab = openTabs[i];
        if (tab) {
          setActiveTab(tab.id);
        }
      },
      description: `Switch to tab ${i + 1}`,
    })),
  ];

  // Register keyboard shortcuts
  useKeyboardShortcuts(shortcuts);

  return (
    <div>
      {/* Workbench content */}
    </div>
  );
}
