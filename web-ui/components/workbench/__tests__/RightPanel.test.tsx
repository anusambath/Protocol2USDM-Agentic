import { describe, it, expect, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RightPanel } from '../RightPanel';
import { RightPanelTab } from '@/stores/layoutStore';

describe('RightPanel', () => {
  const defaultProps = {
    collapsed: false,
    width: 320,
    activeTab: 'properties' as RightPanelTab,
    onTabChange: vi.fn(),
    activeViewType: 'soa' as string | null,
    selectedCellId: null,
    selectedNodeId: null,
    usdm: {},
    provenance: null,
  };

  describe('Rendering', () => {
    it('renders with complementary role and label', () => {
      render(<RightPanel {...defaultProps} />);
      const panel = screen.getByRole('complementary', { name: /right panel/i });
      expect(panel).toBeInTheDocument();
    });

    it('renders three tabs: Properties, Provenance, Footnotes', () => {
      render(<RightPanel {...defaultProps} />);
      expect(screen.getByRole('tab', { name: /properties/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /provenance/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /footnotes/i })).toBeInTheDocument();
    });

    it('does not render tabs when collapsed', () => {
      render(<RightPanel {...defaultProps} collapsed={true} />);
      expect(screen.queryByRole('tab')).not.toBeInTheDocument();
    });

    it('sets aria-hidden when collapsed', () => {
      render(<RightPanel {...defaultProps} collapsed={true} />);
      const panel = screen.getByRole('complementary', { name: /right panel/i, hidden: true });
      expect(panel).toHaveAttribute('aria-hidden', 'true');
    });
  });

  describe('Tab Navigation', () => {
    it('displays Properties tab content when activeTab is properties', () => {
      render(<RightPanel {...defaultProps} activeTab="properties" />);
      expect(screen.getByText('Properties')).toBeInTheDocument();
    });

    it('displays Provenance tab content when activeTab is provenance', () => {
      render(<RightPanel {...defaultProps} activeTab="provenance" />);
      expect(screen.getByText('Provenance')).toBeInTheDocument();
    });

    it('displays Footnotes tab content when activeTab is footnotes', () => {
      render(<RightPanel {...defaultProps} activeTab="footnotes" />);
      expect(screen.getByText('Footnotes')).toBeInTheDocument();
    });

    it('calls onTabChange when a tab is clicked', async () => {
      const user = userEvent.setup();
      const onTabChange = vi.fn();
      render(<RightPanel {...defaultProps} onTabChange={onTabChange} />);

      const provenanceTab = screen.getByRole('tab', { name: /provenance/i });
      await user.click(provenanceTab);

      expect(onTabChange).toHaveBeenCalledWith('provenance');
    });
  });

  describe('Properties Tab', () => {
    it('displays empty state when no selection is active', () => {
      render(<RightPanel {...defaultProps} activeTab="properties" />);
      expect(screen.getByText('No selection')).toBeInTheDocument();
      expect(
        screen.getByText(/select a cell or node to view its properties/i)
      ).toBeInTheDocument();
    });

    it('displays cell ID when selectedCellId is provided', () => {
      render(
        <RightPanel
          {...defaultProps}
          activeTab="properties"
          selectedCellId="cell-row-3-col-5"
        />
      );
      expect(screen.getByText(/cell: cell-row-3-col-5/i)).toBeInTheDocument();
    });

    it('displays node ID when selectedNodeId is provided', () => {
      render(
        <RightPanel
          {...defaultProps}
          activeTab="properties"
          selectedNodeId="node-visit-1"
        />
      );
      expect(screen.getByText(/node: node-visit-1/i)).toBeInTheDocument();
    });

    it('displays both cell and node when both are selected', () => {
      render(
        <RightPanel
          {...defaultProps}
          activeTab="properties"
          selectedCellId="cell-row-2-col-3"
          selectedNodeId="node-visit-2"
        />
      );
      expect(screen.getByText(/cell: cell-row-2-col-3/i)).toBeInTheDocument();
      expect(screen.getByText(/node: node-visit-2/i)).toBeInTheDocument();
    });

    it('displays placeholder message', () => {
      render(
        <RightPanel
          {...defaultProps}
          activeTab="properties"
          selectedCellId="cell-1"
        />
      );
      expect(screen.getByText(/properties panel coming soon/i)).toBeInTheDocument();
    });
  });

  describe('Provenance Tab', () => {
    it('displays empty state when no cell is selected', () => {
      render(<RightPanel {...defaultProps} activeTab="provenance" />);
      expect(screen.getByText('No cell selected')).toBeInTheDocument();
      expect(
        screen.getByText(/select a cell in the soa table to view its provenance details/i)
      ).toBeInTheDocument();
    });

    it('displays selected cell ID when selectedCellId is provided', () => {
      render(
        <RightPanel
          {...defaultProps}
          activeTab="provenance"
          selectedCellId="cell-row-4-col-2"
        />
      );
      expect(screen.getByText('cell-row-4-col-2')).toBeInTheDocument();
    });

    it('displays placeholder message when cell is selected', () => {
      render(
        <RightPanel
          {...defaultProps}
          activeTab="provenance"
          selectedCellId="cell-1"
        />
      );
      expect(screen.getByText(/provenance panel coming soon/i)).toBeInTheDocument();
    });

    it('does not display node selection in provenance tab', () => {
      render(
        <RightPanel
          {...defaultProps}
          activeTab="provenance"
          selectedNodeId="node-visit-1"
        />
      );
      // Should show empty state since provenance only cares about cells
      expect(screen.getByText('No cell selected')).toBeInTheDocument();
    });
  });

  describe('Footnotes Tab', () => {
    it('displays empty state when no cell is selected and no footnotes', () => {
      render(<RightPanel {...defaultProps} activeTab="footnotes" />);
      expect(screen.getByText('No cell selected')).toBeInTheDocument();
    });

    it('displays no footnotes message when cell selected but no USDM footnotes', () => {
      render(
        <RightPanel
          {...defaultProps}
          activeTab="footnotes"
          selectedCellId="cell-row-1|col-1"
        />
      );
      // With no soaFootnotes in USDM and a cell selected, shows protocol-level empty state
      expect(screen.getByText('No footnotes')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('implements ARIA tabpanel pattern', () => {
      render(<RightPanel {...defaultProps} activeTab="properties" />);
      const tabpanel = screen.getByRole('tabpanel');
      expect(tabpanel).toHaveAttribute('id', 'panel-properties');
      expect(tabpanel).toHaveAttribute('aria-labelledby', 'tab-properties');
    });

    it('has correct tabpanel ID for each tab', () => {
      const { rerender } = render(<RightPanel {...defaultProps} activeTab="properties" />);
      expect(screen.getByRole('tabpanel')).toHaveAttribute('id', 'panel-properties');

      rerender(<RightPanel {...defaultProps} activeTab="provenance" />);
      expect(screen.getByRole('tabpanel')).toHaveAttribute('id', 'panel-provenance');

      rerender(<RightPanel {...defaultProps} activeTab="footnotes" />);
      expect(screen.getByRole('tabpanel')).toHaveAttribute('id', 'panel-footnotes');
    });
  });

  describe('Reactive Updates', () => {
    it('updates content when selectedCellId changes', () => {
      const { rerender } = render(
        <RightPanel {...defaultProps} activeTab="properties" selectedCellId={null} />
      );
      expect(screen.getByText('No selection')).toBeInTheDocument();

      rerender(
        <RightPanel
          {...defaultProps}
          activeTab="properties"
          selectedCellId="cell-new"
        />
      );
      expect(screen.getByText(/cell: cell-new/i)).toBeInTheDocument();
    });

    it('updates content when selectedNodeId changes', () => {
      const { rerender } = render(
        <RightPanel {...defaultProps} activeTab="properties" selectedNodeId={null} />
      );
      expect(screen.getByText('No selection')).toBeInTheDocument();

      rerender(
        <RightPanel
          {...defaultProps}
          activeTab="properties"
          selectedNodeId="node-new"
        />
      );
      expect(screen.getByText(/node: node-new/i)).toBeInTheDocument();
    });

    it('updates content when activeTab changes', () => {
      const { rerender } = render(
        <RightPanel
          {...defaultProps}
          activeTab="properties"
          selectedCellId="cell-1"
        />
      );
      expect(screen.getByText('Properties')).toBeInTheDocument();

      rerender(
        <RightPanel
          {...defaultProps}
          activeTab="provenance"
          selectedCellId="cell-1"
        />
      );
      expect(screen.getByText('Provenance')).toBeInTheDocument();
    });
  });

  describe('Width Animation', () => {
    it('applies width from props when not collapsed', () => {
      render(<RightPanel {...defaultProps} width={400} />);
      const panel = screen.getByRole('complementary', { name: /right panel/i });
      // Framer Motion applies inline styles
      expect(panel).toHaveStyle({ minWidth: '400px' });
    });

    it('applies minWidth 0 when collapsed', () => {
      render(<RightPanel {...defaultProps} collapsed={true} width={400} />);
      const panel = screen.getByRole('complementary', { name: /right panel/i, hidden: true });
      expect(panel).toHaveStyle({ minWidth: '0px' });
    });
  });

  describe('Edge Cases', () => {
    it('handles empty usdm object', () => {
      render(
        <RightPanel
          {...defaultProps}
          activeTab="properties"
          selectedCellId="cell-1"
          usdm={{}}
        />
      );
      expect(screen.getByText(/properties panel coming soon/i)).toBeInTheDocument();
    });

    it('handles null provenance', () => {
      render(
        <RightPanel
          {...defaultProps}
          activeTab="provenance"
          selectedCellId="cell-1"
          provenance={null}
        />
      );
      expect(screen.getByText(/provenance panel coming soon/i)).toBeInTheDocument();
    });

    it('handles switching between tabs with different selection requirements', async () => {
      const user = userEvent.setup();
      render(
        <RightPanel
          {...defaultProps}
          activeTab="properties"
          selectedNodeId="node-1"
        />
      );

      // Properties tab shows node selection
      expect(screen.getByText(/node: node-1/i)).toBeInTheDocument();

      // Switch to provenance tab (only cares about cells)
      const provenanceTab = screen.getByRole('tab', { name: /provenance/i });
      await user.click(provenanceTab);

      // Should show empty state since no cell is selected
      expect(screen.getByText('No cell selected')).toBeInTheDocument();
    });
  });
});
