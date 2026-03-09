import { render, screen, fireEvent } from '@testing-library/react';
import { ProvenanceView } from '../ProvenanceView';
import type { ProvenanceData } from '@/lib/provenance/types';

// Mock the protocol store
jest.mock('@/stores/protocolStore', () => ({
  useProtocolStore: jest.fn(() => ({
    activities: [],
    encounters: [],
  })),
  selectStudyDesign: jest.fn(),
}));

describe('ByAgentTab', () => {
  const mockProvenance: ProvenanceData = {
    entities: {
      metadata: {
        study_title: {
          source: 'text',
          agent: 'metadata_agent',
          model: 'gemini-2.5-flash',
          confidence: 0.95,
          pageRefs: [1, 2],
          timestamp: '2024-01-15T10:00:00Z',
        },
        study_phase: {
          source: 'both',
          agent: 'metadata_agent',
          model: 'gemini-2.5-flash',
          confidence: 0.88,
          pageRefs: [1],
          timestamp: '2024-01-15T10:01:00Z',
        },
      },
      eligibility: {
        inclusion_1: {
          source: 'text',
          agent: 'eligibility_agent',
          model: 'claude-opus-4',
          confidence: 0.92,
          pageRefs: [5, 6],
          timestamp: '2024-01-15T10:05:00Z',
        },
        exclusion_1: {
          source: 'vision',
          agent: 'eligibility_agent',
          model: 'claude-opus-4',
          confidence: 0.78,
          pageRefs: [6],
          timestamp: '2024-01-15T10:06:00Z',
        },
      },
      objectives: {
        primary_objective: {
          source: 'both',
          agent: 'objectives_agent',
          model: 'gemini-2.5-pro',
          confidence: 0.91,
          pageRefs: [8],
          timestamp: '2024-01-15T10:10:00Z',
        },
      },
    },
  };

  it('should render agent groups with correct entity counts', () => {
    render(<ProvenanceView provenance={mockProvenance} />);
    
    // Switch to By Agent tab
    const byAgentTab = screen.getByRole('tab', { name: /by agent/i });
    fireEvent.click(byAgentTab);
    
    // Check that agents are displayed
    expect(screen.getByText(/metadata agent/i)).toBeInTheDocument();
    expect(screen.getByText(/eligibility agent/i)).toBeInTheDocument();
    expect(screen.getByText(/objectives agent/i)).toBeInTheDocument();
    
    // Check entity counts
    expect(screen.getByText('2 entities')).toBeInTheDocument(); // metadata_agent
    expect(screen.getByText('2 entities')).toBeInTheDocument(); // eligibility_agent
    expect(screen.getByText('1 entity')).toBeInTheDocument(); // objectives_agent
  });

  it('should calculate and display average confidence correctly', () => {
    render(<ProvenanceView provenance={mockProvenance} />);
    
    // Switch to By Agent tab
    const byAgentTab = screen.getByRole('tab', { name: /by agent/i });
    fireEvent.click(byAgentTab);
    
    // metadata_agent: (0.95 + 0.88) / 2 = 0.915 = 92%
    // eligibility_agent: (0.92 + 0.78) / 2 = 0.85 = 85%
    // objectives_agent: 0.91 = 91%
    
    // These should be displayed as badges
    expect(screen.getByText('92%')).toBeInTheDocument();
    expect(screen.getByText('85%')).toBeInTheDocument();
    expect(screen.getByText('91%')).toBeInTheDocument();
  });

  it('should display models used by each agent', () => {
    render(<ProvenanceView provenance={mockProvenance} />);
    
    // Switch to By Agent tab
    const byAgentTab = screen.getByRole('tab', { name: /by agent/i });
    fireEvent.click(byAgentTab);
    
    // Check that model badges are displayed
    expect(screen.getByText('Gemini 2.5 Flash')).toBeInTheDocument();
    expect(screen.getByText('Claude Opus 4')).toBeInTheDocument();
    expect(screen.getByText('Gemini 2.5 Pro')).toBeInTheDocument();
  });

  it('should expand agent section to show entities', () => {
    render(<ProvenanceView provenance={mockProvenance} />);
    
    // Switch to By Agent tab
    const byAgentTab = screen.getByRole('tab', { name: /by agent/i });
    fireEvent.click(byAgentTab);
    
    // Initially, entity details should not be visible
    expect(screen.queryByText('study_title')).not.toBeInTheDocument();
    
    // Click to expand metadata_agent
    const metadataAgentHeader = screen.getByText(/metadata agent/i).closest('div[role="button"]');
    if (metadataAgentHeader) {
      fireEvent.click(metadataAgentHeader);
    }
    
    // Now entity details should be visible
    expect(screen.getByText('study_title')).toBeInTheDocument();
    expect(screen.getByText('study_phase')).toBeInTheDocument();
  });

  it('should filter agents by search query', () => {
    render(<ProvenanceView provenance={mockProvenance} />);
    
    // Switch to By Agent tab
    const byAgentTab = screen.getByRole('tab', { name: /by agent/i });
    fireEvent.click(byAgentTab);
    
    // All agents should be visible initially
    expect(screen.getByText(/metadata agent/i)).toBeInTheDocument();
    expect(screen.getByText(/eligibility agent/i)).toBeInTheDocument();
    expect(screen.getByText(/objectives agent/i)).toBeInTheDocument();
    
    // Search for "eligibility"
    const searchInput = screen.getByPlaceholderText(/search agents or entities/i);
    fireEvent.change(searchInput, { target: { value: 'eligibility' } });
    
    // Only eligibility_agent should be visible
    expect(screen.queryByText(/metadata agent/i)).not.toBeInTheDocument();
    expect(screen.getByText(/eligibility agent/i)).toBeInTheDocument();
    expect(screen.queryByText(/objectives agent/i)).not.toBeInTheDocument();
  });

  it('should sort agents by entity count', () => {
    render(<ProvenanceView provenance={mockProvenance} />);
    
    // Switch to By Agent tab
    const byAgentTab = screen.getByRole('tab', { name: /by agent/i });
    fireEvent.click(byAgentTab);
    
    // Get all agent headers
    const agentHeaders = screen.getAllByRole('heading', { level: 3 });
    
    // Default sort should be by entity count (descending)
    // metadata_agent (2), eligibility_agent (2), objectives_agent (1)
    // The order might vary for agents with same count, but objectives should be last
    const lastAgent = agentHeaders[agentHeaders.length - 1];
    expect(lastAgent.textContent).toContain('Objectives Agent');
  });

  it('should toggle comparison view', () => {
    render(<ProvenanceView provenance={mockProvenance} />);
    
    // Switch to By Agent tab
    const byAgentTab = screen.getByRole('tab', { name: /by agent/i });
    fireEvent.click(byAgentTab);
    
    // Comparison view should not be visible initially
    expect(screen.queryByText('Agent Comparison')).not.toBeInTheDocument();
    
    // Click "Show Comparison" button
    const comparisonButton = screen.getByRole('button', { name: /show comparison/i });
    fireEvent.click(comparisonButton);
    
    // Comparison view should now be visible
    expect(screen.getByText('Agent Comparison')).toBeInTheDocument();
    
    // Click "Hide Comparison" button
    fireEvent.click(screen.getByRole('button', { name: /hide comparison/i }));
    
    // Comparison view should be hidden again
    expect(screen.queryByText('Agent Comparison')).not.toBeInTheDocument();
  });

  it('should handle empty provenance data gracefully', () => {
    const emptyProvenance: ProvenanceData = {
      entities: {},
    };
    
    render(<ProvenanceView provenance={emptyProvenance} />);
    
    // Switch to By Agent tab
    const byAgentTab = screen.getByRole('tab', { name: /by agent/i });
    fireEvent.click(byAgentTab);
    
    // Should show empty state message
    expect(screen.getByText(/no agent provenance data available/i)).toBeInTheDocument();
  });

  it('should handle agents with no confidence data', () => {
    const provenanceNoConfidence: ProvenanceData = {
      entities: {
        metadata: {
          study_title: {
            source: 'text',
            agent: 'metadata_agent',
            model: 'gemini-2.5-flash',
            pageRefs: [1],
            timestamp: '2024-01-15T10:00:00Z',
          },
        },
      },
    };
    
    render(<ProvenanceView provenance={provenanceNoConfidence} />);
    
    // Switch to By Agent tab
    const byAgentTab = screen.getByRole('tab', { name: /by agent/i });
    fireEvent.click(byAgentTab);
    
    // Should display N/A for confidence
    expect(screen.getByText('N/A')).toBeInTheDocument();
  });
});
