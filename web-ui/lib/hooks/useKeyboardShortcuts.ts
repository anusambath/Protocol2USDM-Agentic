/**
 * useKeyboardShortcuts hook
 * 
 * Provides keyboard shortcut handling for provenance UI
 * 
 * Shortcuts:
 * - Esc: Close sidebar
 * - Cmd+K / Ctrl+K: Open search
 * - Cmd+P / Ctrl+P: Open preview
 * - Arrow keys: Navigate pages
 * - +/-: Zoom controls
 */

import { useEffect } from 'react';

export interface KeyboardShortcutHandlers {
  onEscape?: () => void;
  onSearch?: () => void;
  onPreview?: () => void;
  onArrowLeft?: () => void;
  onArrowRight?: () => void;
  onArrowUp?: () => void;
  onArrowDown?: () => void;
  onZoomIn?: () => void;
  onZoomOut?: () => void;
}

export function useKeyboardShortcuts(handlers: KeyboardShortcutHandlers) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Check if user is typing in an input field
      const target = e.target as HTMLElement;
      const isInputField = 
        target.tagName === 'INPUT' || 
        target.tagName === 'TEXTAREA' || 
        target.isContentEditable;

      // Esc key - always works, even in input fields
      if (e.key === 'Escape' && handlers.onEscape) {
        e.preventDefault();
        handlers.onEscape();
        return;
      }

      // Don't handle other shortcuts if user is typing
      if (isInputField) {
        return;
      }

      const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
      const modKey = isMac ? e.metaKey : e.ctrlKey;

      // Cmd/Ctrl + K - Search
      if (e.key === 'k' && modKey && handlers.onSearch) {
        e.preventDefault();
        handlers.onSearch();
        return;
      }

      // Cmd/Ctrl + P - Preview
      if (e.key === 'p' && modKey && handlers.onPreview) {
        e.preventDefault();
        handlers.onPreview();
        return;
      }

      // Arrow keys - Page navigation
      if (e.key === 'ArrowLeft' && handlers.onArrowLeft) {
        e.preventDefault();
        handlers.onArrowLeft();
        return;
      }

      if (e.key === 'ArrowRight' && handlers.onArrowRight) {
        e.preventDefault();
        handlers.onArrowRight();
        return;
      }

      if (e.key === 'ArrowUp' && handlers.onArrowUp) {
        e.preventDefault();
        handlers.onArrowUp();
        return;
      }

      if (e.key === 'ArrowDown' && handlers.onArrowDown) {
        e.preventDefault();
        handlers.onArrowDown();
        return;
      }

      // +/= key - Zoom in
      if ((e.key === '+' || e.key === '=') && handlers.onZoomIn) {
        e.preventDefault();
        handlers.onZoomIn();
        return;
      }

      // - key - Zoom out
      if (e.key === '-' && handlers.onZoomOut) {
        e.preventDefault();
        handlers.onZoomOut();
        return;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handlers]);
}
