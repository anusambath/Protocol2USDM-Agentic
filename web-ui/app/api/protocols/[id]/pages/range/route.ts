import { NextResponse } from 'next/server';

/**
 * GET /api/protocols/[id]/pages/range?start=1&end=3
 * 
 * Returns URLs for a range of protocol pages.
 * This is an optimization endpoint to avoid multiple individual requests.
 */
export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const { searchParams } = new URL(request.url);
  
  const startParam = searchParams.get('start');
  const endParam = searchParams.get('end');

  // Validate parameters
  if (!startParam || !endParam) {
    return NextResponse.json(
      { error: 'Missing start or end parameter' },
      { status: 400 }
    );
  }

  const start = parseInt(startParam);
  const end = parseInt(endParam);

  if (isNaN(start) || isNaN(end) || start < 1 || end < start) {
    return NextResponse.json(
      { error: 'Invalid page range' },
      { status: 400 }
    );
  }

  // Limit range to prevent abuse
  if (end - start > 50) {
    return NextResponse.json(
      { error: 'Page range too large (max 50 pages)' },
      { status: 400 }
    );
  }

  // Generate URLs for each page in range
  const pages = [];
  for (let pageNum = start; pageNum <= end; pageNum++) {
    pages.push({
      pageNum,
      url: `/api/protocols/${id}/pages/${pageNum}`,
    });
  }

  return NextResponse.json({ pages });
}
