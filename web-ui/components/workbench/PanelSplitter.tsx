'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

interface PanelSplitterProps {
  position: 'left' | 'right';
  onResize: (delta: number) => void;
  onDoubleClick: () => void;
}

export function PanelSplitter({ position, onResize, onDoubleClick }: PanelSplitterProps) {
  const [isDragging, setIsDragging] = useState(false);
  const initialXRef = useRef<number>(0);
  const splitterRef = useRef<HTMLDivElement>(null);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
    initialXRef.current = e.clientX;
  }, []);

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!isDragging) return;

      const delta = e.clientX - initialXRef.current;
      initialXRef.current = e.clientX;
      onResize(delta);
    },
    [isDragging, onResize]
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      // Arrow keys adjust width by 10px increments
      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        // For left splitter, left arrow decreases sidebar width (negative delta)
        // For right splitter, left arrow increases right panel width (negative delta)
        onResize(position === 'left' ? -10 : -10);
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        // For left splitter, right arrow increases sidebar width (positive delta)
        // For right splitter, right arrow decreases right panel width (positive delta)
        onResize(position === 'left' ? 10 : 10);
      }
    },
    [onResize, position]
  );

  // Set up global mouse event listeners during drag
  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);

      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, handleMouseMove, handleMouseUp]);

  return (
    <div
      ref={splitterRef}
      role="separator"
      aria-orientation="vertical"
      aria-label={`${position} panel splitter`}
      tabIndex={0}
      className="relative w-1 bg-border hover:bg-accent transition-colors cursor-col-resize focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
      onMouseDown={handleMouseDown}
      onDoubleClick={onDoubleClick}
      onKeyDown={handleKeyDown}
    >
      {/* Visual indicator on hover/focus */}
      <div className="absolute inset-y-0 left-1/2 -translate-x-1/2 w-1 bg-transparent hover:bg-primary/20 transition-colors" />
    </div>
  );
}
