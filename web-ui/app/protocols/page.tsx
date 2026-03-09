import Link from 'next/link';
import { FileText, Calendar, Tag, ArrowRight } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import fs from 'fs/promises';
import path from 'path';

const OUTPUT_DIR =
  process.env.PROTOCOL_OUTPUT_DIR || path.join(process.cwd(), '..', 'output');

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

async function processDirectory(dirName: string): Promise<ProtocolSummary | null> {
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

    // Extract timestamp from folder name (format: *_YYYYMMDD_HHMMSS)
    const timestampMatch = dirName.match(/_(\d{8})_(\d{6})$/);
    let generatedAt: string;
    if (timestampMatch) {
      const [, dateStr, timeStr] = timestampMatch;
      // Parse YYYYMMDD_HHMMSS to ISO format
      const year = dateStr.substring(0, 4);
      const month = dateStr.substring(4, 6);
      const day = dateStr.substring(6, 8);
      const hour = timeStr.substring(0, 2);
      const minute = timeStr.substring(2, 4);
      const second = timeStr.substring(4, 6);
      generatedAt = `${year}-${month}-${day}T${hour}:${minute}:${second}`;
    } else {
      // Fallback to USDM generatedAt or file modification time
      if (usdm.generatedAt) {
        generatedAt = usdm.generatedAt;
      } else {
        const stats = await fs.stat(usdmPath);
        generatedAt = stats.mtime.toISOString();
      }
    }

    return {
      id: dirName,
      name: dirName,
      usdmVersion: usdm.usdmVersion || '4.0',
      generatedAt,
      activityCount: studyDesign?.activities?.length || 0,
      encounterCount: studyDesign?.encounters?.length || 0,
    };
  } catch {
    return null;
  }
}

async function loadProtocols(): Promise<{ protocols: ProtocolSummary[]; error?: string }> {
  try {
    const entries = await fs.readdir(OUTPUT_DIR, { withFileTypes: true });
    const dirs = entries.filter((e) => e.isDirectory()).map((e) => e.name);

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

    return { protocols };
  } catch (err) {
    return {
      protocols: [],
      error: err instanceof Error ? err.message : 'Failed to load protocols',
    };
  }
}

export default async function ProtocolsPage() {
  const { protocols, error } = await loadProtocols();

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="border-b bg-white sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-primary flex items-center justify-center">
              <FileText className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold">Protocol2USDM</h1>
              <p className="text-xs text-muted-foreground">Protocol Browser</p>
            </div>
          </Link>
        </div>
      </header>

      {/* Content */}
      <main className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <h2 className="text-2xl font-bold mb-2">Available Protocols</h2>
          <p className="text-muted-foreground">
            Select a protocol to view its Schedule of Activities and timeline.
          </p>
        </div>

        {error && (
          <Card className="border-destructive">
            <CardContent className="py-6">
              <p className="text-destructive">{error}</p>
              <Link href="/protocols">
                <Button variant="outline" className="mt-4">
                  Retry
                </Button>
              </Link>
            </CardContent>
          </Card>
        )}

        {!error && protocols.length === 0 && (
          <Card>
            <CardContent className="py-12 text-center">
              <FileText className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
              <h3 className="text-lg font-semibold mb-2">No Protocols Found</h3>
              <p className="text-muted-foreground mb-4">
                Run the extraction pipeline to generate protocol USDM files.
              </p>
              <code className="block bg-muted p-4 rounded-lg text-sm text-left max-w-xl mx-auto">
                python run_extraction.py &quot;input/protocol.pdf&quot;
              </code>
            </CardContent>
          </Card>
        )}

        {!error && protocols.length > 0 && (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {protocols.map((protocol) => (
              <ProtocolCard key={protocol.id} protocol={protocol} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

function ProtocolCard({ protocol }: { protocol: ProtocolSummary }) {
  // Format the date and time for display
  const formattedDateTime = new Date(protocol.generatedAt).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true
  });

  return (
    <Card className="hover:shadow-lg transition-shadow">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-primary" />
          <span className="truncate">{protocol.name}</span>
        </CardTitle>
        <CardDescription className="flex items-center gap-4 text-xs">
          <span className="flex items-center gap-1">
            <Tag className="h-3 w-3" />
            USDM {protocol.usdmVersion}
          </span>
          <span className="flex items-center gap-1">
            <Calendar className="h-3 w-3" />
            {formattedDateTime}
          </span>
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-4 text-sm text-muted-foreground mb-4">
          <span>{protocol.activityCount} activities</span>
          <span>{protocol.encounterCount} encounters</span>
        </div>
        <Link href={`/protocols/${protocol.id}`}>
          <Button className="w-full">
            View Protocol
            <ArrowRight className="h-4 w-4 ml-2" />
          </Button>
        </Link>
      </CardContent>
    </Card>
  );
}
