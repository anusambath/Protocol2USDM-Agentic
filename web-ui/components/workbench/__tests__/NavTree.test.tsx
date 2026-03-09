import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { NavTree } from '../NavTree';
import { ViewType } from '@/stores/layoutStore';

describe('NavTree', () => {
  const mockOnNavigate = vi.fn();
  const mockOnToggleGroup = vi.fn();

  const defaultProps = {
    activeTabId: null,
    expandedGroups: {},
    onNavigate: mockOnNavigate,
    onToggleGroup: mockOnToggleGroup,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders all four group headers', () => {
      render(<NavTree {...defaultProps} />);

      expect(screen.getByText('Protocol')).toBeInTheDocument();
      expect(screen.getByText('Advanced')).toBeInTheDocument();
      expect(screen.getByText('Quality')).toBeInTheDocument();
      expect(screen.getByText('Data')).toBeInTheDocument();
    });

    it('applies ARIA tree role to container', () => {
      render(<NavTree {...defaultProps} />);

      const tree = screen.getByRole('tree', { name: 'Protocol navigation' });
      expect(tree).toBeInTheDocument();
    });

    it('applies aria-expanded attribute to group headers', () => {
      render(
        <NavTree
          {...defaultProps}
          expandedGroups={{ protocol: true, advanced: false }}
        />
      );

      const protocolGroup = screen.getByText('Protocol').closest('[role="treeitem"]');
      const advancedGroup = screen.getByText('Advanced').closest('[role="treeitem"]');

      expect(protocolGroup).toHaveAttribute('aria-expanded', 'true');
      expect(advancedGroup).toHaveAttribute('aria-expanded', 'false');
    });
  });

  describe('Group Expansion', () => {
    it('shows child items when group is expanded', () => {
      render(
        <NavTree
          {...defaultProps}
          expandedGroups={{ protocol: true }}
        />
      );

      // Protocol group items should be visible
      expect(screen.getByText('Study Metadata')).toBeInTheDocument();
      expect(screen.getByText('Eligibility Criteria')).toBeInTheDocument();
      expect(screen.getByText('Objectives & Endpoints')).toBeInTheDocument();
    });

    it('hides child items when group is collapsed', () => {
      render(
        <NavTree
          {...defaultProps}
          expandedGroups={{ protocol: false }}
        />
      );

      // Protocol group items should not be visible
      expect(screen.queryByText('Study Metadata')).not.toBeInTheDocument();
      expect(screen.queryByText('Eligibility Criteria')).not.toBeInTheDocument();
    });

    it('calls onToggleGroup when group header is clicked', () => {
      render(<NavTree {...defaultProps} />);

      const protocolButton = screen.getByText('Protocol');
      fireEvent.click(protocolButton);

      expect(mockOnToggleGroup).toHaveBeenCalledWith('protocol');
    });
  });

  describe('Navigation', () => {
    it('calls onNavigate when nav item is clicked', () => {
      render(
        <NavTree
          {...defaultProps}
          expandedGroups={{ protocol: true }}
        />
      );

      const overviewButton = screen.getByText('Study Metadata');
      fireEvent.click(overviewButton);

      expect(mockOnNavigate).toHaveBeenCalledWith('overview');
    });

    it('highlights active item', () => {
      render(
        <NavTree
          {...defaultProps}
          activeTabId="overview"
          expandedGroups={{ protocol: true }}
        />
      );

      const overviewButton = screen.getByText('Study Metadata');
      expect(overviewButton).toHaveClass('bg-accent');
      expect(overviewButton).toHaveAttribute('aria-current', 'page');
    });

    it('does not highlight inactive items', () => {
      render(
        <NavTree
          {...defaultProps}
          activeTabId="overview"
          expandedGroups={{ protocol: true }}
        />
      );

      const eligibilityButton = screen.getByText('Eligibility Criteria');
      expect(eligibilityButton).not.toHaveClass('bg-accent');
      expect(eligibilityButton).not.toHaveAttribute('aria-current');
    });
  });

  describe('Static Group Definitions', () => {
    it('renders Protocol group with correct items', () => {
      render(
        <NavTree
          {...defaultProps}
          expandedGroups={{ protocol: true }}
        />
      );

      expect(screen.getByText('Study Metadata')).toBeInTheDocument();
      expect(screen.getByText('Eligibility Criteria')).toBeInTheDocument();
      expect(screen.getByText('Objectives & Endpoints')).toBeInTheDocument();
      expect(screen.getByText('Study Design')).toBeInTheDocument();
      expect(screen.getByText('Interventions')).toBeInTheDocument();
      expect(screen.getByText('Amendment History')).toBeInTheDocument();
    });

    it('renders Advanced group with correct items', () => {
      render(
        <NavTree
          {...defaultProps}
          expandedGroups={{ advanced: true }}
        />
      );

      expect(screen.getByText('Extensions')).toBeInTheDocument();
      expect(screen.getByText('Advanced Entities')).toBeInTheDocument();
      expect(screen.getByText('Procedures & Devices')).toBeInTheDocument();
      expect(screen.getByText('Study Sites')).toBeInTheDocument();
      expect(screen.getByText('Footnotes')).toBeInTheDocument();
      expect(screen.getByText('Schedule Timeline')).toBeInTheDocument();
      expect(screen.getByText('Narrative')).toBeInTheDocument();
    });

    it('renders Quality group with correct items', () => {
      render(
        <NavTree
          {...defaultProps}
          expandedGroups={{ quality: true }}
        />
      );

      expect(screen.getByText('Quality Metrics')).toBeInTheDocument();
      expect(screen.getByText('Validation Results')).toBeInTheDocument();
    });

    it('renders Data group with correct items', () => {
      render(
        <NavTree
          {...defaultProps}
          expandedGroups={{ data: true }}
        />
      );

      expect(screen.getByText('Document Structure')).toBeInTheDocument();
      expect(screen.getByText('SoA Images')).toBeInTheDocument();
      expect(screen.getByText('SoA Table')).toBeInTheDocument();
      expect(screen.getByText('Timeline')).toBeInTheDocument();
      expect(screen.getByText('Provenance')).toBeInTheDocument();
    });
  });

  describe('Keyboard Navigation', () => {
    it('handles ArrowDown to move focus to next item', () => {
      render(
        <NavTree
          {...defaultProps}
          expandedGroups={{ protocol: true }}
        />
      );

      const tree = screen.getByRole('tree');
      const firstButton = screen.getByText('Protocol');
      
      firstButton.focus();
      fireEvent.keyDown(tree, { key: 'ArrowDown' });

      // Focus should move to first child item
      expect(document.activeElement).toBe(screen.getByText('Study Metadata'));
    });

    it('handles ArrowUp to move focus to previous item', () => {
      render(
        <NavTree
          {...defaultProps}
          expandedGroups={{ protocol: true }}
        />
      );

      const tree = screen.getByRole('tree');
      const secondItem = screen.getByText('Study Metadata');
      
      secondItem.focus();
      fireEvent.keyDown(tree, { key: 'ArrowUp' });

      // Focus should move back to group header
      expect(document.activeElement).toBe(screen.getByText('Protocol'));
    });

    it('handles ArrowRight to expand collapsed group', () => {
      render(
        <NavTree
          {...defaultProps}
          expandedGroups={{ protocol: false }}
        />
      );

      const tree = screen.getByRole('tree');
      const protocolButton = screen.getByText('Protocol');
      
      protocolButton.focus();
      fireEvent.keyDown(tree, { key: 'ArrowRight' });

      expect(mockOnToggleGroup).toHaveBeenCalledWith('protocol');
    });

    it('handles ArrowLeft to collapse expanded group', () => {
      render(
        <NavTree
          {...defaultProps}
          expandedGroups={{ protocol: true }}
        />
      );

      const tree = screen.getByRole('tree');
      const protocolButton = screen.getByText('Protocol');
      
      protocolButton.focus();
      fireEvent.keyDown(tree, { key: 'ArrowLeft' });

      expect(mockOnToggleGroup).toHaveBeenCalledWith('protocol');
    });

    it('handles Enter to activate focused item', () => {
      render(
        <NavTree
          {...defaultProps}
          expandedGroups={{ protocol: true }}
        />
      );

      const tree = screen.getByRole('tree');
      const overviewButton = screen.getByText('Study Metadata');
      
      overviewButton.focus();
      fireEvent.keyDown(tree, { key: 'Enter' });

      expect(mockOnNavigate).toHaveBeenCalledWith('overview');
    });

    it('handles Space to activate focused item', () => {
      render(
        <NavTree
          {...defaultProps}
          expandedGroups={{ protocol: true }}
        />
      );

      const tree = screen.getByRole('tree');
      const overviewButton = screen.getByText('Study Metadata');
      
      overviewButton.focus();
      fireEvent.keyDown(tree, { key: ' ' });

      expect(mockOnNavigate).toHaveBeenCalledWith('overview');
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA labels on group buttons', () => {
      render(
        <NavTree
          {...defaultProps}
          expandedGroups={{ protocol: true }}
        />
      );

      const protocolButton = screen.getByLabelText('Protocol group, expanded');
      expect(protocolButton).toBeInTheDocument();
    });

    it('has proper ARIA labels on nav items', () => {
      render(
        <NavTree
          {...defaultProps}
          expandedGroups={{ protocol: true }}
        />
      );

      const overviewButton = screen.getByLabelText('Study Metadata');
      expect(overviewButton).toBeInTheDocument();
    });

    it('applies role="group" to expanded item containers', () => {
      const { container } = render(
        <NavTree
          {...defaultProps}
          expandedGroups={{ protocol: true }}
        />
      );

      const groups = container.querySelectorAll('[role="group"]');
      expect(groups.length).toBeGreaterThan(0);
    });

    it('applies focus ring styles to focusable elements', () => {
      render(
        <NavTree
          {...defaultProps}
          expandedGroups={{ protocol: true }}
        />
      );

      const protocolButton = screen.getByText('Protocol');
      expect(protocolButton).toHaveClass('focus:ring-2');
    });
  });

  describe('Edge Cases', () => {
    it('handles null activeTabId', () => {
      render(
        <NavTree
          {...defaultProps}
          activeTabId={null}
          expandedGroups={{ protocol: true }}
        />
      );

      const overviewButton = screen.getByText('Study Metadata');
      expect(overviewButton).not.toHaveAttribute('aria-current');
    });

    it('handles empty expandedGroups object', () => {
      render(
        <NavTree
          {...defaultProps}
          expandedGroups={{}}
        />
      );

      // All groups should be collapsed
      expect(screen.queryByText('Study Metadata')).not.toBeInTheDocument();
      expect(screen.queryByText('Extensions')).not.toBeInTheDocument();
      expect(screen.queryByText('Quality Metrics')).not.toBeInTheDocument();
      expect(screen.queryByText('SoA Table')).not.toBeInTheDocument();
    });

    it('handles all groups expanded', () => {
      render(
        <NavTree
          {...defaultProps}
          expandedGroups={{
            protocol: true,
            advanced: true,
            quality: true,
            data: true,
          }}
        />
      );

      // All items should be visible
      expect(screen.getByText('Study Metadata')).toBeInTheDocument();
      expect(screen.getByText('Extensions')).toBeInTheDocument();
      expect(screen.getByText('Quality Metrics')).toBeInTheDocument();
      expect(screen.getByText('SoA Table')).toBeInTheDocument();
    });
  });
});
