import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { ActivityBar } from '../ActivityBar';
import { ActivityBarMode } from '@/stores/layoutStore';

describe('ActivityBar', () => {
  const mockOnModeChange = vi.fn();
  const mockOnToggleSidebar = vi.fn();

  const defaultProps = {
    activeMode: 'explorer' as ActivityBarMode,
    onModeChange: mockOnModeChange,
    onToggleSidebar: mockOnToggleSidebar,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders all three mode buttons', () => {
      render(<ActivityBar {...defaultProps} />);

      expect(screen.getByLabelText('Explorer')).toBeInTheDocument();
      expect(screen.getByLabelText('Search')).toBeInTheDocument();
      expect(screen.getByLabelText('Quality')).toBeInTheDocument();
    });

    it('renders with proper ARIA toolbar role', () => {
      render(<ActivityBar {...defaultProps} />);

      const toolbar = screen.getByRole('toolbar', { name: 'Activity Bar' });
      expect(toolbar).toBeInTheDocument();
    });

    it('highlights the active mode button', () => {
      render(<ActivityBar {...defaultProps} activeMode="search" />);

      const searchButton = screen.getByLabelText('Search');
      expect(searchButton).toHaveAttribute('aria-pressed', 'true');
      expect(searchButton).toHaveClass('bg-accent');
    });

    it('does not highlight inactive mode buttons', () => {
      render(<ActivityBar {...defaultProps} activeMode="explorer" />);

      const searchButton = screen.getByLabelText('Search');
      const qualityButton = screen.getByLabelText('Quality');

      expect(searchButton).toHaveAttribute('aria-pressed', 'false');
      expect(qualityButton).toHaveAttribute('aria-pressed', 'false');
      expect(searchButton).not.toHaveClass('bg-accent');
      expect(qualityButton).not.toHaveClass('bg-accent');
    });
  });

  describe('Mode Switching', () => {
    it('calls onModeChange when clicking an inactive mode button', async () => {
      const user = userEvent.setup();
      render(<ActivityBar {...defaultProps} activeMode="explorer" />);

      const searchButton = screen.getByLabelText('Search');
      await user.click(searchButton);

      expect(mockOnModeChange).toHaveBeenCalledWith('search');
      expect(mockOnModeChange).toHaveBeenCalledTimes(1);
      expect(mockOnToggleSidebar).not.toHaveBeenCalled();
    });

    it('switches between all three modes correctly', async () => {
      const user = userEvent.setup();
      render(<ActivityBar {...defaultProps} activeMode="explorer" />);

      // Switch to search
      await user.click(screen.getByLabelText('Search'));
      expect(mockOnModeChange).toHaveBeenCalledWith('search');

      // Switch to quality
      await user.click(screen.getByLabelText('Quality'));
      expect(mockOnModeChange).toHaveBeenCalledWith('quality');

      expect(mockOnModeChange).toHaveBeenCalledTimes(2);
    });
  });

  describe('Sidebar Toggle', () => {
    it('calls onToggleSidebar when clicking the active mode button', async () => {
      const user = userEvent.setup();
      render(<ActivityBar {...defaultProps} activeMode="explorer" />);

      const explorerButton = screen.getByLabelText('Explorer');
      await user.click(explorerButton);

      expect(mockOnToggleSidebar).toHaveBeenCalledTimes(1);
      expect(mockOnModeChange).not.toHaveBeenCalled();
    });

    it('toggles sidebar for each active mode', async () => {
      const user = userEvent.setup();
      
      // Test with explorer active
      const { rerender } = render(<ActivityBar {...defaultProps} activeMode="explorer" />);
      await user.click(screen.getByLabelText('Explorer'));
      expect(mockOnToggleSidebar).toHaveBeenCalledTimes(1);

      // Test with search active
      rerender(<ActivityBar {...defaultProps} activeMode="search" />);
      await user.click(screen.getByLabelText('Search'));
      expect(mockOnToggleSidebar).toHaveBeenCalledTimes(2);

      // Test with quality active
      rerender(<ActivityBar {...defaultProps} activeMode="quality" />);
      await user.click(screen.getByLabelText('Quality'));
      expect(mockOnToggleSidebar).toHaveBeenCalledTimes(3);
    });
  });

  describe('Accessibility', () => {
    it('has proper aria-label for each button', () => {
      render(<ActivityBar {...defaultProps} />);

      expect(screen.getByLabelText('Explorer')).toBeInTheDocument();
      expect(screen.getByLabelText('Search')).toBeInTheDocument();
      expect(screen.getByLabelText('Quality')).toBeInTheDocument();
    });

    it('has proper aria-pressed state for active button', () => {
      render(<ActivityBar {...defaultProps} activeMode="search" />);

      expect(screen.getByLabelText('Explorer')).toHaveAttribute('aria-pressed', 'false');
      expect(screen.getByLabelText('Search')).toHaveAttribute('aria-pressed', 'true');
      expect(screen.getByLabelText('Quality')).toHaveAttribute('aria-pressed', 'false');
    });

    it('is keyboard accessible', async () => {
      const user = userEvent.setup();
      render(<ActivityBar {...defaultProps} activeMode="explorer" />);

      const searchButton = screen.getByLabelText('Search');
      
      // Tab to the button and press Enter
      await user.tab();
      await user.keyboard('{Enter}');

      expect(mockOnModeChange).toHaveBeenCalled();
    });
  });

  describe('Visual Feedback', () => {
    it('applies correct classes for active mode', () => {
      render(<ActivityBar {...defaultProps} activeMode="explorer" />);

      const explorerButton = screen.getByLabelText('Explorer');
      expect(explorerButton).toHaveClass('bg-accent', 'text-accent-foreground');
    });

    it('applies correct classes for inactive modes', () => {
      render(<ActivityBar {...defaultProps} activeMode="explorer" />);

      const searchButton = screen.getByLabelText('Search');
      expect(searchButton).toHaveClass('text-muted-foreground');
      expect(searchButton).not.toHaveClass('bg-accent');
    });
  });
});
