import { z } from 'zod';

// Cell source types
export type CellSource = 'text' | 'vision' | 'both' | 'needs_review' | 'none';

// Source type for entities (includes 'derived')
export type SourceType = 'text' | 'vision' | 'both' | 'derived';

// Model types
export type ModelType = 'gemini' | 'claude' | 'unknown';

// Bounding box for PDF highlighting
export const BoundingBoxSchema = z.object({
  page: z.number(),
  x: z.number(),
  y: z.number(),
  width: z.number(),
  height: z.number(),
});

export type BoundingBox = z.infer<typeof BoundingBoxSchema>;

// Extended entity provenance with agent, model, and timestamp
export const EntityProvenanceExtendedSchema = z.object({
  source: z.enum(['text', 'vision', 'both', 'derived']),
  agent: z.string().optional(), // Agent name (e.g., "metadata_agent")
  model: z.string().optional(), // Model name (e.g., "gemini-2.5-flash", "claude-opus-4-6")
  confidence: z.number().min(0).max(1).optional(),
  pageRefs: z.array(z.number()).optional(),
  timestamp: z.string().optional(), // ISO 8601 timestamp
  footnoteRefs: z.array(z.string()).optional(), // For SOA cells
  boundingBox: BoundingBoxSchema.optional(),
});

export type EntityProvenanceExtended = z.infer<typeof EntityProvenanceExtendedSchema>;

// Legacy entity provenance (for backward compatibility)
export const EntityProvenanceSchema = z.object({
  source: z.enum(['text', 'vision', 'both']),
  confidence: z.number().optional(),
  pageRefs: z.array(z.number()).optional(),
  boundingBox: BoundingBoxSchema.optional(),
});

export type EntityProvenance = z.infer<typeof EntityProvenanceSchema>;

// Full provenance data structure
export const ProvenanceDataSchema = z.object({
  // New format: entities object with activity/encounter sources
  entities: z.object({
    activities: z.record(z.string(), z.enum(['text', 'vision', 'both'])).optional(),
    plannedTimepoints: z.record(z.string(), z.enum(['text', 'vision', 'both'])).optional(),
    encounters: z.record(z.string(), z.enum(['text', 'vision', 'both'])).optional(),
    epochs: z.record(z.string(), z.enum(['text', 'vision', 'both'])).optional(),
    activityGroups: z.record(z.string(), z.enum(['text', 'vision', 'both'])).optional(),
  }).optional(),
  
  // New format: cells as flat map "activityId|encounterId" -> source
  cells: z.record(
    z.string(), // "activityId|encounterId"
    z.enum(['text', 'vision', 'both', 'needs_review'])
  ).optional(),
  
  // Legacy format: Entity-level provenance
  activities: z.record(z.string(), EntityProvenanceSchema).optional(),
  plannedTimepoints: z.record(z.string(), EntityProvenanceSchema).optional(),
  encounters: z.record(z.string(), EntityProvenanceSchema).optional(),
  epochs: z.record(z.string(), EntityProvenanceSchema).optional(),
  
  // Legacy format: Cell-level provenance (activity × timepoint)
  activityTimepoints: z.record(
    z.string(), // activityId
    z.record(z.string(), z.enum(['text', 'vision', 'both', 'needs_review'])) // timepointId → source
  ).optional(),
  
  // Footnote references per cell (supports both formats)
  cellFootnotes: z.union([
    z.record(z.string(), z.array(z.string())), // New: "activityId|encounterId" -> refs
    z.record(z.string(), z.record(z.string(), z.array(z.string()))) // Legacy: nested
  ]).optional(),
  
  // Page references per cell (supports both formats)
  cellPageRefs: z.union([
    z.record(z.string(), z.array(z.number())), // New: "activityId|encounterId" -> page numbers
    z.record(z.string(), z.record(z.string(), z.array(z.number()))) // Legacy: nested
  ]).optional(),
  
  // Page references per entity
  entityPageRefs: z.record(
    z.string(), // entity ID
    z.array(z.number()) // page numbers
  ).optional(),
  
  // SoA footnotes
  footnotes: z.array(z.string()).optional(),
});

export type ProvenanceData = z.infer<typeof ProvenanceDataSchema>;

// Extended provenance data with agent/model information
export const ProvenanceDataExtendedSchema = z.object({
  // Metadata about the provenance data
  metadata: z.object({
    extractionDate: z.string(),
    pipelineVersion: z.string().optional(),
    protocolId: z.string(),
    totalEntities: z.number(),
  }).optional(),
  
  // Extended entity provenance by type
  entities: z.object({
    activities: z.record(z.string(), EntityProvenanceExtendedSchema).optional(),
    plannedTimepoints: z.record(z.string(), EntityProvenanceExtendedSchema).optional(),
    encounters: z.record(z.string(), EntityProvenanceExtendedSchema).optional(),
    epochs: z.record(z.string(), EntityProvenanceExtendedSchema).optional(),
    activityGroups: z.record(z.string(), EntityProvenanceExtendedSchema).optional(),
    metadata: z.record(z.string(), EntityProvenanceExtendedSchema).optional(),
    eligibility: z.record(z.string(), EntityProvenanceExtendedSchema).optional(),
    objectives: z.record(z.string(), EntityProvenanceExtendedSchema).optional(),
    endpoints: z.record(z.string(), EntityProvenanceExtendedSchema).optional(),
    interventions: z.record(z.string(), EntityProvenanceExtendedSchema).optional(),
    procedures: z.record(z.string(), EntityProvenanceExtendedSchema).optional(),
    devices: z.record(z.string(), EntityProvenanceExtendedSchema).optional(),
    narratives: z.record(z.string(), EntityProvenanceExtendedSchema).optional(),
  }).optional(),
  
  // Cell-level provenance (for SOA table)
  cells: z.record(z.string(), z.enum(['text', 'vision', 'both', 'needs_review'])).optional(),
  cellFootnotes: z.record(z.string(), z.array(z.string())).optional(),
  cellPageRefs: z.record(z.string(), z.array(z.number())).optional(),
  
  // Legacy format support
  activityTimepoints: z.record(
    z.string(),
    z.record(z.string(), z.enum(['text', 'vision', 'both', 'needs_review']))
  ).optional(),
  
  // SoA footnotes
  footnotes: z.array(z.string()).optional(),
});

export type ProvenanceDataExtended = z.infer<typeof ProvenanceDataExtendedSchema>;

// Selected entity for sidebar display
export interface SelectedEntity {
  type: string; // Entity type (e.g., "study_title", "activity", "eligibility_criterion")
  id: string; // Entity ID
  provenance: EntityProvenanceExtended;
}

// Cached page for IndexedDB
export interface CachedPage {
  protocolId: string;
  pageNum: number;
  blob: Blob;
  timestamp: number;
  size: number;
}

// Provenance statistics
export interface ProvenanceStats {
  confirmed: number;
  textOnly: number;
  visionOnly: number;
  needsReview: number;
  orphaned: number;
  total: number;
}

// Helper to calculate provenance stats
export function calculateProvenanceStats(provenance: ProvenanceData | null): ProvenanceStats {
  const stats: ProvenanceStats = {
    confirmed: 0,
    textOnly: 0,
    visionOnly: 0,
    needsReview: 0,
    orphaned: 0,
    total: 0,
  };

  if (!provenance) return stats;

  // New format: provenance.cells
  if (provenance.cells) {
    for (const source of Object.values(provenance.cells)) {
      stats.total++;
      switch (source) {
        case 'both':
          stats.confirmed++;
          break;
        case 'text':
          stats.textOnly++;
          break;
        case 'vision':
          stats.visionOnly++;
          break;
        case 'needs_review':
          stats.needsReview++;
          break;
      }
    }
    return stats;
  }

  // Legacy format: provenance.activityTimepoints
  if (provenance.activityTimepoints) {
    for (const activityCells of Object.values(provenance.activityTimepoints)) {
      for (const source of Object.values(activityCells)) {
        stats.total++;
        switch (source) {
          case 'both':
            stats.confirmed++;
            break;
          case 'text':
            stats.textOnly++;
            break;
          case 'vision':
          case 'needs_review':
            stats.needsReview++;
            break;
        }
      }
    }
  }

  return stats;
}

// Get provenance color class
export function getProvenanceColorClass(source: CellSource): string {
  switch (source) {
    case 'both':
      return 'cell-confirmed';
    case 'text':
      return 'cell-text-only';
    case 'vision':
    case 'needs_review':
      return 'cell-vision-only';
    case 'none':
      return 'cell-orphaned';
    default:
      return '';
  }
}

// Get provenance hex color
export function getProvenanceColor(source: CellSource): string {
  switch (source) {
    case 'both':
      return '#4ade80';
    case 'text':
      return '#60a5fa';
    case 'vision':
    case 'needs_review':
      return '#fb923c';
    case 'none':
      return '#f87171';
    default:
      return 'transparent';
  }
}


// Helper to extract model type from model string
export function getModelType(modelString: string | undefined): ModelType {
  if (!modelString) return 'unknown';
  const lower = modelString.toLowerCase();
  if (lower.includes('gemini')) return 'gemini';
  if (lower.includes('claude')) return 'claude';
  return 'unknown';
}

// Helper to get model display name
export function getModelDisplayName(modelString: string | undefined): string {
  if (!modelString) return 'Unknown Model';
  
  // Extract version info
  if (modelString.includes('gemini-2.5-flash')) return 'Gemini 2.5 Flash';
  if (modelString.includes('gemini-2.5-pro')) return 'Gemini 2.5 Pro';
  if (modelString.includes('gemini')) return 'Gemini';
  if (modelString.includes('claude-opus-4')) return 'Claude Opus 4';
  if (modelString.includes('claude-sonnet')) return 'Claude Sonnet';
  if (modelString.includes('claude')) return 'Claude';
  
  return modelString;
}

// Helper to get agent display name
export function getAgentDisplayName(agentId: string | undefined): string {
  if (!agentId) return 'Unknown Agent';
  
  // Remove _agent suffix and convert to title case
  const name = agentId.replace(/_agent$/, '').replace(/_/g, ' ');
  return name.split(' ').map(word => 
    word.charAt(0).toUpperCase() + word.slice(1)
  ).join(' ');
}

// Helper to format confidence score as percentage
export function formatConfidence(confidence: number | undefined): string {
  if (confidence === undefined) return 'N/A';
  return `${Math.round(confidence * 100)}%`;
}

// Helper to get confidence level label
export function getConfidenceLevel(confidence: number | undefined): 'high' | 'medium' | 'low' | 'unknown' {
  if (confidence === undefined) return 'unknown';
  if (confidence >= 0.75) return 'high';
  if (confidence >= 0.5) return 'medium';
  return 'low';
}

// Helper to format timestamp as relative time
export function formatRelativeTime(timestamp: string | undefined): string {
  if (!timestamp) return 'Unknown';
  
  try {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    
    return date.toLocaleDateString();
  } catch {
    return 'Unknown';
  }
}

// Helper to format page references
export function formatPageRefs(pageRefs: number[] | undefined): string {
  if (!pageRefs || pageRefs.length === 0) return 'No pages';
  if (pageRefs.length === 1) return `Page ${pageRefs[0]}`;
  if (pageRefs.length <= 3) return `Pages ${pageRefs.join(', ')}`;
  return `Pages ${pageRefs[0]}-${pageRefs[pageRefs.length - 1]} (${pageRefs.length} total)`;
}

// Helper to get source type display label
export function getSourceTypeLabel(source: SourceType | CellSource): string {
  switch (source) {
    case 'both':
      return 'Confirmed (Text + Vision)';
    case 'text':
      return 'Text Only';
    case 'vision':
      return 'Vision Only';
    case 'derived':
      return 'Derived';
    case 'needs_review':
      return 'Needs Review';
    case 'none':
      return 'No Provenance';
    default:
      return 'Unknown';
  }
}
