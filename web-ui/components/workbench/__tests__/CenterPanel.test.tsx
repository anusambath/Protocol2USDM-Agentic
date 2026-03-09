import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CenterPanel } from '../CenterPanel';
import { LayoutTab } from '@/stores/layoutStore';

// Mock the viewRegistry
vi.mock('@/lib/viewRegistry', () => ({
  viewRegistry: {
    overview: {
      viewType: 'overview',
      label: 'Study Metadata',
      icon: 'FileText',
      group: 'protocol',
      component: () => <div data-testid="overview-view">Overview View</div>,
    },
    soa: {
      viewType: 'soa',
      label: 'SoA Table',
      icon: 'Table',
      group: 'data',
      component: () => <div data-testid="soa-view">SoA View</div>,
    },
    timeline: {
      viewType: 'timeline',
      label: 'Timeline',
      icon: 'GitBranch',
      group: 'data',
      component: () => <div data-testid="timeline-view">Timeline View</div>,
    },
  },
}));

describe('CenterPanel', () => {
  const mockUsdm = { studyId: 'test-123' };
  const mockProtocolId = 'protocol-123';
  const mockProvenance = { cellId: 'test' };
  const mockIntermediateFiles = { file1: 'data' };

  const defaultProps = {
    openTabs: [] as LayoutTab[],
    activeTabId: null,
    onTabChange: vi.fn(),
    onTabClose: vi.fn(),
    usdm: mockUsdm,
    protocolId: mockProtocolId,
    provenance: mockProvenance,
    intermediateFiles: mockIntermediateFiles,
  };

  it('renders welcome state when no tabs are open', () => {
    render(<CenterPanel {...defaultProps} />);

    expect(screen.getByText('Welcome to Protocol2USDM')).toBeInTheDocument();
    expect(
      screen.getByText('Select a view from the sidebar or choose a quick action below to get started')
    ).toBeInTheDocument();
  });

  it('displays quick action links in welcome state', () => {
    render(<CenterPanel {...defaultProps} />);

    expect(screen.getByText('Study Metadata')).toBeInTheDocument();
    expect(screen.getByText('SoA Table')).toBeInTheDocument();
    expect(screen.getByText('Timeline')).toBeInTheDocument();
    expect(screen.getByText('Quality Metrics')).toBeInTheDocument();
  });

  it('calls onTabChange when quick action is clicked', async () => {
    const user = userEvent.setup();
    const onTabChange = vi.fn();

    render(<CenterPanel {...defaultProps} onTabChange={onTabChange} />);

    const soaButton = screen.getByText('SoA Table').closest('button');
    expect(soaButton).toBeInTheDocument();

    if (soaButton) {
      await user.click(soaButton);
      expect(onTabChange).toHaveBeenCalledWith('soa');
    }
  });

  it('renders PanelTabBar when tabs are open', () => {
    const openTabs: LayoutTab[] = [
      { id: 'overview-1', viewType: 'overview', label: 'Study Metadata', icon: 'FileText' },
      { id: 'soa-1', viewType: 'soa', label: 'SoA Table', icon: 'Table' },
    ];

    render(<CenterPanel {...defaultProps} openTabs={openTabs} activeTabId="overview-1" />);

    expect(screen.getByRole('tablist')).toBeInTheDocument();
    expect(screen.getByText('Study Metadata')).toBeInTheDocument();
    expect(screen.getByText('SoA Table')).toBeInTheDocument();
  });

  it('renders active view component', () => {
    const openTabs: LayoutTab[] = [
      { id: 'overview-1', viewType: 'overview', label: 'Study Metadata', icon: 'FileText' },
    ];

    render(<CenterPanel {...defaultProps} openTabs={openTabs} activeTabId="overview-1" />);

    expect(screen.getByTestId('overview-view')).toBeInTheDocument();
    expect(screen.getByText('Overview View')).toBeInTheDocument();
  });

  it('only renders active tab component (lazy rendering)', () => {
    const openTabs: LayoutTab[] = [
      { id: 'overview-1', viewType: 'overview', label: 'Study Metadata', icon: 'FileText' },
      { id: 'soa-1', viewType: 'soa', label: 'SoA Table', icon: 'Table' },
    ];

    render(<CenterPanel {...defaultProps} openTabs={openTabs} activeTabId="overview-1" />);

    // Only active tab should be rendered
    expect(screen.getByTestId('overview-view')).toBeInTheDocument();
    expect(screen.queryByTestId('soa-view')).not.toBeInTheDocument();
  });

  it('switches active view when activeTabId changes', () => {
    const openTabs: LayoutTab[] = [
      { id: 'overview-1', viewType: 'overview', label: 'Study Metadata', icon: 'FileText' },
      { id: 'soa-1', viewType: 'soa', label: 'SoA Table', icon: 'Table' },
    ];

    const { rerender } = render(
      <CenterPanel {...defaultProps} openTabs={openTabs} activeTabId="overview-1" />
    );

    expect(screen.getByTestId('overview-view')).toBeInTheDocument();

    // Change active tab
    rerender(<CenterPanel {...defaultProps} openTabs={openTabs} activeTabId="soa-1" />);

    expect(screen.queryByTestId('overview-view')).not.toBeInTheDocument();
    expect(screen.getByTestId('soa-view')).toBeInTheDocument();
  });

  it('passes correct props to view components', () => {
    const openTabs: LayoutTab[] = [
      { id: 'overview-1', viewType: 'overview', label: 'Study Metadata', icon: 'FileText' },
    ];

    const onCellSelect = vi.fn();
    const onNodeSelect = vi.fn();

    render(
      <CenterPanel
        {...defaultProps}
        openTabs={openTabs}
        activeTabId="overview-1"
        onCellSelect={onCellSelect}
        onNodeSelect={onNodeSelect}
      />
    );

    // View component should be rendered (props are passed internally)
    expect(screen.getByTestId('overview-view')).toBeInTheDocument();
  });

  it('calls onTabClose when tab close button is clicked', async () => {
    const user = userEvent.setup();
    const onTabClose = vi.fn();

    const openTabs: LayoutTab[] = [
      { id: 'overview-1', viewType: 'overview', label: 'Study Metadata', icon: 'FileText' },
    ];

    render(
      <CenterPanel {...defaultProps} openTabs={openTabs} activeTabId="overview-1" onTabClose={onTabClose} />
    );

    const closeButton = screen.getByLabelText('Close Study Metadata');
    await user.click(closeButton);

    expect(onTabClose).toHaveBeenCalledWith('overview-1');
  });

  it('has correct ARIA attributes', () => {
    const openTabs: LayoutTab[] = [
      { id: 'overview-1', viewType: 'overview', label: 'Study Metadata', icon: 'FileText' },
    ];

    render(<CenterPanel {...defaultProps} openTabs={openTabs} activeTabId="overview-1" />);

    const main = screen.getByRole('main');
    expect(main).toHaveAttribute('aria-label', 'Center panel');

    const tabpanel = screen.getByRole('tabpanel');
    expect(tabpanel).toHaveAttribute('id', 'panel-overview-1');
    expect(tabpanel).toHaveAttribute('aria-labelledby', 'tab-overview-1');
  });

  it('displays welcome state when last tab is closed', () => {
    const openTabs: LayoutTab[] = [
      { id: 'overview-1', viewType: 'overview', label: 'Study Metadata', icon: 'FileText' },
    ];

    const { rerender } = render(
      <CenterPanel {...defaultProps} openTabs={openTabs} activeTabId="overview-1" />
    );

    expect(screen.getByTestId('overview-view')).toBeInTheDocument();

    // Close the last tab
    rerender(<CenterPanel {...defaultProps} openTabs={[]} activeTabId={null} />);

    expect(screen.queryByTestId('overview-view')).not.toBeInTheDocument();
    expect(screen.getByText('Welcome to Protocol2USDM')).toBeInTheDocument();
  });

  it('handles missing view component gracefully', () => {
    const openTabs: LayoutTab[] = [
      { id: 'unknown-1', viewType: 'unknown' as any, label: 'Unknown View', icon: 'FileText' },
    ];

    render(<CenterPanel {...defaultProps} openTabs={openTabs} activeTabId="unknown-1" />);

    // Should display welcome state when view component is not found
    expect(screen.getByText('Welcome to Protocol2USDM')).toBeInTheDocument();
  });
});
