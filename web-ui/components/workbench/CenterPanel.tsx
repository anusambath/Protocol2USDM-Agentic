'use client';

import { useMemo, useCallback, Component, ReactNode } from 'react';
import { LayoutTab } from '@/stores/layoutStore';
import { PanelTabBar } from './PanelTabBar';
import { viewRegistry } from '@/lib/viewRegistry';
import { ProvenanceDataExtended } from '@/lib/provenance/types';
import { AlertTriangle } from 'lucide-react';

interface CenterPanelProps {
  openTabs: LayoutTab[];
  activeTabId: string | null;
  onTabChange: (tabId: string) => void;
  onTabClose: (tabId: string) => void;
  // View rendering props
  usdm: Record<string, unknown>;
  protocolId: string;
  provenance: ProvenanceDataExtended | null;
  idMapping: Record<string, string> | null;
  intermediateFiles: Record<string, unknown> | null;
  onCellSelect?: (cellId: string) => void;
  onNodeSelect?: (nodeId: string) => void;
}

export function CenterPanel({
  openTabs,
  activeTabId,
  onTabChange,
  onTabClose,
  usdm,
  protocolId,
  provenance,
  idMapping,
  intermediateFiles,
  onCellSelect,
  onNodeSelect,
}: CenterPanelProps) {
  // Convert LayoutTab[] to PanelTabBar format
  const tabBarTabs = useMemo(
    () =>
      openTabs.map((tab) => ({
        id: tab.id,
        label: tab.label,
        icon: tab.icon,
        closable: true,
      })),
    [openTabs]
  );

  // Find the active tab
  const activeTab = useMemo(
    () => {
      const tab = openTabs.find((tab) => tab.id === activeTabId);
      if (tab) {
        // Validate tab structure
        if (!tab.viewType || typeof tab.viewType !== 'string') {
          console.error('Invalid tab structure - viewType is not a string:', tab);
          console.error('Full tab object:', JSON.stringify(tab, null, 2));
          return null;
        }
        if (!tab.label || typeof tab.label !== 'string') {
          console.error('Invalid tab structure - label is not a string:', tab);
          return null;
        }
      }
      return tab || null;
    },
    [openTabs, activeTabId]
  );

  // Get safe viewType string for error boundaries
  const safeViewType = useMemo(() => {
    if (!activeTab) return 'unknown';
    if (typeof activeTab.viewType === 'string') return activeTab.viewType;
    console.error('activeTab.viewType is not a string:', activeTab.viewType);
    return 'unknown';
  }, [activeTab]);

  // Get the view component for the active tab
  const ActiveViewComponent = useMemo(() => {
    if (!activeTab) return null;
    const viewEntry = viewRegistry[activeTab.viewType];
    if (!viewEntry) {
      console.error(`View entry not found for viewType: ${activeTab.viewType}`);
      return null;
    }
    if (!viewEntry.component) {
      console.error(`Component not found in view entry for viewType: ${activeTab.viewType}`);
      return null;
    }
    return viewEntry.component;
  }, [activeTab]);

  // Prepare props for the active view - different views need different props
  const viewProps = useMemo(() => {
    if (!activeTab) return {};
    
    const baseProps: any = {};
    
    // Most views need usdm - pass null if not available to avoid undefined errors
    if (activeTab.viewType !== 'images') {
      baseProps.usdm = usdm || null;
    }
    
    // Some views need protocolId
    if (['images', 'validation'].includes(activeTab.viewType)) {
      baseProps.protocolId = protocolId;
    }
    
    // Pass provenance and idMapping to all views (for inline provenance display)
    baseProps.provenance = provenance || null;
    baseProps.idMapping = idMapping || null;
    
    // Timeline needs executionModel and onNodeSelect
    if (activeTab.viewType === 'timeline') {
      baseProps.executionModel = intermediateFiles?.executionModel || null;
      baseProps.onNodeSelect = onNodeSelect;
    }
    
    // SoA needs onCellSelect
    if (activeTab.viewType === 'soa') {
      baseProps.onCellSelect = onCellSelect;
    }
    
    return baseProps;
  }, [activeTab, usdm, protocolId, provenance, intermediateFiles, onNodeSelect, onCellSelect]);

  // Navigation handler for WelcomeState - this should trigger the parent's navigation
  const handleNavigate = useCallback((viewType: string) => {
    // This is a placeholder - the welcome screen shouldn't directly open tabs
    // Users should use the sidebar navigation instead
    console.log('Navigate to:', viewType);
  }, []);

  return (
    <div
      role="main"
      aria-label="Center panel"
      className="flex flex-col h-full bg-background overflow-hidden"
    >
      {/* Tab bar at top */}
      {openTabs.length > 0 && (
        <PanelTabBar
          tabs={tabBarTabs}
          activeTabId={activeTabId}
          onTabChange={onTabChange}
          onTabClose={onTabClose}
        />
      )}

      {/* Active view content */}
      <div className="flex-1 overflow-auto">
        {ActiveViewComponent ? (
          <div
            id={`panel-${activeTabId}`}
            role="tabpanel"
            aria-labelledby={`tab-${activeTabId}`}
            className="h-full"
          >
            <ErrorBoundary 
              fallback={<ViewErrorFallback viewType={safeViewType} />}
              viewType={safeViewType}
            >
              <ActiveViewComponent {...viewProps} />
            </ErrorBoundary>
          </div>
        ) : activeTab ? (
          <ViewNotFoundFallback viewType={activeTab.viewType} onClose={() => onTabClose(activeTab.id)} />
        ) : (
          <WelcomeState onNavigate={handleNavigate} />
        )}
      </div>
    </div>
  );
}

/**
 * Welcome state displayed when no tabs are open
 */
interface WelcomeStateProps {
  onNavigate: (viewType: string) => void;
}

function WelcomeState({ onNavigate: _onNavigate }: WelcomeStateProps) {
  return (
    <div className="flex items-center justify-center h-full p-8">
      <div className="max-w-2xl w-full space-y-8">
        {/* Welcome message */}
        <div className="text-center space-y-2">
          <h2 className="text-3xl font-semibold text-foreground">
            Welcome to Protocol2USDM
          </h2>
          <p className="text-muted-foreground">
            Select a view from the sidebar to get started
          </p>
        </div>

        {/* Additional help text */}
        <div className="text-center text-sm text-muted-foreground space-y-2">
          <p>
            Press <kbd className="px-2 py-1 rounded bg-muted border border-border">Ctrl+K</kbd> to
            open the command palette for quick navigation
          </p>
          <p className="text-xs">
            Use the Explorer panel on the left to browse all available views
          </p>
        </div>
      </div>
    </div>
  );
}


/**
 * Error boundary for view components
 */
class ErrorBoundary extends Component<
  { children: ReactNode; fallback: ReactNode; viewType?: string },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: { children: ReactNode; fallback: ReactNode; viewType?: string }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: any) {
    console.error(`View component error in ${this.props.viewType || 'unknown'} view:`, error, errorInfo);
    
    // Log additional context to help debug
    if (error.message.includes('Objects are not valid as a React child')) {
      console.error('This error typically means a component is trying to render an object directly.');
      console.error('Check that all data being rendered is converted to strings or proper JSX.');
    }
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback;
    }
    return this.props.children;
  }
}

/**
 * Error fallback for view components
 */
function ViewErrorFallback({ viewType }: { viewType?: string }) {
  return (
    <div className="flex items-center justify-center h-full p-8">
      <div className="max-w-md text-center space-y-4">
        <div className="p-3 rounded-full bg-destructive/10 w-fit mx-auto">
          <AlertTriangle className="h-8 w-8 text-destructive" />
        </div>
        <div>
          <h3 className="font-semibold text-foreground mb-2">View Error</h3>
          <p className="text-sm text-muted-foreground">
            There was an error loading the {viewType || 'view'} component.
          </p>
          <p className="text-xs text-muted-foreground mt-2">
            Check the browser console for more details.
          </p>
        </div>
      </div>
    </div>
  );
}

/**
 * Fallback for missing view components
 */
function ViewNotFoundFallback({ viewType, onClose }: { viewType: string; onClose: () => void }) {
  return (
    <div className="flex items-center justify-center h-full p-8">
      <div className="max-w-md text-center space-y-4">
        <div className="p-3 rounded-full bg-destructive/10 w-fit mx-auto">
          <AlertTriangle className="h-8 w-8 text-destructive" />
        </div>
        <div>
          <h3 className="font-semibold text-foreground mb-2">View Not Available</h3>
          <p className="text-sm text-muted-foreground">
            The view component for "{viewType}" could not be found.
          </p>
          <button
            onClick={onClose}
            className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            Close Tab
          </button>
        </div>
      </div>
    </div>
  );
}
