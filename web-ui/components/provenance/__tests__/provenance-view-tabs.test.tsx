/**
 * Tests for ProvenanceView tab navigation and split view
 * 
 * Validates:
 * - Tab navigation renders all 5 tabs
 * - Split view layout with resizable divider
 * - localStorage persistence of split ratio
 * - Tab content switching
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ProvenanceView } from '../ProvenanceView';
import type { ProvenanceData } from '@/lib/provenance/types';

// Mock the stores
vi.mock('@/stores/protocolStore', () => ({
  useProtocolStore: vi.fn((selector) => {
    const mockStudyDesign = {
      activities: [
        { id: 'act1', name: 'Activity 1', label: 'Activity 1' },
        { id: 'act2', name: 'Activity 2', label: 'Activity 2' },
      ],
      encounters: [
        { id: 'enc1', name: 'Encounter 1', timing: { windowLabel: 'Visit 1' } },
        { id: 'enc2', name: 'Encounter 2', timing: { windowLabel: 'Visit 2' } },
      ],
    };
    return selector({ studyDesign: mockStudyDesign });
  }),
  selectStudyDesign: (state: any) => state.studyDesign,
}));

// Mock ProvenanceExplorer
vi.mock('../ProvenanceExplorer', () => ({
  ProvenanceExplorer: ({ provenance, activities, encounters }: any) => (
    <div data-testid="provenance-explorer">
      ProvenanceExplorer with {activities.length} activities and {encounters.length} encounters
    </div>
  ),
}));

const mockProvenance: ProvenanceData = {
  cells: {
    'act1|enc1': 'both',
    'act1|enc2': 'text',
    'act2|enc1': 'vision',
  },
  cellFootnotes: {},
  cellPageRefs: {},
  entities: {},
  metadata: {
    extractionDate: '2024-01-01',
    pipelineVersion: '1.0.0',
    protocolId: 'test-protocol',
    totalEntities: 3,
  },
};

describe('ProvenanceView - Tab Navigation', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();
  });

  it('renders all 5 tabs', () => {
    render(<ProvenanceView provenance={mockProvenance} />);

    expect(screen.getByRole('tab', { name: /overview/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /by section/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /by agent/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /by page/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /soa details/i })).toBeInTheDocument();
  });

  it('defaults to Overview tab', () => {
    render(<ProvenanceView provenance={mockProvenance} />);

    const overviewTab = screen.getByRole('tab', { name: /overview/i });
    expect(overviewTab).toHaveAttribute('data-state', 'active');
  });

  it('switches tabs when clicked', () => {
    render(<ProvenanceView provenance={mockProvenance} />);

    // Click on By Section tab
    const bySectionTab = screen.getByRole('tab', { name: /by section/i });
    fireEvent.click(bySectionTab);

    expect(bySectionTab).toHaveAttribute('data-state', 'active');
    // By Section tab now shows "No entity provenance data available" since mockProvenance has no entities
    expect(screen.getByText(/no entity provenance data available/i)).toBeInTheDocument();
  });

  it('renders ProvenanceExplorer in SOA Details tab', () => {
    render(<ProvenanceView provenance={mockProvenance} />);

    // Click on SOA Details tab
    const soaTab = screen.getByRole('tab', { name: /soa details/i });
    fireEvent.click(soaTab);

    expect(screen.getByTestId('provenance-explorer')).toBeInTheDocument();
    expect(screen.getByText(/2 activities and 2 encounters/i)).toBeInTheDocument();
  });

  it('renders placeholder content for Overview tab', () => {
    render(<ProvenanceView provenance={mockProvenance} />);

    expect(screen.getByText(/overview tab - coming soon/i)).toBeInTheDocument();
    expect(screen.getByText(/statistics, charts, and agent contribution/i)).toBeInTheDocument();
  });

  it('renders placeholder content for By Section tab', () => {
    render(<ProvenanceView provenance={mockProvenance} />);

    const bySectionTab = screen.getByRole('tab', { name: /by section/i });
    fireEvent.click(bySectionTab);

    // By Section tab now shows "No entity provenance data available" since mockProvenance has no entities
    expect(screen.getByText(/no entity provenance data available/i)).toBeInTheDocument();
  });

  it('renders placeholder content for By Agent tab', () => {
    render(<ProvenanceView provenance={mockProvenance} />);

    const byAgentTab = screen.getByRole('tab', { name: /by agent/i });
    fireEvent.click(byAgentTab);

    expect(screen.getByText(/by agent tab - coming soon/i)).toBeInTheDocument();
    expect(screen.getByText(/group entities by agent/i)).toBeInTheDocument();
  });

  it('renders placeholder content for By Page tab', () => {
    render(<ProvenanceView provenance={mockProvenance} />);

    const byPageTab = screen.getByRole('tab', { name: /by page/i });
    fireEvent.click(byPageTab);

    expect(screen.getByText(/by page tab - coming soon/i)).toBeInTheDocument();
    expect(screen.getByText(/group entities by source page/i)).toBeInTheDocument();
  });
});

describe('ProvenanceView - Split View', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('renders split view with divider', () => {
    render(<ProvenanceView provenance={mockProvenance} />);

    const dividers = screen.getAllByRole('separator', { name: /resize split pane/i });
    expect(dividers.length).toBeGreaterThan(0);
  });

  it('renders protocol preview placeholder in bottom section', () => {
    render(<ProvenanceView provenance={mockProvenance} />);

    expect(screen.getByText(/protocol preview will appear here/i)).toBeInTheDocument();
    expect(screen.getByText(/select an entity to view its source pages/i)).toBeInTheDocument();
  });

  it('saves split ratio to localStorage', async () => {
    render(<ProvenanceView provenance={mockProvenance} />);

    // Simulate dragging the divider (this is a simplified test)
    // In a real scenario, we'd need to simulate mouse events more accurately
    
    // Check that default ratio is saved
    await waitFor(() => {
      const saved = localStorage.getItem('provenance-tab-split-ratio');
      expect(saved).toBe('0.4');
    });
  });

  it('loads split ratio from localStorage on mount', () => {
    // Set a custom ratio in localStorage
    localStorage.setItem('provenance-tab-split-ratio', '0.6');

    render(<ProvenanceView provenance={mockProvenance} />);

    // The component should load the saved ratio
    // We can't easily test the actual height, but we can verify localStorage was read
    expect(localStorage.getItem('provenance-tab-split-ratio')).toBe('0.6');
  });

  it('clamps split ratio between 0.2 and 0.8', () => {
    // Set an invalid ratio
    localStorage.setItem('provenance-tab-split-ratio', '0.95');

    render(<ProvenanceView provenance={mockProvenance} />);

    // The component should ignore the invalid ratio and use default
    // After render, it should save the default
    expect(localStorage.getItem('provenance-tab-split-ratio')).toBe('0.4');
  });
});

describe('ProvenanceView - Empty States', () => {
  it('shows message when no study design available', async () => {
    // Mock empty study design
    const { useProtocolStore } = await import('@/stores/protocolStore');
    vi.mocked(useProtocolStore).mockImplementation((selector: any) => {
      return selector({ studyDesign: null });
    });

    render(<ProvenanceView provenance={mockProvenance} />);

    expect(screen.getByText(/no study design data available/i)).toBeInTheDocument();
  });

  it('shows message when no provenance data available', () => {
    render(<ProvenanceView provenance={null} />);

    expect(screen.getByText(/no provenance data available for this protocol/i)).toBeInTheDocument();
    expect(screen.getByText(/run the extraction pipeline/i)).toBeInTheDocument();
  });
});
