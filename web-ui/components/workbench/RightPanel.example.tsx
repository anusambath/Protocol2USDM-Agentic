'use client';

import { useState } from 'react';
import { RightPanel } from './RightPanel';
import { RightPanelTab } from '@/stores/layoutStore';

/**
 * Example 1: Basic RightPanel with no selection
 */
export function BasicRightPanelExample() {
  const [activeTab, setActiveTab] = useState<RightPanelTab>('properties');

  return (
    <div className="h-screen w-[320px]">
      <RightPanel
        collapsed={false}
        width={320}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        selectedCellId={null}
        selectedNodeId={null}
        usdm={{}}
        provenance={null}
      />
    </div>
  );
}

/**
 * Example 2: RightPanel with cell selection
 */
export function RightPanelWithCellSelectionExample() {
  const [activeTab, setActiveTab] = useState<RightPanelTab>('provenance');

  return (
    <div className="h-screen w-[320px]">
      <RightPanel
        collapsed={false}
        width={320}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        selectedCellId="activity1|encounter1"
        selectedNodeId={null}
        usdm={{}}
        provenance={{
          cells: {
            'activity1|encounter1': 'text' as const,
          },
          cellPageRefs: {
            'activity1|encounter1': [12],
          },
        }}
      />
    </div>
  );
}

/**
 * Example 3: RightPanel with node selection
 */
export function RightPanelWithNodeSelectionExample() {
  const [activeTab, setActiveTab] = useState<RightPanelTab>('properties');

  return (
    <div className="h-screen w-[320px]">
      <RightPanel
        collapsed={false}
        width={320}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        selectedCellId={null}
        selectedNodeId="node-visit-1"
        usdm={{}}
        provenance={null}
      />
    </div>
  );
}

/**
 * Example 4: Collapsed RightPanel
 */
export function CollapsedRightPanelExample() {
  const [activeTab, setActiveTab] = useState<RightPanelTab>('properties');

  return (
    <div className="h-screen w-[320px]">
      <RightPanel
        collapsed={true}
        width={320}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        selectedCellId={null}
        selectedNodeId={null}
        usdm={{}}
        provenance={null}
      />
    </div>
  );
}

/**
 * Example 5: Interactive RightPanel with toggle
 */
export function InteractiveRightPanelExample() {
  const [collapsed, setCollapsed] = useState(false);
  const [activeTab, setActiveTab] = useState<RightPanelTab>('properties');
  const [selectedCellId, setSelectedCellId] = useState<string | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  return (
    <div className="flex h-screen">
      {/* Control panel */}
      <div className="flex-1 p-8 space-y-6 bg-muted/30">
        <h2 className="text-2xl font-semibold">RightPanel Interactive Demo</h2>

        {/* Collapse toggle */}
        <div className="space-y-2">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={collapsed}
              onChange={(e) => setCollapsed(e.target.checked)}
              className="rounded"
            />
            <span>Collapsed</span>
          </label>
        </div>

        {/* Tab selection */}
        <div className="space-y-2">
          <p className="font-medium">Active Tab:</p>
          <div className="flex gap-2">
            {(['properties', 'provenance', 'footnotes'] as RightPanelTab[]).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  activeTab === tab
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted hover:bg-muted/80'
                }`}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Selection controls */}
        <div className="space-y-4">
          <div className="space-y-2">
            <p className="font-medium">Cell Selection:</p>
            <div className="flex gap-2">
              <button
                onClick={() => setSelectedCellId('cell-row-2-col-3')}
                className="px-3 py-1.5 rounded-md text-sm bg-muted hover:bg-muted/80"
              >
                Select Cell
              </button>
              <button
                onClick={() => setSelectedCellId(null)}
                className="px-3 py-1.5 rounded-md text-sm bg-muted hover:bg-muted/80"
              >
                Clear
              </button>
            </div>
            {selectedCellId && (
              <p className="text-sm text-muted-foreground">
                Selected: {selectedCellId}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <p className="font-medium">Node Selection:</p>
            <div className="flex gap-2">
              <button
                onClick={() => setSelectedNodeId('node-visit-1')}
                className="px-3 py-1.5 rounded-md text-sm bg-muted hover:bg-muted/80"
              >
                Select Node
              </button>
              <button
                onClick={() => setSelectedNodeId(null)}
                className="px-3 py-1.5 rounded-md text-sm bg-muted hover:bg-muted/80"
              >
                Clear
              </button>
            </div>
            {selectedNodeId && (
              <p className="text-sm text-muted-foreground">
                Selected: {selectedNodeId}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* RightPanel */}
      <RightPanel
        collapsed={collapsed}
        width={320}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        selectedCellId={selectedCellId}
        selectedNodeId={selectedNodeId}
        usdm={{}}
        provenance={
          selectedCellId
            ? {
                [selectedCellId]: {
                  source: 'text',
                  confidence: 0.92,
                  pdfPage: 8,
                },
              }
            : null
        }
      />
    </div>
  );
}

/**
 * Example 6: RightPanel with different widths
 */
export function RightPanelWidthExample() {
  const [width, setWidth] = useState(320);
  const [activeTab, setActiveTab] = useState<RightPanelTab>('properties');

  return (
    <div className="flex h-screen">
      <div className="flex-1 p-8 space-y-6 bg-muted/30">
        <h2 className="text-2xl font-semibold">RightPanel Width Demo</h2>

        <div className="space-y-2">
          <label className="block">
            <span className="font-medium">Width: {width}px</span>
            <input
              type="range"
              min={240}
              max={600}
              value={width}
              onChange={(e) => setWidth(Number(e.target.value))}
              className="w-full mt-2"
            />
          </label>
          <div className="flex gap-2">
            <button
              onClick={() => setWidth(240)}
              className="px-3 py-1.5 rounded-md text-sm bg-muted hover:bg-muted/80"
            >
              Min (240px)
            </button>
            <button
              onClick={() => setWidth(320)}
              className="px-3 py-1.5 rounded-md text-sm bg-muted hover:bg-muted/80"
            >
              Default (320px)
            </button>
            <button
              onClick={() => setWidth(600)}
              className="px-3 py-1.5 rounded-md text-sm bg-muted hover:bg-muted/80"
            >
              Max (600px)
            </button>
          </div>
        </div>
      </div>

      <RightPanel
        collapsed={false}
        width={width}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        selectedCellId="cell-row-1-col-2"
        selectedNodeId={null}
        usdm={{}}
        provenance={null}
      />
    </div>
  );
}
