import { NextResponse } from 'next/server';
import { promises as fs } from 'fs';
import path from 'path';

const OUTPUT_DIR = process.env.PROTOCOL_OUTPUT_DIR || path.join(process.cwd(), '..', 'output');

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const protocolDir = path.join(OUTPUT_DIR, id);

  try {
    // Check if protocol directory exists
    await fs.access(protocolDir);

    // List all image files in the protocol directory root
    const files = await fs.readdir(protocolDir);
    const imageFiles = files
      .filter(f => /^soa_page_\d+\.(png|jpg|jpeg|gif|webp)$/i.test(f))
      .sort((a, b) => {
        // Sort by page number
        const numA = parseInt(a.match(/soa_page_(\d+)/i)?.[1] || '0');
        const numB = parseInt(b.match(/soa_page_(\d+)/i)?.[1] || '0');
        return numA - numB;
      });

    const images = imageFiles.map(filename => {
      // Extract page number from filename like "soa_page_011.png"
      const pageMatch = filename.match(/page[_-]?(\d+)/i);
      const page = pageMatch ? parseInt(pageMatch[1]) : undefined;

      return {
        filename,
        url: `/api/protocols/${id}/images/${filename}`,
        page,
        name: filename.replace(/\.[^.]+$/, ''),
      };
    });

    return NextResponse.json({ images });
  } catch {
    // Protocol directory not found or no images
    return NextResponse.json({ images: [] });
  }
}
