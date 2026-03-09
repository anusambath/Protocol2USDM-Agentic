'use client';

import { useMemo, useState, useEffect, useRef } from 'react';
import { AlertCircle, ChevronRight, Search, Filter, X, ChevronDown, SlidersHorizontal } from 'lucide-react';
import { ProvenanceExplorer } from './ProvenanceExplorer';
import { ProtocolPreview } from './ProtocolPreview';
import { useProtocolStore, selectStudyDesign } from '@/stores/protocolStore';
import type { ProvenanceData, EntityProvenanceExtended } from '@/lib/provenance/types';
import { 
  getAgentDisplayName, 
  getModelDisplayName, 
  formatPageRefs, 
  formatConfidence,
  getConfidenceLevel,
  getSourceTypeLabel,
  formatRelativeTime
} from '@/lib/provenance/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';

interface ProvenanceViewProps {
  provenance: ProvenanceData | null;
}

// Selected entity interface for protocol preview
interface SelectedEntity {
  id: string;
  type: string;
  pages: number[];
}

// Global filter state interface
interface GlobalFilters {
  search: string;
  entityTypes: string[];
  agents: string[];
  models: string[];
  confidenceRange: [number, number];
  sourceTypes: string[];
  dateRange: { start: string | null; end: string | null };
  sortBy: 'confidence' | 'page' | 'agent' | 'timestamp';
  sortOrder: 'asc' | 'desc';
}

const DEFAULT_FILTERS: GlobalFilters = {
  search: '',
  entityTypes: [],
  agents: [],
  models: [],
  confidenceRange: [0, 100],
  sourceTypes: [],
  dateRange: { start: null, end: null },
  sortBy: 'confidence',
  sortOrder: 'desc',
};

const FILTER_STORAGE_KEY = 'provenance-tab-filters';
const SPLIT_RATIO_KEY = 'provenance-tab-split-ratio';
const DEFAULT_SPLIT_RATIO = 0.4; // 40% top, 60% bottom

export function ProvenanceView({ provenance }: ProvenanceViewProps) {
  const studyDesign = useProtocolStore(selectStudyDesign);
  const protocolId = useProtocolStore(state => state.protocolId);
  const [activeTab, setActiveTab] = useState('overview');
  const [splitRatio, setSplitRatio] = useState(DEFAULT_SPLIT_RATIO);
  const [isDragging, setIsDragging] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [globalFilters, setGlobalFilters] = useState<GlobalFilters>(DEFAULT_FILTERS);
  const [selectedEntity, setSelectedEntity] = useState<SelectedEntity | null>(null);
  const [idMapping, setIdMapping] = useState<Record<string, string> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Load ID mapping when protocol changes
  useEffect(() => {
    if (!protocolId) return;
    
    const loadMapping = async () => {
      try {
        const response = await fetch(`/api/protocols/${protocolId}/id-mapping`);
        if (response.ok) {
          const mapping = await response.json();
          setIdMapping(mapping);
        } else {
          console.warn('ID mapping not available for this protocol');
          setIdMapping(null);
        }
      } catch (error) {
        console.error('Failed to load ID mapping:', error);
        setIdMapping(null);
      }
    };
    
    loadMapping();
  }, [protocolId]);

  // Load split ratio and filters from localStorage on mount
  useEffect(() => {
    const savedRatio = localStorage.getItem(SPLIT_RATIO_KEY);
    if (savedRatio) {
      const ratio = parseFloat(savedRatio);
      if (!isNaN(ratio) && ratio >= 0.2 && ratio <= 0.8) {
        setSplitRatio(ratio);
      }
    }

    const savedFilters = localStorage.getItem(FILTER_STORAGE_KEY);
    if (savedFilters) {
      try {
        const filters = JSON.parse(savedFilters);
        setGlobalFilters({ ...DEFAULT_FILTERS, ...filters });
      } catch (e) {
        console.error('Failed to parse saved filters:', e);
      }
    }
  }, []);

  // Save split ratio to localStorage when it changes
  useEffect(() => {
    localStorage.setItem(SPLIT_RATIO_KEY, splitRatio.toString());
  }, [splitRatio]);

  // Save filters to localStorage when they change
  useEffect(() => {
    localStorage.setItem(FILTER_STORAGE_KEY, JSON.stringify(globalFilters));
  }, [globalFilters]);

  // Extract unique values for filter options
  const filterOptions = useMemo(() => {
    const entityTypes = new Set<string>();
    const agents = new Set<string>();
    const models = new Set<string>();
    
    if (provenance?.entities) {
      Object.entries(provenance.entities).forEach(([entityType, entities]) => {
        if (!entities) return;
        
        Object.entries(entities).forEach(([_, entityProv]) => {
          entityTypes.add(entityType);
          if (entityProv.agent) agents.add(entityProv.agent);
          if (entityProv.model) models.add(entityProv.model);
        });
      });
    }
    
    return {
      entityTypes: Array.from(entityTypes).sort(),
      agents: Array.from(agents).sort(),
      models: Array.from(models).sort(),
      sourceTypes: ['text', 'vision', 'both', 'derived'],
    };
  }, [provenance]);

  // Count active filters
  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (globalFilters.search) count++;
    if (globalFilters.entityTypes.length > 0) count++;
    if (globalFilters.agents.length > 0) count++;
    if (globalFilters.models.length > 0) count++;
    if (globalFilters.confidenceRange[0] > 0 || globalFilters.confidenceRange[1] < 100) count++;
    if (globalFilters.sourceTypes.length > 0) count++;
    if (globalFilters.dateRange.start || globalFilters.dateRange.end) count++;
    return count;
  }, [globalFilters]);

  const clearAllFilters = () => {
    setGlobalFilters(DEFAULT_FILTERS);
  };

  const updateFilter = <K extends keyof GlobalFilters>(key: K, value: GlobalFilters[K]) => {
    setGlobalFilters(prev => ({ ...prev, [key]: value }));
  };

  // Extract activities and encounters from study design
  const { activities, encounters } = useMemo(() => {
    if (!studyDesign) {
      return { activities: [], encounters: [] };
    }

    const activities = (studyDesign.activities || []).map(a => ({
      id: a.id,
      name: a.label || a.name,
    }));

    const encounters = (studyDesign.encounters || []).map(e => ({
      id: e.id,
      name: e.timing?.windowLabel || e.name,
    }));

    return { activities, encounters };
  }, [studyDesign]);

  // Handle split pane dragging
  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return;

      const containerRect = containerRef.current.getBoundingClientRect();
      const relativeY = e.clientY - containerRect.top;
      const newRatio = relativeY / containerRect.height;

      // Clamp between 0.2 and 0.8
      const clampedRatio = Math.max(0.2, Math.min(0.8, newRatio));
      setSplitRatio(clampedRatio);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging]);

  if (!studyDesign) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <p className="text-muted-foreground">No study design data available</p>
        </CardContent>
      </Card>
    );
  }

  if (!provenance) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <p className="text-muted-foreground">
            No provenance data available for this protocol.
          </p>
          <p className="text-sm text-muted-foreground mt-2">
            Run the extraction pipeline with vision validation to generate provenance data.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Global Filter Panel */}
      <div className="border-b border-border">
        <div className="p-4 space-y-3">
          {/* Filter header with toggle and clear */}
          <div className="flex items-center justify-between">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowFilters(!showFilters)}
              className="gap-2"
            >
              <SlidersHorizontal className="h-4 w-4" />
              Filters
              {activeFilterCount > 0 && (
                <Badge variant="secondary" className="ml-1">
                  {activeFilterCount}
                </Badge>
              )}
              <ChevronDown className={`h-4 w-4 transition-transform ${showFilters ? 'rotate-180' : ''}`} />
            </Button>
            
            {activeFilterCount > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={clearAllFilters}
                className="gap-2"
              >
                <X className="h-4 w-4" />
                Clear All
              </Button>
            )}
          </div>

          {/* Collapsible filter controls */}
          {showFilters && (
            <div className="space-y-3 pt-2">
              {/* Global search */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search across all entities..."
                  value={globalFilters.search}
                  onChange={(e) => updateFilter('search', e.target.value)}
                  className="pl-9"
                />
              </div>

              {/* Filter controls grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {/* Entity Type Filter */}
                <Popover>
                  <PopoverTrigger asChild>
                    <Button variant="outline" className="justify-between">
                      <span className="truncate">
                        Entity Type
                        {globalFilters.entityTypes.length > 0 && ` (${globalFilters.entityTypes.length})`}
                      </span>
                      <ChevronDown className="h-4 w-4 ml-2 flex-shrink-0" />
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-64 p-3">
                    <div className="space-y-2 max-h-64 overflow-auto">
                      {filterOptions.entityTypes.map((type) => (
                        <div key={type} className="flex items-center space-x-2">
                          <Checkbox
                            id={`entity-${type}`}
                            checked={globalFilters.entityTypes.includes(type)}
                            onCheckedChange={(checked) => {
                              if (checked) {
                                updateFilter('entityTypes', [...globalFilters.entityTypes, type]);
                              } else {
                                updateFilter('entityTypes', globalFilters.entityTypes.filter(t => t !== type));
                              }
                            }}
                          />
                          <Label htmlFor={`entity-${type}`} className="text-sm cursor-pointer">
                            {type.replace(/_/g, ' ')}
                          </Label>
                        </div>
                      ))}
                    </div>
                  </PopoverContent>
                </Popover>

                {/* Agent Filter */}
                <Popover>
                  <PopoverTrigger asChild>
                    <Button variant="outline" className="justify-between">
                      <span className="truncate">
                        Agent
                        {globalFilters.agents.length > 0 && ` (${globalFilters.agents.length})`}
                      </span>
                      <ChevronDown className="h-4 w-4 ml-2 flex-shrink-0" />
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-64 p-3">
                    <div className="space-y-2 max-h-64 overflow-auto">
                      {filterOptions.agents.map((agent) => (
                        <div key={agent} className="flex items-center space-x-2">
                          <Checkbox
                            id={`agent-${agent}`}
                            checked={globalFilters.agents.includes(agent)}
                            onCheckedChange={(checked) => {
                              if (checked) {
                                updateFilter('agents', [...globalFilters.agents, agent]);
                              } else {
                                updateFilter('agents', globalFilters.agents.filter(a => a !== agent));
                              }
                            }}
                          />
                          <Label htmlFor={`agent-${agent}`} className="text-sm cursor-pointer capitalize">
                            {getAgentDisplayName(agent)}
                          </Label>
                        </div>
                      ))}
                    </div>
                  </PopoverContent>
                </Popover>

                {/* Model Filter */}
                <Popover>
                  <PopoverTrigger asChild>
                    <Button variant="outline" className="justify-between">
                      <span className="truncate">
                        Model
                        {globalFilters.models.length > 0 && ` (${globalFilters.models.length})`}
                      </span>
                      <ChevronDown className="h-4 w-4 ml-2 flex-shrink-0" />
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-64 p-3">
                    <div className="space-y-2 max-h-64 overflow-auto">
                      {filterOptions.models.map((model) => (
                        <div key={model} className="flex items-center space-x-2">
                          <Checkbox
                            id={`model-${model}`}
                            checked={globalFilters.models.includes(model)}
                            onCheckedChange={(checked) => {
                              if (checked) {
                                updateFilter('models', [...globalFilters.models, model]);
                              } else {
                                updateFilter('models', globalFilters.models.filter(m => m !== model));
                              }
                            }}
                          />
                          <Label htmlFor={`model-${model}`} className="text-sm cursor-pointer">
                            {getModelDisplayName(model)}
                          </Label>
                        </div>
                      ))}
                    </div>
                  </PopoverContent>
                </Popover>

                {/* Source Type Filter */}
                <Popover>
                  <PopoverTrigger asChild>
                    <Button variant="outline" className="justify-between">
                      <span className="truncate">
                        Source Type
                        {globalFilters.sourceTypes.length > 0 && ` (${globalFilters.sourceTypes.length})`}
                      </span>
                      <ChevronDown className="h-4 w-4 ml-2 flex-shrink-0" />
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-64 p-3">
                    <div className="space-y-2">
                      {filterOptions.sourceTypes.map((source) => (
                        <div key={source} className="flex items-center space-x-2">
                          <Checkbox
                            id={`source-${source}`}
                            checked={globalFilters.sourceTypes.includes(source)}
                            onCheckedChange={(checked) => {
                              if (checked) {
                                updateFilter('sourceTypes', [...globalFilters.sourceTypes, source]);
                              } else {
                                updateFilter('sourceTypes', globalFilters.sourceTypes.filter(s => s !== source));
                              }
                            }}
                          />
                          <Label htmlFor={`source-${source}`} className="text-sm cursor-pointer capitalize">
                            {getSourceTypeLabel(source)}
                          </Label>
                        </div>
                      ))}
                    </div>
                  </PopoverContent>
                </Popover>

                {/* Confidence Range Slider */}
                <div className="col-span-1 md:col-span-2">
                  <Label className="text-sm mb-2 block">
                    Confidence Range: {globalFilters.confidenceRange[0]}% - {globalFilters.confidenceRange[1]}%
                  </Label>
                  <Slider
                    min={0}
                    max={100}
                    step={5}
                    value={globalFilters.confidenceRange}
                    onValueChange={(value) => updateFilter('confidenceRange', value as [number, number])}
                    className="w-full"
                  />
                </div>
              </div>

              {/* Sort controls */}
              <div className="flex gap-2 pt-2 border-t border-border">
                <Select 
                  value={globalFilters.sortBy} 
                  onValueChange={(value: any) => updateFilter('sortBy', value)}
                >
                  <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="Sort by" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="confidence">Confidence</SelectItem>
                    <SelectItem value="page">Page Number</SelectItem>
                    <SelectItem value="agent">Agent</SelectItem>
                    <SelectItem value="timestamp">Timestamp</SelectItem>
                  </SelectContent>
                </Select>

                <Select 
                  value={globalFilters.sortOrder} 
                  onValueChange={(value: any) => updateFilter('sortOrder', value)}
                >
                  <SelectTrigger className="w-[140px]">
                    <SelectValue placeholder="Order" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="asc">Ascending</SelectItem>
                    <SelectItem value="desc">Descending</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
        <TabsList className="w-full justify-start border-b rounded-none h-auto p-0 bg-transparent">
          <TabsTrigger 
            value="overview"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
          >
            Overview
          </TabsTrigger>
          <TabsTrigger 
            value="by-section"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
          >
            By Section
          </TabsTrigger>
          <TabsTrigger 
            value="by-agent"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
          >
            By Agent
          </TabsTrigger>
          <TabsTrigger 
            value="by-page"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
          >
            By Page
          </TabsTrigger>
          <TabsTrigger 
            value="soa-details"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
          >
            SOA Details
          </TabsTrigger>
        </TabsList>

        <div ref={containerRef} className="flex-1 flex flex-col overflow-hidden">
          <TabsContent value="overview" className="flex-1 flex flex-col overflow-hidden mt-0">
            <div className="flex-1 flex flex-col overflow-hidden">
              {/* Top section - Entity list/view (40%) */}
              <div
                className="overflow-auto border-b border-border"
                style={{ height: `${splitRatio * 100}%` }}
              >
                <OverviewTab provenance={provenance} globalFilters={globalFilters} />
              </div>

              {/* Draggable divider */}
              <div
                className="h-1 bg-border hover:bg-primary cursor-row-resize transition-all duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-ring"
                onMouseDown={handleMouseDown}
                role="separator"
                aria-label="Resize split pane"
                aria-valuenow={Math.round(splitRatio * 100)}
                aria-valuemin={20}
                aria-valuemax={80}
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    setSplitRatio(Math.max(0.2, splitRatio - 0.05));
                  } else if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    setSplitRatio(Math.min(0.8, splitRatio + 0.05));
                  }
                }}
              />

              {/* Bottom section - Protocol preview (60%) */}
              <div
                className="overflow-auto"
                style={{ height: `${(1 - splitRatio) * 100}%` }}
              >
                {selectedEntity && protocolId ? (
                  <ProtocolPreview
                    protocolId={protocolId}
                    pageNumbers={selectedEntity.pages}
                  />
                ) : (
                  <div className="flex items-center justify-center h-full text-muted-foreground p-4">
                    <div className="text-center">
                      <p>Protocol preview will appear here</p>
                      <p className="text-sm mt-2">Select an entity to view its source pages</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </TabsContent>

          <TabsContent value="by-section" className="flex-1 flex flex-col overflow-hidden mt-0">
            <div className="flex-1 flex flex-col overflow-hidden">
              {/* Top section - Entity list/view (40%) */}
              <div
                className="overflow-auto border-b border-border"
                style={{ height: `${splitRatio * 100}%` }}
              >
                <BySectionTab 
                  provenance={provenance} 
                  globalFilters={globalFilters}
                  selectedEntity={selectedEntity}
                  onEntitySelect={setSelectedEntity}
                />
              </div>

              {/* Draggable divider */}
              <div
                className="h-1 bg-border hover:bg-primary cursor-row-resize transition-all duration-150 ease-in-out"
                onMouseDown={handleMouseDown}
                role="separator"
                aria-label="Resize split pane"
                tabIndex={0}
              />

              {/* Bottom section - Protocol preview (60%) */}
              <div
                className="overflow-auto"
                style={{ height: `${(1 - splitRatio) * 100}%` }}
              >
                {selectedEntity && protocolId ? (
                  <ProtocolPreview
                    protocolId={protocolId}
                    pageNumbers={selectedEntity.pages}
                  />
                ) : (
                  <div className="flex items-center justify-center h-full text-muted-foreground p-4">
                    <div className="text-center">
                      <p>Protocol preview will appear here</p>
                      <p className="text-sm mt-2">Select an entity to view its source pages</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </TabsContent>

          <TabsContent value="by-agent" className="flex-1 flex flex-col overflow-hidden mt-0">
            <div className="flex-1 flex flex-col overflow-hidden">
              {/* Top section - Entity list/view (40%) */}
              <div
                className="overflow-auto border-b border-border"
                style={{ height: `${splitRatio * 100}%` }}
              >
                <ByAgentTab 
                  provenance={provenance} 
                  globalFilters={globalFilters}
                  selectedEntity={selectedEntity}
                  onEntitySelect={setSelectedEntity}
                />
              </div>

              {/* Draggable divider */}
              <div
                className="h-1 bg-border hover:bg-primary cursor-row-resize transition-all duration-150 ease-in-out"
                onMouseDown={handleMouseDown}
                role="separator"
                aria-label="Resize split pane"
                tabIndex={0}
              />

              {/* Bottom section - Protocol preview (60%) */}
              <div
                className="overflow-auto"
                style={{ height: `${(1 - splitRatio) * 100}%` }}
              >
                {selectedEntity && protocolId ? (
                  <ProtocolPreview
                    protocolId={protocolId}
                    pageNumbers={selectedEntity.pages}
                  />
                ) : (
                  <div className="flex items-center justify-center h-full text-muted-foreground p-4">
                    <div className="text-center">
                      <p>Protocol preview will appear here</p>
                      <p className="text-sm mt-2">Select an entity to view its source pages</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </TabsContent>

          <TabsContent value="by-page" className="flex-1 flex flex-col overflow-hidden mt-0">
            <div className="flex-1 flex flex-col overflow-hidden">
              {/* Top section - Entity list/view (40%) */}
              <div
                className="overflow-auto border-b border-border"
                style={{ height: `${splitRatio * 100}%` }}
              >
                <ByPageTab 
                  provenance={provenance} 
                  globalFilters={globalFilters}
                  selectedEntity={selectedEntity}
                  onEntitySelect={setSelectedEntity}
                />
              </div>

              {/* Draggable divider */}
              <div
                className="h-1 bg-border hover:bg-primary cursor-row-resize transition-all duration-150 ease-in-out"
                onMouseDown={handleMouseDown}
                role="separator"
                aria-label="Resize split pane"
                tabIndex={0}
              />

              {/* Bottom section - Protocol preview (60%) */}
              <div
                className="overflow-auto"
                style={{ height: `${(1 - splitRatio) * 100}%` }}
              >
                {selectedEntity && protocolId ? (
                  <ProtocolPreview
                    protocolId={protocolId}
                    pageNumbers={selectedEntity.pages}
                  />
                ) : (
                  <div className="flex items-center justify-center h-full text-muted-foreground p-4">
                    <div className="text-center">
                      <p>Protocol preview will appear here</p>
                      <p className="text-sm mt-2">Select an entity to view its source pages</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </TabsContent>

          <TabsContent value="soa-details" className="flex-1 overflow-auto mt-0 p-4">
            <ProvenanceExplorer
              provenance={provenance}
              activities={activities}
              encounters={encounters}
              idMapping={idMapping}
            />
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}

// Placeholder components for tabs (to be implemented in subsequent tasks)

// Helper function to apply global filters to an entity
function applyGlobalFilters(entity: EntityItem, globalFilters: GlobalFilters): boolean {
  // Search filter
  if (globalFilters.search) {
    const query = globalFilters.search.toLowerCase();
    const matchesSearch = 
      entity.id.toLowerCase().includes(query) ||
      entity.type.toLowerCase().includes(query) ||
      entity.agent.toLowerCase().includes(query) ||
      entity.model.toLowerCase().includes(query);
    if (!matchesSearch) return false;
  }

  // Entity type filter
  if (globalFilters.entityTypes.length > 0 && !globalFilters.entityTypes.includes(entity.type)) {
    return false;
  }

  // Agent filter
  if (globalFilters.agents.length > 0 && !globalFilters.agents.includes(entity.agent)) {
    return false;
  }

  // Model filter
  if (globalFilters.models.length > 0 && !globalFilters.models.includes(entity.model)) {
    return false;
  }

  // Confidence range filter
  if (entity.confidence !== undefined) {
    const confidencePercent = entity.confidence * 100;
    if (confidencePercent < globalFilters.confidenceRange[0] || confidencePercent > globalFilters.confidenceRange[1]) {
      return false;
    }
  }

  // Source type filter
  if (globalFilters.sourceTypes.length > 0 && !globalFilters.sourceTypes.includes(entity.source)) {
    return false;
  }

  // Date range filter (if timestamp is available)
  // Note: This would require timestamp to be added to EntityItem interface
  // For now, we'll skip this as it's not in the current EntityItem interface

  return true;
}

// Helper function to sort entities based on global sort settings
function sortEntities(entities: EntityItem[], globalFilters: GlobalFilters): EntityItem[] {
  const sorted = [...entities].sort((a, b) => {
    let comparison = 0;
    
    switch (globalFilters.sortBy) {
      case 'confidence':
        const aConf = a.confidence ?? 0;
        const bConf = b.confidence ?? 0;
        comparison = aConf - bConf;
        break;
      case 'page':
        const aPage = a.pages[0] ?? 0;
        const bPage = b.pages[0] ?? 0;
        comparison = aPage - bPage;
        break;
      case 'agent':
        comparison = a.agent.localeCompare(b.agent);
        break;
      case 'timestamp':
        // Would need timestamp in EntityItem
        comparison = 0;
        break;
    }
    
    return globalFilters.sortOrder === 'asc' ? comparison : -comparison;
  });
  
  return sorted;
}

function OverviewTab({ provenance, globalFilters }: { provenance: ProvenanceData; globalFilters: GlobalFilters }) {
  // Calculate comprehensive statistics from provenance data
  const stats = useMemo(() => {
    const result = {
      totalEntities: 0,
      entitiesWithProvenance: 0,
      coveragePercent: 0,
      avgConfidence: 0,
      minConfidence: 1,
      maxConfidence: 0,
      sourceTypeCounts: { text: 0, vision: 0, both: 0, derived: 0 },
      agentContributionCounts: {} as Record<string, number>,
      modelUsageCounts: {} as Record<string, number>,
      lowConfidenceCount: 0,
      confidenceDistribution: { '0-0.2': 0, '0.2-0.4': 0, '0.4-0.6': 0, '0.6-0.8': 0, '0.8-1.0': 0 },
    };

    // Process entities from ProvenanceDataExtended format
    const entities = (provenance as any).entities;
    if (entities) {
      const entityTypes = [
        'activities', 'plannedTimepoints', 'encounters', 'epochs', 'activityGroups',
        'metadata', 'eligibility', 'objectives', 'endpoints', 'interventions',
        'procedures', 'devices', 'narratives'
      ];

      let totalConfidence = 0;
      let confidenceCount = 0;

      for (const entityType of entityTypes) {
        const entityGroup = entities[entityType];
        if (entityGroup && typeof entityGroup === 'object') {
          for (const [entityId, entityProv] of Object.entries(entityGroup)) {
            result.totalEntities++;
            
            if (entityProv && typeof entityProv === 'object') {
              result.entitiesWithProvenance++;
              
              // Source type counts
              const source = (entityProv as any).source;
              if (source && source in result.sourceTypeCounts) {
                result.sourceTypeCounts[source as keyof typeof result.sourceTypeCounts]++;
              }
              
              // Agent contribution
              const agent = (entityProv as any).agent;
              if (agent) {
                result.agentContributionCounts[agent] = (result.agentContributionCounts[agent] || 0) + 1;
              }
              
              // Model usage
              const model = (entityProv as any).model;
              if (model) {
                result.modelUsageCounts[model] = (result.modelUsageCounts[model] || 0) + 1;
              }
              
              // Confidence statistics
              const confidence = (entityProv as any).confidence;
              if (typeof confidence === 'number') {
                totalConfidence += confidence;
                confidenceCount++;
                
                result.minConfidence = Math.min(result.minConfidence, confidence);
                result.maxConfidence = Math.max(result.maxConfidence, confidence);
                
                // Low confidence count
                if (confidence < 0.5) {
                  result.lowConfidenceCount++;
                }
                
                // Confidence distribution
                if (confidence < 0.2) result.confidenceDistribution['0-0.2']++;
                else if (confidence < 0.4) result.confidenceDistribution['0.2-0.4']++;
                else if (confidence < 0.6) result.confidenceDistribution['0.4-0.6']++;
                else if (confidence < 0.8) result.confidenceDistribution['0.6-0.8']++;
                else result.confidenceDistribution['0.8-1.0']++;
              }
            }
          }
        }
      }

      result.coveragePercent = result.totalEntities > 0 
        ? Math.round((result.entitiesWithProvenance / result.totalEntities) * 100) 
        : 0;
      
      result.avgConfidence = confidenceCount > 0 
        ? totalConfidence / confidenceCount 
        : 0;
    }

    return result;
  }, [provenance]);

  // Get max count for agent chart scaling
  const maxAgentCount = Math.max(...Object.values(stats.agentContributionCounts), 1);
  const maxConfidenceCount = Math.max(...Object.values(stats.confidenceDistribution), 1);

  return (
    <div className="p-6 space-y-6">
      {/* Enhanced Statistics Dashboard */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Overview Statistics</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-4 pb-3">
              <p className="text-sm text-muted-foreground mb-1">Total Entities</p>
              <p className="text-2xl font-bold">{stats.totalEntities}</p>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-4 pb-3">
              <p className="text-sm text-muted-foreground mb-1">Coverage</p>
              <p className="text-2xl font-bold">{stats.coveragePercent}%</p>
              <p className="text-xs text-muted-foreground">
                {stats.entitiesWithProvenance} / {stats.totalEntities}
              </p>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-4 pb-3">
              <p className="text-sm text-muted-foreground mb-1">Avg Confidence</p>
              <p className="text-2xl font-bold">
                {stats.avgConfidence > 0 ? `${Math.round(stats.avgConfidence * 100)}%` : 'N/A'}
              </p>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-4 pb-3">
              <p className="text-sm text-muted-foreground mb-1">Confidence Range</p>
              <p className="text-lg font-bold">
                {stats.minConfidence < 1 
                  ? `${Math.round(stats.minConfidence * 100)}% - ${Math.round(stats.maxConfidence * 100)}%`
                  : 'N/A'}
              </p>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Low Confidence Alert Section */}
      {stats.lowConfidenceCount > 0 && (
        <Card className="border-orange-200 bg-orange-50 dark:bg-orange-950/20">
          <CardContent className="pt-4 pb-3">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-orange-600" />
              <div>
                <p className="font-semibold text-orange-900 dark:text-orange-100">
                  Low Confidence Entities
                </p>
                <p className="text-sm text-orange-700 dark:text-orange-300">
                  {stats.lowConfidenceCount} {stats.lowConfidenceCount === 1 ? 'entity has' : 'entities have'} confidence below 50%
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Agent Contribution Chart */}
        <Card>
          <CardContent className="pt-6">
            <h4 className="font-semibold mb-4">Agent Contributions</h4>
            {Object.keys(stats.agentContributionCounts).length > 0 ? (
              <div className="space-y-3">
                {Object.entries(stats.agentContributionCounts)
                  .sort(([, a], [, b]) => b - a)
                  .map(([agent, count]) => (
                    <div key={agent}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium capitalize">
                          {agent.replace(/_/g, ' ')}
                        </span>
                        <span className="text-sm text-muted-foreground">{count}</span>
                      </div>
                      <div className="h-6 bg-muted rounded overflow-hidden">
                        <div
                          className="h-full bg-primary transition-all"
                          style={{ width: `${(count / maxAgentCount) * 100}%` }}
                        />
                      </div>
                    </div>
                  ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-8">
                No agent data available
              </p>
            )}
          </CardContent>
        </Card>

        {/* Source Type Breakdown */}
        <Card>
          <CardContent className="pt-6">
            <h4 className="font-semibold mb-4">Source Type Breakdown</h4>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded bg-green-500" />
                  <span className="text-sm">Both (Text + Vision)</span>
                </div>
                <span className="text-sm font-medium">{stats.sourceTypeCounts.both}</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded bg-blue-500" />
                  <span className="text-sm">Text Only</span>
                </div>
                <span className="text-sm font-medium">{stats.sourceTypeCounts.text}</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded bg-purple-500" />
                  <span className="text-sm">Vision Only</span>
                </div>
                <span className="text-sm font-medium">{stats.sourceTypeCounts.vision}</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded bg-gray-500" />
                  <span className="text-sm">Derived</span>
                </div>
                <span className="text-sm font-medium">{stats.sourceTypeCounts.derived}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Confidence Distribution Histogram */}
        <Card>
          <CardContent className="pt-6">
            <h4 className="font-semibold mb-4">Confidence Distribution</h4>
            {Object.values(stats.confidenceDistribution).some(v => v > 0) ? (
              <div className="space-y-3">
                {Object.entries(stats.confidenceDistribution).map(([range, count]) => (
                  <div key={range}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium">{range}</span>
                      <span className="text-sm text-muted-foreground">{count}</span>
                    </div>
                    <div className="h-6 bg-muted rounded overflow-hidden">
                      <div
                        className={`h-full transition-all ${
                          range === '0.8-1.0' ? 'bg-green-500' :
                          range === '0.6-0.8' ? 'bg-blue-500' :
                          range === '0.4-0.6' ? 'bg-yellow-500' :
                          range === '0.2-0.4' ? 'bg-orange-500' :
                          'bg-red-500'
                        }`}
                        style={{ width: `${(count / maxConfidenceCount) * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-8">
                No confidence data available
              </p>
            )}
          </CardContent>
        </Card>

        {/* Model Usage Breakdown */}
        <Card>
          <CardContent className="pt-6">
            <h4 className="font-semibold mb-4">Model Usage</h4>
            {Object.keys(stats.modelUsageCounts).length > 0 ? (
              <div className="space-y-3">
                {Object.entries(stats.modelUsageCounts)
                  .sort(([, a], [, b]) => b - a)
                  .map(([model, count]) => (
                    <div key={model} className="flex items-center justify-between">
                      <span className="text-sm font-medium">
                        {model.includes('gemini') ? '🔷 ' : model.includes('claude') ? '🟣 ' : ''}
                        {model}
                      </span>
                      <span className="text-sm text-muted-foreground">{count}</span>
                    </div>
                  ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-8">
                No model data available
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// Section mapping: entity types to section names
const SECTION_MAPPINGS: Record<string, string> = {
  // Study Metadata
  study_title: 'Study Metadata',
  study_identifier: 'Study Metadata',
  study_phase: 'Study Metadata',
  organization: 'Study Metadata',
  study_acronym: 'Study Metadata',
  study_rationale: 'Study Metadata',
  study_type: 'Study Metadata',
  study_version: 'Study Metadata',
  amendment_scope: 'Study Metadata',
  
  // Eligibility Criteria
  eligibility_criterion: 'Eligibility Criteria',
  inclusion_criterion: 'Eligibility Criteria',
  exclusion_criterion: 'Eligibility Criteria',
  
  // Objectives & Endpoints
  objective: 'Objectives & Endpoints',
  endpoint: 'Objectives & Endpoints',
  
  // Study Design
  study_design: 'Study Design',
  epoch: 'Study Design',
  arm: 'Study Design',
  population: 'Study Design',
  
  // Interventions
  study_intervention: 'Interventions',
  intervention: 'Interventions',
  
  // Procedures & Devices
  procedure: 'Procedures & Devices',
  medical_device: 'Procedures & Devices',
  
  // Advanced Entities
  indication: 'Advanced Entities',
  biomedical_concept: 'Advanced Entities',
  estimand: 'Advanced Entities',
  analysis_population: 'Advanced Entities',
  
  // Narrative
  narrative_content: 'Narrative',
  
  // SOA
  activities: 'SOA',
  encounters: 'SOA',
  plannedTimepoints: 'SOA',
};

interface EntityItem {
  id: string;
  type: string;
  agent: string;
  model: string;
  pages: number[];
  confidence?: number;
  source: string;
}

interface Section {
  name: string;
  entities: EntityItem[];
}

function BySectionTab({ 
  provenance, 
  globalFilters,
  selectedEntity,
  onEntitySelect 
}: { 
  provenance: ProvenanceData; 
  globalFilters: GlobalFilters;
  selectedEntity: SelectedEntity | null;
  onEntitySelect: (entity: SelectedEntity | null) => void;
}) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [filterBy, setFilterBy] = useState<'all' | 'high' | 'medium' | 'low'>('all');
  const [filterSource, setFilterSource] = useState<'all' | 'text' | 'vision' | 'both' | 'derived'>('all');

  // Group entities by section
  const sections = useMemo(() => {
    const sectionMap = new Map<string, EntityItem[]>();
    
    // Process entities from provenance data
    if (provenance.entities) {
      Object.entries(provenance.entities).forEach(([entityType, entities]) => {
        if (!entities) return;
        
        Object.entries(entities).forEach(([entityId, entityProv]) => {
          // Determine section name
          const sectionName = SECTION_MAPPINGS[entityType] || 'Other';
          
          // Create entity item
          const item: EntityItem = {
            id: entityId,
            type: entityType,
            agent: entityProv.agent || 'Unknown',
            model: entityProv.model || 'Unknown',
            pages: entityProv.pageRefs || [],
            confidence: entityProv.confidence,
            source: entityProv.source,
          };
          
          // Add to section
          if (!sectionMap.has(sectionName)) {
            sectionMap.set(sectionName, []);
          }
          sectionMap.get(sectionName)!.push(item);
        });
      });
    }
    
    // Convert to array and sort sections
    const sectionsArray: Section[] = Array.from(sectionMap.entries())
      .map(([name, entities]) => ({ name, entities }))
      .sort((a, b) => a.name.localeCompare(b.name));
    
    return sectionsArray;
  }, [provenance]);

  // Filter sections based on search and filters
  const filteredSections = useMemo(() => {
    return sections.map(section => {
      let filteredEntities = section.entities;
      
      // Apply global filters first
      filteredEntities = filteredEntities.filter(entity => applyGlobalFilters(entity, globalFilters));
      
      // Apply local search filter (in addition to global)
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        filteredEntities = filteredEntities.filter(entity => 
          entity.id.toLowerCase().includes(query) ||
          entity.type.toLowerCase().includes(query) ||
          entity.agent.toLowerCase().includes(query)
        );
      }
      
      // Apply local confidence filter (in addition to global)
      if (filterBy !== 'all') {
        filteredEntities = filteredEntities.filter(entity => {
          const level = getConfidenceLevel(entity.confidence);
          return level === filterBy;
        });
      }
      
      // Apply local source filter (in addition to global)
      if (filterSource !== 'all') {
        filteredEntities = filteredEntities.filter(entity => 
          entity.source === filterSource
        );
      }
      
      // Apply global sorting
      filteredEntities = sortEntities(filteredEntities, globalFilters);
      
      return {
        ...section,
        entities: filteredEntities,
      };
    }).filter(section => section.entities.length > 0);
  }, [sections, searchQuery, filterBy, filterSource, globalFilters]);

  const toggleSection = (sectionName: string) => {
    setExpandedSections(prev => {
      const next = new Set(prev);
      if (next.has(sectionName)) {
        next.delete(sectionName);
      } else {
        next.add(sectionName);
      }
      return next;
    });
  };

  const totalEntities = sections.reduce((sum, section) => sum + section.entities.length, 0);

  if (sections.length === 0) {
    return (
      <Card className="m-4">
        <CardContent className="py-12 text-center">
          <p className="text-muted-foreground">No entity provenance data available</p>
          <p className="text-sm text-muted-foreground mt-2">
            Extended provenance data with entity information is not available for this protocol.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header with filters */}
      <div className="border-b border-border p-4 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold">Entities by Section</h3>
            <p className="text-sm text-muted-foreground">
              {totalEntities} entities across {sections.length} sections
            </p>
          </div>
        </div>
        
        {/* Search and filters */}
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search entities..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
          
          <Select value={filterBy} onValueChange={(value: any) => setFilterBy(value)}>
            <SelectTrigger className="w-[180px]">
              <Filter className="h-4 w-4 mr-2" />
              <SelectValue placeholder="Filter by confidence" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Confidence</SelectItem>
              <SelectItem value="high">High (&gt;75%)</SelectItem>
              <SelectItem value="medium">Medium (50-75%)</SelectItem>
              <SelectItem value="low">Low (&lt;50%)</SelectItem>
            </SelectContent>
          </Select>
          
          <Select value={filterSource} onValueChange={(value: any) => setFilterSource(value)}>
            <SelectTrigger className="w-[180px]">
              <Filter className="h-4 w-4 mr-2" />
              <SelectValue placeholder="Filter by source" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Sources</SelectItem>
              <SelectItem value="text">Text Only</SelectItem>
              <SelectItem value="vision">Vision Only</SelectItem>
              <SelectItem value="both">Both</SelectItem>
              <SelectItem value="derived">Derived</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Sections list */}
      <div className="flex-1 overflow-auto">
        {filteredSections.length === 0 ? (
          <div className="py-12 text-center">
            <p className="text-muted-foreground">No entities match your filters</p>
          </div>
        ) : (
          <div className="p-4 space-y-2">
            {filteredSections.map((section) => (
              <Card key={section.name} className="overflow-hidden">
                <CardHeader 
                  className="p-4 cursor-pointer hover:bg-accent transition-colors"
                  onClick={() => toggleSection(section.name)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <ChevronRight 
                        className={`h-4 w-4 transition-transform ${
                          expandedSections.has(section.name) ? 'rotate-90' : ''
                        }`}
                      />
                      <CardTitle className="text-base">{section.name}</CardTitle>
                      <Badge variant="secondary" className="ml-2">
                        {section.entities.length}
                      </Badge>
                    </div>
                  </div>
                </CardHeader>
                
                {expandedSections.has(section.name) && (
                  <CardContent className="p-0">
                    <div className="divide-y divide-border">
                      {section.entities.map((entity) => {
                        const isSelected = selectedEntity?.id === entity.id && selectedEntity?.type === entity.type;
                        return <div
                          key={`${entity.type}-${entity.id}`}
                          className={`p-4 hover:bg-accent cursor-pointer transition-colors ${
                            isSelected ? 'bg-accent border-l-4 border-primary' : ''
                          }`}
                          onClick={() => {
                            onEntitySelect({
                              id: entity.id,
                              type: entity.type,
                              pages: entity.pages,
                            });
                          }}
                        >
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                <p className="font-medium text-sm truncate">{entity.id}</p>
                                <Badge variant="outline" className="text-xs">
                                  {entity.type}
                                </Badge>
                              </div>
                              
                              <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                                <span>Agent: {getAgentDisplayName(entity.agent)}</span>
                                <span>•</span>
                                <span>Model: {getModelDisplayName(entity.model)}</span>
                                {entity.pages.length > 0 && (
                                  <>
                                    <span>•</span>
                                    <span>{formatPageRefs(entity.pages)}</span>
                                  </>
                                )}
                              </div>
                            </div>
                            
                            <div className="flex items-center gap-2 flex-shrink-0">
                              {entity.confidence !== undefined && (
                                <Badge 
                                  variant={
                                    getConfidenceLevel(entity.confidence) === 'high' 
                                      ? 'default' 
                                      : getConfidenceLevel(entity.confidence) === 'medium'
                                      ? 'secondary'
                                      : 'destructive'
                                  }
                                  className="text-xs"
                                >
                                  {formatConfidence(entity.confidence)}
                                </Badge>
                              )}
                              <Badge variant="outline" className="text-xs">
                                {getSourceTypeLabel(entity.source)}
                              </Badge>
                            </div>
                          </div>
                        </div>;
                      })}
                    </div>
                  </CardContent>
                )}
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

interface AgentMetrics {
  agentId: string;
  totalEntities: number;
  avgConfidence: number;
  models: Set<string>;
  entities: EntityItem[];
  earliestTimestamp?: string;
  latestTimestamp?: string;
}

function ByAgentTab({ 
  provenance, 
  globalFilters,
  selectedEntity,
  onEntitySelect 
}: { 
  provenance: ProvenanceData; 
  globalFilters: GlobalFilters;
  selectedEntity: SelectedEntity | null;
  onEntitySelect: (entity: SelectedEntity | null) => void;
}) {
  const [expandedAgents, setExpandedAgents] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<'entities' | 'confidence' | 'name'>('entities');
  const [showComparison, setShowComparison] = useState(false);

  // Group entities by agent and calculate metrics
  const agentMetrics = useMemo(() => {
    const agentMap = new Map<string, AgentMetrics>();
    
    // Process entities from provenance data
    if (provenance.entities) {
      Object.entries(provenance.entities).forEach(([entityType, entities]) => {
        if (!entities) return;
        
        Object.entries(entities).forEach(([entityId, entityProv]) => {
          const agentId = entityProv.agent || 'unknown';
          
          // Initialize agent metrics if not exists
          if (!agentMap.has(agentId)) {
            agentMap.set(agentId, {
              agentId,
              totalEntities: 0,
              avgConfidence: 0,
              models: new Set(),
              entities: [],
            });
          }
          
          const metrics = agentMap.get(agentId)!;
          
          // Create entity item
          const item: EntityItem = {
            id: entityId,
            type: entityType,
            agent: agentId,
            model: entityProv.model || 'Unknown',
            pages: entityProv.pageRefs || [],
            confidence: entityProv.confidence,
            source: entityProv.source,
          };
          
          metrics.entities.push(item);
          metrics.totalEntities++;
          
          // Track models
          if (entityProv.model) {
            metrics.models.add(entityProv.model);
          }
          
          // Track timestamps
          if (entityProv.timestamp) {
            if (!metrics.earliestTimestamp || entityProv.timestamp < metrics.earliestTimestamp) {
              metrics.earliestTimestamp = entityProv.timestamp;
            }
            if (!metrics.latestTimestamp || entityProv.timestamp > metrics.latestTimestamp) {
              metrics.latestTimestamp = entityProv.timestamp;
            }
          }
        });
      });
    }
    
    // Calculate average confidence for each agent
    agentMap.forEach((metrics) => {
      const confidenceValues = metrics.entities
        .map(e => e.confidence)
        .filter((c): c is number => c !== undefined);
      
      if (confidenceValues.length > 0) {
        metrics.avgConfidence = confidenceValues.reduce((sum, c) => sum + c, 0) / confidenceValues.length;
      }
    });
    
    // Convert to array
    return Array.from(agentMap.values());
  }, [provenance]);

  // Filter and sort agents
  const filteredAgents = useMemo(() => {
    // First apply global filters to each agent's entities
    let filtered = agentMetrics.map(agent => ({
      ...agent,
      entities: agent.entities.filter(entity => applyGlobalFilters(entity, globalFilters)),
      totalEntities: agent.entities.filter(entity => applyGlobalFilters(entity, globalFilters)).length,
    })).filter(agent => agent.totalEntities > 0);
    
    // Apply local search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(agent => 
        agent.agentId.toLowerCase().includes(query) ||
        agent.entities.some(e => 
          e.id.toLowerCase().includes(query) ||
          e.type.toLowerCase().includes(query)
        )
      );
    }
    
    // Apply sorting (use global sort if applicable, otherwise use local)
    const sorted = [...filtered].sort((a, b) => {
      switch (sortBy) {
        case 'entities':
          return b.totalEntities - a.totalEntities;
        case 'confidence':
          return b.avgConfidence - a.avgConfidence;
        case 'name':
          return a.agentId.localeCompare(b.agentId);
        default:
          return 0;
      }
    });
    
    return sorted;
  }, [agentMetrics, searchQuery, sortBy, globalFilters]);

  const toggleAgent = (agentId: string) => {
    setExpandedAgents(prev => {
      const next = new Set(prev);
      if (next.has(agentId)) {
        next.delete(agentId);
      } else {
        next.add(agentId);
      }
      return next;
    });
  };

  const totalEntities = agentMetrics.reduce((sum, agent) => sum + agent.totalEntities, 0);

  if (agentMetrics.length === 0) {
    return (
      <Card className="m-4">
        <CardContent className="py-12 text-center">
          <p className="text-muted-foreground">No agent provenance data available</p>
          <p className="text-sm text-muted-foreground mt-2">
            Extended provenance data with agent information is not available for this protocol.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header with filters */}
      <div className="border-b border-border p-4 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold">Entities by Agent</h3>
            <p className="text-sm text-muted-foreground">
              {totalEntities} entities across {agentMetrics.length} agents
            </p>
          </div>
          
          <Button
            variant={showComparison ? "default" : "outline"}
            size="sm"
            onClick={() => setShowComparison(!showComparison)}
          >
            {showComparison ? 'Hide' : 'Show'} Comparison
          </Button>
        </div>
        
        {/* Search and sort */}
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search agents or entities..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
          
          <Select value={sortBy} onValueChange={(value: any) => setSortBy(value)}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="entities">Most Entities</SelectItem>
              <SelectItem value="confidence">Highest Confidence</SelectItem>
              <SelectItem value="name">Agent Name</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Agent comparison view */}
      {showComparison && (
        <div className="border-b border-border p-4 bg-muted/30">
          <h4 className="font-semibold mb-3">Agent Comparison</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredAgents.map((agent) => (
              <Card key={agent.agentId}>
                <CardContent className="pt-4 pb-3">
                  <p className="font-medium mb-2 capitalize">
                    {getAgentDisplayName(agent.agentId)}
                  </p>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Entities:</span>
                      <span className="font-medium">{agent.totalEntities}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Avg Confidence:</span>
                      <span className="font-medium">
                        {agent.avgConfidence > 0 ? formatConfidence(agent.avgConfidence) : 'N/A'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Models:</span>
                      <span className="font-medium">{agent.models.size}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Agents list */}
      <div className="flex-1 overflow-auto">
        {filteredAgents.length === 0 ? (
          <div className="py-12 text-center">
            <p className="text-muted-foreground">No agents match your search</p>
          </div>
        ) : (
          <div className="p-4 space-y-2">
            {filteredAgents.map((agent) => (
              <Card key={agent.agentId} className="overflow-hidden">
                <CardHeader 
                  className="p-4 cursor-pointer hover:bg-accent transition-colors"
                  onClick={() => toggleAgent(agent.agentId)}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-2 flex-1">
                      <ChevronRight 
                        className={`h-4 w-4 mt-1 transition-transform flex-shrink-0 ${
                          expandedAgents.has(agent.agentId) ? 'rotate-90' : ''
                        }`}
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2">
                          <CardTitle className="text-base capitalize">
                            {getAgentDisplayName(agent.agentId)}
                          </CardTitle>
                          <Badge variant="secondary">
                            {agent.totalEntities} {agent.totalEntities === 1 ? 'entity' : 'entities'}
                          </Badge>
                        </div>
                        
                        {/* Agent metrics */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                          <div>
                            <p className="text-muted-foreground text-xs mb-1">Avg Confidence</p>
                            <p className="font-medium">
                              {agent.avgConfidence > 0 ? (
                                <Badge 
                                  variant={
                                    getConfidenceLevel(agent.avgConfidence) === 'high' 
                                      ? 'default' 
                                      : getConfidenceLevel(agent.avgConfidence) === 'medium'
                                      ? 'secondary'
                                      : 'destructive'
                                  }
                                >
                                  {formatConfidence(agent.avgConfidence)}
                                </Badge>
                              ) : (
                                'N/A'
                              )}
                            </p>
                          </div>
                          
                          <div>
                            <p className="text-muted-foreground text-xs mb-1">Models Used</p>
                            <div className="flex flex-wrap gap-1">
                              {Array.from(agent.models).map((model) => (
                                <Badge key={model} variant="outline" className="text-xs">
                                  {getModelDisplayName(model)}
                                </Badge>
                              ))}
                            </div>
                          </div>
                          
                          {agent.earliestTimestamp && agent.latestTimestamp && (
                            <div className="col-span-2">
                              <p className="text-muted-foreground text-xs mb-1">Extraction Time Range</p>
                              <p className="text-xs">
                                {formatRelativeTime(agent.earliestTimestamp)} to {formatRelativeTime(agent.latestTimestamp)}
                              </p>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </CardHeader>
                
                {expandedAgents.has(agent.agentId) && (
                  <CardContent className="p-0">
                    <div className="divide-y divide-border">
                      {agent.entities.map((entity) => {
                        const isSelected = selectedEntity?.id === entity.id && selectedEntity?.type === entity.type;
                        return <div
                          key={`${entity.type}-${entity.id}`}
                          className={`p-4 hover:bg-accent cursor-pointer transition-colors ${
                            isSelected ? 'bg-accent border-l-4 border-primary' : ''
                          }`}
                          onClick={(e) => {
                            e.stopPropagation();
                            onEntitySelect({
                              id: entity.id,
                              type: entity.type,
                              pages: entity.pages,
                            });
                          }}
                        >
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                <p className="font-medium text-sm truncate">{entity.id}</p>
                                <Badge variant="outline" className="text-xs">
                                  {entity.type}
                                </Badge>
                              </div>
                              
                              <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                                <span>Model: {getModelDisplayName(entity.model)}</span>
                                {entity.pages.length > 0 && (
                                  <>
                                    <span>•</span>
                                    <span>{formatPageRefs(entity.pages)}</span>
                                  </>
                                )}
                              </div>
                            </div>
                            
                            <div className="flex items-center gap-2 flex-shrink-0">
                              {entity.confidence !== undefined && (
                                <Badge 
                                  variant={
                                    getConfidenceLevel(entity.confidence) === 'high' 
                                      ? 'default' 
                                      : getConfidenceLevel(entity.confidence) === 'medium'
                                      ? 'secondary'
                                      : 'destructive'
                                  }
                                  className="text-xs"
                                >
                                  {formatConfidence(entity.confidence)}
                                </Badge>
                              )}
                              <Badge variant="outline" className="text-xs">
                                {getSourceTypeLabel(entity.source)}
                              </Badge>
                            </div>
                          </div>
                        </div>;
                      })}
                    </div>
                  </CardContent>
                )}
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

interface PageGroup {
  pageNum: number;
  entities: EntityItem[];
  entityCount: number;
}

function ByPageTab({ 
  provenance, 
  globalFilters,
  selectedEntity,
  onEntitySelect 
}: { 
  provenance: ProvenanceData; 
  globalFilters: GlobalFilters;
  selectedEntity: SelectedEntity | null;
  onEntitySelect: (entity: SelectedEntity | null) => void;
}) {
  const [expandedPages, setExpandedPages] = useState<Set<number>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<'page' | 'entities'>('page');
  const [showHeatmap, setShowHeatmap] = useState(true);

  // Group entities by page and calculate statistics
  const pageGroups = useMemo(() => {
    const pageMap = new Map<number, EntityItem[]>();
    
    // Process entities from provenance data
    if (provenance.entities) {
      Object.entries(provenance.entities).forEach(([entityType, entities]) => {
        if (!entities) return;
        
        Object.entries(entities).forEach(([entityId, entityProv]) => {
          const pages = entityProv.pageRefs || [];
          
          // Create entity item
          const item: EntityItem = {
            id: entityId,
            type: entityType,
            agent: entityProv.agent || 'Unknown',
            model: entityProv.model || 'Unknown',
            pages: pages,
            confidence: entityProv.confidence,
            source: entityProv.source,
          };
          
          // Add entity to each page it references
          pages.forEach(pageNum => {
            if (!pageMap.has(pageNum)) {
              pageMap.set(pageNum, []);
            }
            pageMap.get(pageNum)!.push(item);
          });
        });
      });
    }
    
    // Convert to array and create page groups
    const groups: PageGroup[] = Array.from(pageMap.entries())
      .map(([pageNum, entities]) => ({
        pageNum,
        entities,
        entityCount: entities.length,
      }));
    
    return groups;
  }, [provenance]);

  // Calculate statistics
  const stats = useMemo(() => {
    if (pageGroups.length === 0) {
      return {
        totalPages: 0,
        pagesWithEntities: 0,
        maxEntitiesPerPage: 0,
        minPage: 0,
        maxPage: 0,
        avgEntitiesPerPage: 0,
        gaps: [] as number[],
      };
    }
    
    const pageNums = pageGroups.map(g => g.pageNum).sort((a, b) => a - b);
    const minPage = pageNums[0];
    const maxPage = pageNums[pageNums.length - 1];
    const totalPages = maxPage - minPage + 1;
    const maxEntitiesPerPage = Math.max(...pageGroups.map(g => g.entityCount));
    const avgEntitiesPerPage = pageGroups.reduce((sum, g) => sum + g.entityCount, 0) / pageGroups.length;
    
    // Find gaps (pages with no entities)
    const gaps: number[] = [];
    for (let i = minPage; i <= maxPage; i++) {
      if (!pageGroups.find(g => g.pageNum === i)) {
        gaps.push(i);
      }
    }
    
    return {
      totalPages,
      pagesWithEntities: pageGroups.length,
      maxEntitiesPerPage,
      minPage,
      maxPage,
      avgEntitiesPerPage,
      gaps,
    };
  }, [pageGroups]);

  // Filter and sort page groups
  const filteredPageGroups = useMemo(() => {
    // First apply global filters to each page's entities
    let filtered = pageGroups.map(page => ({
      ...page,
      entities: page.entities.filter(entity => applyGlobalFilters(entity, globalFilters)),
      entityCount: page.entities.filter(entity => applyGlobalFilters(entity, globalFilters)).length,
    })).filter(page => page.entityCount > 0);
    
    // Apply local search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(page => 
        page.pageNum.toString().includes(query) ||
        page.entities.some(e => 
          e.id.toLowerCase().includes(query) ||
          e.type.toLowerCase().includes(query) ||
          e.agent.toLowerCase().includes(query)
        )
      );
    }
    
    // Apply sorting
    const sorted = [...filtered].sort((a, b) => {
      switch (sortBy) {
        case 'page':
          return a.pageNum - b.pageNum;
        case 'entities':
          return b.entityCount - a.entityCount;
        default:
          return 0;
      }
    });
    
    return sorted;
  }, [pageGroups, searchQuery, sortBy, globalFilters]);

  const togglePage = (pageNum: number) => {
    setExpandedPages(prev => {
      const next = new Set(prev);
      if (next.has(pageNum)) {
        next.delete(pageNum);
      } else {
        next.add(pageNum);
      }
      return next;
    });
  };

  // Get color intensity for heatmap based on entity count
  const getHeatmapColor = (entityCount: number): string => {
    if (entityCount === 0) return 'bg-gray-200 dark:bg-gray-800';
    if (stats.maxEntitiesPerPage === 0) return 'bg-blue-200 dark:bg-blue-900';
    
    const intensity = entityCount / stats.maxEntitiesPerPage;
    if (intensity >= 0.8) return 'bg-red-500 dark:bg-red-600';
    if (intensity >= 0.6) return 'bg-orange-500 dark:bg-orange-600';
    if (intensity >= 0.4) return 'bg-yellow-500 dark:bg-yellow-600';
    if (intensity >= 0.2) return 'bg-blue-400 dark:bg-blue-700';
    return 'bg-blue-200 dark:bg-blue-900';
  };

  const getHeatmapTitle = (pageNum: number, entityCount: number): string => {
    return `Page ${pageNum}: ${entityCount} ${entityCount === 1 ? 'entity' : 'entities'}`;
  };

  if (pageGroups.length === 0) {
    return (
      <Card className="m-4">
        <CardContent className="py-12 text-center">
          <p className="text-muted-foreground">No page provenance data available</p>
          <p className="text-sm text-muted-foreground mt-2">
            Extended provenance data with page references is not available for this protocol.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header with statistics */}
      <div className="border-b border-border p-4 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold">Entities by Page</h3>
            <p className="text-sm text-muted-foreground">
              {stats.pagesWithEntities} pages with entities (Pages {stats.minPage}-{stats.maxPage})
            </p>
          </div>
          
          <Button
            variant={showHeatmap ? "default" : "outline"}
            size="sm"
            onClick={() => setShowHeatmap(!showHeatmap)}
          >
            {showHeatmap ? 'Hide' : 'Show'} Heatmap
          </Button>
        </div>

        {/* Page statistics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="bg-muted/50 rounded-lg p-3">
            <p className="text-xs text-muted-foreground mb-1">Total Pages</p>
            <p className="text-lg font-bold">{stats.totalPages}</p>
          </div>
          <div className="bg-muted/50 rounded-lg p-3">
            <p className="text-xs text-muted-foreground mb-1">Pages with Entities</p>
            <p className="text-lg font-bold">{stats.pagesWithEntities}</p>
          </div>
          <div className="bg-muted/50 rounded-lg p-3">
            <p className="text-xs text-muted-foreground mb-1">Max Entities/Page</p>
            <p className="text-lg font-bold">{stats.maxEntitiesPerPage}</p>
          </div>
          <div className="bg-muted/50 rounded-lg p-3">
            <p className="text-xs text-muted-foreground mb-1">Avg Entities/Page</p>
            <p className="text-lg font-bold">{stats.avgEntitiesPerPage.toFixed(1)}</p>
          </div>
        </div>

        {/* Gaps alert */}
        {stats.gaps.length > 0 && (
          <Card className="border-orange-200 bg-orange-50 dark:bg-orange-950/20">
            <CardContent className="pt-3 pb-3">
              <div className="flex items-start gap-2">
                <AlertCircle className="h-5 w-5 text-orange-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-orange-900 dark:text-orange-100 mb-1">
                    {stats.gaps.length} Page{stats.gaps.length > 1 ? 's' : ''} with No Entities
                  </p>
                  <p className="text-sm text-orange-700 dark:text-orange-300">
                    {stats.gaps.length <= 10 
                      ? `Pages: ${stats.gaps.join(', ')}`
                      : `Pages: ${stats.gaps.slice(0, 10).join(', ')}, and ${stats.gaps.length - 10} more`
                    }
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
        
        {/* Search and sort */}
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search pages or entities..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
          
          <Select value={sortBy} onValueChange={(value: any) => setSortBy(value)}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="page">Page Number</SelectItem>
              <SelectItem value="entities">Most Entities</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Heatmap visualization */}
      {showHeatmap && (
        <div className="border-b border-border p-4 bg-muted/30">
          <div className="flex items-center justify-between mb-3">
            <h4 className="font-semibold">Page Coverage Heatmap</h4>
            <div className="flex items-center gap-4 text-xs">
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 rounded bg-gray-200 dark:bg-gray-800" />
                <span className="text-muted-foreground">No entities</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 rounded bg-blue-200 dark:bg-blue-900" />
                <span className="text-muted-foreground">Low</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 rounded bg-yellow-500 dark:bg-yellow-600" />
                <span className="text-muted-foreground">Medium</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 rounded bg-red-500 dark:bg-red-600" />
                <span className="text-muted-foreground">High</span>
              </div>
            </div>
          </div>
          
          {/* Heatmap grid */}
          <div className="grid grid-cols-10 gap-2">
            {Array.from({ length: stats.totalPages }, (_, i) => {
              const pageNum = stats.minPage + i;
              const pageGroup = pageGroups.find(g => g.pageNum === pageNum);
              const entityCount = pageGroup?.entityCount || 0;
              const isGap = entityCount === 0;
              
              return (
                <button
                  key={pageNum}
                  className={`
                    aspect-square rounded flex flex-col items-center justify-center
                    transition-all hover:scale-110 hover:shadow-lg
                    ${getHeatmapColor(entityCount)}
                    ${isGap ? 'opacity-50' : ''}
                  `}
                  title={getHeatmapTitle(pageNum, entityCount)}
                  onClick={() => {
                    if (!isGap) {
                      togglePage(pageNum);
                      // Scroll to page in list
                      const element = document.getElementById(`page-${pageNum}`);
                      if (element) {
                        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
                      }
                    }
                  }}
                >
                  <span className="text-xs font-medium text-gray-900 dark:text-gray-100">
                    {pageNum}
                  </span>
                  {!isGap && (
                    <span className="text-[10px] text-gray-700 dark:text-gray-300">
                      {entityCount}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Pages list */}
      <div className="flex-1 overflow-auto">
        {filteredPageGroups.length === 0 ? (
          <div className="py-12 text-center">
            <p className="text-muted-foreground">No pages match your search</p>
          </div>
        ) : (
          <div className="p-4 space-y-2">
            {filteredPageGroups.map((page) => (
              <Card key={page.pageNum} id={`page-${page.pageNum}`} className="overflow-hidden">
                <CardHeader 
                  className="p-4 cursor-pointer hover:bg-accent transition-colors"
                  onClick={() => togglePage(page.pageNum)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <ChevronRight 
                        className={`h-4 w-4 transition-transform ${
                          expandedPages.has(page.pageNum) ? 'rotate-90' : ''
                        }`}
                      />
                      <CardTitle className="text-base">Page {page.pageNum}</CardTitle>
                      <Badge variant="secondary" className="ml-2">
                        {page.entityCount} {page.entityCount === 1 ? 'entity' : 'entities'}
                      </Badge>
                    </div>
                    
                    {/* Intensity indicator */}
                    <div className="flex items-center gap-2">
                      <div className="flex items-center gap-1">
                        {Array.from({ length: 5 }, (_, i) => (
                          <div
                            key={i}
                            className={`w-2 h-4 rounded ${
                              i < Math.ceil((page.entityCount / stats.maxEntitiesPerPage) * 5)
                                ? 'bg-primary'
                                : 'bg-muted'
                            }`}
                          />
                        ))}
                      </div>
                    </div>
                  </div>
                </CardHeader>
                
                {expandedPages.has(page.pageNum) && (
                  <CardContent className="p-0">
                    <div className="divide-y divide-border">
                      {page.entities.map((entity) => {
                        const isSelected = selectedEntity?.id === entity.id && selectedEntity?.type === entity.type;
                        return <div
                          key={`${entity.type}-${entity.id}`}
                          className={`p-4 hover:bg-accent cursor-pointer transition-colors ${
                            isSelected ? 'bg-accent border-l-4 border-primary' : ''
                          }`}
                          onClick={(e) => {
                            e.stopPropagation();
                            onEntitySelect({
                              id: entity.id,
                              type: entity.type,
                              pages: entity.pages,
                            });
                          }}
                        >
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                <p className="font-medium text-sm truncate">{entity.id}</p>
                                <Badge variant="outline" className="text-xs">
                                  {entity.type}
                                </Badge>
                              </div>
                              
                              <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                                <span>Agent: {getAgentDisplayName(entity.agent)}</span>
                                <span>•</span>
                                <span>Model: {getModelDisplayName(entity.model)}</span>
                                {entity.pages.length > 1 && (
                                  <>
                                    <span>•</span>
                                    <span>Also on: {entity.pages.filter(p => p !== page.pageNum).join(', ')}</span>
                                  </>
                                )}
                              </div>
                            </div>
                            
                            <div className="flex items-center gap-2 flex-shrink-0">
                              {entity.confidence !== undefined && (
                                <Badge 
                                  variant={
                                    getConfidenceLevel(entity.confidence) === 'high' 
                                      ? 'default' 
                                      : getConfidenceLevel(entity.confidence) === 'medium'
                                      ? 'secondary'
                                      : 'destructive'
                                  }
                                  className="text-xs"
                                >
                                  {formatConfidence(entity.confidence)}
                                </Badge>
                              )}
                              <Badge variant="outline" className="text-xs">
                                {getSourceTypeLabel(entity.source)}
                              </Badge>
                            </div>
                          </div>
                        </div>;
                      })}
                    </div>
                  </CardContent>
                )}
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default ProvenanceView;
