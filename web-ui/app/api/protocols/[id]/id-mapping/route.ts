import { NextRequest, NextResponse } from 'next/server';
import path from 'path';
import fs from 'fs/promises';

/**
 * GET /api/protocols/[id]/id-mapping
 * 
 * Returns the ID mapping file for a protocol
 * Maps pre-UUID IDs to UUID IDs
 */
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const protocolId = params.id;
    
    // Construct path to id_mapping.json
    const outputDir = process.env.OUTPUT_DIR || path.join(process.cwd(), '..', 'output');
    const idMappingPath = path.join(outputDir, protocolId, 'id_mapping.json');
    
    // Check if file exists
    try {
      await fs.access(idMappingPath);
    } catch {
      return NextResponse.json(
        { error: 'ID mapping file not found' },
        { status: 404 }
      );
    }
    
    // Read and parse the file
    const fileContent = await fs.readFile(idMappingPath, 'utf-8');
    const idMapping = JSON.parse(fileContent);
    
    return NextResponse.json(idMapping);
  } catch (error) {
    console.error('Error loading ID mapping:', error);
    return NextResponse.json(
      { error: 'Failed to load ID mapping' },
      { status: 500 }
    );
  }
}
