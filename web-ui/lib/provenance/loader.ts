/**
 * Provenance data loading utilities
 * 
 * Handles loading provenance JSON from output directory with:
 * - Error handling for missing or malformed data
 * - Data transformation for legacy formats
 * - Validation using Zod schemas
 */

import { 
  ProvenanceData, 
  ProvenanceDataExtended,
  ProvenanceDataSchema,
  ProvenanceDataExtendedSchema,
  EntityProvenanceExtended,
  EntityProvenanceExtendedSchema
} from './types';

/**
 * Load provenance data from a protocol's output directory
 * 
 * @param protocolId - The protocol ID (e.g., "Alexion_NCT04573309_Wilsons_20260306_220032")
 * @returns Parsed and validated provenance data, or null if not found/invalid
 */
export async function loadProvenanceData(protocolId: string): Promise<ProvenanceDataExtended | null> {
  try {
    // Fetch provenance.json from the protocol's output directory
    const response = await fetch(`/api/protocols/${protocolId}/provenance`);
    
    if (!response.ok) {
      if (response.status === 404) {
        console.warn(`Provenance data not found for protocol ${protocolId}`);
        return null;
      }
      throw new Error(`Failed to load provenance data: ${response.statusText}`);
    }
    
    const rawData = await response.json();
    
    // Try to parse as extended format first
    const extendedResult = ProvenanceDataExtendedSchema.safeParse(rawData);
    if (extendedResult.success) {
      return extendedResult.data;
    }
    
    // Fall back to legacy format and transform
    const legacyResult = ProvenanceDataSchema.safeParse(rawData);
    if (legacyResult.success) {
      console.info('Transforming legacy provenance format to extended format');
      return transformLegacyToExtended(legacyResult.data);
    }
    
    // If both fail, log detailed validation errors
    console.error('Invalid provenance data - validation failed:', {
      protocolId,
      extendedFormatErrors: extendedResult.error?.errors.map(e => ({
        path: e.path.join('.'),
        message: e.message,
        code: e.code,
      })),
      legacyFormatErrors: legacyResult.error?.errors.map(e => ({
        path: e.path.join('.'),
        message: e.message,
        code: e.code,
      })),
      timestamp: new Date().toISOString(),
    });
    
    // Log a user-friendly message
    console.warn('Invalid provenance data: The provenance file does not match the expected schema. Some provenance features may not work correctly.');
    
    return null;
  } catch (error) {
    console.error('Error loading provenance data:', {
      protocolId,
      error: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : undefined,
      timestamp: new Date().toISOString(),
    });
    return null;
  }
}

/**
 * Load ID mapping from a protocol's output directory
 * 
 * @param protocolId - The protocol ID
 * @returns ID mapping (pre-UUID -> UUID) or null if not found
 */
export async function loadIdMapping(protocolId: string): Promise<Record<string, string> | null> {
  try {
    const response = await fetch(`/api/protocols/${protocolId}/id-mapping`);
    
    if (!response.ok) {
      if (response.status === 404) {
        console.warn(`ID mapping not found for protocol ${protocolId}`);
        return null;
      }
      throw new Error(`Failed to load ID mapping: ${response.statusText}`);
    }
    
    const idMapping = await response.json();
    return idMapping;
  } catch (error) {
    console.error('Error loading ID mapping:', {
      protocolId,
      error: error instanceof Error ? error.message : String(error),
      timestamp: new Date().toISOString(),
    });
    return null;
  }
}

/**
 * Transform legacy provenance format to extended format
 * 
 * Legacy format has minimal fields (source, confidence, pageRefs)
 * Extended format adds agent, model, timestamp
 * 
 * @param legacy - Legacy provenance data
 * @returns Extended provenance data with defaults for missing fields
 */
function transformLegacyToExtended(legacy: ProvenanceData): ProvenanceDataExtended {
  const extended: ProvenanceDataExtended = {
    entities: {},
    cells: legacy.cells,
    cellFootnotes: transformCellFootnotes(legacy.cellFootnotes),
    cellPageRefs: transformCellPageRefs(legacy.cellPageRefs),
    activityTimepoints: legacy.activityTimepoints,
    footnotes: legacy.footnotes,
  };
  
  // Transform entity-level provenance
  if (legacy.activities) {
    extended.entities!.activities = transformEntityMap(legacy.activities);
  }
  if (legacy.plannedTimepoints) {
    extended.entities!.plannedTimepoints = transformEntityMap(legacy.plannedTimepoints);
  }
  if (legacy.encounters) {
    extended.entities!.encounters = transformEntityMap(legacy.encounters);
  }
  if (legacy.epochs) {
    extended.entities!.epochs = transformEntityMap(legacy.epochs);
  }
  
  return extended;
}

/**
 * Transform a map of legacy entity provenance to extended format
 */
function transformEntityMap(
  legacyMap: Record<string, { source: 'text' | 'vision' | 'both'; confidence?: number; pageRefs?: number[] }>
): Record<string, EntityProvenanceExtended> {
  const result: Record<string, EntityProvenanceExtended> = {};
  
  for (const [id, prov] of Object.entries(legacyMap)) {
    result[id] = {
      source: prov.source,
      confidence: prov.confidence,
      pageRefs: prov.pageRefs,
      // Legacy data doesn't have agent/model/timestamp, so leave undefined
      agent: undefined,
      model: undefined,
      timestamp: undefined,
    };
  }
  
  return result;
}

/**
 * Transform cell footnotes from legacy nested format to flat format
 * 
 * Legacy: { activityId: { timepointId: [refs] } }
 * New: { "activityId|timepointId": [refs] }
 */
function transformCellFootnotes(
  footnotes: Record<string, Record<string, string[]>> | Record<string, string[]> | undefined
): Record<string, string[]> | undefined {
  if (!footnotes) return undefined;
  
  // Check if already in new format (flat map)
  const firstValue = Object.values(footnotes)[0];
  if (Array.isArray(firstValue)) {
    return footnotes as Record<string, string[]>;
  }
  
  // Transform from nested to flat
  const result: Record<string, string[]> = {};
  for (const [activityId, timepointMap] of Object.entries(footnotes)) {
    for (const [timepointId, refs] of Object.entries(timepointMap as Record<string, string[]>)) {
      result[`${activityId}|${timepointId}`] = refs;
    }
  }
  
  return result;
}

/**
 * Transform cell page refs from legacy nested format to flat format
 * 
 * Legacy: { activityId: { timepointId: [pages] } }
 * New: { "activityId|timepointId": [pages] }
 */
function transformCellPageRefs(
  pageRefs: Record<string, Record<string, number[]>> | Record<string, number[]> | undefined
): Record<string, number[]> | undefined {
  if (!pageRefs) return undefined;
  
  // Check if already in new format (flat map)
  const firstValue = Object.values(pageRefs)[0];
  if (Array.isArray(firstValue)) {
    return pageRefs as Record<string, number[]>;
  }
  
  // Transform from nested to flat
  const result: Record<string, number[]> = {};
  for (const [activityId, timepointMap] of Object.entries(pageRefs)) {
    for (const [timepointId, pages] of Object.entries(timepointMap as Record<string, number[]>)) {
      result[`${activityId}|${timepointId}`] = pages;
    }
  }
  
  return result;
}

/**
 * Get provenance for a specific entity
 * 
 * @param data - Provenance data
 * @param entityType - Entity type (e.g., "activities", "metadata")
 * @param entityId - Entity ID
 * @returns Entity provenance or null if not found
 */
export function getEntityProvenance(
  data: ProvenanceDataExtended | null,
  entityType: string,
  entityId: string
): EntityProvenanceExtended | null {
  if (!data?.entities) return null;
  
  const entityMap = (data.entities as any)[entityType];
  if (!entityMap) return null;
  
  return entityMap[entityId] || null;
}

/**
 * Get provenance for a specific SOA cell
 * 
 * @param data - Provenance data
 * @param activityId - Activity ID
 * @param encounterId - Encounter ID (or timepoint ID for legacy)
 * @returns Cell source type or null if not found
 */
export function getCellProvenance(
  data: ProvenanceDataExtended | null,
  activityId: string,
  encounterId: string
): { 
  source: 'text' | 'vision' | 'both' | 'needs_review' | null;
  footnotes?: string[];
  pageRefs?: number[];
} {
  if (!data) return { source: null };
  
  // Try new format first
  const cellKey = `${activityId}|${encounterId}`;
  if (data.cells && cellKey in data.cells) {
    return {
      source: data.cells[cellKey],
      footnotes: data.cellFootnotes?.[cellKey],
      pageRefs: data.cellPageRefs?.[cellKey],
    };
  }
  
  // Fall back to legacy format
  if (data.activityTimepoints?.[activityId]?.[encounterId]) {
    const source = data.activityTimepoints[activityId][encounterId];
    return {
      source,
      footnotes: (data.cellFootnotes as any)?.[activityId]?.[encounterId],
      pageRefs: (data.cellPageRefs as any)?.[activityId]?.[encounterId],
    };
  }
  
  return { source: null };
}

/**
 * Get all entities with provenance data
 * 
 * @param data - Provenance data
 * @returns Array of entities with their provenance
 */
export function getAllEntitiesWithProvenance(
  data: ProvenanceDataExtended | null
): Array<{ type: string; id: string; provenance: EntityProvenanceExtended }> {
  if (!data?.entities) return [];
  
  const result: Array<{ type: string; id: string; provenance: EntityProvenanceExtended }> = [];
  
  for (const [entityType, entityMap] of Object.entries(data.entities)) {
    if (!entityMap) continue;
    
    for (const [entityId, provenance] of Object.entries(entityMap)) {
      result.push({
        type: entityType,
        id: entityId,
        provenance,
      });
    }
  }
  
  return result;
}

/**
 * Validate provenance data against schema
 * 
 * @param data - Raw provenance data
 * @returns Validation result with parsed data or errors
 */
export function validateProvenanceData(data: unknown): {
  success: boolean;
  data?: ProvenanceDataExtended;
  errors?: string[];
} {
  // Try extended format first
  const extendedResult = ProvenanceDataExtendedSchema.safeParse(data);
  if (extendedResult.success) {
    return { success: true, data: extendedResult.data };
  }
  
  // Try legacy format
  const legacyResult = ProvenanceDataSchema.safeParse(data);
  if (legacyResult.success) {
    return { 
      success: true, 
      data: transformLegacyToExtended(legacyResult.data) 
    };
  }
  
  // Both failed
  return {
    success: false,
    errors: [
      ...extendedResult.error.errors.map(e => `${e.path.join('.')}: ${e.message}`),
    ],
  };
}
