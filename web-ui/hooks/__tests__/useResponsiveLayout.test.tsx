import { renderHook, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useResponsiveLayout } from '../useResponsiveLayout';
import { useLayoutStore } from '@/stores/layoutStore';

// Mock the layoutStore
vi.mock('@/stores/layoutStore', () => ({
  useLayoutStore: vi.fn(),
}));

describe('useResponsiveLayout', () => {
  let mockToggleSidebar: ReturnType<typeof vi.fn>;
  let mockToggleRightPanel: ReturnType<typeof vi.fn>;
  let mockSidebarCollapsed: boolean;
  let mockRightPanelCollapsed: boolean;
  let mediaQueryListeners: Array<(e: MediaQueryListEvent) => void>;
  let mockMediaQueryList: MediaQueryList;

  beforeEach(() => {
    mockToggleSidebar = vi.fn();
    mockToggleRightPanel = vi.fn();
    mockSidebarCollapsed = false;
    mockRightPanelCollapsed = false;
    mediaQueryListeners = [];

    // Mock matchMedia
    mockMediaQueryList = {
      matches: false,
      media: '(max-width: 1023px)',
      addEventListener: vi.fn((event: string, handler: (e: MediaQueryListEvent) => void) => {
        if (event === 'change') {
          mediaQueryListeners.push(handler);
        }
      }),
      removeEventListener: vi.fn((event: string, handler: (e: MediaQueryListEvent) => void) => {
        if (event === 'change') {
          const index = mediaQueryListeners.indexOf(handler);
          if (index > -1) {
            mediaQueryListeners.splice(index, 1);
          }
        }
      }),
    } as unknown as MediaQueryList;

    window.matchMedia = vi.fn(() => mockMediaQueryList);

    // Mock useLayoutStore
    vi.mocked(useLayoutStore).mockImplementation((selector: any) => {
      const state = {
        toggleSidebar: mockToggleSidebar,
        toggleRightPanel: mockToggleRightPanel,
        sidebarCollapsed: mockSidebarCollapsed,
        rightPanelCollapsed: mockRightPanelCollapsed,
      };
      return selector(state);
    });

    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  it('should auto-collapse panels when viewport < 1024px', async () => {
    // Start with desktop viewport
    mockMediaQueryList.matches = false;

    renderHook(() => useResponsiveLayout());

    // Advance timers for initial check debounce
    vi.advanceTimersByTime(100);

    // Simulate viewport change to mobile
    mockMediaQueryList.matches = true;
    const event = new Event('change') as MediaQueryListEvent;
    Object.defineProperty(event, 'matches', { value: true });

    mediaQueryListeners.forEach((listener) => listener(event as MediaQueryListEvent));

    // Advance timers for debounce
    vi.advanceTimersByTime(100);

    await waitFor(() => {
      expect(mockToggleSidebar).toHaveBeenCalledTimes(1);
      expect(mockToggleRightPanel).toHaveBeenCalledTimes(1);
    });
  });

  it('should restore panels when viewport >= 1024px', async () => {
    // Start with mobile viewport (collapsed panels)
    mockMediaQueryList.matches = true;
    mockSidebarCollapsed = true;
    mockRightPanelCollapsed = true;

    const { rerender } = renderHook(() => useResponsiveLayout());

    // Advance timers for initial check debounce
    vi.advanceTimersByTime(100);

    // Update mock to reflect collapsed state
    vi.mocked(useLayoutStore).mockImplementation((selector: any) => {
      const state = {
        toggleSidebar: mockToggleSidebar,
        toggleRightPanel: mockToggleRightPanel,
        sidebarCollapsed: true,
        rightPanelCollapsed: true,
      };
      return selector(state);
    });

    rerender();

    // Simulate viewport change to desktop
    mockMediaQueryList.matches = false;
    const event = new Event('change') as MediaQueryListEvent;
    Object.defineProperty(event, 'matches', { value: false });

    mediaQueryListeners.forEach((listener) => listener(event as MediaQueryListEvent));

    // Advance timers for debounce
    vi.advanceTimersByTime(100);

    await waitFor(() => {
      expect(mockToggleSidebar).toHaveBeenCalled();
      expect(mockToggleRightPanel).toHaveBeenCalled();
    });
  });

  it('should not collapse already collapsed panels', async () => {
    // Start with desktop viewport but panels already collapsed
    mockMediaQueryList.matches = false;
    mockSidebarCollapsed = true;
    mockRightPanelCollapsed = true;

    vi.mocked(useLayoutStore).mockImplementation((selector: any) => {
      const state = {
        toggleSidebar: mockToggleSidebar,
        toggleRightPanel: mockToggleRightPanel,
        sidebarCollapsed: true,
        rightPanelCollapsed: true,
      };
      return selector(state);
    });

    renderHook(() => useResponsiveLayout());

    // Advance timers for initial check debounce
    vi.advanceTimersByTime(100);

    // Simulate viewport change to mobile
    mockMediaQueryList.matches = true;
    const event = new Event('change') as MediaQueryListEvent;
    Object.defineProperty(event, 'matches', { value: true });

    mediaQueryListeners.forEach((listener) => listener(event as MediaQueryListEvent));

    // Advance timers for debounce
    vi.advanceTimersByTime(100);

    await waitFor(() => {
      // Should not toggle since panels are already collapsed
      expect(mockToggleSidebar).not.toHaveBeenCalled();
      expect(mockToggleRightPanel).not.toHaveBeenCalled();
    });
  });

  it('should debounce resize events by 100ms', async () => {
    mockMediaQueryList.matches = false;

    renderHook(() => useResponsiveLayout());

    // Advance timers for initial check debounce
    vi.advanceTimersByTime(100);

    // Simulate multiple rapid viewport changes
    mockMediaQueryList.matches = true;
    const event1 = new Event('change') as MediaQueryListEvent;
    Object.defineProperty(event1, 'matches', { value: true });

    mediaQueryListeners.forEach((listener) => listener(event1 as MediaQueryListEvent));

    // Advance only 50ms (not enough to trigger debounce)
    vi.advanceTimersByTime(50);

    // Another change event
    const event2 = new Event('change') as MediaQueryListEvent;
    Object.defineProperty(event2, 'matches', { value: true });

    mediaQueryListeners.forEach((listener) => listener(event2 as MediaQueryListEvent));

    // Advance another 50ms (total 100ms from last event)
    vi.advanceTimersByTime(50);

    await waitFor(() => {
      // Should only execute once due to debouncing
      expect(mockToggleSidebar).toHaveBeenCalledTimes(1);
      expect(mockToggleRightPanel).toHaveBeenCalledTimes(1);
    });
  });

  it('should cleanup event listener on unmount', () => {
    const { unmount } = renderHook(() => useResponsiveLayout());

    unmount();

    expect(mockMediaQueryList.removeEventListener).toHaveBeenCalledWith(
      'change',
      expect.any(Function)
    );
  });

  it('should use matchMedia with correct query', () => {
    renderHook(() => useResponsiveLayout());

    expect(window.matchMedia).toHaveBeenCalledWith('(max-width: 1023px)');
  });

  it('should perform initial check on mount', async () => {
    // Start with mobile viewport
    mockMediaQueryList.matches = true;

    renderHook(() => useResponsiveLayout());

    // Advance timers for initial check debounce
    vi.advanceTimersByTime(100);

    await waitFor(() => {
      expect(mockToggleSidebar).toHaveBeenCalledTimes(1);
      expect(mockToggleRightPanel).toHaveBeenCalledTimes(1);
    });
  });
});
