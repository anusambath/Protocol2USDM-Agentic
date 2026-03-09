/**
 * CenterPanel Component Examples
 * 
 * This file demonstrates various usage scenarios for the CenterPanel component.
 */

import React from 'react';
import { CenterPanel } from './CenterPanel';
import { LayoutTab } from '@/stores/layoutStore';

// Example 1: Empty state (no tabs open)
export function EmptyStateExample() {
  const handleTabChange = (tabId: string) => {
    console.log('Opening tab:', tabId);
    // In real usage, this would call layoutStore.openTab()
  };

  return (
    <CenterPanel
      openTabs={[]}
      activeTabId={null}
      onTabChange={handleTabChange}
      onTabClose={() => {}}
      usdm={{}}
      protocolId="PROTO-2024-001"
      provenance={null}
      intermediateFiles={null}
    />
  );
}

// Example 2: Single tab open
export function SingleTabExample() {
  const openTabs: LayoutTab[] = [
    {
      id: 'overview-1',
      viewType: 'overview',
      label: 'Study Metadata',
      icon: 'FileText',
    },
  ];

  const mockUsdm = {
    studyId: 'STUDY-001',
    studyTitle: 'Phase III Clinical Trial',
    studyVersion: '1.0',
  };

  return (
    <CenterPanel
      openTabs={openTabs}
      activeTabId="overview-1"
      onTabChange={(tabId) => console.log('Switched to:', tabId)}
      onTabClose={(tabId) => console.log('Closed:', tabId)}
      usdm={mockUsdm}
      protocolId="PROTO-2024-001"
      provenance={null}
      intermediateFiles={null}
    />
  );
}

// Example 3: Multiple tabs open
export function MultipleTabsExample() {
  const openTabs: LayoutTab[] = [
    {
      id: 'overview-1',
      viewType: 'overview',
      label: 'Study Metadata',
      icon: 'FileText',
    },
    {
      id: 'soa-1',
      viewType: 'soa',
      label: 'SoA Table',
      icon: 'Table',
    },
    {
      id: 'timeline-1',
      viewType: 'timeline',
      label: 'Timeline',
      icon: 'GitBranch',
    },
    {
      id: 'quality-1',
      viewType: 'quality',
      label: 'Quality Metrics',
      icon: 'BarChart3',
    },
  ];

  const mockUsdm = {
    studyId: 'STUDY-001',
    studyTitle: 'Phase III Clinical Trial',
  };

  const mockProvenance = {
    cells: {
      'activity1|encounter1': 'both' as const,
    },
    cellPageRefs: {
      'activity1|encounter1': [12],
    },
  };

  return (
    <CenterPanel
      openTabs={openTabs}
      activeTabId="soa-1"
      onTabChange={(tabId) => console.log('Switched to:', tabId)}
      onTabClose={(tabId) => console.log('Closed:', tabId)}
      usdm={mockUsdm}
      protocolId="PROTO-2024-001"
      provenance={mockProvenance}
      intermediateFiles={null}
    />
  );
}

// Example 4: With selection callbacks (for Right Panel integration)
export function WithSelectionCallbacksExample() {
  const openTabs: LayoutTab[] = [
    {
      id: 'soa-1',
      viewType: 'soa',
      label: 'SoA Table',
      icon: 'Table',
    },
    {
      id: 'timeline-1',
      viewType: 'timeline',
      label: 'Timeline',
      icon: 'GitBranch',
    },
  ];

  const handleCellSelect = (cellId: string) => {
    console.log('Cell selected:', cellId);
    // In real usage, this would update Right Panel to show provenance
  };

  const handleNodeSelect = (nodeId: string) => {
    console.log('Node selected:', nodeId);
    // In real usage, this would update Right Panel to show node details
  };

  return (
    <CenterPanel
      openTabs={openTabs}
      activeTabId="soa-1"
      onTabChange={(tabId) => console.log('Switched to:', tabId)}
      onTabClose={(tabId) => console.log('Closed:', tabId)}
      usdm={{}}
      protocolId="PROTO-2024-001"
      provenance={null}
      intermediateFiles={null}
      onCellSelect={handleCellSelect}
      onNodeSelect={handleNodeSelect}
    />
  );
}

// Example 5: Integrated with Layout Store
export function IntegratedExample() {
  // This example shows how CenterPanel integrates with the layout store
  // In real usage, you would use the actual useLayoutStore hook
  
  const mockLayoutStore = {
    openTabs: [
      {
        id: 'overview-1',
        viewType: 'overview' as const,
        label: 'Study Metadata',
        icon: 'FileText',
      },
      {
        id: 'eligibility-1',
        viewType: 'eligibility' as const,
        label: 'Eligibility Criteria',
        icon: 'UserCheck',
      },
    ],
    activeTabId: 'overview-1',
    setActiveTab: (tabId: string) => {
      console.log('Setting active tab:', tabId);
    },
    closeTab: (tabId: string) => {
      console.log('Closing tab:', tabId);
    },
  };

  return (
    <CenterPanel
      openTabs={mockLayoutStore.openTabs}
      activeTabId={mockLayoutStore.activeTabId}
      onTabChange={mockLayoutStore.setActiveTab}
      onTabClose={mockLayoutStore.closeTab}
      usdm={{}}
      protocolId="PROTO-2024-001"
      provenance={null}
      intermediateFiles={null}
    />
  );
}

// Example 6: With intermediate files (for data views)
export function WithIntermediateFilesExample() {
  const openTabs: LayoutTab[] = [
    {
      id: 'document-1',
      viewType: 'document',
      label: 'Document Structure',
      icon: 'FileTree',
    },
    {
      id: 'images-1',
      viewType: 'images',
      label: 'SoA Images',
      icon: 'Image',
    },
  ];

  const mockIntermediateFiles = {
    documentStructure: {
      sections: [
        { id: 'sec-1', title: 'Introduction', page: 1 },
        { id: 'sec-2', title: 'Methods', page: 5 },
      ],
    },
    soaImages: [
      { id: 'img-1', url: '/images/soa-1.png', page: 12 },
      { id: 'img-2', url: '/images/soa-2.png', page: 13 },
    ],
  };

  return (
    <CenterPanel
      openTabs={openTabs}
      activeTabId="document-1"
      onTabChange={(tabId) => console.log('Switched to:', tabId)}
      onTabClose={(tabId) => console.log('Closed:', tabId)}
      usdm={{}}
      protocolId="PROTO-2024-001"
      provenance={null}
      intermediateFiles={mockIntermediateFiles}
    />
  );
}

// Example 7: Tab switching demonstration
export function TabSwitchingExample() {
  // This example demonstrates how tab switching works
  // Only the active tab's component is mounted (lazy rendering)
  
  const openTabs: LayoutTab[] = [
    { id: 'tab-1', viewType: 'overview', label: 'Overview', icon: 'FileText' },
    { id: 'tab-2', viewType: 'soa', label: 'SoA', icon: 'Table' },
    { id: 'tab-3', viewType: 'timeline', label: 'Timeline', icon: 'GitBranch' },
  ];

  // Simulate switching between tabs
  const [activeTabId, setActiveTabId] = React.useState('tab-1');

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <button onClick={() => setActiveTabId('tab-1')}>Switch to Overview</button>
        <button onClick={() => setActiveTabId('tab-2')}>Switch to SoA</button>
        <button onClick={() => setActiveTabId('tab-3')}>Switch to Timeline</button>
      </div>
      
      <CenterPanel
        openTabs={openTabs}
        activeTabId={activeTabId}
        onTabChange={setActiveTabId}
        onTabClose={(tabId) => console.log('Closed:', tabId)}
        usdm={{}}
        protocolId="PROTO-2024-001"
        provenance={null}
        intermediateFiles={null}
      />
    </div>
  );
}

// Example 8: Error handling (missing view component)
export function ErrorHandlingExample() {
  const openTabs: LayoutTab[] = [
    {
      id: 'unknown-1',
      viewType: 'unknown' as any, // Invalid view type
      label: 'Unknown View',
      icon: 'FileText',
    },
  ];

  // When the view component is not found in the registry,
  // CenterPanel gracefully falls back to the welcome state
  return (
    <CenterPanel
      openTabs={openTabs}
      activeTabId="unknown-1"
      onTabChange={(tabId) => console.log('Switched to:', tabId)}
      onTabClose={(tabId) => console.log('Closed:', tabId)}
      usdm={{}}
      protocolId="PROTO-2024-001"
      provenance={null}
      intermediateFiles={null}
    />
  );
}
