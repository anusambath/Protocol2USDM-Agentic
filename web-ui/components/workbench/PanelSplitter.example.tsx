'use client';

import { useState } from 'react';
import { PanelSplitter } from './PanelSplitter';

/**
 * Example demonstrating PanelSplitter usage with two resizable panels
 */
export function PanelSplitterExample() {
  const [leftPanelWidth, setLeftPanelWidth] = useState(260);
  const [leftPanelCollapsed, setLeftPanelCollapsed] = useState(false);

  const handleResize = (delta: number) => {
    // Apply constraints: min 200px, max 480px
    const newWidth = Math.max(200, Math.min(480, leftPanelWidth + delta));
    setLeftPanelWidth(newWidth);
  };

  const handleDoubleClick = () => {
    setLeftPanelCollapsed(!leftPanelCollapsed);
  };

  return (
    <div className="h-screen w-screen flex overflow-hidden">
      {/* Left Panel */}
      <div
        className="bg-muted border-r transition-all duration-200"
        style={{ width: leftPanelCollapsed ? 0 : leftPanelWidth }}
      >
        {!leftPanelCollapsed && (
          <div className="p-4">
            <h2 className="text-lg font-semibold mb-2">Left Panel</h2>
            <p className="text-sm text-muted-foreground">
              Width: {leftPanelWidth}px
            </p>
            <p className="text-sm text-muted-foreground mt-2">
              Try dragging the splitter, double-clicking it, or using arrow keys when focused.
            </p>
          </div>
        )}
      </div>

      {/* Panel Splitter */}
      {!leftPanelCollapsed && (
        <PanelSplitter
          position="left"
          onResize={handleResize}
          onDoubleClick={handleDoubleClick}
        />
      )}

      {/* Right Panel (Center Content) */}
      <div className="flex-1 bg-background p-4">
        <h2 className="text-lg font-semibold mb-2">Center Panel</h2>
        <p className="text-sm text-muted-foreground">
          This panel takes up the remaining space.
        </p>
        {leftPanelCollapsed && (
          <button
            onClick={() => setLeftPanelCollapsed(false)}
            className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded"
          >
            Show Left Panel
          </button>
        )}
      </div>
    </div>
  );
}

/**
 * Example with two splitters (left and right panels)
 */
export function DualPanelSplitterExample() {
  const [leftWidth, setLeftWidth] = useState(260);
  const [rightWidth, setRightWidth] = useState(320);
  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const [rightCollapsed, setRightCollapsed] = useState(false);

  const handleLeftResize = (delta: number) => {
    const newWidth = Math.max(200, Math.min(480, leftWidth + delta));
    setLeftWidth(newWidth);
  };

  const handleRightResize = (delta: number) => {
    // For right splitter, positive delta decreases right panel width
    const newWidth = Math.max(240, Math.min(600, rightWidth - delta));
    setRightWidth(newWidth);
  };

  return (
    <div className="h-screen w-screen flex overflow-hidden">
      {/* Left Panel */}
      <div
        className="bg-muted border-r transition-all duration-200"
        style={{ width: leftCollapsed ? 0 : leftWidth }}
      >
        {!leftCollapsed && (
          <div className="p-4">
            <h2 className="text-lg font-semibold mb-2">Sidebar</h2>
            <p className="text-sm text-muted-foreground">
              Width: {leftWidth}px
            </p>
          </div>
        )}
      </div>

      {!leftCollapsed && (
        <PanelSplitter
          position="left"
          onResize={handleLeftResize}
          onDoubleClick={() => setLeftCollapsed(!leftCollapsed)}
        />
      )}

      {/* Center Panel */}
      <div className="flex-1 bg-background p-4 min-w-[400px]">
        <h2 className="text-lg font-semibold mb-2">Center Panel</h2>
        <p className="text-sm text-muted-foreground">
          Main content area (min 400px)
        </p>
      </div>

      {!rightCollapsed && (
        <PanelSplitter
          position="right"
          onResize={handleRightResize}
          onDoubleClick={() => setRightCollapsed(!rightCollapsed)}
        />
      )}

      {/* Right Panel */}
      <div
        className="bg-muted border-l transition-all duration-200"
        style={{ width: rightCollapsed ? 0 : rightWidth }}
      >
        {!rightCollapsed && (
          <div className="p-4">
            <h2 className="text-lg font-semibold mb-2">Right Panel</h2>
            <p className="text-sm text-muted-foreground">
              Width: {rightWidth}px
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
