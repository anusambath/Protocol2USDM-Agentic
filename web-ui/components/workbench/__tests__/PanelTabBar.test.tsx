import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PanelTabBar } from '../PanelTabBar';

describe('PanelTabBar', () => {
  const mockTabs = [
    { id: 'tab1', label: 'Overview', icon: 'FileText', closable: true },
    { id: 'tab2', label: 'Timeline', icon: 'Clock', closable: true },
    { id: 'tab3', label: 'Schedule', icon: 'Calendar', closable: false },
  ];

  it('renders all tabs with icons and labels', () => {
    const onTabChange = vi.fn();
    render(<PanelTabBar tabs={mockTabs} activeTabId="tab1" onTabChange={onTabChange} />);

    expect(screen.getByRole('tab', { name: /overview/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /timeline/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /schedule/i })).toBeInTheDocument();
  });

  it('marks the active tab with aria-selected', () => {
    const onTabChange = vi.fn();
    render(<PanelTabBar tabs={mockTabs} activeTabId="tab2" onTabChange={onTabChange} />);

    const activeTab = screen.getByRole('tab', { name: /timeline/i });
    expect(activeTab).toHaveAttribute('aria-selected', 'true');

    const inactiveTab = screen.getByRole('tab', { name: /overview/i });
    expect(inactiveTab).toHaveAttribute('aria-selected', 'false');
  });

  it('calls onTabChange when a tab is clicked', async () => {
    const user = userEvent.setup();
    const onTabChange = vi.fn();
    render(<PanelTabBar tabs={mockTabs} activeTabId="tab1" onTabChange={onTabChange} />);

    const tab2 = screen.getByRole('tab', { name: /timeline/i });
    await user.click(tab2);

    expect(onTabChange).toHaveBeenCalledWith('tab2');
  });

  it('renders close buttons for closable tabs when onTabClose is provided', () => {
    const onTabChange = vi.fn();
    const onTabClose = vi.fn();
    render(
      <PanelTabBar
        tabs={mockTabs}
        activeTabId="tab1"
        onTabChange={onTabChange}
        onTabClose={onTabClose}
      />
    );

    // Tab1 and Tab2 are closable
    expect(screen.getByLabelText('Close Overview')).toBeInTheDocument();
    expect(screen.getByLabelText('Close Timeline')).toBeInTheDocument();

    // Tab3 is not closable
    expect(screen.queryByLabelText('Close Schedule')).not.toBeInTheDocument();
  });

  it('does not render close buttons when onTabClose is not provided', () => {
    const onTabChange = vi.fn();
    render(<PanelTabBar tabs={mockTabs} activeTabId="tab1" onTabChange={onTabChange} />);

    expect(screen.queryByLabelText(/close/i)).not.toBeInTheDocument();
  });

  it('calls onTabClose when close button is clicked', async () => {
    const user = userEvent.setup();
    const onTabChange = vi.fn();
    const onTabClose = vi.fn();
    render(
      <PanelTabBar
        tabs={mockTabs}
        activeTabId="tab1"
        onTabChange={onTabChange}
        onTabClose={onTabClose}
      />
    );

    const closeButton = screen.getByLabelText('Close Overview');
    await user.click(closeButton);

    expect(onTabClose).toHaveBeenCalledWith('tab1');
    expect(onTabChange).not.toHaveBeenCalled(); // Should not activate the tab
  });

  it('navigates to next tab with ArrowRight key', async () => {
    const user = userEvent.setup();
    const onTabChange = vi.fn();
    render(<PanelTabBar tabs={mockTabs} activeTabId="tab1" onTabChange={onTabChange} />);

    const activeTab = screen.getByRole('tab', { name: /overview/i });
    activeTab.focus();
    await user.keyboard('{ArrowRight}');

    expect(onTabChange).toHaveBeenCalledWith('tab2');
  });

  it('navigates to previous tab with ArrowLeft key', async () => {
    const user = userEvent.setup();
    const onTabChange = vi.fn();
    render(<PanelTabBar tabs={mockTabs} activeTabId="tab2" onTabChange={onTabChange} />);

    const tabList = screen.getByRole('tablist');
    tabList.focus();
    await user.keyboard('{ArrowLeft}');

    expect(onTabChange).toHaveBeenCalledWith('tab1');
  });

  it('wraps to last tab when pressing ArrowLeft on first tab', async () => {
    const user = userEvent.setup();
    const onTabChange = vi.fn();
    render(<PanelTabBar tabs={mockTabs} activeTabId="tab1" onTabChange={onTabChange} />);

    const tabList = screen.getByRole('tablist');
    tabList.focus();
    await user.keyboard('{ArrowLeft}');

    expect(onTabChange).toHaveBeenCalledWith('tab3');
  });

  it('wraps to first tab when pressing ArrowRight on last tab', async () => {
    const user = userEvent.setup();
    const onTabChange = vi.fn();
    render(<PanelTabBar tabs={mockTabs} activeTabId="tab3" onTabChange={onTabChange} />);

    const tabList = screen.getByRole('tablist');
    tabList.focus();
    await user.keyboard('{ArrowRight}');

    expect(onTabChange).toHaveBeenCalledWith('tab1');
  });

  it('navigates to first tab with Home key', async () => {
    const user = userEvent.setup();
    const onTabChange = vi.fn();
    render(<PanelTabBar tabs={mockTabs} activeTabId="tab3" onTabChange={onTabChange} />);

    const tabList = screen.getByRole('tablist');
    tabList.focus();
    await user.keyboard('{Home}');

    expect(onTabChange).toHaveBeenCalledWith('tab1');
  });

  it('navigates to last tab with End key', async () => {
    const user = userEvent.setup();
    const onTabChange = vi.fn();
    render(<PanelTabBar tabs={mockTabs} activeTabId="tab1" onTabChange={onTabChange} />);

    const tabList = screen.getByRole('tablist');
    tabList.focus();
    await user.keyboard('{End}');

    expect(onTabChange).toHaveBeenCalledWith('tab3');
  });

  it('implements ARIA tablist pattern correctly', () => {
    const onTabChange = vi.fn();
    render(<PanelTabBar tabs={mockTabs} activeTabId="tab1" onTabChange={onTabChange} />);

    const tabList = screen.getByRole('tablist');
    expect(tabList).toHaveAttribute('aria-label', 'Panel tabs');

    const tabs = screen.getAllByRole('tab');
    expect(tabs).toHaveLength(3);

    tabs.forEach((tab, index) => {
      expect(tab).toHaveAttribute('aria-controls', `panel-${mockTabs[index].id}`);
    });
  });

  it('sets correct tabIndex values (0 for active, -1 for inactive)', () => {
    const onTabChange = vi.fn();
    render(<PanelTabBar tabs={mockTabs} activeTabId="tab2" onTabChange={onTabChange} />);

    const activeTab = screen.getByRole('tab', { name: /timeline/i });
    expect(activeTab).toHaveAttribute('tabIndex', '0');

    const inactiveTab1 = screen.getByRole('tab', { name: /overview/i });
    expect(inactiveTab1).toHaveAttribute('tabIndex', '-1');

    const inactiveTab2 = screen.getByRole('tab', { name: /schedule/i });
    expect(inactiveTab2).toHaveAttribute('tabIndex', '-1');
  });

  it('returns null when tabs array is empty', () => {
    const onTabChange = vi.fn();
    const { container } = render(
      <PanelTabBar tabs={[]} activeTabId={null} onTabChange={onTabChange} />
    );

    expect(container.firstChild).toBeNull();
  });

  it('uses fallback icon when icon name is not found', () => {
    const onTabChange = vi.fn();
    const tabsWithInvalidIcon = [
      { id: 'tab1', label: 'Test', icon: 'NonExistentIcon', closable: false },
    ];

    // Should not throw an error
    expect(() => {
      render(
        <PanelTabBar tabs={tabsWithInvalidIcon} activeTabId="tab1" onTabChange={onTabChange} />
      );
    }).not.toThrow();

    expect(screen.getByRole('tab', { name: /test/i })).toBeInTheDocument();
  });
});
