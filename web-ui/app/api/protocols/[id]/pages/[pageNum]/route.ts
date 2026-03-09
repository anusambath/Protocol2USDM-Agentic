import { NextResponse } from 'next/server';
import { promises as fs } from 'fs';
import path from 'path';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

const OUTPUT_DIR = process.env.PROTOCOL_OUTPUT_DIR || path.join(process.cwd(), '..', 'output');
const CACHE_DIR = process.env.PAGE_CACHE_DIR || path.join(process.cwd(), '..', 'cache', 'protocol-pages');
const DPI = 150;

/**
 * GET /api/protocols/[id]/pages/[pageNum]
 * 
 * Returns a protocol page as a PNG image.
 * Implements caching strategy: check cache first, render if needed.
 */
export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string; pageNum: string }> }
) {
  const { id, pageNum } = await params;
  const pageNumber = parseInt(pageNum);

  // Validate page number
  if (isNaN(pageNumber) || pageNumber < 1) {
    return NextResponse.json(
      { error: 'Invalid page number' },
      { status: 400 }
    );
  }

  try {
    // Check if protocol PDF exists
    const protocolDir = path.join(OUTPUT_DIR, id);
    const files = await fs.readdir(protocolDir);
    const pdfFile = files.find(f => f.endsWith('.pdf'));
    
    if (!pdfFile) {
      return NextResponse.json(
        { error: 'Protocol file not found' },
        { status: 404 }
      );
    }

    const pdfPath = path.join(protocolDir, pdfFile);

    // Check cache first
    const cacheFilePath = path.join(CACHE_DIR, id, `page-${pageNumber.toString().padStart(3, '0')}.png`);
    
    try {
      await fs.access(cacheFilePath);
      // Cache hit - return cached image
      const imageBuffer = await fs.readFile(cacheFilePath);
      
      return new NextResponse(imageBuffer, {
        headers: {
          'Content-Type': 'image/png',
          'Cache-Control': 'public, max-age=86400, immutable', // 24 hours
        },
      });
    } catch {
      // Cache miss - need to render
    }

    // Render page using Python script
    const renderResult = await renderPDFPage(pdfPath, pageNumber, cacheFilePath);
    
    if (!renderResult.success) {
      return NextResponse.json(
        { error: renderResult.error || 'Failed to render PDF page' },
        { status: 500 }
      );
    }

    // Read and return the rendered image
    const imageBuffer = await fs.readFile(cacheFilePath);
    
    return new NextResponse(imageBuffer, {
      headers: {
        'Content-Type': 'image/png',
        'Cache-Control': 'public, max-age=86400, immutable',
      },
    });

  } catch (error) {
    console.error('Error rendering protocol page:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

/**
 * Render a PDF page to PNG using Python/PyMuPDF
 */
async function renderPDFPage(
  pdfPath: string,
  pageNum: number,
  outputPath: string
): Promise<{ success: boolean; error?: string }> {
  try {
    // Ensure cache directory exists
    await fs.mkdir(path.dirname(outputPath), { recursive: true });

    // Python script to render PDF page
    const pythonScript = `
import sys
import fitz  # PyMuPDF

try:
    pdf_path = sys.argv[1]
    page_num = int(sys.argv[2]) - 1  # Convert to 0-indexed
    output_path = sys.argv[3]
    dpi = ${DPI}
    
    doc = fitz.open(pdf_path)
    
    if page_num < 0 or page_num >= len(doc):
        print(f"Page number out of range (1-{len(doc)})", file=sys.stderr)
        sys.exit(1)
    
    page = doc[page_num]
    
    # Render at specified DPI
    zoom = dpi / 72  # 72 DPI is default
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    
    # Save as PNG
    pix.save(output_path)
    
    doc.close()
    print("success")
    
except Exception as e:
    print(f"Error: {str(e)}", file=sys.stderr)
    sys.exit(1)
`;

    // Write Python script to temp file
    const scriptPath = path.join(path.dirname(outputPath), '_render_page.py');
    await fs.writeFile(scriptPath, pythonScript);

    // Execute Python script with timeout
    const { stdout, stderr } = await execAsync(
      `python "${scriptPath}" "${pdfPath}" ${pageNum} "${outputPath}"`,
      { timeout: 30000 } // 30 second timeout
    );

    // Clean up script file
    await fs.unlink(scriptPath).catch(() => {});

    if (stdout.includes('success')) {
      return { success: true };
    } else {
      return { success: false, error: stderr || 'Unknown error' };
    }

  } catch (error: any) {
    return { 
      success: false, 
      error: error.message || 'Failed to execute rendering script' 
    };
  }
}
