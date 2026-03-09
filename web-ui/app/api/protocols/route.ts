import { NextResponse } from 'next/server';
import fs from 'fs/promises';
import path from 'path';

// Configure the output directory path
const OUTPUT_DIR = process.env.PROTOCOL_OUTPUT_DIR ||
  path.join(process.cwd(), '..', 'output');

// Max ms to spend reading a single USDM file before giving up
const FILE_READ_TIMEOUT_MS = 5000;

interface ProtocolSummary {
  id: string;
  name: string;
  usdmVersion: string;
  generatedAt: string;
  activityCount: number;
  encounterCount: number;
}

async function readWithTimeout(filePath: string, timeoutMs: number): Promise<string> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(
      () => reject(new Error(`Timed out reading ${filePath}`)),
      timeoutMs
    );
    fs.readFile(filePath, 'utf-8')
      .then((content) => { clearTimeout(timer); resolve(content); })
      .catch((err) => { clearTimeout(timer); reject(err); });
  });
}

async function processDirectory(
  dirName: string
): Promise<ProtocolSummary | null> {
  const protocolDir = path.join(OUTPUT_DIR, dirName);

  let usdmPath: string | null = null;
  try {
    const files = await fs.readdir(protocolDir);
    const usdmFile =
      files.find((f) => f.endsWith('_usdm.json')) ||
      files.find((f) => f === 'protocol_usdm.json');
    if (usdmFile) usdmPath = path.join(protocolDir, usdmFile);
  } catch {
    return null;
  }

  if (!usdmPath) return null;

  try {
    const content = await readWithTimeout(usdmPath, FILE_READ_TIMEOUT_MS);
    const usdm = JSON.parse(content);
    const studyDesign = usdm.study?.versions?.[0]?.studyDesigns?.[0];

    return {
      id: dirName,
      name: dirName,
      usdmVersion: usdm.usdmVersion || '4.0',
      generatedAt: usdm.generatedAt || new Date().toISOString(),
      activityCount: studyDesign?.activities?.length || 0,
      encounterCount: studyDesign?.encounters?.length || 0,
    };
  } catch {
    return null;
  }
}

export async function GET() {
  try {
    const entries = await fs.readdir(OUTPUT_DIR, { withFileTypes: true });
    const dirs = entries.filter((e) => e.isDirectory()).map((e) => e.name);

    // Process all directories in parallel so slow/syncing files don't block each other
    const results = await Promise.allSettled(dirs.map(processDirectory));

    const protocols: ProtocolSummary[] = results
      .filter(
        (r): r is PromiseFulfilledResult<ProtocolSummary> =>
          r.status === 'fulfilled' && r.value !== null
      )
      .map((r) => r.value);

    protocols.sort(
      (a, b) =>
        new Date(b.generatedAt).getTime() - new Date(a.generatedAt).getTime()
    );

    return NextResponse.json({ protocols });
  } catch (error) {
    console.error('Error loading protocols:', error);
    return NextResponse.json(
      { error: 'Failed to load protocols', protocols: [] },
      { status: 500 }
    );
  }
}
