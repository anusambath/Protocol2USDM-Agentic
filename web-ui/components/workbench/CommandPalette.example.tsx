'use client';

import { useState } from 'react';
import { CommandPalette } from './CommandPalette';
import { Button } from '@/components/ui/button';

export default function CommandPaletteExample() {
  const [isOpen, setIsOpen] = useState(false);
  const [lastExecuted, setLastExecuted] = useState<string | null>(null);

  const handleExecute = (commandId: string) => {
    setLastExecuted(commandId);
    console.log('Executed command:', commandId);
  };

  return (
    <div className="p-8 space-y-4">
      <div className="space-y-2">
        <h2 className="text-2xl font-bold">CommandPalette Component</h2>
        <p className="text-muted-foreground">
          A keyboard-activated command palette for quick navigation and actions.
        </p>
      </div>

      <div className="space-y-4">
        <div className="flex items-center gap-4">
          <Button onClick={() => setIsOpen(true)}>
            Open Command Palette
          </Button>
          <kbd className="px-2 py-1 text-xs font-mono bg-muted rounded border border-border">
            Ctrl/Cmd+K
          </kbd>
        </div>

        {lastExecuted && (
          <div className="p-4 bg-muted rounded-lg">
            <p className="text-sm">
              <span className="font-semibold">Last executed command:</span>{' '}
              <code className="px-2 py-0.5 bg-background rounded text-xs">
                {lastExecuted}
              </code>
            </p>
          </div>
        )}
      </div>

      <div className="space-y-2 text-sm">
        <h3 className="font-semibold">Features:</h3>
        <ul className="list-disc list-inside space-y-1 text-muted-foreground">
          <li>Fuzzy search across 28 commands (20 navigation + 8 actions)</li>
          <li>Keyboard navigation with Arrow Up/Down</li>
          <li>Enter to select, Escape to close</li>
          <li>Categorized results (Navigate to / Actions)</li>
          <li>Shortcut hints for commands</li>
          <li>Animated entry/exit with Framer Motion</li>
          <li>ARIA combobox pattern for accessibility</li>
          <li>Focus trap while open</li>
        </ul>
      </div>

      <div className="space-y-2 text-sm">
        <h3 className="font-semibold">Try searching for:</h3>
        <ul className="list-disc list-inside space-y-1 text-muted-foreground">
          <li>"soa" → Schedule of Activities</li>
          <li>"save" → Save Draft</li>
          <li>"timeline" → Timeline Graph</li>
          <li>"toggle" → Toggle Sidebar / Toggle Right Panel</li>
          <li>"export" → Export CSV / JSON / PDF</li>
        </ul>
      </div>

      <CommandPalette
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        onExecute={handleExecute}
      />
    </div>
  );
}
