/**
 * Entity Matcher - Automatically matches USDM entities to provenance records
 * 
 * This utility provides a systematic way to find provenance for any USDM entity
 * by using the id_mapping.json to bridge UUID-based USDM IDs to pre-UUID provenance IDs.
 */

import { ProvenanceDataExtended, EntityProvenanceExtended } from './types';

/**
 * ID mapping from pre-UUID to UUID
 * Loaded from id_mapping.json in the protocol output directory
 */
export type IdMapping = Record<string, string>;

/**
 * Reverse ID mapping from UUID to pre-UUID
 */
export type ReverseIdMapping = Record<string, string>;

/**
 * Create a reverse mapping from UUID to pre-UUID ID
 */
export function createReverseMapping(idMapping: IdMapping): ReverseIdMapping {
  const reverse: ReverseIdMapping = {};
  for (const [preUuid, uuid] of Object.entries(idMapping)) {
    reverse[uuid] = preUuid;
  }
  return reverse;
}

/**
 * Find provenance for a USDM entity by its UUID
 * 
 * @param provenance - Provenance data with entities organized by type
 * @param usdmEntityId - UUID of the USDM entity
 * @param reverseMapping - Reverse ID mapping (UUID -> pre-UUID)
 * @param entityType - Optional entity type hint to narrow search
 * @returns Entity provenance or null if not found
 */
export function findProvenanceByUuid(
  provenance: ProvenanceDataExtended | null,
  usdmEntityId: string,
  reverseMapping: ReverseIdMapping,
  entityType?: string
): EntityProvenanceExtended | null {
  if (!provenance?.entities) return null;
  
  // Get the pre-UUID ID from the reverse mapping
  const preUuidId = reverseMapping[usdmEntityId];
  if (!preUuidId) return null;
  
  // If entity type is provided, search only that type
  if (entityType) {
    const entityMap = (provenance.entities as any)[entityType];
    if (entityMap && entityMap[preUuidId]) {
      return entityMap[preUuidId];
    }
    return null;
  }
  
  // Otherwise, search all entity types
  for (const [type, entityMap] of Object.entries(provenance.entities)) {
    if (entityMap && (entityMap as any)[preUuidId]) {
      return (entityMap as any)[preUuidId];
    }
  }
  
  return null;
}

/**
 * Find provenance for a USDM entity by matching its properties
 * 
 * This is a fallback when UUID mapping doesn't work. It tries to match
 * entities by their type and sequential order.
 * 
 * @param provenance - Provenance data
 * @param entityType - Entity type (e.g., "study_title", "organization")
 * @param index - Index of the entity in the USDM array (0-based)
 * @returns Entity provenance or null if not found
 */
export function findProvenanceByTypeAndIndex(
  provenance: ProvenanceDataExtended | null,
  entityType: string,
  index: number
): EntityProvenanceExtended | null {
  if (!provenance?.entities) return null;
  
  const entityMap = (provenance.entities as any)[entityType];
  if (!entityMap) return null;
  
  // Get all entity IDs for this type and sort them
  const entityIds = Object.keys(entityMap).sort();
  
  // Return the entity at the given index
  if (index >= 0 && index < entityIds.length) {
    return entityMap[entityIds[index]];
  }
  
  return null;
}

/**
 * Get entity type from USDM entity
 * 
 * Maps USDM entity types to provenance entity types
 */
export function getProvenanceEntityType(usdmEntity: any): string | null {
  // Check for explicit type field
  if (usdmEntity.type) {
    return normalizeEntityType(usdmEntity.type);
  }
  
  // Check for instanceType (used in some USDM entities)
  if (usdmEntity.instanceType) {
    return normalizeEntityType(usdmEntity.instanceType);
  }
  
  // Try to infer from object structure
  if (usdmEntity.name && usdmEntity.type?.decode) {
    return 'organization';
  }
  
  if (usdmEntity.text && usdmEntity.type?.decode?.includes('Title')) {
    return 'study_title';
  }
  
  return null;
}

/**
 * Normalize entity type to match provenance format
 * 
 * Converts various USDM type formats to the snake_case format used in provenance
 */
function normalizeEntityType(type: string): string {
  // Convert PascalCase to snake_case
  return type
    .replace(/([A-Z])/g, '_$1')
    .toLowerCase()
    .replace(/^_/, '');
}

/**
 * Batch find provenance for multiple entities
 * 
 * @param provenance - Provenance data
 * @param entities - Array of USDM entities with their IDs
 * @param reverseMapping - Reverse ID mapping
 * @returns Map of entity ID to provenance
 */
export function batchFindProvenance(
  provenance: ProvenanceDataExtended | null,
  entities: Array<{ id: string; type?: string }>,
  reverseMapping: ReverseIdMapping
): Map<string, EntityProvenanceExtended> {
  const result = new Map<string, EntityProvenanceExtended>();
  
  for (const entity of entities) {
    const prov = findProvenanceByUuid(
      provenance,
      entity.id,
      reverseMapping,
      entity.type
    );
    
    if (prov) {
      result.set(entity.id, prov);
    }
  }
  
  return result;
}
