import { useEffect } from 'react';

export interface ShortcutConfig {
  key: string;
  ctrl?: boolean;
  meta?: boolean;
  action: () => void;
  description: string;
}

/**
 * useKeyboardShortcuts Hook (Keyboard_Manager)
 * 
 * Registers global keyboard shortcuts with the following logic:
 * 1. Check focus context - skip if target is input, textarea, or has [data-ag-grid-editor]
 * 2. Match shortcut - build key string and look up in registry
 * 3. Execute action - call preventDefault() and execute registered action
 * 
 * Shortcuts are defined by the consumer and typically include:
 * - Ctrl/Cmd+S: Save Draft
 * - Ctrl/Cmd+B: Toggle Sidebar
 * - Ctrl/Cmd+J: Toggle Right Panel
 * - Ctrl/Cmd+K: Command Palette
 * - Ctrl/Cmd+W: Close Active Tab
 * - Ctrl/Cmd+1-9: Switch to tab at ordinal position
 * 
 * @param shortcuts - Array of shortcut configurations
 * 
 * @example
 * ```tsx
 * useKeyboardShortcuts([
 *   { key: 's', ctrl: true, action: handleSave, description: 'Save Draft' },
 *   { key: 'b', ctrl: true, action: toggleSidebar, description: 'Toggle Sidebar' },
 * ]);
 * ```
 */
export function useKeyboardShortcuts(shortcuts: ShortcutConfig[]) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // 1. Check focus context - skip interception for input elements
      const target = event.target as HTMLElement;
      const isInputElement =
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.hasAttribute('data-ag-grid-editor') ||
        target.isContentEditable;

      if (isInputElement) {
        return; // Allow default input behavior
      }

      // 2. Build key string for matching
      const isMac = typeof navigator !== 'undefined' && /Mac/.test(navigator.platform);
      const modifierKey = isMac ? event.metaKey : event.ctrlKey;
      
      // Normalize key to lowercase for consistent matching
      const key = event.key.toLowerCase();

      // 3. Match shortcut in registry
      const matchedShortcut = shortcuts.find((shortcut) => {
        const keyMatches = shortcut.key.toLowerCase() === key;
        
        // For shortcuts that specify ctrl or meta, check if the appropriate modifier is pressed
        // On Mac, Cmd key is used (metaKey), on Windows/Linux, Ctrl key is used (ctrlKey)
        if (shortcut.ctrl || shortcut.meta) {
          return keyMatches && modifierKey;
        }

        // For shortcuts without modifiers, just match the key
        return keyMatches;
      });

      // 4. Execute action if matched
      if (matchedShortcut) {
        event.preventDefault();
        matchedShortcut.action();
      }
    };

    // Register global keydown listener
    window.addEventListener('keydown', handleKeyDown);

    // Cleanup on unmount
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [shortcuts]);
}
