import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CommandPalette } from '../CommandPalette';

describe('CommandPalette', () => {
  const mockOnClose = vi.fn();
  const mockOnExecute = vi.fn();

  beforeEach(() => {
    mockOnClose.mockClear();
    mockOnExecute.mockClear();
  });

  describe('Rendering', () => {
    it('should not render when isOpen is false', () => {
      render(
        <CommandPalette isOpen={false} onClose={mockOnClose} onExecute={mockOnExecute} />
      );

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('should render when isOpen is true', () => {
      render(
        <CommandPalette isOpen={true} onClose={mockOnClose} onExecute={mockOnExecute} />
      );

      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByRole('combobox')).toBeInTheDocument();
      expect(screen.getByRole('listbox')).toBeInTheDocument();
    });

    it('should render search input with placeholder', () => {
      render(
        <CommandPalette isOpen={true} onClose={mockOnClose} onExecute={mockOnExecute} />
      );

      const input = screen.getByPlaceholderText(/type a command or search/i);
      expect(input).toBeInTheDocument();
    });

    it('should render all commands initially', () => {
      render(
        <CommandPalette isOpen={true} onClose={mockOnClose} onExecute={mockOnExecute} />
      );

      // Should show navigation and action categories
      expect(screen.getByText(/navigate to/i)).toBeInTheDocument();
      expect(screen.getByText(/actions/i)).toBeInTheDocument();

      // Should show some sample commands
      expect(screen.getByText(/protocol overview/i)).toBeInTheDocument();
      expect(screen.getByText(/save draft/i)).toBeInTheDocument();
    });
  });

  describe('ARIA Attributes', () => {
    it('should have proper ARIA combobox attributes', () => {
      render(
        <CommandPalette isOpen={true} onClose={mockOnClose} onExecute={mockOnExecute} />
      );

      const combobox = screen.getByRole('combobox');
      expect(combobox).toHaveAttribute('aria-expanded', 'true');
      expect(combobox).toHaveAttribute('aria-haspopup', 'listbox');
      expect(combobox).toHaveAttribute('aria-controls', 'command-listbox');
    });

    it('should have proper ARIA listbox attributes', () => {
      render(
        <CommandPalette isOpen={true} onClose={mockOnClose} onExecute={mockOnExecute} />
      );

      const listbox = screen.getByRole('listbox');
      expect(listbox).toHaveAttribute('id', 'command-listbox');
      expect(listbox).toHaveAttribute('aria-label', 'Command results');
    });

    it('should set aria-activedescendant on input', () => {
      render(
        <CommandPalette isOpen={true} onClose={mockOnClose} onExecute={mockOnExecute} />
      );

      const input = screen.getByPlaceholderText(/type a command or search/i);
      const activedescendant = input.getAttribute('aria-activedescendant');
      
      // Should point to the first command
      expect(activedescendant).toMatch(/^command-/);
    });

    it('should mark selected option with aria-selected', () => {
      render(
        <CommandPalette isOpen={true} onClose={mockOnClose} onExecute={mockOnExecute} />
      );

      const options = screen.getAllByRole('option');
      expect(options[0]).toHaveAttribute('aria-selected', 'true');
      expect(options[1]).toHaveAttribute('aria-selected', 'false');
    });
  });

  describe('Fuzzy Search', () => {
    it('should filter commands based on query', async () => {
      const user = userEvent.setup();
      render(
        <CommandPalette isOpen={true} onClose={mockOnClose} onExecute={mockOnExecute} />
      );

      const input = screen.getByPlaceholderText(/type a command or search/i);
      await user.type(input, 'soa');

      // Should show Schedule of Activities
      await waitFor(() => {
        expect(screen.getByText(/schedule of activities/i)).toBeInTheDocument();
      });

      // Should not show unrelated commands
      expect(screen.queryByText(/protocol overview/i)).not.toBeInTheDocument();
    });

    it('should show empty state when no results match', async () => {
      const user = userEvent.setup();
      render(
        <CommandPalette isOpen={true} onClose={mockOnClose} onExecute={mockOnExecute} />
      );

      const input = screen.getByPlaceholderText(/type a command or search/i);
      await user.type(input, 'zzzzzzzzz');

      await waitFor(() => {
        expect(screen.getByText(/no commands found/i)).toBeInTheDocument();
      });
    });

    it('should reset results when query is cleared', async () => {
      const user = userEvent.setup();
      render(
        <CommandPalette isOpen={true} onClose={mockOnClose} onExecute={mockOnExecute} />
      );

      const input = screen.getByPlaceholderText(/type a command or search/i);
      
      // Type query
      await user.type(input, 'soa');
      await waitFor(() => {
        expect(screen.queryByText(/protocol overview/i)).not.toBeInTheDocument();
      });

      // Clear query
      await user.clear(input);
      await waitFor(() => {
        expect(screen.getByText(/protocol overview/i)).toBeInTheDocument();
      });
    });
  });

  describe('Keyboard Navigation', () => {
    it('should move selection down with ArrowDown', async () => {
      render(
        <CommandPalette isOpen={true} onClose={mockOnClose} onExecute={mockOnExecute} />
      );

      const input = screen.getByPlaceholderText(/type a command or search/i);
      const options = screen.getAllByRole('option');

      // First option should be selected initially
      expect(options[0]).toHaveAttribute('aria-selected', 'true');

      // Press ArrowDown
      fireEvent.keyDown(input, { key: 'ArrowDown' });

      await waitFor(() => {
        expect(options[1]).toHaveAttribute('aria-selected', 'true');
      });
    });

    it('should move selection up with ArrowUp', async () => {
      render(
        <CommandPalette isOpen={true} onClose={mockOnClose} onExecute={mockOnExecute} />
      );

      const input = screen.getByPlaceholderText(/type a command or search/i);
      const options = screen.getAllByRole('option');

      // Move down first
      fireEvent.keyDown(input, { key: 'ArrowDown' });
      await waitFor(() => {
        expect(options[1]).toHaveAttribute('aria-selected', 'true');
      });

      // Move back up
      fireEvent.keyDown(input, { key: 'ArrowUp' });
      await waitFor(() => {
        expect(options[0]).toHaveAttribute('aria-selected', 'true');
      });
    });

    it('should not move selection above first item', () => {
      render(
        <CommandPalette isOpen={true} onClose={mockOnClose} onExecute={mockOnExecute} />
      );

      const input = screen.getByPlaceholderText(/type a command or search/i);
      const options = screen.getAllByRole('option');

      // First option is selected
      expect(options[0]).toHaveAttribute('aria-selected', 'true');

      // Try to move up
      fireEvent.keyDown(input, { key: 'ArrowUp' });

      // Should still be on first option
      expect(options[0]).toHaveAttribute('aria-selected', 'true');
    });

    it('should execute selected command on Enter', () => {
      render(
        <CommandPalette isOpen={true} onClose={mockOnClose} onExecute={mockOnExecute} />
      );

      const input = screen.getByPlaceholderText(/type a command or search/i);

      // Press Enter (first command should be selected)
      fireEvent.keyDown(input, { key: 'Enter' });

      expect(mockOnExecute).toHaveBeenCalledTimes(1);
      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    it('should close on Escape', () => {
      render(
        <CommandPalette isOpen={true} onClose={mockOnClose} onExecute={mockOnExecute} />
      );

      const input = screen.getByPlaceholderText(/type a command or search/i);

      // Press Escape
      fireEvent.keyDown(input, { key: 'Escape' });

      expect(mockOnClose).toHaveBeenCalledTimes(1);
      expect(mockOnExecute).not.toHaveBeenCalled();
    });
  });

  describe('Mouse Interaction', () => {
    it('should execute command on click', async () => {
      const user = userEvent.setup();
      render(
        <CommandPalette isOpen={true} onClose={mockOnClose} onExecute={mockOnExecute} />
      );

      const firstOption = screen.getAllByRole('option')[0];
      await user.click(firstOption);

      expect(mockOnExecute).toHaveBeenCalledTimes(1);
      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    it('should close when clicking backdrop', async () => {
      const user = userEvent.setup();
      render(
        <CommandPalette isOpen={true} onClose={mockOnClose} onExecute={mockOnExecute} />
      );

      const dialog = screen.getByRole('dialog');
      await user.click(dialog);

      expect(mockOnClose).toHaveBeenCalledTimes(1);
      expect(mockOnExecute).not.toHaveBeenCalled();
    });
  });

  describe('Focus Management', () => {
    it('should focus input when opened', () => {
      const { rerender } = render(
        <CommandPalette isOpen={false} onClose={mockOnClose} onExecute={mockOnExecute} />
      );

      rerender(
        <CommandPalette isOpen={true} onClose={mockOnClose} onExecute={mockOnExecute} />
      );

      const input = screen.getByPlaceholderText(/type a command or search/i);
      expect(input).toHaveFocus();
    });

    it('should clear query when opened', () => {
      const { rerender } = render(
        <CommandPalette isOpen={true} onClose={mockOnClose} onExecute={mockOnExecute} />
      );

      const input = screen.getByPlaceholderText(/type a command or search/i) as HTMLInputElement;
      fireEvent.change(input, { target: { value: 'test query' } });
      expect(input.value).toBe('test query');

      // Close and reopen
      rerender(
        <CommandPalette isOpen={false} onClose={mockOnClose} onExecute={mockOnExecute} />
      );
      rerender(
        <CommandPalette isOpen={true} onClose={mockOnClose} onExecute={mockOnExecute} />
      );

      expect(input.value).toBe('');
    });
  });

  describe('Category Grouping', () => {
    it('should group commands by category', () => {
      render(
        <CommandPalette isOpen={true} onClose={mockOnClose} onExecute={mockOnExecute} />
      );

      expect(screen.getByText(/navigate to/i)).toBeInTheDocument();
      expect(screen.getByText(/actions/i)).toBeInTheDocument();
    });

    it('should show navigation commands under Navigate to', () => {
      render(
        <CommandPalette isOpen={true} onClose={mockOnClose} onExecute={mockOnExecute} />
      );

      const navigateSection = screen.getByText(/navigate to/i).parentElement;
      expect(navigateSection).toBeInTheDocument();
      
      // Check that navigation commands appear after the "Navigate to" header
      expect(screen.getByText(/protocol overview/i)).toBeInTheDocument();
      expect(screen.getByText(/eligibility criteria/i)).toBeInTheDocument();
    });

    it('should show action commands under Actions', () => {
      render(
        <CommandPalette isOpen={true} onClose={mockOnClose} onExecute={mockOnExecute} />
      );

      const actionsSection = screen.getByText(/actions/i).parentElement;
      expect(actionsSection).toBeInTheDocument();
      
      // Check that action commands appear after the "Actions" header
      expect(screen.getByText(/save draft/i)).toBeInTheDocument();
      expect(screen.getByText(/publish/i)).toBeInTheDocument();
    });
  });

  describe('Shortcut Hints', () => {
    it('should display shortcut hints for commands that have them', () => {
      render(
        <CommandPalette isOpen={true} onClose={mockOnClose} onExecute={mockOnExecute} />
      );

      // Save Draft has ⌘S shortcut
      const saveDraftOption = screen.getByText(/save draft/i).closest('button');
      expect(saveDraftOption).toHaveTextContent('⌘S');
    });

    it('should not display shortcut hints for commands without them', () => {
      render(
        <CommandPalette isOpen={true} onClose={mockOnClose} onExecute={mockOnExecute} />
      );

      // Protocol Overview has no shortcut
      const overviewOption = screen.getByText(/protocol overview/i).closest('button');
      expect(overviewOption).not.toHaveTextContent('⌘');
    });
  });
});
