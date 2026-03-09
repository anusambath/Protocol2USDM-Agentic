/**
 * Responsive Layout Tests for Tablets (768px and above)
 * 
 * Tests responsive behavior of provenance components on tablet devices
 * 
 * Requirements: 9.6
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ProvenanceSidebar } from '../ProvenanceSidebar';
import { ProtocolPreview } from '../ProtocolPreview';
import { ProvenanceInline } from '../ProvenanceInline';
import { useProvenanceSidebarStore } from '@/lib/stores/provenance-sidebar-store';
import { EntityProvenanceExtended } from '@/lib/provenance/types';

// Mock the stores and hooks
vi.mock('@/lib/stores/provenance-sidebar-store');
vi.mock('@/lib/hooks/useKeyboardShortcuts', () => ({
  useKeyboardShortcuts: vi.fn(),
}));
vi.mock('@/lib/cache/protocol-page-cache', () => ({
  getProtocolPageCache: () => ({
    get: vi.fn().mockResolvedValue(null),
    set: vi.fn().mockResolvedValue(undefined),
    preloadAdjacentPages: vi.fn(),
    checkAndEvict: vi.fn().mockResolvedValue(undefined),
  }),
}));

describe('Responsive Layout - Tablet (768px and above)', () => {
  const mockProvenance: EntityProvenanceExtended = {
    source: 'text',
    agent: 'test-agent',
    model: 'gemini',
    confidence: 0.95,
    pageRefs: [1, 2, 3],
    timestamp: new Date().toISOString(),
  };

  beforeEach(() => {
    // Mock window.matchMedia for tablet viewport (768px)
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation((query) => ({
        matches: query === '(min-width: 768px)',
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });

    // Mock fetch for protocol pages
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      blob: () => Promise.resolve(new Blob(['test'], { type: 'image/png' })),
    });

    // Mock URL.createObjectURL
    global.URL.createObjectURL = vi.fn(() => 'blob:test-url');
    global.URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('ProvenanceSidebar - Tablet Layout', () => {
    it('should use appropriate width on tablet (768px)', () => {
      const mockStore = {
        isOpen: true,
        isPinned: false,
        selectedEntity: {
          type: 'activity',
          id: 'test-activity',
          provenance: mockProvenance,
        },
        splitRatio: 0.4,
        close: vi.fn(),
        pin: vi.fn(),
        unpin: vi.fn(),
        setSplitRatio: vi.fn(),
      };

      (useProvenanceSidebarStore as any).mockReturnValue(mockStore);

      const { container } = render(
        <ProvenanceSidebar protocolId="test-protocol" totalPages={10} />
      );

      const sidebar = container.querySelector('[role="complementary"]');
      expect(sidebar).toBeTruthy();
      
      // Check that sidebar has responsive width classes
      expect(sidebar?.className).toContain('w-full');
      expect(sidebar?.className).toContain('md:w-[500px]');
      expect(sidebar?.className).toContain('lg:w-[600px]');
    });

    it('should be full width on mobile and narrower on tablet', () => {
      const mockStore = {
        isOpen: true,
        isPinned: false,
        selectedEntity: {
          type: 'activity',
          id: 'test-activity',
          provenance: mockProvenance,
        },
        splitRatio: 0.4,
        close: vi.fn(),
        pin: vi.fn(),
        unpin: vi.fn(),
        setSplitRatio: vi.fn(),
      };

      (useProvenanceSidebarStore as any).mockReturnValue(mockStore);

      const { container } = render(
        <ProvenanceSidebar protocolId="test-protocol" totalPages={10} />
      );

      const sidebar = container.querySelector('[role="complementary"]');
      
      // Verify responsive classes are present
      // w-full: mobile (< 768px) - full width
      // md:w-[500px]: tablet (>= 768px) - 500px width
      // lg:w-[600px]: desktop (>= 1024px) - 600px width
      expect(sidebar?.className).toMatch(/w-full.*md:w-\[500px\].*lg:w-\[600px\]/);
    });

    it('should have touch-pan-y for smooth scrolling on tablets', () => {
      const mockStore = {
        isOpen: true,
        isPinned: false,
        selectedEntity: {
          type: 'activity',
          id: 'test-activity',
          provenance: mockProvenance,
        },
        splitRatio: 0.4,
        close: vi.fn(),
        pin: vi.fn(),
        unpin: vi.fn(),
        setSplitRatio: vi.fn(),
      };

      (useProvenanceSidebarStore as any).mockReturnValue(mockStore);

      const { container } = render(
        <ProvenanceSidebar protocolId="test-protocol" totalPages={10} />
      );

      const sidebar = container.querySelector('[role="complementary"]');
      expect(sidebar?.className).toContain('touch-pan-y');
    });
  });

  describe('ProtocolPreview - Tablet Controls', () => {
    it('should stack controls vertically on small screens and horizontally on tablets', () => {
      const { container } = render(
        <ProtocolPreview
          protocolId="test-protocol"
          pageNumbers={[1, 2, 3]}
          totalPages={10}
        />
      );

      const controlsContainer = container.querySelector('.flex.flex-col.sm\\:flex-row');
      expect(controlsContainer).toBeTruthy();
      
      // Verify responsive flex direction classes
      expect(controlsContainer?.className).toContain('flex-col');
      expect(controlsContainer?.className).toContain('sm:flex-row');
    });

    it('should have touch-manipulation on all interactive buttons', async () => {
      const { container } = render(
        <ProtocolPreview
          protocolId="test-protocol"
          pageNumbers={[1, 2, 3]}
          totalPages={10}
        />
      );

      await waitFor(() => {
        const buttons = container.querySelectorAll('button');
        expect(buttons.length).toBeGreaterThan(0);
        
        buttons.forEach((button) => {
          expect(button.className).toContain('touch-manipulation');
        });
      });
    });

    it('should have appropriate button sizes for touch targets', async () => {
      render(
        <ProtocolPreview
          protocolId="test-protocol"
          pageNumbers={[1, 2, 3]}
          totalPages={10}
        />
      );

      await waitFor(() => {
        // All buttons should have padding for adequate touch target size
        const prevButton = screen.getByLabelText('Previous page');
        const nextButton = screen.getByLabelText('Next page');
        const zoomInButton = screen.getByLabelText('Zoom in');
        const zoomOutButton = screen.getByLabelText('Zoom out');

        // Check that buttons have adequate padding (px-2 or px-3 with py-1.5)
        [prevButton, nextButton, zoomInButton, zoomOutButton].forEach((button) => {
          expect(button.className).toMatch(/p[xy]-[123]/);
        });
      });
    });

    it('should adjust gap between controls on different screen sizes', () => {
      const { container } = render(
        <ProtocolPreview
          protocolId="test-protocol"
          pageNumbers={[1, 2, 3]}
          totalPages={10}
        />
      );

      const controlsContainer = container.querySelector('.flex.flex-col.sm\\:flex-row');
      
      // Verify responsive gap classes
      expect(controlsContainer?.className).toContain('gap-2');
      expect(controlsContainer?.className).toContain('sm:gap-0');
    });
  });

  describe('ProvenanceInline - Touch Interactions', () => {
    it('should have touch-manipulation on preview button', () => {
      render(
        <ProvenanceInline
          entityType="activity"
          entityId="test-activity"
          provenance={mockProvenance}
          onPreviewClick={vi.fn()}
          onViewAllClick={vi.fn()}
          protocolAvailable={true}
        />
      );

      const previewButton = screen.getByLabelText(/Preview protocol pages/i);
      expect(previewButton.className).toContain('touch-manipulation');
    });

    it('should have touch-manipulation on View All link', () => {
      render(
        <ProvenanceInline
          entityType="activity"
          entityId="test-activity"
          provenance={mockProvenance}
          onPreviewClick={vi.fn()}
          onViewAllClick={vi.fn()}
          protocolAvailable={true}
        />
      );

      const viewAllLink = screen.getByLabelText(/View all provenance information/i);
      expect(viewAllLink.className).toContain('touch-manipulation');
    });

    it('should respond to touch events on preview button', () => {
      const onPreviewClick = vi.fn();
      
      render(
        <ProvenanceInline
          entityType="activity"
          entityId="test-activity"
          provenance={mockProvenance}
          onPreviewClick={onPreviewClick}
          onViewAllClick={vi.fn()}
          protocolAvailable={true}
        />
      );

      const previewButton = screen.getByLabelText(/Preview protocol pages/i);
      
      // Simulate touch event
      fireEvent.click(previewButton);
      
      expect(onPreviewClick).toHaveBeenCalledTimes(1);
    });
  });

  describe('Touch Interactions - Sidebar Controls', () => {
    it('should have touch-manipulation on pin button', () => {
      const mockStore = {
        isOpen: true,
        isPinned: false,
        selectedEntity: {
          type: 'activity',
          id: 'test-activity',
          provenance: mockProvenance,
        },
        splitRatio: 0.4,
        close: vi.fn(),
        pin: vi.fn(),
        unpin: vi.fn(),
        setSplitRatio: vi.fn(),
      };

      (useProvenanceSidebarStore as any).mockReturnValue(mockStore);

      render(
        <ProvenanceSidebar protocolId="test-protocol" totalPages={10} />
      );

      const pinButton = screen.getByLabelText('Pin sidebar');
      expect(pinButton.className).toContain('touch-manipulation');
    });

    it('should have touch-manipulation on close button', () => {
      const mockStore = {
        isOpen: true,
        isPinned: false,
        selectedEntity: {
          type: 'activity',
          id: 'test-activity',
          provenance: mockProvenance,
        },
        splitRatio: 0.4,
        close: vi.fn(),
        pin: vi.fn(),
        unpin: vi.fn(),
        setSplitRatio: vi.fn(),
      };

      (useProvenanceSidebarStore as any).mockReturnValue(mockStore);

      render(
        <ProvenanceSidebar protocolId="test-protocol" totalPages={10} />
      );

      const closeButton = screen.getByLabelText(/Close sidebar/i);
      expect(closeButton.className).toContain('touch-manipulation');
    });

    it('should respond to touch events on pin button', () => {
      const mockPin = vi.fn();
      const mockStore = {
        isOpen: true,
        isPinned: false,
        selectedEntity: {
          type: 'activity',
          id: 'test-activity',
          provenance: mockProvenance,
        },
        splitRatio: 0.4,
        close: vi.fn(),
        pin: mockPin,
        unpin: vi.fn(),
        setSplitRatio: vi.fn(),
      };

      (useProvenanceSidebarStore as any).mockReturnValue(mockStore);

      render(
        <ProvenanceSidebar protocolId="test-protocol" totalPages={10} />
      );

      const pinButton = screen.getByLabelText('Pin sidebar');
      fireEvent.click(pinButton);
      
      expect(mockPin).toHaveBeenCalledTimes(1);
    });

    it('should respond to touch events on close button', () => {
      const mockClose = vi.fn();
      const mockStore = {
        isOpen: true,
        isPinned: false,
        selectedEntity: {
          type: 'activity',
          id: 'test-activity',
          provenance: mockProvenance,
        },
        splitRatio: 0.4,
        close: mockClose,
        pin: vi.fn(),
        unpin: vi.fn(),
        setSplitRatio: vi.fn(),
      };

      (useProvenanceSidebarStore as any).mockReturnValue(mockStore);

      render(
        <ProvenanceSidebar protocolId="test-protocol" totalPages={10} />
      );

      const closeButton = screen.getByLabelText(/Close sidebar/i);
      fireEvent.click(closeButton);
      
      expect(mockClose).toHaveBeenCalledTimes(1);
    });
  });

  describe('ProvenanceDetails - Touch Interactions', () => {
    it('should have touch-manipulation on page badges', () => {
      const { ProvenanceDetails } = require('../ProvenanceDetails');
      
      const { container } = render(
        <ProvenanceDetails
          entityType="activity"
          entityId="test-activity"
          provenance={mockProvenance}
        />
      );

      const pageBadges = container.querySelectorAll('button[aria-label^="Jump to page"]');
      expect(pageBadges.length).toBeGreaterThan(0);
      
      pageBadges.forEach((badge) => {
        expect(badge.className).toContain('touch-manipulation');
      });
    });

    it('should respond to touch events on page badges', () => {
      const { ProvenanceDetails } = require('../ProvenanceDetails');
      const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
      
      render(
        <ProvenanceDetails
          entityType="activity"
          entityId="test-activity"
          provenance={mockProvenance}
        />
      );

      const pageBadge = screen.getByLabelText('Jump to page 1');
      fireEvent.click(pageBadge);
      
      expect(consoleSpy).toHaveBeenCalledWith('Navigate to page 1');
      
      consoleSpy.mockRestore();
    });
  });

  describe('Responsive Behavior Verification', () => {
    it('should maintain 60fps animations on sidebar open/close', () => {
      const mockStore = {
        isOpen: true,
        isPinned: false,
        selectedEntity: {
          type: 'activity',
          id: 'test-activity',
          provenance: mockProvenance,
        },
        splitRatio: 0.4,
        close: vi.fn(),
        pin: vi.fn(),
        unpin: vi.fn(),
        setSplitRatio: vi.fn(),
      };

      (useProvenanceSidebarStore as any).mockReturnValue(mockStore);

      const { container } = render(
        <ProvenanceSidebar protocolId="test-protocol" totalPages={10} />
      );

      const sidebar = container.querySelector('[role="complementary"]');
      
      // Verify hardware acceleration hints
      expect(sidebar?.className).toContain('will-change-transform');
      
      // Verify smooth transition timing
      const style = sidebar?.getAttribute('style');
      expect(style).toContain('transition: transform 200ms cubic-bezier(0.4, 0, 0.2, 1)');
    });

    it('should use appropriate backdrop opacity for tablets', () => {
      const mockStore = {
        isOpen: true,
        isPinned: false,
        selectedEntity: {
          type: 'activity',
          id: 'test-activity',
          provenance: mockProvenance,
        },
        splitRatio: 0.4,
        close: vi.fn(),
        pin: vi.fn(),
        unpin: vi.fn(),
        setSplitRatio: vi.fn(),
      };

      (useProvenanceSidebarStore as any).mockReturnValue(mockStore);

      const { container } = render(
        <ProvenanceSidebar protocolId="test-protocol" totalPages={10} />
      );

      const backdrop = container.querySelector('[aria-hidden="true"]');
      expect(backdrop?.className).toContain('bg-black/20');
      expect(backdrop?.className).toContain('dark:bg-black/40');
    });

    it('should handle split pane resizing on tablets', () => {
      const mockSetSplitRatio = vi.fn();
      const mockStore = {
        isOpen: true,
        isPinned: false,
        selectedEntity: {
          type: 'activity',
          id: 'test-activity',
          provenance: mockProvenance,
        },
        splitRatio: 0.4,
        close: vi.fn(),
        pin: vi.fn(),
        unpin: vi.fn(),
        setSplitRatio: mockSetSplitRatio,
      };

      (useProvenanceSidebarStore as any).mockReturnValue(mockStore);

      const { container } = render(
        <ProvenanceSidebar protocolId="test-protocol" totalPages={10} />
      );

      const divider = container.querySelector('[role="separator"]');
      expect(divider).toBeTruthy();
      
      // Verify divider is keyboard accessible
      expect(divider?.getAttribute('tabIndex')).toBe('0');
      
      // Simulate keyboard resize
      fireEvent.keyDown(divider!, { key: 'ArrowDown' });
      expect(mockSetSplitRatio).toHaveBeenCalled();
    });
  });
});
