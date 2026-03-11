'use client';

import { useMemo } from 'react';
import { motion } from 'framer-motion';
import { RightPanelTab } from '@/stores/layoutStore';
import { PanelTabBar } from './PanelTabBar';
import { Settings, GitBranch, FileText, Eye } from 'lucide-react';
import { ProvenanceDataExtended } from '@/lib/provenance/types';
import { useProvenanceSidebarStore } from '@/lib/stores/provenance-sidebar-store';

interface RightPanelProps {
  collapsed: boolean;
  width: number;
  activeTab: RightPanelTab;
  onTabChange: (tab: RightPanelTab) => void;
  // Contextual data
  selectedCellId: string | null;
  selectedNodeId: string | null;
  usdm: Record<string, unknown>;
  provenance: ProvenanceDataExtended | null;
}

export function RightPanel({
  collapsed,
  width,
  activeTab,
  onTabChange,
  selectedCellId,
  selectedNodeId,
  usdm,
  provenance,
}: RightPanelProps) {
  // Tab configuration for PanelTabBar
  const tabs = useMemo(
    () => [
      { id: 'properties', label: 'Properties', icon: 'Settings', closable: false },
      { id: 'provenance', label: 'Provenance', icon: 'GitBranch', closable: false },
      { id: 'footnotes', label: 'Footnotes', icon: 'FileText', closable: false },
    ],
    []
  );

  // Determine animation width (0 when collapsed, width when expanded)
  const animatedWidth = collapsed ? 0 : width;

  return (
    <motion.aside
      role="complementary"
      aria-label="Right panel"
      aria-hidden={collapsed}
      className="flex flex-col h-full bg-background border-l border-border overflow-hidden"
      initial={false}
      animate={{ width: animatedWidth }}
      transition={{
        duration: 0.2,
        ease: 'easeInOut',
      }}
      style={{ minWidth: collapsed ? 0 : width }}
    >
      {!collapsed && (
        <>
          {/* Tab bar at top */}
          <PanelTabBar
            tabs={tabs}
            activeTabId={activeTab}
            onTabChange={(tabId) => onTabChange(tabId as RightPanelTab)}
          />

          {/* Active tab content */}
          <div className="flex-1 overflow-auto">
            <div
              id={`panel-${activeTab}`}
              role="tabpanel"
              aria-labelledby={`tab-${activeTab}`}
              className="h-full"
            >
              {activeTab === 'properties' && (
                <PropertiesPanel
                  selectedCellId={selectedCellId}
                  selectedNodeId={selectedNodeId}
                  usdm={usdm}
                />
              )}
              {activeTab === 'provenance' && (
                <ProvenancePanel
                  selectedCellId={selectedCellId}
                  provenance={provenance}
                  usdm={usdm}
                />
              )}
              {activeTab === 'footnotes' && (
                <FootnotesPanel
                  selectedCellId={selectedCellId}
                  selectedNodeId={selectedNodeId}
                  usdm={usdm}
                  provenance={provenance}
                />
              )}
            </div>
          </div>
        </>
      )}
    </motion.aside>
  );
}

/**
 * Properties panel - displays properties of selected node/cell
 */
interface PropertiesPanelProps {
  selectedCellId: string | null;
  selectedNodeId: string | null;
  usdm: Record<string, unknown>;
}

function PropertiesPanel({
  selectedCellId,
  selectedNodeId,
  usdm,
}: PropertiesPanelProps) {
  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center gap-2 text-muted-foreground">
        <Settings className="h-5 w-5" />
        <h3 className="font-medium text-foreground">Properties</h3>
      </div>

      {selectedCellId || selectedNodeId ? (
        <div className="space-y-3">
          <div className="p-3 rounded-md bg-muted/50 border border-border">
            <p className="text-sm text-muted-foreground mb-2">Selection:</p>
            {selectedCellId && (
              <p className="text-sm font-mono text-foreground">
                Cell: {selectedCellId}
              </p>
            )}
            {selectedNodeId && (
              <p className="text-sm font-mono text-foreground">
                Node: {selectedNodeId}
              </p>
            )}
          </div>

          <div className="p-4 rounded-md bg-primary/5 border border-primary/20">
            <p className="text-sm text-muted-foreground text-center">
              Properties panel coming soon
            </p>
          </div>
        </div>
      ) : (
        <EmptyState
          icon={Settings}
          message="No selection"
          description="Select a cell or node to view its properties"
        />
      )}
    </div>
  );
}

/**
 * Provenance panel - displays provenance information for selected cell
 */
interface ProvenancePanelProps {
  selectedCellId: string | null;
  provenance: ProvenanceDataExtended | null;
  usdm: Record<string, unknown>;
}

function ProvenancePanel({ selectedCellId, provenance, usdm }: ProvenancePanelProps) {
  const { open } = useProvenanceSidebarStore();
  // Parse cell ID (format: "activityId|visitId")
  const cellInfo = useMemo(() => {
    if (!selectedCellId || !selectedCellId.includes('|')) return null;
    const [activityId, visitId] = selectedCellId.split('|');
    return { activityId, visitId };
  }, [selectedCellId]);

  // Build label → footnote text lookup from USDM soaFootnotes
  const labelToFootnoteText = useMemo(() => {
    const map = new Map<string, string>();
    try {
      const study = usdm?.study as Record<string, unknown> | undefined;
      const versions = study?.versions as Record<string, unknown>[] | undefined;
      const designs = versions?.[0]?.studyDesigns as Record<string, unknown>[] | undefined;
      const footnotes = designs?.[0]?.soaFootnotes as Array<{ label: string; text: string }> | undefined;
      if (footnotes) {
        for (const fn of footnotes) {
          map.set(fn.label.toLowerCase(), fn.text);
        }
      }
    } catch { /* ignore */ }
    return map;
  }, [usdm]);

  // Get provenance data for the selected cell
  const cellProvenance = useMemo(() => {
    if (!cellInfo || !provenance) return null;
    
    // New format: provenance.cells with "activityId|encounterId" keys
    if (provenance.cells) {
      const cellsMap = provenance.cells as Record<string, string>;
      const source = cellsMap[selectedCellId || ''];
      const footnotes = (provenance.cellFootnotes as Record<string, string[]>)?.[selectedCellId || ''] || [];
      
      // Get page references - try new format first, then legacy
      let pageRefs: number[] = [];
      if (provenance.cellPageRefs) {
        // New format: flat map
        pageRefs = (provenance.cellPageRefs as Record<string, number[]>)[selectedCellId || ''] || [];
      }
      
      return { source, footnotes, pageRefs };
    }
    
    // Legacy format: provenance.activityTimepoints
    if (provenance.activityTimepoints) {
      const activityProv = (provenance.activityTimepoints as Record<string, Record<string, string>>)[cellInfo.activityId];
      if (!activityProv) return null;
      
      const source = activityProv[cellInfo.visitId];
      const footnotes = (provenance.cellFootnotes as Record<string, Record<string, string[]>>)?.[cellInfo.activityId]?.[cellInfo.visitId] || [];
      
      // Get page references from legacy format
      let pageRefs: number[] = [];
      if (provenance.cellPageRefs) {
        const legacyPageRefs = provenance.cellPageRefs as Record<string, Record<string, number[]>>;
        pageRefs = legacyPageRefs[cellInfo.activityId]?.[cellInfo.visitId] || [];
      }
      
      return { source, footnotes, pageRefs };
    }
    
    return null;
  }, [cellInfo, provenance, selectedCellId]);

  // Get color for source type
  const getSourceColor = (source: string) => {
    switch (source) {
      case 'both': return '#4ade80'; // green
      case 'text': return '#60a5fa'; // blue
      case 'vision':
      case 'needs_review': return '#fb923c'; // orange
      case 'none': return '#f87171'; // red
      default: return '#9ca3af'; // gray
    }
  };

  // Get label for source type
  const getSourceLabel = (source: string) => {
    switch (source) {
      case 'both': return 'Confirmed';
      case 'text': return 'Text Only';
      case 'vision': return 'Vision Only';
      case 'needs_review': return 'Needs Review';
      case 'none': return 'Orphaned';
      default: return 'Unknown';
    }
  };

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center gap-2 text-muted-foreground">
        <GitBranch className="h-5 w-5" />
        <h3 className="font-medium text-foreground">Provenance</h3>
      </div>

      {/* Debug: Log provenance data */}
      {process.env.NODE_ENV === 'development' && provenance && (
        <div className="text-xs text-muted-foreground">
          <details>
            <summary className="cursor-pointer">Debug: Provenance Data</summary>
            <pre className="mt-2 p-2 bg-muted rounded overflow-auto max-h-40 text-[10px]">
              {JSON.stringify({
                hasCells: !!provenance.cells,
                cellsCount: provenance.cells ? Object.keys(provenance.cells).length : 0,
                hasCellPageRefs: !!provenance.cellPageRefs,
                cellPageRefsCount: provenance.cellPageRefs ? Object.keys(provenance.cellPageRefs as Record<string, unknown>).length : 0,
                hasActivityTimepoints: !!provenance.activityTimepoints,
                selectedCellId,
                cellProvenance: cellProvenance ? {
                  hasSource: !!cellProvenance.source,
                  source: cellProvenance.source,
                  hasPageRefs: !!cellProvenance.pageRefs,
                  pageRefsLength: cellProvenance.pageRefs?.length || 0,
                  pageRefs: cellProvenance.pageRefs,
                  hasFootnotes: !!cellProvenance.footnotes,
                  footnotesLength: cellProvenance.footnotes?.length || 0
                } : null,
                // Sample of cellPageRefs data
                sampleCellPageRefs: provenance.cellPageRefs ? 
                  Object.entries(provenance.cellPageRefs as Record<string, unknown>).slice(0, 3) : null
              }, null, 2)}
            </pre>
          </details>
        </div>
      )}

      {selectedCellId && cellProvenance ? (
        <div className="space-y-4">
          {/* Cell ID */}
          <div className="p-3 rounded-md bg-muted/50 border border-border">
            <p className="text-xs text-muted-foreground mb-1">Selected Cell:</p>
            <p className="text-sm font-mono text-foreground">{selectedCellId}</p>
          </div>

          {/* Source Type */}
          <div className="p-4 rounded-md border" style={{ borderColor: getSourceColor(cellProvenance.source) }}>
            <div className="flex items-center gap-2 mb-2">
              <div 
                className="w-3 h-3 rounded-full" 
                style={{ backgroundColor: getSourceColor(cellProvenance.source) }}
              />
              <span className="font-medium text-sm">
                {getSourceLabel(cellProvenance.source)}
              </span>
            </div>
            <p className="text-xs text-muted-foreground">
              {cellProvenance.source === 'both' && 'Found in both text and vision extraction'}
              {cellProvenance.source === 'text' && 'Found only in text extraction'}
              {cellProvenance.source === 'vision' && 'Found only in vision extraction'}
              {cellProvenance.source === 'needs_review' && 'Requires manual review'}
              {cellProvenance.source === 'none' && 'Not found in extraction'}
            </p>
          </div>

          {/* Preview Button */}
          {cellProvenance.pageRefs && cellProvenance.pageRefs.length > 0 && (
            <button
              onClick={() => {
                open({
                  type: 'soa_cell',
                  id: selectedCellId || '',
                  provenance: {
                    source: cellProvenance.source,
                    confidence: undefined,
                    pageRefs: cellProvenance.pageRefs,
                    agent: 'soa_extraction',
                    model: '',
                    timestamp: '',
                  },
                });
              }}
              className="w-full px-3 py-2 text-sm font-medium text-primary border border-border rounded-md hover:bg-accent transition-all duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 flex items-center justify-center gap-2"
              aria-label="Preview source protocol pages"
            >
              <Eye className="h-4 w-4" />
              Preview Source Pages
            </button>
          )}

          {/* Footnotes */}
          {cellProvenance.footnotes && cellProvenance.footnotes.length > 0 && (
            <div className="p-4 rounded-md bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-800">
              <div className="flex items-center gap-2 mb-2">
                <FileText className="h-4 w-4 text-blue-600" />
                <span className="font-medium text-sm text-blue-900 dark:text-blue-100">
                  Footnotes
                </span>
              </div>
              <div className="space-y-1.5">
                {cellProvenance.footnotes.map((footnote: string, i: number) => {
                  const fnText = labelToFootnoteText.get(footnote.toLowerCase());
                  return (
                    <div key={i} className="flex items-start gap-2">
                      <span className="px-2 py-0.5 text-xs font-bold font-mono bg-blue-200 dark:bg-blue-800 text-blue-900 dark:text-blue-100 rounded shrink-0">
                        {footnote}
                      </span>
                      {fnText && (
                        <span className="text-xs text-blue-800 dark:text-blue-200 leading-relaxed">
                          {fnText}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Source Pages */}
          {cellProvenance.pageRefs && cellProvenance.pageRefs.length > 0 && (
            <div className="p-4 rounded-md bg-purple-50 dark:bg-purple-950/20 border border-purple-200 dark:border-purple-800">
              <div className="flex items-center gap-2 mb-3">
                <FileText className="h-4 w-4 text-purple-600" />
                <span className="font-medium text-sm text-purple-900 dark:text-purple-100">
                  Source Pages
                </span>
              </div>
              <div className="flex flex-wrap gap-2">
                {cellProvenance.pageRefs.map((page: number, i: number) => (
                  <div
                    key={i}
                    className="px-3 py-2 bg-purple-100 dark:bg-purple-900/40 text-purple-900 dark:text-purple-100 rounded-md border border-purple-300 dark:border-purple-700 font-medium text-sm"
                    title={`Page ${page}`}
                  >
                    {page}
                  </div>
                ))}
              </div>
              <p className="text-xs text-purple-700 dark:text-purple-300 mt-2">
                Data extracted from {cellProvenance.pageRefs.length === 1 ? 'page' : 'pages'} {cellProvenance.pageRefs.join(', ')} of the protocol document
              </p>
            </div>
          )}

          {/* Fallback: Show message when no page data available */}
          {(!cellProvenance.pageRefs || cellProvenance.pageRefs.length === 0) && (
            <div className="p-4 rounded-md bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800">
              <div className="flex items-center gap-2 mb-2">
                <FileText className="h-4 w-4 text-amber-600" />
                <span className="font-medium text-sm text-amber-900 dark:text-amber-100">
                  Source Pages
                </span>
              </div>
              <p className="text-xs text-amber-700 dark:text-amber-300">
                Page number tracking not available for this cell. The backend provenance system currently tracks page numbers for study metadata and objectives, but not for individual SoA cells.
              </p>
              <p className="text-xs text-amber-700 dark:text-amber-300 mt-2">
                💡 Tip: Check the "SoA Images" tab to see which pages contain the Schedule of Activities table.
              </p>
            </div>
          )}

          {/* Help text */}
          <div className="p-3 rounded-md bg-muted/30 text-xs text-muted-foreground">
            <p className="mb-1 font-medium">Provenance Legend:</p>
            <ul className="space-y-1 ml-4">
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-green-500" />
                <span>Confirmed - Found in both extractions</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-blue-500" />
                <span>Text Only - Found in text extraction</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-orange-500" />
                <span>Vision/Review - Found in vision or needs review</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-red-500" />
                <span>Orphaned - Not found in extraction</span>
              </li>
            </ul>
          </div>
        </div>
      ) : (
        <EmptyState
          icon={GitBranch}
          message="No cell selected"
          description="Select a cell in the SoA table to view its provenance details"
        />
      )}
    </div>
  );
}

/**
 * Footnotes panel - displays footnotes related to selected content
 */
interface FootnotesPanelProps {
  selectedCellId: string | null;
  selectedNodeId: string | null;
  usdm: Record<string, unknown>;
  provenance: ProvenanceDataExtended | null;
}

function FootnotesPanel({
  selectedCellId,
  selectedNodeId,
  usdm,
  provenance,
}: FootnotesPanelProps) {
  // Extract soaFootnotes from USDM
  const soaFootnotes = useMemo(() => {
    try {
      const study = usdm?.study as Record<string, unknown> | undefined;
      const versions = study?.versions as Record<string, unknown>[] | undefined;
      const designs = versions?.[0]?.studyDesigns as Record<string, unknown>[] | undefined;
      const footnotes = designs?.[0]?.soaFootnotes as Array<{
        id: string;
        instanceType: string;
        label: string;
        text: string;
      }> | undefined;
      return footnotes || [];
    } catch {
      return [];
    }
  }, [usdm]);

  // Get footnote labels for the selected cell from provenance
  const cellFootnoteLabels = useMemo(() => {
    if (!selectedCellId || !provenance) return [];
    const labels = (provenance.cellFootnotes as Record<string, string[]>)?.[selectedCellId] || [];
    return labels;
  }, [selectedCellId, provenance]);

  // Set of active labels for quick lookup
  const activeLabels = useMemo(() => {
    return new Set(cellFootnoteLabels.map(l => l.toLowerCase()));
  }, [cellFootnoteLabels]);

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center gap-2 text-muted-foreground">
        <FileText className="h-5 w-5" />
        <h3 className="font-medium text-foreground">Footnotes</h3>
        {soaFootnotes.length > 0 && (
          <span className="text-xs">({soaFootnotes.length})</span>
        )}
      </div>

      {soaFootnotes.length > 0 ? (
        <div className="space-y-1.5 max-h-[calc(100vh-300px)] overflow-auto">
          {soaFootnotes.map((fn) => {
            const isActive = activeLabels.has(fn.label.toLowerCase());
            return (
              <div
                key={fn.id}
                className={`p-2 rounded text-xs border transition-colors ${
                  isActive
                    ? 'bg-blue-50 dark:bg-blue-950/30 border-blue-300 dark:border-blue-700 ring-1 ring-blue-400 dark:ring-blue-600'
                    : 'bg-muted/30 border-border'
                }`}
              >
                <div className="flex items-start gap-1.5">
                  <span className={`font-mono font-bold shrink-0 ${
                    isActive ? 'text-blue-700 dark:text-blue-300' : 'text-foreground'
                  }`}>
                    {fn.label}.
                  </span>
                  <span className={isActive ? 'text-foreground' : 'text-muted-foreground'}>
                    {fn.text || '(no text)'}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      ) : selectedCellId ? (
        <EmptyState
          icon={FileText}
          message="No footnotes"
          description="No SoA footnotes found in this protocol"
        />
      ) : (
        <EmptyState
          icon={FileText}
          message="No cell selected"
          description="Select a cell in the SoA table to view its footnotes"
        />
      )}
    </div>
  );
}

/**
 * Empty state component for when no contextual information is available
 */
interface EmptyStateProps {
  icon: React.ComponentType<{ className?: string }>;
  message: string;
  description: string;
}

function EmptyState({ icon: Icon, message, description }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center space-y-3">
      <div className="p-3 rounded-full bg-muted/50">
        <Icon className="h-8 w-8 text-muted-foreground" />
      </div>
      <div className="space-y-1">
        <p className="font-medium text-foreground">{message}</p>
        <p className="text-sm text-muted-foreground max-w-[240px]">
          {description}
        </p>
      </div>
    </div>
  );
}
