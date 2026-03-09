import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { StatusBar } from '../StatusBar';

describe('StatusBar', () => {
  const defaultProps = {
    protocolId: 'PROTO-2024-001',
    usdmVersion: '3.0.0',
    isDirty: false,
    overlayStatus: 'draft' as const,
    validationIssueCount: 0,
    onSaveDraft: vi.fn(),
    onPublish: vi.fn(),
    onResetToPublished: vi.fn(),
  };

  it('renders protocol ID', () => {
    render(<StatusBar {...defaultProps} />);
    expect(screen.getByText('PROTO-2024-001')).toBeInTheDocument();
  });

  it('renders USDM version when provided', () => {
    render(<StatusBar {...defaultProps} />);
    expect(screen.getByText(/USDM 3\.0\.0/i)).toBeInTheDocument();
  });

  it('does not render USDM version when undefined', () => {
    render(<StatusBar {...defaultProps} usdmVersion={undefined} />);
    expect(screen.queryByText(/USDM/i)).not.toBeInTheDocument();
  });

  it('displays draft badge with orange styling', () => {
    render(<StatusBar {...defaultProps} overlayStatus="draft" />);
    const badge = screen.getByText('Draft');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass('bg-orange-500');
  });

  it('displays published badge with green styling', () => {
    render(<StatusBar {...defaultProps} overlayStatus="published" />);
    const badge = screen.getByText('Published');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass('bg-green-600');
  });

  it('shows dirty indicator when isDirty is true', () => {
    render(<StatusBar {...defaultProps} isDirty={true} />);
    expect(screen.getByText('Unsaved changes')).toBeInTheDocument();
  });

  it('does not show dirty indicator when isDirty is false', () => {
    render(<StatusBar {...defaultProps} isDirty={false} />);
    expect(screen.queryByText('Unsaved changes')).not.toBeInTheDocument();
  });

  it('shows validation issue count when greater than zero', () => {
    render(<StatusBar {...defaultProps} validationIssueCount={5} />);
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByLabelText('5 validation issues')).toBeInTheDocument();
  });

  it('does not show validation issue count when zero', () => {
    render(<StatusBar {...defaultProps} validationIssueCount={0} />);
    expect(screen.queryByLabelText(/validation issues/i)).not.toBeInTheDocument();
  });

  it('calls onSaveDraft when Save Draft button is clicked', async () => {
    const user = userEvent.setup();
    const onSaveDraft = vi.fn();
    render(<StatusBar {...defaultProps} isDirty={true} onSaveDraft={onSaveDraft} />);

    const saveButton = screen.getByRole('button', { name: /save draft/i });
    await user.click(saveButton);

    expect(onSaveDraft).toHaveBeenCalledTimes(1);
  });

  it('disables Save Draft button when not dirty', () => {
    render(<StatusBar {...defaultProps} isDirty={false} />);
    const saveButton = screen.getByRole('button', { name: /save draft/i });
    expect(saveButton).toBeDisabled();
  });

  it('enables Save Draft button when dirty', () => {
    render(<StatusBar {...defaultProps} isDirty={true} />);
    const saveButton = screen.getByRole('button', { name: /save draft/i });
    expect(saveButton).not.toBeDisabled();
  });

  it('calls onPublish when Publish button is clicked', async () => {
    const user = userEvent.setup();
    const onPublish = vi.fn();
    render(<StatusBar {...defaultProps} onPublish={onPublish} />);

    const publishButton = screen.getByRole('button', { name: /publish/i });
    await user.click(publishButton);

    expect(onPublish).toHaveBeenCalledTimes(1);
  });

  it('calls onResetToPublished when Reset button is clicked', async () => {
    const user = userEvent.setup();
    const onResetToPublished = vi.fn();
    render(<StatusBar {...defaultProps} isDirty={true} onResetToPublished={onResetToPublished} />);

    const resetButton = screen.getByRole('button', { name: /reset/i });
    await user.click(resetButton);

    expect(onResetToPublished).toHaveBeenCalledTimes(1);
  });

  it('disables Reset button when published and not dirty', () => {
    render(<StatusBar {...defaultProps} overlayStatus="published" isDirty={false} />);
    const resetButton = screen.getByRole('button', { name: /reset/i });
    expect(resetButton).toBeDisabled();
  });

  it('enables Reset button when published but dirty', () => {
    render(<StatusBar {...defaultProps} overlayStatus="published" isDirty={true} />);
    const resetButton = screen.getByRole('button', { name: /reset/i });
    expect(resetButton).not.toBeDisabled();
  });

  it('enables Reset button when in draft status', () => {
    render(<StatusBar {...defaultProps} overlayStatus="draft" isDirty={false} />);
    const resetButton = screen.getByRole('button', { name: /reset/i });
    expect(resetButton).not.toBeDisabled();
  });

  it('implements ARIA contentinfo landmark', () => {
    render(<StatusBar {...defaultProps} />);
    const footer = screen.getByRole('contentinfo');
    expect(footer).toBeInTheDocument();
    expect(footer).toHaveAttribute('aria-label', 'Status Bar');
  });

  it('renders all action buttons', () => {
    render(<StatusBar {...defaultProps} />);
    expect(screen.getByRole('button', { name: /save draft/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /publish/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /reset/i })).toBeInTheDocument();
  });

  it('displays correct validation issue count for singular issue', () => {
    render(<StatusBar {...defaultProps} validationIssueCount={1} />);
    expect(screen.getByLabelText('1 validation issues')).toBeInTheDocument();
  });

  it('displays correct validation issue count for multiple issues', () => {
    render(<StatusBar {...defaultProps} validationIssueCount={10} />);
    expect(screen.getByLabelText('10 validation issues')).toBeInTheDocument();
  });

  it('has fixed positioning at viewport bottom', () => {
    const { container } = render(<StatusBar {...defaultProps} />);
    const footer = container.querySelector('footer');
    expect(footer).toHaveClass('fixed', 'bottom-0', 'left-0', 'right-0');
  });

  it('has correct height (32px / h-8)', () => {
    const { container } = render(<StatusBar {...defaultProps} />);
    const footer = container.querySelector('footer');
    expect(footer).toHaveClass('h-8');
  });

  it('has border-top for visual separation', () => {
    const { container } = render(<StatusBar {...defaultProps} />);
    const footer = container.querySelector('footer');
    expect(footer).toHaveClass('border-t');
  });

  it('shows dirty indicator with pulse animation', () => {
    const { container } = render(<StatusBar {...defaultProps} isDirty={true} />);
    const dirtyDot = container.querySelector('.animate-pulse');
    expect(dirtyDot).toBeInTheDocument();
    expect(dirtyDot).toHaveClass('bg-orange-500');
  });

  it('renders with high z-index for visibility', () => {
    const { container } = render(<StatusBar {...defaultProps} />);
    const footer = container.querySelector('footer');
    expect(footer).toHaveClass('z-40');
  });

  it('displays protocol metadata in left section', () => {
    render(<StatusBar {...defaultProps} />);
    const protocolId = screen.getByText('PROTO-2024-001');
    const usdmVersion = screen.getByText(/USDM 3\.0\.0/i);
    
    // Both should be in the document
    expect(protocolId).toBeInTheDocument();
    expect(usdmVersion).toBeInTheDocument();
  });

  it('displays action buttons in right section', () => {
    render(<StatusBar {...defaultProps} />);
    const buttons = screen.getAllByRole('button');
    
    // Should have 3 action buttons
    expect(buttons).toHaveLength(3);
  });

  it('handles missing usdmVersion gracefully', () => {
    render(<StatusBar {...defaultProps} usdmVersion={undefined} />);
    
    // Should still render protocol ID
    expect(screen.getByText('PROTO-2024-001')).toBeInTheDocument();
    
    // Should not render separator or version
    expect(screen.queryByText('|')).not.toBeInTheDocument();
  });

  it('renders validation icon when issues exist', () => {
    const { container } = render(<StatusBar {...defaultProps} validationIssueCount={3} />);
    
    // AlertCircle icon should be rendered (Lucide icon)
    const validationButton = screen.getByLabelText('3 validation issues');
    expect(validationButton).toBeInTheDocument();
  });

  it('applies correct styling to validation count button', () => {
    render(<StatusBar {...defaultProps} validationIssueCount={5} />);
    const validationButton = screen.getByLabelText('5 validation issues');
    
    expect(validationButton).toHaveClass('text-destructive');
  });
});
