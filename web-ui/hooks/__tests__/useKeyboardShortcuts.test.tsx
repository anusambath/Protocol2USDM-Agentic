import { renderHook } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useKeyboardShortcuts, ShortcutConfig } from '../useKeyboardShortcuts';

describe('useKeyboardShortcuts', () => {
  let mockAction: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockAction = vi.fn();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should execute action when matching shortcut is pressed', () => {
    const shortcuts: ShortcutConfig[] = [
      {
        key: 's',
        ctrl: true,
        action: mockAction,
        description: 'Save Draft',
      },
    ];

    renderHook(() => useKeyboardShortcuts(shortcuts));

    const event = new KeyboardEvent('keydown', {
      key: 's',
      ctrlKey: true,
      bubbles: true,
    });

    window.dispatchEvent(event);

    expect(mockAction).toHaveBeenCalledTimes(1);
  });

  it('should call preventDefault when shortcut matches', () => {
    const shortcuts: ShortcutConfig[] = [
      {
        key: 's',
        ctrl: true,
        action: mockAction,
        description: 'Save Draft',
      },
    ];

    renderHook(() => useKeyboardShortcuts(shortcuts));

    const event = new KeyboardEvent('keydown', {
      key: 's',
      ctrlKey: true,
      bubbles: true,
      cancelable: true,
    });

    const preventDefaultSpy = vi.spyOn(event, 'preventDefault');

    window.dispatchEvent(event);

    expect(preventDefaultSpy).toHaveBeenCalled();
    expect(mockAction).toHaveBeenCalled();
  });

  it('should not execute action when focus is in input element', () => {
    const shortcuts: ShortcutConfig[] = [
      {
        key: 's',
        ctrl: true,
        action: mockAction,
        description: 'Save Draft',
      },
    ];

    renderHook(() => useKeyboardShortcuts(shortcuts));

    const input = document.createElement('input');
    document.body.appendChild(input);

    const event = new KeyboardEvent('keydown', {
      key: 's',
      ctrlKey: true,
      bubbles: true,
    });

    Object.defineProperty(event, 'target', {
      value: input,
      enumerable: true,
    });

    window.dispatchEvent(event);

    expect(mockAction).not.toHaveBeenCalled();

    document.body.removeChild(input);
  });

  it('should not execute action when focus is in textarea element', () => {
    const shortcuts: ShortcutConfig[] = [
      {
        key: 's',
        ctrl: true,
        action: mockAction,
        description: 'Save Draft',
      },
    ];

    renderHook(() => useKeyboardShortcuts(shortcuts));

    const textarea = document.createElement('textarea');
    document.body.appendChild(textarea);

    const event = new KeyboardEvent('keydown', {
      key: 's',
      ctrlKey: true,
      bubbles: true,
    });

    Object.defineProperty(event, 'target', {
      value: textarea,
      enumerable: true,
    });

    window.dispatchEvent(event);

    expect(mockAction).not.toHaveBeenCalled();

    document.body.removeChild(textarea);
  });

  it('should not execute action when focus is in AG Grid editor', () => {
    const shortcuts: ShortcutConfig[] = [
      {
        key: 's',
        ctrl: true,
        action: mockAction,
        description: 'Save Draft',
      },
    ];

    renderHook(() => useKeyboardShortcuts(shortcuts));

    const div = document.createElement('div');
    div.setAttribute('data-ag-grid-editor', 'true');
    document.body.appendChild(div);

    const event = new KeyboardEvent('keydown', {
      key: 's',
      ctrlKey: true,
      bubbles: true,
    });

    Object.defineProperty(event, 'target', {
      value: div,
      enumerable: true,
    });

    window.dispatchEvent(event);

    expect(mockAction).not.toHaveBeenCalled();

    document.body.removeChild(div);
  });

  it('should not execute action when focus is in contentEditable element', () => {
    const shortcuts: ShortcutConfig[] = [
      {
        key: 's',
        ctrl: true,
        action: mockAction,
        description: 'Save Draft',
      },
    ];

    renderHook(() => useKeyboardShortcuts(shortcuts));

    const div = document.createElement('div');
    div.contentEditable = 'true';
    document.body.appendChild(div);

    const event = new KeyboardEvent('keydown', {
      key: 's',
      ctrlKey: true,
      bubbles: true,
    });

    Object.defineProperty(event, 'target', {
      value: div,
      enumerable: true,
    });

    window.dispatchEvent(event);

    expect(mockAction).not.toHaveBeenCalled();

    document.body.removeChild(div);
  });

  it('should handle multiple shortcuts', () => {
    const saveDraftAction = vi.fn();
    const toggleSidebarAction = vi.fn();

    const shortcuts: ShortcutConfig[] = [
      {
        key: 's',
        ctrl: true,
        action: saveDraftAction,
        description: 'Save Draft',
      },
      {
        key: 'b',
        ctrl: true,
        action: toggleSidebarAction,
        description: 'Toggle Sidebar',
      },
    ];

    renderHook(() => useKeyboardShortcuts(shortcuts));

    // Test first shortcut
    const event1 = new KeyboardEvent('keydown', {
      key: 's',
      ctrlKey: true,
      bubbles: true,
    });
    window.dispatchEvent(event1);
    expect(saveDraftAction).toHaveBeenCalledTimes(1);
    expect(toggleSidebarAction).not.toHaveBeenCalled();

    // Test second shortcut
    const event2 = new KeyboardEvent('keydown', {
      key: 'b',
      ctrlKey: true,
      bubbles: true,
    });
    window.dispatchEvent(event2);
    expect(saveDraftAction).toHaveBeenCalledTimes(1);
    expect(toggleSidebarAction).toHaveBeenCalledTimes(1);
  });

  it('should handle case-insensitive key matching', () => {
    const shortcuts: ShortcutConfig[] = [
      {
        key: 'S',
        ctrl: true,
        action: mockAction,
        description: 'Save Draft',
      },
    ];

    renderHook(() => useKeyboardShortcuts(shortcuts));

    const event = new KeyboardEvent('keydown', {
      key: 's',
      ctrlKey: true,
      bubbles: true,
    });

    window.dispatchEvent(event);

    expect(mockAction).toHaveBeenCalledTimes(1);
  });

  it('should not execute action when modifier key is missing', () => {
    const shortcuts: ShortcutConfig[] = [
      {
        key: 's',
        ctrl: true,
        action: mockAction,
        description: 'Save Draft',
      },
    ];

    renderHook(() => useKeyboardShortcuts(shortcuts));

    const event = new KeyboardEvent('keydown', {
      key: 's',
      ctrlKey: false,
      bubbles: true,
    });

    window.dispatchEvent(event);

    expect(mockAction).not.toHaveBeenCalled();
  });

  it('should cleanup event listener on unmount', () => {
    const shortcuts: ShortcutConfig[] = [
      {
        key: 's',
        ctrl: true,
        action: mockAction,
        description: 'Save Draft',
      },
    ];

    const { unmount } = renderHook(() => useKeyboardShortcuts(shortcuts));

    unmount();

    const event = new KeyboardEvent('keydown', {
      key: 's',
      ctrlKey: true,
      bubbles: true,
    });

    window.dispatchEvent(event);

    expect(mockAction).not.toHaveBeenCalled();
  });
});
