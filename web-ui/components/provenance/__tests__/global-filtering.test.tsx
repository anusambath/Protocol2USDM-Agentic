import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ProvenanceView } from '../ProvenanceView';
import type { ProvenanceData } from '@/lib/provenance/types';

// Mock Zustand store
jest.mock('@/stores/protocolStore', () => ({
  useProtocolStore: jest.fn(() => ({
    studyDesign: {
      activities: [],
      encounters: [],
    },
  })),
  selectStudyDesign: jest.fn(),
}));

describe('ProvenanceView - Global Filtering', () => {
  const mockProvenance: ProvenanceData = {
    entities: {
      activities: {
        'activity-1': {
          source: 'text',
          agent: 'metadata_agent',
          model: 'gemini-1.5-pro',
          confidence: 0.95,
          pageRefs: [1, 2],
          timestamp: '2024-01-01T00:00:00Z',
        },
        'activity-2': {
          source: 'vision',
          agent: 'eligibility_agent',
          model: 'claude-3-opus',
          confidence: 0.75,
          pageRefs: [3],
          timestamp: '2024-01-02T00:00:00Z',
        },
      },
      metadata: {
        'study_title': {
          source: 'both',
          agent: 'metadata_agent',
          model: 'gemini-1.5-pro',
          confidence: 0.85,
          pageRefs: [1],
          timestamp: '2024-01-01T00:00:00Z',
        },
      },
    },
    cells: {},
    metadata: {
      extractionDate: '2024-01-01',
      pipelineVersion: '1.0.0',
      protocolId: 'test-protocol',
      totalEntities: 3,
    },
  };

  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();
  });

  it('should render filter toggle button', () => {
    render(<ProvenanceView provenance={mockProvenance} />);
    
    const filterButton = screen.getByRole('button', { name: /filters/i });
    expect(filterButton).toBeInTheDocument();
  });

  it('should show filter controls when toggle is clicked', async () => {
    render(<ProvenanceView provenance={mockProvenance} />);
    
    const filterButton = screen.getByRole('button', { name: /filters/i });
    fireEvent.click(filterButton);
    
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/search across all entities/i)).toBeInTheDocument();
    });
  });

  it('should display active filter count badge', async () => {
    render(<ProvenanceView provenance={mockProvenance} />);
    
    // Open filters
    const filterButton = screen.getByRole('button', { name: /filters/i });
    fireEvent.click(filterButton);
    
    // Add a search filter
    const searchInput = screen.getByPlaceholderText(/search across all entities/i);
    fireEvent.change(searchInput, { target: { value: 'activity' } });
    
    await waitFor(() => {
      expect(screen.getByText('1')).toBeInTheDocument(); // Badge showing 1 active filter
    });
  });

  it('should clear all filters when Clear All is clicked', async () => {
    render(<ProvenanceView provenance={mockProvenance} />);
    
    // Open filters
    const filterButton = screen.getByRole('button', { name: /filters/i });
    fireEvent.click(filterButton);
    
    // Add a search filter
    const searchInput = screen.getByPlaceholderText(/search across all entities/i);
    fireEvent.change(searchInput, { target: { value: 'activity' } });
    
    // Wait for filter to be applied
    await waitFor(() => {
      expect(screen.getByText('1')).toBeInTheDocument();
    });
    
    // Click Clear All
    const clearButton = screen.getByRole('button', { name: /clear all/i });
    fireEvent.click(clearButton);
    
    // Badge should be gone
    await waitFor(() => {
      expect(screen.queryByText('1')).not.toBeInTheDocument();
    });
    
    // Search input should be cleared
    expect(searchInput).toHaveValue('');
  });

  it('should persist filters to localStorage', async () => {
    render(<ProvenanceView provenance={mockProvenance} />);
    
    // Open filters
    const filterButton = screen.getByRole('button', { name: /filters/i });
    fireEvent.click(filterButton);
    
    // Add a search filter
    const searchInput = screen.getByPlaceholderText(/search across all entities/i);
    fireEvent.change(searchInput, { target: { value: 'test search' } });
    
    await waitFor(() => {
      const savedFilters = localStorage.getItem('provenance-tab-filters');
      expect(savedFilters).toBeTruthy();
      
      const filters = JSON.parse(savedFilters!);
      expect(filters.search).toBe('test search');
    });
  });

  it('should load filters from localStorage on mount', () => {
    // Set filters in localStorage
    const savedFilters = {
      search: 'saved search',
      entityTypes: ['activities'],
      agents: [],
      models: [],
      confidenceRange: [0, 100],
      sourceTypes: [],
      dateRange: { start: null, end: null },
      sortBy: 'confidence',
      sortOrder: 'desc',
    };
    localStorage.setItem('provenance-tab-filters', JSON.stringify(savedFilters));
    
    render(<ProvenanceView provenance={mockProvenance} />);
    
    // Open filters
    const filterButton = screen.getByRole('button', { name: /filters/i });
    fireEvent.click(filterButton);
    
    // Check that search input has the saved value
    const searchInput = screen.getByPlaceholderText(/search across all entities/i);
    expect(searchInput).toHaveValue('saved search');
  });

  it('should show confidence range slider', async () => {
    render(<ProvenanceView provenance={mockProvenance} />);
    
    // Open filters
    const filterButton = screen.getByRole('button', { name: /filters/i });
    fireEvent.click(filterButton);
    
    await waitFor(() => {
      expect(screen.getByText(/confidence range:/i)).toBeInTheDocument();
    });
  });

  it('should show sort controls', async () => {
    render(<ProvenanceView provenance={mockProvenance} />);
    
    // Open filters
    const filterButton = screen.getByRole('button', { name: /filters/i });
    fireEvent.click(filterButton);
    
    await waitFor(() => {
      // Check for sort by dropdown
      const sortByButtons = screen.getAllByRole('combobox');
      expect(sortByButtons.length).toBeGreaterThan(0);
    });
  });
});
