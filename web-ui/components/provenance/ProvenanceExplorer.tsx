'use client';

import { useState, useMemo, useRef, useEffect, useCallback } from 'react';
import dynamic from 'next/dynamic';
import { 
  Search, 
  Filter, 
  ChevronRight, 
  FileText,
  Eye,
  AlertTriangle,
  CheckCircle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ProvenanceStats } from './ProvenanceStats';
import type { ProvenanceData, CellSource } from '@/lib/provenance/types';
import { getProvenanceColor } from '@/lib/provenance/types';
import { cn } from '@/lib/utils';
import { debounce, throttle } from '@/lib/performance/optimization';

// Dynamic import for react-window to avoid SSR issues with Next.js 16
const FixedSizeList = dynamic(
  () => import('react-window').then((mod) => mod.FixedSizeList),
  { ssr: false }
);

interface ProvenanceExplorerProps {
  provenance: ProvenanceData | null;
  activities: Array<{ id: string; name: string }>;
  encounters: Array<{ id: string; name: string }>;
  onCellSelect?: (activityId: string, visitId: string) => void;
  idMapping?: Record<string, string> | null; // pre-UUID -> UUID mapping
}

type FilterType = 'all' | 'confirmed' | 'text' | 'vision' | 'orphaned';

export function ProvenanceExplorer({
  provenance,
  activities,
  encounters,
  onCellSelect,
  idMapping,
}: ProvenanceExplorerProps) {
  const [searchText, setSearchText] = useState('');
  const [debouncedSearchText, setDebouncedSearchText] = useState('');
  const [filter, setFilter] = useState<FilterType>('all');
  const [expandedActivities, setExpandedActivities] = useState<Set<string>>(new Set());
  const listRef = useRef<any>(null); // Using any due to dynamic import
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerHeight, setContainerHeight] = useState(600);

  // Create reverse ID mapping (UUID -> pre-UUID)
  const reverseIdMapping = useMemo(() => {
    if (!idMapping) {
      console.warn('ProvenanceExplorer: No ID mapping available');
      return {};
    }
    const reverse: Record<string, string> = {};
    for (const [preUuid, uuid] of Object.entries(idMapping)) {
      reverse[uuid] = preUuid;
    }
    console.log('ProvenanceExplorer: Created reverse ID mapping with', Object.keys(reverse).length, 'entries');
    return reverse;
  }, [idMapping]);

  // Debounced search handler (300ms)
  const debouncedSetSearch = useCallback(
    debounce((value: string) => {
      setDebouncedSearchText(value);
    }, 300),
    []
  );

  // Handle search input change
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchText(value);
    debouncedSetSearch(value);
  };

  // Measure container height for virtualization
  useEffect(() => {
    if (!containerRef.current) return;
    
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerHeight(entry.contentRect.height);
      }
    });
    
    resizeObserver.observe(containerRef.current);
    return () => resizeObserver.disconnect();
  }, []);

  // Build provenance items grouped by activity
  const provenanceItems = useMemo(() => {
    if (!provenance) return [];
    
    const items: Array<{
      activityId: string;
      activityName: string;
      cells: Array<{
        visitId: string;
        visitName: string;
        source: CellSource;
        footnotes: string[];
      }>;
    }> = [];

    // Support new format: provenance.cells with "activityId|encounterId" keys
    if (provenance.cells) {
      console.log('ProvenanceExplorer: Processing cells format, total cells:', Object.keys(provenance.cells).length);
      const activityCellsMap = new Map<string, Array<{ visitId: string; source: CellSource }>>();
      
      for (const [key, source] of Object.entries(provenance.cells)) {
        const [activityId, visitId] = key.split('|');
        if (!activityId || !visitId) continue;
        
        if (!activityCellsMap.has(activityId)) {
          activityCellsMap.set(activityId, []);
        }
        activityCellsMap.get(activityId)!.push({ visitId, source: source as CellSource });
      }
      
      console.log('ProvenanceExplorer: Grouped into', activityCellsMap.size, 'activities');
      
      for (const activity of activities) {
        // Convert UUID to pre-UUID for lookup
        const preUuidActivityId = reverseIdMapping[activity.id] || activity.id;
        const cellsData = activityCellsMap.get(preUuidActivityId);
        
        if (activity.id !== preUuidActivityId) {
          console.log('ProvenanceExplorer: Mapped activity UUID', activity.id, '→ pre-UUID', preUuidActivityId, 'found cells:', !!cellsData);
        }
        
        if (!cellsData) continue;
        
        const cells = cellsData.map(({ visitId, source }) => {
          // Find encounter by pre-UUID ID
          const encounter = encounters.find(e => {
            const preUuidEncounterId = reverseIdMapping[e.id] || e.id;
            return preUuidEncounterId === visitId;
          });
          
          const footnoteKey = `${preUuidActivityId}|${visitId}`;
          const footnotes = (provenance.cellFootnotes as Record<string, string[]>)?.[footnoteKey] || [];
          
          return {
            visitId: encounter?.id || visitId, // Return UUID for display
            visitName: encounter?.name || visitId,
            source,
            footnotes,
          };
        });
        
        if (cells.length > 0) {
          items.push({
            activityId: activity.id,
            activityName: activity.name,
            cells,
          });
        }
      }
      
      console.log('ProvenanceExplorer: Final items count:', items.length);
      return items;
    }
    
    // Legacy format: provenance.activityTimepoints
    if (provenance.activityTimepoints) {
      for (const activity of activities) {
        const activityProv = provenance.activityTimepoints[activity.id];
        if (!activityProv) continue;

        const cells: typeof items[0]['cells'] = [];
        
        for (const [visitId, source] of Object.entries(activityProv)) {
          const encounter = encounters.find(e => e.id === visitId);
          const footnotes = (provenance.cellFootnotes as Record<string, Record<string, string[]>>)?.[activity.id]?.[visitId] || [];
          
          cells.push({
            visitId,
            visitName: encounter?.name || visitId,
            source: source as CellSource,
            footnotes,
          });
        }

        if (cells.length > 0) {
          items.push({
            activityId: activity.id,
            activityName: activity.name,
            cells,
          });
        }
      }
    }

    return items;
  }, [provenance, activities, encounters, reverseIdMapping]);

  // Filter items
  const filteredItems = useMemo(() => {
    let items = provenanceItems;

    // Filter by source type
    if (filter !== 'all') {
      items = items.map(item => ({
        ...item,
        cells: item.cells.filter(cell => {
          switch (filter) {
            case 'confirmed': return cell.source === 'both';
            case 'text': return cell.source === 'text';
            case 'vision': return cell.source === 'vision' || cell.source === 'needs_review';
            case 'orphaned': return cell.source === 'none';
            default: return true;
          }
        }),
      })).filter(item => item.cells.length > 0);
    }

    // Filter by debounced search text
    if (debouncedSearchText) {
      const search = debouncedSearchText.toLowerCase();
      items = items.filter(item =>
        item.activityName.toLowerCase().includes(search) ||
        item.cells.some(cell => cell.visitName.toLowerCase().includes(search))
      );
    }

    return items;
  }, [provenanceItems, filter, debouncedSearchText]);

  // Toggle activity expansion
  const toggleActivity = (activityId: string) => {
    setExpandedActivities(prev => {
      const next = new Set(prev);
      if (next.has(activityId)) {
        next.delete(activityId);
      } else {
        next.add(activityId);
      }
      return next;
    });
  };

  // Expand all
  const expandAll = () => {
    setExpandedActivities(new Set(filteredItems.map(i => i.activityId)));
  };

  // Collapse all
  const collapseAll = () => {
    setExpandedActivities(new Set());
  };

  const filterButtons: Array<{ id: FilterType; label: string; icon: React.ReactNode }> = [
    { id: 'all', label: 'All', icon: null },
    { id: 'confirmed', label: 'Confirmed', icon: <CheckCircle className="h-3 w-3 text-green-600" /> },
    { id: 'text', label: 'Text Only', icon: <FileText className="h-3 w-3 text-blue-600" /> },
    { id: 'vision', label: 'Needs Review', icon: <AlertTriangle className="h-3 w-3 text-orange-600" /> },
    { id: 'orphaned', label: 'Orphaned', icon: <Eye className="h-3 w-3 text-red-600" /> },
  ];

  // Use virtualization for lists with more than 100 items
  const useVirtualization = filteredItems.length > 100;
  const itemHeight = 80; // Approximate height of collapsed item

  // Throttled scroll handler (100ms)
  const handleScroll = useCallback(
    throttle(() => {
      // Scroll handling logic if needed
      // Currently react-window handles scroll internally
    }, 100),
    []
  );

  // Row renderer for virtualized list
  const Row = ({ index, style }: { index: number; style: React.CSSProperties }) => {
    const item = filteredItems[index];
    return (
      <div style={style}>
        <ProvenanceActivityItem
          item={item}
          isExpanded={expandedActivities.has(item.activityId)}
          onToggle={() => toggleActivity(item.activityId)}
          onCellClick={onCellSelect}
          provenance={provenance}
          reverseIdMapping={reverseIdMapping}
        />
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Info banner about cell-level provenance */}
      <Card className="border-blue-200 bg-blue-50 dark:border-blue-900 dark:bg-blue-950">
        <CardContent className="pt-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
            <div className="flex-1 text-sm">
              <p className="font-medium text-blue-900 dark:text-blue-100 mb-1">
                Cell-Level Provenance Information
              </p>
              <p className="text-blue-800 dark:text-blue-200">
                This view shows cell-level provenance tracking for the Schedule of Activities (SOA) table. 
                Currently, cell provenance includes source type (text/vision/confirmed), footnote references, and page numbers. 
                Agent and model information is tracked at the entity level (activities, encounters) but not yet available at the individual cell level.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Stats */}
      <ProvenanceStats provenance={provenance} />

      {/* Controls */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-col md:flex-row gap-4">
            {/* Search */}
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search activities or visits..."
                value={searchText}
                onChange={handleSearchChange}
                className="w-full pl-9 pr-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
            </div>

            {/* Filter buttons */}
            <div className="flex items-center gap-1 flex-wrap">
              {filterButtons.map((btn) => (
                <Button
                  key={btn.id}
                  variant={filter === btn.id ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setFilter(btn.id)}
                  className="gap-1"
                >
                  {btn.icon}
                  {btn.label}
                </Button>
              ))}
            </div>
          </div>

          {/* Expand/collapse */}
          <div className="flex items-center gap-2 mt-3 pt-3 border-t">
            <span className="text-sm text-muted-foreground">
              {filteredItems.length} activities with provenance
              {searchText && searchText !== debouncedSearchText && (
                <span className="ml-2 text-xs text-blue-600">Searching...</span>
              )}
            </span>
            <div className="flex-1" />
            <Button variant="ghost" size="sm" onClick={expandAll}>
              Expand All
            </Button>
            <Button variant="ghost" size="sm" onClick={collapseAll}>
              Collapse All
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Provenance items */}
      <div ref={containerRef} className="flex-1 min-h-0">
        {filteredItems.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <Eye className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
              <p className="text-muted-foreground">
                {searchText || filter !== 'all'
                  ? 'No matching provenance data found'
                  : 'No provenance data available'}
              </p>
            </CardContent>
          </Card>
        ) : useVirtualization ? (
          <FixedSizeList
            ref={listRef}
            height={containerHeight}
            itemCount={filteredItems.length}
            itemSize={itemHeight}
            width="100%"
            className="space-y-2"
            onScroll={handleScroll}
          >
            {Row}
          </FixedSizeList>
        ) : (
          <div className="space-y-2">
            {filteredItems.map((item) => (
              <ProvenanceActivityItem
                key={item.activityId}
                item={item}
                isExpanded={expandedActivities.has(item.activityId)}
                onToggle={() => toggleActivity(item.activityId)}
                onCellClick={onCellSelect}
                provenance={provenance}
                reverseIdMapping={reverseIdMapping}
              />
            ))}
          </div>
        )}
      </div>

      {/* SoA Footnotes removed - displayed in Advanced -> Footnotes section instead */}
    </div>
  );
}

// Activity item with expandable cells
function ProvenanceActivityItem({
  item,
  isExpanded,
  onToggle,
  onCellClick,
  provenance,
  reverseIdMapping,
}: {
  item: {
    activityId: string;
    activityName: string;
    cells: Array<{
      visitId: string;
      visitName: string;
      source: CellSource;
      footnotes: string[];
    }>;
  };
  isExpanded: boolean;
  onToggle: () => void;
  onCellClick?: (activityId: string, visitId: string) => void;
  provenance: ProvenanceData | null;
  reverseIdMapping: Record<string, string>;
}) {
  // Count by source type
  const counts = useMemo(() => {
    const c = { confirmed: 0, text: 0, review: 0, orphaned: 0 };
    for (const cell of item.cells) {
      if (cell.source === 'both') c.confirmed++;
      else if (cell.source === 'text') c.text++;
      else if (cell.source === 'vision' || cell.source === 'needs_review') c.review++;
      else c.orphaned++;
    }
    return c;
  }, [item.cells]);

  return (
    <Card>
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-3 p-4 text-left hover:bg-muted/50 transition-colors"
      >
        <ChevronRight
          className={cn(
            'h-4 w-4 text-muted-foreground transition-transform',
            isExpanded && 'rotate-90'
          )}
        />
        <div className="flex-1 min-w-0">
          <p className="font-medium truncate">{item.activityName}</p>
          <p className="text-xs text-muted-foreground">
            {item.cells.length} cells tracked
          </p>
        </div>
        
        {/* Mini counts */}
        <div className="flex items-center gap-2 text-xs">
          {counts.confirmed > 0 && (
            <span className="flex items-center gap-1 text-green-600">
              <span className="w-2 h-2 rounded-full bg-green-500" />
              {counts.confirmed}
            </span>
          )}
          {counts.text > 0 && (
            <span className="flex items-center gap-1 text-blue-600">
              <span className="w-2 h-2 rounded-full bg-blue-500" />
              {counts.text}
            </span>
          )}
          {counts.review > 0 && (
            <span className="flex items-center gap-1 text-orange-600">
              <span className="w-2 h-2 rounded-full bg-orange-500" />
              {counts.review}
            </span>
          )}
          {counts.orphaned > 0 && (
            <span className="flex items-center gap-1 text-red-600">
              <span className="w-2 h-2 rounded-full bg-red-500" />
              {counts.orphaned}
            </span>
          )}
        </div>
      </button>

      {/* Expanded cells */}
      {isExpanded && (
        <div className="px-4 pb-4 border-t">
          <div className="mt-3 grid gap-2">
            {item.cells.map((cell) => {
              // Convert UUIDs to pre-UUIDs for provenance lookup
              const preUuidActivityId = reverseIdMapping[item.activityId] || item.activityId;
              const preUuidVisitId = reverseIdMapping[cell.visitId] || cell.visitId;
              const cellKey = `${preUuidActivityId}|${preUuidVisitId}`;
              const pageRefs = (provenance?.cellPageRefs as Record<string, number[]>)?.[cellKey] || [];
              
              return (
                <button
                  key={cell.visitId}
                  onClick={() => onCellClick?.(item.activityId, cell.visitId)}
                  className="flex items-start gap-3 p-3 rounded-md hover:bg-muted text-left text-sm border border-transparent hover:border-border transition-colors"
                >
                  <div
                    className="w-3 h-3 rounded mt-0.5 flex-shrink-0"
                    style={{ backgroundColor: getProvenanceColor(cell.source) }}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="font-medium">{cell.visitName}</div>
                    <div className="flex items-center gap-2 mt-1 flex-wrap">
                      <span className="text-xs px-2 py-0.5 rounded-full bg-muted text-muted-foreground capitalize">
                        {cell.source === 'both' ? 'confirmed' : cell.source === 'needs_review' ? 'needs review' : cell.source}
                      </span>
                      {pageRefs.length > 0 && (
                        <span className="text-xs text-blue-600 dark:text-blue-400">
                          📄 Page{pageRefs.length > 1 ? 's' : ''} {pageRefs.join(', ')}
                        </span>
                      )}
                      {cell.footnotes.length > 0 && (
                        <span className="text-xs text-purple-600 dark:text-purple-400">
                          📝 Footnote{cell.footnotes.length > 1 ? 's' : ''} [{cell.footnotes.join(', ')}]
                        </span>
                      )}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </Card>
  );
}

export default ProvenanceExplorer;
