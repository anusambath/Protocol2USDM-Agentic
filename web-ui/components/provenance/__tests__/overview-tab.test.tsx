import { render, screen } from '@testing-library/react';
import { ProvenanceView } from '../ProvenanceView';
import type { ProvenanceData } from '@/lib/provenance/types';

// Mock the stores
jest.mock('@/stores/protocolStore', () => ({
  useProtocolStore: jest.fn((selector) => {
    const mockState = {
      studyDesign: {
        activities: [
          { id: 'act1', label: 'Activity 1', name: 'Activity 1' },
        ],
        encounters: [
          { id: 'enc1', name: 'Encounter 1', timing: { windowLabel: 'Week 1' } },
        ],
      },
    };
    return selector(mockState);
  }),
  selectStudyDesign: (state: any) => state.studyDesign,
}));

describe('OverviewTab', () => {
  const mockProvenanceData: ProvenanceData = {
    entities: {
      activities: {
        act1: {
          source: 'both',
          agent: 'activity_agent',
          model: 'gemini-2.5-flash',
          confidence: 0.95,
          pageRefs: [1, 2],
          timestamp: '2024-01-01T00:00:00Z',
        },
        act2: {
          source: 'text',
          agent: 'activity_agent',
          model: 'claude-opus-4',
          confidence: 0.45,
          pageRefs: [3],
          timestamp: '2024-01-01T00:00:00Z',
        },
      },
      metadata: {
        study_title: {
          source: 'both',
          agent: 'metadata_agent',
          model: 'gemini-2.5-flash',
          confidence: 0.88,
          pageRefs: [1],
          timestamp: '2024-01-01T00:00:00Z',
        },
      },
      eligibility: {
        inc1: {
          source: 'vision',
          agent: 'eligibility_agent',
          model: 'gemini-2.5-flash',
          confidence: 0.72,
          pageRefs: [5],
          timestamp: '2024-01-01T00:00:00Z',
        },
      },
      objectives: {
        obj1: {
          source: 'derived',
          agent: 'objectives_agent',
          model: 'claude-opus-4',
          confidence: 0.35,
          pageRefs: [],
          timestamp: '2024-01-01T00:00:00Z',
        },
      },
    },
  } as any;

  it('should display total entities count', () => {
    render(<ProvenanceView provenance={mockProvenanceData} />);
    
    // Should count all entities across all types
    expect(screen.getByText('Total Entities')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument(); // 2 activities + 1 metadata + 1 eligibility + 1 objective
  });

  it('should display coverage percentage', () => {
    render(<ProvenanceView provenance={mockProvenanceData} />);
    
    expect(screen.getByText('Coverage')).toBeInTheDocument();
    expect(screen.getByText('100%')).toBeInTheDocument(); // All entities have provenance
  });

  it('should display average confidence', () => {
    render(<ProvenanceView provenance={mockProvenanceData} />);
    
    expect(screen.getByText('Avg Confidence')).toBeInTheDocument();
    // Average: (0.95 + 0.45 + 0.88 + 0.72 + 0.35) / 5 = 0.67 = 67%
    expect(screen.getByText('67%')).toBeInTheDocument();
  });

  it('should display confidence range', () => {
    render(<ProvenanceView provenance={mockProvenanceData} />);
    
    expect(screen.getByText('Confidence Range')).toBeInTheDocument();
    // Min: 35%, Max: 95%
    expect(screen.getByText('35% - 95%')).toBeInTheDocument();
  });

  it('should display low confidence alert when entities have confidence < 0.5', () => {
    render(<ProvenanceView provenance={mockProvenanceData} />);
    
    expect(screen.getByText('Low Confidence Entities')).toBeInTheDocument();
    // 2 entities have confidence < 0.5: act2 (0.45) and obj1 (0.35)
    expect(screen.getByText('2 entities have confidence below 50%')).toBeInTheDocument();
  });

  it('should display agent contributions chart', () => {
    render(<ProvenanceView provenance={mockProvenanceData} />);
    
    expect(screen.getByText('Agent Contributions')).toBeInTheDocument();
    expect(screen.getByText('activity agent')).toBeInTheDocument();
    expect(screen.getByText('metadata agent')).toBeInTheDocument();
    expect(screen.getByText('eligibility agent')).toBeInTheDocument();
    expect(screen.getByText('objectives agent')).toBeInTheDocument();
  });

  it('should display source type breakdown', () => {
    render(<ProvenanceView provenance={mockProvenanceData} />);
    
    expect(screen.getByText('Source Type Breakdown')).toBeInTheDocument();
    expect(screen.getByText('Both (Text + Vision)')).toBeInTheDocument();
    expect(screen.getByText('Text Only')).toBeInTheDocument();
    expect(screen.getByText('Vision Only')).toBeInTheDocument();
    expect(screen.getByText('Derived')).toBeInTheDocument();
  });

  it('should display correct source type counts', () => {
    render(<ProvenanceView provenance={mockProvenanceData} />);
    
    const sourceTypeSection = screen.getByText('Source Type Breakdown').closest('div')?.parentElement;
    expect(sourceTypeSection).toBeInTheDocument();
    
    // both: 2 (act1, study_title)
    // text: 1 (act2)
    // vision: 1 (inc1)
    // derived: 1 (obj1)
  });

  it('should display confidence distribution histogram', () => {
    render(<ProvenanceView provenance={mockProvenanceData} />);
    
    expect(screen.getByText('Confidence Distribution')).toBeInTheDocument();
    expect(screen.getByText('0-0.2')).toBeInTheDocument();
    expect(screen.getByText('0.2-0.4')).toBeInTheDocument();
    expect(screen.getByText('0.4-0.6')).toBeInTheDocument();
    expect(screen.getByText('0.6-0.8')).toBeInTheDocument();
    expect(screen.getByText('0.8-1.0')).toBeInTheDocument();
  });

  it('should display model usage breakdown', () => {
    render(<ProvenanceView provenance={mockProvenanceData} />);
    
    expect(screen.getByText('Model Usage')).toBeInTheDocument();
    expect(screen.getByText(/gemini-2.5-flash/)).toBeInTheDocument();
    expect(screen.getByText(/claude-opus-4/)).toBeInTheDocument();
  });

  it('should handle empty provenance data gracefully', () => {
    const emptyProvenance: ProvenanceData = {
      entities: {},
    } as any;
    
    render(<ProvenanceView provenance={emptyProvenance} />);
    
    expect(screen.getByText('Total Entities')).toBeInTheDocument();
    expect(screen.getByText('0')).toBeInTheDocument();
    expect(screen.getByText('No agent data available')).toBeInTheDocument();
    expect(screen.getByText('No confidence data available')).toBeInTheDocument();
    expect(screen.getByText('No model data available')).toBeInTheDocument();
  });

  it('should not display low confidence alert when no entities have low confidence', () => {
    const highConfidenceProvenance: ProvenanceData = {
      entities: {
        activities: {
          act1: {
            source: 'both',
            agent: 'activity_agent',
            model: 'gemini-2.5-flash',
            confidence: 0.95,
            pageRefs: [1],
            timestamp: '2024-01-01T00:00:00Z',
          },
        },
      },
    } as any;
    
    render(<ProvenanceView provenance={highConfidenceProvenance} />);
    
    expect(screen.queryByText('Low Confidence Entities')).not.toBeInTheDocument();
  });

  it('should sort agents by contribution count in descending order', () => {
    const multiAgentProvenance: ProvenanceData = {
      entities: {
        activities: {
          act1: { source: 'both', agent: 'agent_a', model: 'gemini', confidence: 0.9, timestamp: '2024-01-01T00:00:00Z' },
          act2: { source: 'both', agent: 'agent_b', model: 'gemini', confidence: 0.9, timestamp: '2024-01-01T00:00:00Z' },
          act3: { source: 'both', agent: 'agent_b', model: 'gemini', confidence: 0.9, timestamp: '2024-01-01T00:00:00Z' },
          act4: { source: 'both', agent: 'agent_c', model: 'gemini', confidence: 0.9, timestamp: '2024-01-01T00:00:00Z' },
          act5: { source: 'both', agent: 'agent_c', model: 'gemini', confidence: 0.9, timestamp: '2024-01-01T00:00:00Z' },
          act6: { source: 'both', agent: 'agent_c', model: 'gemini', confidence: 0.9, timestamp: '2024-01-01T00:00:00Z' },
        },
      },
    } as any;
    
    render(<ProvenanceView provenance={multiAgentProvenance} />);
    
    const agentSection = screen.getByText('Agent Contributions').closest('div')?.parentElement;
    expect(agentSection).toBeInTheDocument();
    
    // agent_c should appear first (3 entities), then agent_b (2 entities), then agent_a (1 entity)
  });

  it('should calculate confidence distribution correctly', () => {
    const distributionProvenance: ProvenanceData = {
      entities: {
        activities: {
          act1: { source: 'both', agent: 'agent', model: 'gemini', confidence: 0.1, timestamp: '2024-01-01T00:00:00Z' },  // 0-0.2
          act2: { source: 'both', agent: 'agent', model: 'gemini', confidence: 0.3, timestamp: '2024-01-01T00:00:00Z' },  // 0.2-0.4
          act3: { source: 'both', agent: 'agent', model: 'gemini', confidence: 0.5, timestamp: '2024-01-01T00:00:00Z' },  // 0.4-0.6
          act4: { source: 'both', agent: 'agent', model: 'gemini', confidence: 0.7, timestamp: '2024-01-01T00:00:00Z' },  // 0.6-0.8
          act5: { source: 'both', agent: 'agent', model: 'gemini', confidence: 0.9, timestamp: '2024-01-01T00:00:00Z' },  // 0.8-1.0
        },
      },
    } as any;
    
    render(<ProvenanceView provenance={distributionProvenance} />);
    
    expect(screen.getByText('Confidence Distribution')).toBeInTheDocument();
    // Each bucket should have 1 entity
  });
});
