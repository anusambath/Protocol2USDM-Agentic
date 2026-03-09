/**
 * Command Registry for Command Palette
 * 
 * This module defines all available commands for the Command Palette (Ctrl/Cmd+K).
 * Commands are categorized as either 'navigation' (for opening views) or 'action' (for executing operations).
 * 
 * The registry includes:
 * - 20 navigation commands matching the NavTree structure
 * - 8 action commands for common operations
 * 
 * @module commandRegistry
 */

/**
 * Command entry for the Command Palette
 */
export interface CommandEntry {
  /** Unique identifier for the command */
  id: string;
  /** Display label shown in the palette */
  label: string;
  /** Command category: navigation opens views, action executes operations */
  category: 'navigation' | 'action';
  /** Lucide icon name (e.g., 'FileText', 'Save') */
  icon: string;
  /** Optional keyboard shortcut display string (e.g., "⌘K", "⌘S") */
  shortcut?: string;
  /** Keywords for fuzzy search matching */
  keywords: string[];
}

/**
 * Complete command registry for the Command Palette.
 * 
 * Navigation commands are organized by group:
 * - Protocol: Core protocol information
 * - Advanced: Detailed protocol elements
 * - Quality: Validation and metrics
 * - Data: Data views and exports
 * 
 * Action commands provide quick access to common operations.
 */
export const commandRegistry: CommandEntry[] = [
  // Protocol Group (6 commands)
  {
    id: 'nav-overview',
    label: 'Protocol Overview',
    category: 'navigation',
    icon: 'FileText',
    keywords: ['overview', 'protocol', 'metadata', 'study', 'summary'],
  },
  {
    id: 'nav-eligibility',
    label: 'Eligibility Criteria',
    category: 'navigation',
    icon: 'Users',
    keywords: ['eligibility', 'criteria', 'inclusion', 'exclusion', 'participants'],
  },
  {
    id: 'nav-objectives',
    label: 'Objectives & Endpoints',
    category: 'navigation',
    icon: 'Target',
    keywords: ['objectives', 'endpoints', 'goals', 'outcomes', 'measures'],
  },
  {
    id: 'nav-design',
    label: 'Study Design',
    category: 'navigation',
    icon: 'Layout',
    keywords: ['design', 'study', 'structure', 'arms', 'phases'],
  },
  {
    id: 'nav-interventions',
    label: 'Interventions',
    category: 'navigation',
    icon: 'Pill',
    keywords: ['interventions', 'treatments', 'drugs', 'medications', 'therapy'],
  },
  {
    id: 'nav-amendments',
    label: 'Amendment History',
    category: 'navigation',
    icon: 'History',
    keywords: ['amendments', 'history', 'changes', 'revisions', 'versions'],
  },

  // Advanced Group (7 commands)
  {
    id: 'nav-extensions',
    label: 'Extensions',
    category: 'navigation',
    icon: 'Puzzle',
    keywords: ['extensions', 'custom', 'fields', 'metadata'],
  },
  {
    id: 'nav-entities',
    label: 'Advanced Entities',
    category: 'navigation',
    icon: 'Database',
    keywords: ['entities', 'advanced', 'data', 'structures'],
  },
  {
    id: 'nav-procedures',
    label: 'Procedures & Devices',
    category: 'navigation',
    icon: 'Stethoscope',
    keywords: ['procedures', 'devices', 'medical', 'equipment', 'tests'],
  },
  {
    id: 'nav-sites',
    label: 'Study Sites',
    category: 'navigation',
    icon: 'MapPin',
    keywords: ['sites', 'locations', 'centers', 'facilities'],
  },
  {
    id: 'nav-footnotes',
    label: 'Footnotes',
    category: 'navigation',
    icon: 'MessageSquare',
    keywords: ['footnotes', 'notes', 'annotations', 'comments'],
  },
  {
    id: 'nav-schedule',
    label: 'Schedule',
    category: 'navigation',
    icon: 'Calendar',
    keywords: ['schedule', 'timeline', 'activities', 'visits', 'events'],
  },
  {
    id: 'nav-narrative',
    label: 'Narrative',
    category: 'navigation',
    icon: 'BookOpen',
    keywords: ['narrative', 'text', 'description', 'document'],
  },

  // Quality Group (2 commands)
  {
    id: 'nav-quality',
    label: 'Quality Metrics',
    category: 'navigation',
    icon: 'BarChart3',
    keywords: ['quality', 'metrics', 'dashboard', 'statistics', 'analysis'],
  },
  {
    id: 'nav-validation',
    label: 'Validation Results',
    category: 'navigation',
    icon: 'CheckCircle2',
    keywords: ['validation', 'errors', 'warnings', 'issues', 'checks'],
  },

  // Data Group (5 commands)
  {
    id: 'nav-document',
    label: 'Document Structure',
    category: 'navigation',
    icon: 'FileCode',
    keywords: ['document', 'structure', 'json', 'usdm', 'data'],
  },
  {
    id: 'nav-images',
    label: 'Images',
    category: 'navigation',
    icon: 'Image',
    keywords: ['images', 'figures', 'diagrams', 'pictures'],
  },
  {
    id: 'nav-soa',
    label: 'Schedule of Activities',
    category: 'navigation',
    icon: 'Table',
    keywords: ['soa', 'schedule', 'activities', 'table', 'grid'],
  },
  {
    id: 'nav-timeline',
    label: 'Timeline Graph',
    category: 'navigation',
    icon: 'GitBranch',
    keywords: ['timeline', 'graph', 'visualization', 'flow', 'diagram'],
  },
  {
    id: 'nav-provenance',
    label: 'Provenance',
    category: 'navigation',
    icon: 'FileSearch',
    keywords: ['provenance', 'source', 'extraction', 'origin', 'tracking'],
  },

  // Action Commands (8 commands)
  {
    id: 'action-save-draft',
    label: 'Save Draft',
    category: 'action',
    icon: 'Save',
    shortcut: '⌘S',
    keywords: ['save', 'draft', 'persist', 'store'],
  },
  {
    id: 'action-publish',
    label: 'Publish',
    category: 'action',
    icon: 'Upload',
    keywords: ['publish', 'promote', 'release', 'finalize'],
  },
  {
    id: 'action-reset',
    label: 'Reset to Published',
    category: 'action',
    icon: 'RotateCcw',
    keywords: ['reset', 'revert', 'discard', 'undo', 'published'],
  },
  {
    id: 'action-toggle-sidebar',
    label: 'Toggle Sidebar',
    category: 'action',
    icon: 'PanelLeft',
    shortcut: '⌘B',
    keywords: ['toggle', 'sidebar', 'navigation', 'hide', 'show'],
  },
  {
    id: 'action-toggle-right-panel',
    label: 'Toggle Right Panel',
    category: 'action',
    icon: 'PanelRight',
    shortcut: '⌘J',
    keywords: ['toggle', 'right', 'panel', 'details', 'hide', 'show'],
  },
  {
    id: 'action-export-csv',
    label: 'Export CSV',
    category: 'action',
    icon: 'FileSpreadsheet',
    keywords: ['export', 'csv', 'download', 'spreadsheet'],
  },
  {
    id: 'action-export-json',
    label: 'Export JSON',
    category: 'action',
    icon: 'FileJson',
    keywords: ['export', 'json', 'download', 'data', 'usdm'],
  },
  {
    id: 'action-export-pdf',
    label: 'Export PDF',
    category: 'action',
    icon: 'FileDown',
    keywords: ['export', 'pdf', 'download', 'document', 'print'],
  },
];

/**
 * Get all navigation commands
 */
export function getNavigationCommands(): CommandEntry[] {
  return commandRegistry.filter((cmd) => cmd.category === 'navigation');
}

/**
 * Get all action commands
 */
export function getActionCommands(): CommandEntry[] {
  return commandRegistry.filter((cmd) => cmd.category === 'action');
}

/**
 * Get a command by its ID
 */
export function getCommandById(id: string): CommandEntry | undefined {
  return commandRegistry.find((cmd) => cmd.id === id);
}

/**
 * Search commands using fuzzy matching
 * 
 * @param query - Search query string
 * @returns Filtered and sorted commands matching the query
 */
export function searchCommands(query: string): CommandEntry[] {
  if (!query.trim()) {
    return commandRegistry;
  }

  const lowerQuery = query.toLowerCase();
  const queryChars = lowerQuery.split('');

  // Filter and score commands
  const scored = commandRegistry
    .map((cmd) => {
      const searchText = `${cmd.label} ${cmd.keywords.join(' ')}`.toLowerCase();
      
      // Check if all query characters appear in order
      let searchIndex = 0;
      let matchPositions: number[] = [];
      
      for (const char of queryChars) {
        const foundIndex = searchText.indexOf(char, searchIndex);
        if (foundIndex === -1) {
          return null; // No match
        }
        matchPositions.push(foundIndex);
        searchIndex = foundIndex + 1;
      }

      // Calculate score (lower is better)
      // Prefer matches at the start and with characters close together
      const firstMatchPosition = matchPositions[0] || 0;
      const matchSpread = matchPositions[matchPositions.length - 1] - matchPositions[0];
      const score = firstMatchPosition + matchSpread * 0.1;

      return { cmd, score };
    })
    .filter((item): item is { cmd: CommandEntry; score: number } => item !== null);

  // Sort by score (ascending) and return commands
  return scored
    .sort((a, b) => a.score - b.score)
    .map((item) => item.cmd);
}
