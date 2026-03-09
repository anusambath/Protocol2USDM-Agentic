import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs/promises';
import path from 'path';

/**
 * GET /api/protocols/[id]/provenance
 * 
 * Returns the provenance.json file for a protocol
 */
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const protocolId = params.id;
    
    // Construct path to {protocol_id}_provenance.json
    const outputDir = path.join(process.cwd(), '..', 'output', protocolId);
    
    // Extract the protocol name from the full ID (e.g., "Alexion_NCT04573309_Wilsons" from "Alexion_NCT04573309_Wilsons_20260306_220032")
    const protocolName = protocolId.split('_').slice(0, -2).join('_');
    const provenancePath = path.join(outputDir, `${protocolName}_provenance.json`);
    
    // Check if file exists
    try {
      await fs.access(provenancePath);
    } catch {
      return NextResponse.json(
        { error: 'Provenance data not found' },
        { status: 404 }
      );
    }
    
    // Read and parse provenance file
    const content = await fs.readFile(provenancePath, 'utf-8');
    const rawProvenance = JSON.parse(content);
    
    // Transform from records array to entities structure
    const provenanceData = transformProvenanceData(rawProvenance);
    
    return NextResponse.json(provenanceData);
  } catch (error) {
    console.error('Error loading provenance data:', error);
    return NextResponse.json(
      { error: 'Failed to load provenance data' },
      { status: 500 }
    );
  }
}

/**
 * Transform provenance from records array format to entities structure
 * 
 * Input format (from Python backend):
 * {
 *   "generated_at": "...",
 *   "summary": {...},
 *   "records": [
 *     {
 *       "entity_id": "title_1",
 *       "entity_type": "study_title",
 *       "source_agent_id": "metadata_agent",
 *       "confidence_score": 0.72,
 *       "source_pages": [0, 1, 2],
 *       "model_used": "gemini-2.5-flash",
 *       "source_type": "text",
 *       "extraction_timestamp": "...",
 *       ...
 *     }
 *   ]
 * }
 * 
 * Output format (for frontend):
 * {
 *   "entities": {
 *     "study_title": {
 *       "title_1": {
 *         "source": "text",
 *         "confidence": 0.72,
 *         "pageRefs": [0, 1, 2],
 *         "agent": "metadata_agent",
 *         "model": "gemini-2.5-flash",
 *         "timestamp": "..."
 *       }
 *     }
 *   },
 *   "cells": {},
 *   "cellPageRefs": {},
 *   ...
 * }
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
  
  // Add SOA cell provenance if present (merged by provenance agent)
  if (rawProvenance.cells) {
    Object.assign(cells, rawProvenance.cells);
  }
  
  // Add cell page references if present
  if (rawProvenance.cellPageRefs) {
    Object.assign(cellPageRefs, rawProvenance.cellPageRefs);
  }
  
  return {
    entities,
    cells,
    cellPageRefs,
    cellFootnotes: rawProvenance.cellFootnotes || {},
    // Include summary for debugging
    _summary: rawProvenance.summary,
  };
}
