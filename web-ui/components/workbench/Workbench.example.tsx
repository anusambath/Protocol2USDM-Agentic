/**
 * Workbench Component Example
 * 
 * This example demonstrates how to use the Workbench component
 * in a Next.js page to render the IDE/Workbench-style interface.
 */

import { Workbench } from './Workbench';

// Example 1: Basic usage with mock data
export function BasicWorkbenchExample() {
  const mockProtocolId = 'PROTO-2024-001';
  
  const mockUsdm = {
    version: '3.0.0',
    studyTitle: 'Phase III Clinical Trial for Drug X',
    studyType: 'Interventional',
    studyPhase: 'Phase 3',
    // ... other USDM fields
  };

  const mockProvenance = {
    cells: {
      'activity1|encounter1': 'both' as const,
      'activity2|encounter2': 'text' as const,
    },
    cellPageRefs: {
      'activity1|encounter1': [12, 15],
    },
  };

  const mockIntermediateFiles = {
    extractedText: '...',
    extractedTables: [],
    extractedImages: [],
  };

  return (
    <Workbench
      protocolId={mockProtocolId}
      usdm={mockUsdm}
      provenance={mockProvenance}
      intermediateFiles={mockIntermediateFiles}
    />
  );
}

// Example 2: Integration with Next.js page
export function NextJsPageExample() {
  // In a real Next.js page, you would fetch data from an API
  // This example shows the structure
  
  return (
    <div>
      {/* 
        In app/protocols/[id]/page.tsx:
        
        import { Workbench } from '@/components/workbench/Workbench';
        
        export default async function ProtocolDetailPage({
          params,
        }: {
          params: { id: string };
        }) {
          // Fetch protocol data
          const response = await fetch(`/api/protocols/${params.id}/usdm`);
          const data = await response.json();
          
          return (
            <Workbench
              protocolId={params.id}
              usdm={data.usdm}
              provenance={data.provenance}
              intermediateFiles={data.intermediateFiles}
            />
          );
        }
      */}
    </div>
  );
}

// Example 3: With custom keyboard shortcuts
export function WorkbenchWithCustomShortcutsExample() {
  // The Workbench component already registers standard shortcuts
  // If you need additional shortcuts, you can use useKeyboardShortcuts
  // in a parent component or wrapper
  
  return (
    <div>
      {/*
        import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts';
        
        function CustomWorkbenchWrapper() {
          // Add custom shortcuts
          useKeyboardShortcuts([
            {
              key: 'e',
              ctrl: true,
              action: () => console.log('Custom export shortcut'),
              description: 'Custom Export',
            },
          ]);
          
          return (
            <Workbench
              protocolId="PROTO-2024-001"
              usdm={mockUsdm}
              provenance={mockProvenance}
              intermediateFiles={mockIntermediateFiles}
            />
          );
        }
      */}
    </div>
  );
}

// Example 4: With theme provider
export function WorkbenchWithThemeExample() {
  return (
    <div>
      {/*
        import { ThemeProvider } from '@/components/theme/ThemeProvider';
        
        function App() {
          return (
            <ThemeProvider>
              <Workbench
                protocolId="PROTO-2024-001"
                usdm={mockUsdm}
                provenance={mockProvenance}
                intermediateFiles={mockIntermediateFiles}
              />
            </ThemeProvider>
          );
        }
      */}
    </div>
  );
}

// Example 5: Demonstrating layout state persistence
export function LayoutPersistenceExample() {
  return (
    <div>
      {/*
        The Workbench automatically persists layout state to localStorage
        via the layoutStore (Zustand persist middleware).
        
        Persisted state includes:
        - Panel widths (sidebar, right panel)
        - Collapsed states (sidebar, right panel)
        - Open tabs and active tab
        - Nav tree expanded groups
        - Activity bar mode
        
        To reset layout to defaults:
        
        import { useLayoutStore } from '@/stores/layoutStore';
        
        function ResetLayoutButton() {
          const resetToDefaults = useLayoutStore((state) => state.resetToDefaults);
          
          return (
            <button onClick={resetToDefaults}>
              Reset Layout to Defaults
            </button>
          );
        }
      */}
    </div>
  );
}

// Example 6: Accessing layout state from outside Workbench
export function ExternalLayoutControlExample() {
  return (
    <div>
      {/*
        You can control the Workbench layout from outside the component
        by using the layoutStore directly:
        
        import { useLayoutStore } from '@/stores/layoutStore';
        
        function ExternalControls() {
          const {
            toggleSidebar,
            toggleRightPanel,
            openTab,
            setActivityBarMode,
          } = useLayoutStore();
          
          const handleOpenSoA = () => {
            openTab({
              id: 'soa-' + Date.now(),
              viewType: 'soa',
              label: 'SoA Table',
              icon: 'Table',
            });
          };
          
          return (
            <div>
              <button onClick={toggleSidebar}>Toggle Sidebar</button>
              <button onClick={toggleRightPanel}>Toggle Right Panel</button>
              <button onClick={handleOpenSoA}>Open SoA Table</button>
              <button onClick={() => setActivityBarMode('search')}>
                Switch to Search
              </button>
            </div>
          );
        }
      */}
    </div>
  );
}

// Example 7: Responsive behavior demonstration
export function ResponsiveWorkbenchExample() {
  return (
    <div>
      {/*
        The Workbench automatically adapts to viewport changes:
        
        - Viewport < 1024px: Sidebar and Right Panel auto-collapse
        - Viewport >= 1024px: Panels restore to persisted states
        
        This behavior is handled by the useResponsiveLayout hook
        and requires no additional configuration.
        
        To test responsive behavior:
        1. Open the Workbench in a desktop browser
        2. Resize the browser window to < 1024px width
        3. Observe panels auto-collapsing
        4. Resize back to >= 1024px
        5. Observe panels restoring to previous states
      */}
    </div>
  );
}

// Example 8: Command Palette usage
export function CommandPaletteExample() {
  return (
    <div>
      {/*
        The Command Palette is automatically integrated into the Workbench.
        
        To open the Command Palette:
        - Press Ctrl+K (Windows/Linux) or Cmd+K (macOS)
        - Or call setIsCommandPaletteOpen(true) programmatically
        
        Available commands:
        - Navigation: All 20 views from the view registry
        - Actions: Save Draft, Publish, Reset, Toggle Panels, Export
        
        The palette supports:
        - Fuzzy search filtering
        - Keyboard navigation (Arrow Up/Down, Enter, Escape)
        - Command categories (Navigation, Actions)
        - Shortcut hints for actions
      */}
    </div>
  );
}
