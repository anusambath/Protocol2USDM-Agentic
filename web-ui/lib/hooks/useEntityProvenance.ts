/**
 * useEntityProvenance Hook
 * 
 * Provides easy access to provenance data for USDM entities
 * Automatically handles UUID to pre-UUID mapping
 */

import { useMemo } from 'react';
import { ProvenanceDataExtended, EntityProvenanceExtended } from '@/lib/provenance/types';
import {
  createReverseMapping,
  findProvenanceByUuid,
  findProvenanceByTypeAndIndex,
  ReverseIdMapping,
} from '@/lib/provenance/entity-matcher';

interface UseEntityProvenanceOptions {
  provenance: ProvenanceDataExtended | null;
  idMapping?: Record<string, string>;
}

interface UseEntityProvenanceResult {
  /**
   * Get provenance for a USDM entity by its UUID
   */
  getProvenance: (
    entityId: string,
    entityType?: string
  ) => EntityProvenanceExtended | null;
  
  /**
   * Get provenance by entity type and index (fallback method)
   */
  getProvenanceByIndex: (
    entityType: string,
    index: number
  ) => EntityProvenanceExtended | null;
  
  /**
   * Check if provenance exists for an entity
   */
  hasProvenance: (entityId: string, entityType?: string) => boolean;
  
  /**
   * Get all entity IDs that have provenance for a given type
   */
  getEntitiesWithProvenance: (entityType: string) => string[];
}

/**
 * Hook to access provenance data for USDM entities
 * 
 * @example
 * ```tsx
 * const { getProvenance, hasProvenance } = useEntityProvenance({
 *   provenance,
 *   idMapping
 * });
 * 
 * const titleProvenance = getProvenance(title.id, 'study_title');
 * if (titleProvenance) {
 *   return <ProvenanceInline provenance={titleProvenance} />;
 * }
 * ```
 */
export function useEntityProvenance({
  provenance,
  idMapping,
}: UseEntityProvenanceOptions): UseEntityProvenanceResult {
  // Create reverse mapping (UUID -> pre-UUID)
  const reverseMapping = useMemo<ReverseIdMapping>(() => {
    if (!idMapping) return {};
    return createReverseMapping(idMapping);
  }, [idMapping]);
  
  // Get provenance for a USDM entity by UUID
  const getProvenance = useMemo(
    () => (entityId: string, entityType?: string) => {
      return findProvenanceByUuid(
        provenance,
        entityId,
        reverseMapping,
        entityType
      );
    },
    [provenance, reverseMapping]
  );
  
  // Get provenance by type and index (fallback)
  const getProvenanceByIndex = useMemo(
    () => (entityType: string, index: number) => {
      return findProvenanceByTypeAndIndex(provenance, entityType, index);
    },
    [provenance]
  );
  
  // Check if provenance exists
  const hasProvenance = useMemo(
    () => (entityId: string, entityType?: string) => {
      return getProvenance(entityId, entityType) !== null;
    },
    [getProvenance]
  );
  
  // Get all entities with provenance for a type
  const getEntitiesWithProvenance = useMemo(
    () => (entityType: string) => {
      if (!provenance?.entities) return [];
      
      const entityMap = (provenance.entities as any)[entityType];
      if (!entityMap) return [];
      
      return Object.keys(entityMap);
    },
    [provenance]
  );
  
  return {
    getProvenance,
    getProvenanceByIndex,
    hasProvenance,
    getEntitiesWithProvenance,
  };
}
