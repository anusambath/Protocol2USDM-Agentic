'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import * as LucideIcons from 'lucide-react';
import { commandRegistry, searchCommands, CommandEntry } from '@/lib/commandRegistry';
import { cn } from '@/lib/utils';

export interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onExecute: (commandId: string) => void;
}

export function CommandPalette({ isOpen, onClose, onExecute }: CommandPaletteProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<CommandEntry[]>(commandRegistry);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listboxRef = useRef<HTMLDivElement>(null);

  // Update results when query changes
  useEffect(() => {
    const filtered = searchCommands(query);
    setResults(filtered);
    setSelectedIndex(0); // Reset selection when results change
  }, [query]);

  // Focus input when palette opens
  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus();
      setQuery(''); // Clear query on open
      setResults(commandRegistry); // Show all commands initially
      setSelectedIndex(0);
    }
  }, [isOpen]);

  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex((prev) => Math.min(prev + 1, results.length - 1));
          break;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex((prev) => Math.max(prev - 1, 0));
          break;
        case 'Enter':
          e.preventDefault();
          if (results[selectedIndex]) {
            onExecute(results[selectedIndex].id);
            onClose();
          }
          break;
        case 'Escape':
          e.preventDefault();
          onClose();
          break;
      }
    },
    [results, selectedIndex, onExecute, onClose]
  );

  // Scroll selected item into view
  useEffect(() => {
    if (listboxRef.current && isOpen) {
      const selectedElement = listboxRef.current.querySelector(
        `[data-index="${selectedIndex}"]`
      ) as HTMLElement;
      selectedElement?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  }, [selectedIndex, isOpen]);

  // Handle click outside to close
  const handleBackdropClick = useCallback(
    (e: React.MouseEvent) => {
      if (e.target === e.currentTarget) {
        onClose();
      }
    },
    [onClose]
  );

  // Get icon component by name
  const getIcon = (iconName: string) => {
    const Icon = (LucideIcons as any)[iconName];
    return Icon || LucideIcons.FileText;
  };

  // Prevent body scroll when open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          className="fixed inset-0 z-50 flex items-start justify-center bg-black/50 backdrop-blur-sm"
          onClick={handleBackdropClick}
          role="dialog"
          aria-modal="true"
          aria-label="Command Palette"
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className="mt-[20vh] w-full max-w-2xl mx-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="bg-background border border-border rounded-lg shadow-2xl overflow-hidden">
              {/* Search Input */}
              <div
                role="combobox"
                aria-expanded="true"
                aria-haspopup="listbox"
                aria-owns="command-listbox"
                aria-controls="command-listbox"
                className="relative"
              >
                <div className="flex items-center gap-3 px-4 py-3 border-b border-border">
                  <LucideIcons.Search className="w-5 h-5 text-muted-foreground flex-shrink-0" />
                  <input
                    ref={inputRef}
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Type a command or search..."
                    className="flex-1 bg-transparent text-foreground placeholder:text-muted-foreground outline-none text-base"
                    aria-autocomplete="list"
                    aria-controls="command-listbox"
                    aria-activedescendant={
                      results[selectedIndex] ? `command-${results[selectedIndex].id}` : undefined
                    }
                  />
                  <kbd className="hidden sm:inline-flex items-center gap-1 px-2 py-1 text-xs font-mono text-muted-foreground bg-muted rounded border border-border">
                    ESC
                  </kbd>
                </div>
              </div>

              {/* Results List */}
              <div
                ref={listboxRef}
                id="command-listbox"
                role="listbox"
                aria-label="Command results"
                className="max-h-[400px] overflow-y-auto overscroll-contain"
              >
                {results.length === 0 ? (
                  <div className="px-4 py-8 text-center text-muted-foreground">
                    <LucideIcons.SearchX className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">No commands found</p>
                    <p className="text-xs mt-1">Try a different search term</p>
                  </div>
                ) : (
                  <div className="py-2">
                    {/* Group by category */}
                    {['navigation', 'action'].map((category) => {
                      const categoryResults = results.filter((cmd) => cmd.category === category);
                      if (categoryResults.length === 0) return null;

                      return (
                        <div key={category} className="mb-2 last:mb-0">
                          <div className="px-4 py-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                            {category === 'navigation' ? 'Navigate to' : 'Actions'}
                          </div>
                          {categoryResults.map((command) => {
                            const Icon = getIcon(command.icon);
                            const index = results.indexOf(command);
                            const isSelected = index === selectedIndex;

                            return (
                              <button
                                key={command.id}
                                id={`command-${command.id}`}
                                role="option"
                                aria-selected={isSelected}
                                data-index={index}
                                onClick={() => {
                                  onExecute(command.id);
                                  onClose();
                                }}
                                className={cn(
                                  'w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors',
                                  'focus:outline-none',
                                  isSelected
                                    ? 'bg-accent text-accent-foreground'
                                    : 'hover:bg-accent/50'
                                )}
                              >
                                <Icon className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
                                <span className="flex-1 text-sm font-medium">{command.label}</span>
                                {command.shortcut && (
                                  <kbd className="hidden sm:inline-flex items-center gap-0.5 px-2 py-0.5 text-xs font-mono text-muted-foreground bg-muted rounded border border-border">
                                    {command.shortcut}
                                  </kbd>
                                )}
                              </button>
                            );
                          })}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Footer hint */}
              <div className="px-4 py-2 border-t border-border bg-muted/30 flex items-center gap-4 text-xs text-muted-foreground">
                <span className="flex items-center gap-1.5">
                  <kbd className="px-1.5 py-0.5 bg-background rounded border border-border">↑</kbd>
                  <kbd className="px-1.5 py-0.5 bg-background rounded border border-border">↓</kbd>
                  to navigate
                </span>
                <span className="flex items-center gap-1.5">
                  <kbd className="px-1.5 py-0.5 bg-background rounded border border-border">↵</kbd>
                  to select
                </span>
                <span className="flex items-center gap-1.5">
                  <kbd className="px-1.5 py-0.5 bg-background rounded border border-border">ESC</kbd>
                  to close
                </span>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
