import { NextResponse } from 'next/server';
import fs from 'fs/promises';
import path from 'path';
import crypto from 'crypto';

const OUTPUT_DIR = process.env.PROTOCOL_OUTPUT_DIR || 
  path.join(process.cwd(), '..', 'output');

// Extract footnotes from USDM extension attributes
function extractFootnotesFromUSDM(usdm: Record<string, unknown>): string[] {
  const footnotes: string[] = [];
  const footnoteMap = new Map<string, string>(); // footnoteId -> text
  
  try {
    // Navigate to studyDesign extensions
    const study = usdm.study as Record<string, unknown> | undefined;
    const versions = (study?.versions as unknown[]) ?? [];
    const version = versions[0] as Record<string, unknown> | undefined;
    const studyDesigns = (version?.studyDesigns as Record<string, unknown>[]) ?? [];
    const studyDesign = studyDesigns[0];
    
    if (!studyDesign) return footnotes;
    
    // Look for extensionAttributes containing footnoteConditions
    const extensions = (studyDesign.extensionAttributes as Array<{
      url?: string;
      valueString?: string;
    }>) ?? [];
    
    for (const ext of extensions) {
      if (ext.url?.includes('footnoteConditions') && ext.valueString) {
        try {
          const conditions = JSON.parse(ext.valueString) as Array<{
            footnoteId?: string;
            text?: string;
          }>;
          
          // Build unique footnotes by footnoteId
          for (const cond of conditions) {
            if (cond.footnoteId && cond.text && !footnoteMap.has(cond.footnoteId)) {
              footnoteMap.set(cond.footnoteId, cond.text);
            }
          }
        } catch {
          // Skip malformed JSON
        }
      }
    }
    
    // Sort footnotes by their ID (numeric or alphabetic)
    const sortedEntries = Array.from(footnoteMap.entries()).sort((a, b) => {
      const aNum = parseFloat(a[0].replace(/[^\d.]/g, ''));
      const bNum = parseFloat(b[0].replace(/[^\d.]/g, ''));
      if (!isNaN(aNum) && !isNaN(bNum)) return aNum - bNum;
      return a[0].localeCompare(b[0]);
    });
    
    // Format as "id: text"
    for (const [id, text] of sortedEntries) {
      footnotes.push(`${id} ${text}`);
    }
  } catch {
    // Return empty array on error
  }
  
  return footnotes;
}

// Helper to safely load JSON file
async function loadJsonFile(filePath: string): Promise<unknown | null> {
  try {
    const content = await fs.readFile(filePath, 'utf-8');
    return JSON.parse(content);
  } catch {
    return null;
  }
}

/**
 * Transform provenance from records array format to entities structure
 */
function transformProvenanceData(rawProvenance: any): any {
  const entities: Record<string, Record<string, any>> = {};
  const cells: Record<string, string> = {};
  const cellPageRefs: Record<string, number[]> = {};
  
  // Process each record
  for (const record of rawProvenance.records || []) {
    const entityType = record.entity_type;
    const entityId = record.entity_id;
    
    // Initialize entity type map if needed
    if (!entities[entityType]) {
      entities[entityType] = {};
    }
    
    // Add entity provenance
    // Convert 0-indexed source_pages to 1-indexed pageRefs for display
    const pageRefs = (record.source_pages || []).map((page: number) => page + 1);
    
    entities[entityType][entityId] = {
      source: record.source_type || 'text',
      confidence: record.confidence_score,
      pageRefs: pageRefs,
      agent: record.source_agent_id,
      model: record.model_used,
      timestamp: record.extraction_timestamp,
    };
  }
  
  // Preserve SOA cell provenance from raw data (merged by provenance agent)
  if (rawProvenance.cells) {
    Object.assign(cells, rawProvenance.cells);
  }
  
  // Preserve cell page references
  if (rawProvenance.cellPageRefs) {
    Object.assign(cellPageRefs, rawProvenance.cellPageRefs);
  }
  
  return {
    entities,
    cells,
    cellPageRefs,
    cellFootnotes: rawProvenance.cellFootnotes || {},
    // Preserve records for downstream derivation (e.g., cellPageRefs)
    records: rawProvenance.records || [],
    // Include summary for debugging
    _summary: rawProvenance.summary,
  };
}


// Derive cell-level provenance ("activityId|encounterId" -> CellSource) from:
//   - USDM scheduleTimelines instances (activityIds + encounterId in UUID space)
//   - provenance records (entity_id in pre-UUID space, source_type)
//   - id_mapping (pre-UUID id -> UUID)
function deriveProvenanceCells(
  usdm: Record<string, unknown>,
  provenanceRecords: Array<{ 
    entity_id: string; 
    entity_type: string; 
    source_type: string;
    source_pages?: number[];
  }>,
  idMapping: Record<string, string>
): { 
  cells: Record<string, string>;
  cellPageRefs: Record<string, number[]>;
} {
  const cells: Record<string, string> = {};
  const cellPageRefs: Record<string, number[]> = {};

  // Build reverse map: UUID -> original_id (for looking up provenance source)
  const uuidToOriginal: Record<string, string> = {};
  for (const [orig, uuid] of Object.entries(idMapping)) {
    uuidToOriginal[uuid] = orig;
  }
  
  console.log('[deriveProvenanceCells] ID mapping sample:', {
    totalMappings: Object.keys(idMapping).length,
    sampleOrigToUuid: Object.entries(idMapping).slice(0, 5),
    sampleUuidToOrig: Object.entries(uuidToOriginal).slice(0, 5)
  });

  // Build provenance lookup: original_id -> source_type and source_pages
  const sourceByOrigId: Record<string, string> = {};
  const pagesByOrigId: Record<string, number[]> = {};
  let recordsWithPages = 0;
  for (const rec of provenanceRecords) {
    if (rec.entity_type === 'scheduled_instance') {
      // Map source_type to CellSource values the UI understands
      const src = rec.source_type === 'vision' ? 'vision'
                : rec.source_type === 'text'   ? 'text'
                : rec.source_type === 'both'   ? 'both'
                : 'needs_review';
      sourceByOrigId[rec.entity_id] = src;
      
      // Store page references if available (convert 0-indexed to 1-indexed)
      if (rec.source_pages && rec.source_pages.length > 0) {
        pagesByOrigId[rec.entity_id] = rec.source_pages.map((page: number) => page + 1);
        recordsWithPages++;
      }
    }
  }
  
  console.log('[deriveProvenanceCells] Built lookups:', {
    sourceByOrigIdCount: Object.keys(sourceByOrigId).length,
    pagesByOrigIdCount: Object.keys(pagesByOrigId).length,
    recordsWithPages,
    samplePages: Object.entries(pagesByOrigId).slice(0, 3)
  });

  // Walk all ScheduledActivityInstance objects in the USDM
  let instancesProcessed = 0;
  let instancesMatched = 0;
  try {
    const study = usdm.study as Record<string, unknown>;
    const versions = (study?.versions as Record<string, unknown>[]) ?? [];
    const version = versions[0] ?? {};
    const designs = (version.studyDesigns as Record<string, unknown>[]) ?? [];
    const design = designs[0] ?? {};
    const timelines = (design.scheduleTimelines as Record<string, unknown>[]) ?? [];

    for (const tl of timelines) {
      const instances = (tl.instances as Record<string, unknown>[]) ?? [];
      for (const inst of instances) {
        if (inst.instanceType !== 'ScheduledActivityInstance') continue;
        instancesProcessed++;
        
        const instUuid = inst.id as string;
        const encounterId = inst.encounterId as string;
        const activityIds = (inst.activityIds as string[]) ?? [];

        if (!encounterId || activityIds.length === 0) continue;

        // Determine source: look up via UUID -> original_id -> provenance record
        const origId = uuidToOriginal[instUuid];
        const source = (origId && sourceByOrigId[origId]) ?? 'both';
        const pages = (origId && pagesByOrigId[origId]) ?? [];
        
        if (instancesProcessed <= 3) {
          console.log(`[deriveProvenanceCells] Instance ${instancesProcessed}:`, {
            instUuid,
            origId,
            hasOrigId: !!origId,
            hasSource: !!sourceByOrigId[origId],
            hasPages: !!pagesByOrigId[origId],
            pages
          });
        }
        
        if (origId && pagesByOrigId[origId]) {
          instancesMatched++;
        }

        for (const actId of activityIds) {
          const cellKey = `${actId}|${encounterId}`;
          cells[cellKey] = source;
          if (pages.length > 0) {
            cellPageRefs[cellKey] = pages;
          }
        }
      }
    }
    
    console.log('[deriveProvenanceCells] Processed instances:', {
      instancesProcessed,
      instancesMatched,
      cellsCreated: Object.keys(cells).length,
      cellPageRefsCreated: Object.keys(cellPageRefs).length
    });
  } catch (err) {
    console.error('[deriveProvenanceCells] Error:', err);
    // Return whatever cells we managed to build
  }

  return { cells, cellPageRefs };
}

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: protocolId } = await params;
    const protocolDir = path.join(OUTPUT_DIR, protocolId);
    
    // Find the USDM file: try {protocol_id}_usdm.json pattern first,
    // then fall back to protocol_usdm.json (legacy)
    const files = await fs.readdir(protocolDir);
    const usdmFile = files.find(f => f.endsWith('_usdm.json'))
      || files.find(f => f === 'protocol_usdm.json');
    
    if (!usdmFile) {
      return NextResponse.json(
        { error: 'USDM file not found in protocol directory' },
        { status: 404 }
      );
    }
    
    const usdmPath = path.join(protocolDir, usdmFile);
    
    // Read USDM file
    const content = await fs.readFile(usdmPath, 'utf-8');
    const usdm = JSON.parse(content);
    
    // Calculate revision hash
    const revision = crypto
      .createHash('sha256')
      .update(content)
      .digest('hex')
      .slice(0, 12);
    
    // Load provenance: try exact match first, then name-based match, then fallback
    // protocolId includes timestamp (e.g., "Alexion_NCT04573309_Wilsons_20260308_212724")
    // but provenance file uses base name (e.g., "Alexion_NCT04573309_Wilsons_provenance.json")
    const protocolBaseName = protocolId.replace(/_\d{8}_\d{6}$/, '');
    const provFile = files.find(f => f === `${protocolId}_provenance.json`)
      || files.find(f => f === `${protocolBaseName}_provenance.json`)
      || files.find(f => f.endsWith('_provenance.json') && !f.match(/^\d+_/))
      || files.find(f => f === 'protocol_usdm_provenance.json');
    let provenance = provFile 
      ? await loadJsonFile(path.join(protocolDir, provFile)) as Record<string, unknown> | null
      : null;
    
    // Transform provenance from records array to entities structure if needed
    if (provenance && Array.isArray((provenance as any).records)) {
      provenance = transformProvenanceData(provenance as any);
    }
    
    // Extract footnotes from USDM extension attributes and add to provenance
    const footnotes = extractFootnotesFromUSDM(usdm);
    
    // Load id_mapping for pre-UUID -> UUID resolution
    const idMapping = (await loadJsonFile(path.join(protocolDir, 'id_mapping.json')) ?? {}) as Record<string, string>;

    // Always ensure provenance exists and has footnotes
    if (!provenance) {
      provenance = {};
    }
    if (footnotes.length > 0) {
      provenance.footnotes = footnotes;
    }

    // Derive cell-level provenance if not already present (new format: cells map)
    // Also derive cellPageRefs if missing, even when cells exist
    const hasCells = provenance.cells && Object.keys(provenance.cells as Record<string, unknown>).length > 0;
    const hasCellPageRefs = provenance.cellPageRefs && Object.keys(provenance.cellPageRefs as Record<string, unknown>).length > 0;
    if (!hasCells || !hasCellPageRefs) {
      const provenanceRecords = ((provenance as Record<string, unknown>).records as Array<{
        entity_id: string; 
        entity_type: string; 
        source_type: string;
        source_pages?: number[];
      }>) ?? [];
      
      console.log('[USDM API] Deriving cell provenance:', {
        hasCells: !!provenance.cells,
        hasCellPageRefs: !!provenance.cellPageRefs,
        recordsCount: provenanceRecords.length,
        scheduledInstanceCount: provenanceRecords.filter(r => r.entity_type === 'scheduled_instance').length,
        idMappingCount: Object.keys(idMapping).length
      });
      
      const { cells: derivedCells, cellPageRefs: derivedPageRefs } = deriveProvenanceCells(usdm, provenanceRecords, idMapping);
      
      console.log('[USDM API] Derived results:', {
        derivedCellsCount: Object.keys(derivedCells).length,
        derivedPageRefsCount: Object.keys(derivedPageRefs).length,
        samplePageRefs: Object.entries(derivedPageRefs).slice(0, 3)
      });
      
      // Only set cells if they don't exist
      if (!hasCells && Object.keys(derivedCells).length > 0) {
        (provenance as Record<string, unknown>).cells = derivedCells;
      }
      
      // Always set cellPageRefs if they were derived
      if (Object.keys(derivedPageRefs).length > 0) {
        (provenance as Record<string, unknown>).cellPageRefs = derivedPageRefs;
      }
    }
    
    // Load intermediate extraction files (new numbered format, with legacy fallback)
    const intermediateFiles = {
      eligibility: await loadJsonFile(path.join(protocolDir, '06_extraction_eligibility.json'))
        || await loadJsonFile(path.join(protocolDir, '3_eligibility_criteria.json')),
      amendments: await loadJsonFile(path.join(protocolDir, '13_extraction_advanced_entities.json'))
        || await loadJsonFile(path.join(protocolDir, '14_amendment_details.json')),
      scheduling: await loadJsonFile(path.join(protocolDir, '11_extraction_scheduling_logic.json'))
        || await loadJsonFile(path.join(protocolDir, '10_scheduling_logic.json')),
      executionModel: await loadJsonFile(path.join(protocolDir, '12_extraction_execution_model.json'))
        || await loadJsonFile(path.join(protocolDir, '11_execution_model.json')),
      soaProvenance: await loadJsonFile(path.join(protocolDir, '19_support_provenance.json'))
        || await loadJsonFile(path.join(protocolDir, '9_final_soa_provenance.json')),
    };
    
    // Strip records from provenance before sending to frontend (large payload, not needed by UI)
    if (provenance) {
      delete (provenance as Record<string, unknown>).records;
      delete (provenance as Record<string, unknown>)._summary;
    }
    
    return NextResponse.json({
      usdm,
      revision,
      provenance,
      idMapping, // Include ID mapping for UUID to pre-UUID resolution
      intermediateFiles,
      generatedAt: usdm.generatedAt,
    });
  } catch (error) {
    console.error('Error loading USDM:', error);
    return NextResponse.json(
      { error: 'Protocol not found' },
      { status: 404 }
    );
  }
}
