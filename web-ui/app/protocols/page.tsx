import Link from 'next/link';
import { FileText, Calendar, Tag, ArrowRight, Clock, Coins, AlertTriangle, Cpu } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import fs from 'fs/promises';
import path from 'path';

const OUTPUT_DIR =
  process.env.PROTOCOL_OUTPUT_DIR || path.join(process.cwd(), '..', 'output');

const FILE_READ_TIMEOUT_MS = 5000;

interface ResultJson {
  status: string;
  duration_seconds: number;
  total_tokens: number;
  total_api_calls: number;
  total_agents: number;
  succeeded_agents: number;
  failed_agents: { id: string; error: string }[];
  entity_count: number;
  models: {
    model: string;
    fast_model: string | null;
    vision_model: string | null;
  };
  started: string;
  finished: string;
}

interface ProtocolSummary {
  id: string;
  name: string;
  usdmVersion: string;
  generatedAt: string;
  activityCount: number;
  encounterCount: number;
  epochCount: number;
  // Enhanced fields from result.json
  duration?: number;
  totalTokens?: number;
  failedAgents?: { id: string; error: string }[];
  models?: {
    model: string;
    fastModel: string | null;
    visionModel: string | null;
  };
  status?: string;
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
      const year = dateStr.substring(0, 4);
      const month = dateStr.substring(4, 6);
      const day = dateStr.substring(6, 8);
      const hour = timeStr.substring(0, 2);
      const minute = timeStr.substring(2, 4);
      const second = timeStr.substring(4, 6);
      generatedAt = `${year}-${month}-${day}T${hour}:${minute}:${second}`;
    } else {
      if (usdm.generatedAt) {
        generatedAt = usdm.generatedAt;
      } else {
        const stats = await fs.stat(usdmPath);
        generatedAt = stats.mtime.toISOString();
      }
    }

    // Derive a readable protocol name from the folder name
    // Folder format: NCT12345_Sponsor_StudyId_Ver_YYYYMMDD_HHMMSS
    // Strip the trailing timestamp and replace underscores
    const cleanName = dirName
      .replace(/_\d{8}_\d{6}$/, '')  // remove timestamp suffix
      .replace(/_/g, ' ');           // underscores to spaces

    const summary: ProtocolSummary = {
      id: dirName,
      name: cleanName,
      usdmVersion: usdm.usdmVersion || '4.0',
      generatedAt,
      activityCount: studyDesign?.activities?.length || 0,
      encounterCount: studyDesign?.encounters?.length || 0,
      epochCount: studyDesign?.epochs?.length || 0,
    };

    // Read result.json for enhanced data
    const resultJsonPath = path.join(protocolDir, 'result.json');
    try {
      const resultContent = await readWithTimeout(resultJsonPath, FILE_READ_TIMEOUT_MS);
      const resultData: ResultJson = JSON.parse(resultContent);
      summary.duration = resultData.duration_seconds;
      summary.totalTokens = resultData.total_tokens;
      summary.failedAgents = resultData.failed_agents;
      summary.status = resultData.status;
      summary.models = {
        model: resultData.models.model,
        fastModel: resultData.models.fast_model,
        visionModel: resultData.models.vision_model,
      };
    } catch {
      // result.json not available — fall back to parsing result.md
      try {
        const mdPath = path.join(protocolDir, 'result.md');
        const mdContent = await readWithTimeout(mdPath, FILE_READ_TIMEOUT_MS);
        const durationMatch = mdContent.match(/\*\*Duration:\*\*\s*([\d.]+)s/);
        const tokensMatch = mdContent.match(/\| Total Tokens \| ([\d,]+) \|/);
        const modelMatch = mdContent.match(/\*\*Model:\*\*\s*(.+)/);
        const statusMatch = mdContent.match(/\*\*Status:\*\*\s*(\w+)/);
        if (durationMatch) summary.duration = parseFloat(durationMatch[1]);
        if (tokensMatch) summary.totalTokens = parseInt(tokensMatch[1].replace(/,/g, ''), 10);
        if (statusMatch) summary.status = statusMatch[1];
        if (modelMatch) {
          summary.models = { model: modelMatch[1].trim(), fastModel: null, visionModel: null };
        }
        // Parse failed agents from result.md
        const failedSection = mdContent.match(/## Failed Agents\n\n([\s\S]*?)(?=\n##|\n*$)/);
        if (failedSection) {
          const failedLines = failedSection[1].match(/- \*\*(.+?)\*\*: (.+)/g);
          if (failedLines) {
            summary.failedAgents = failedLines.map((line) => {
              const m = line.match(/- \*\*(.+?)\*\*: (.+)/);
              return { id: m?.[1] || 'unknown', error: m?.[2] || 'unknown' };
            });
          }
        }
      } catch {
        // No result data available at all
      }
    }

    return summary;
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

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds.toFixed(0)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}m ${secs}s`;
}

function formatTokens(tokens: number): string {
  if (tokens >= 1_000_000) return `${(tokens / 1_000_000).toFixed(1)}M`;
  if (tokens >= 1_000) return `${(tokens / 1_000).toFixed(0)}K`;
  return tokens.toLocaleString();
}

function shortenModelName(name: string): string {
  // Shorten common model names for display
  return name
    .replace('gemini-2.5-pro', 'gemini-2.5-pro')
    .replace('gemini-2.0-flash', 'gemini-2.0-flash')
    .replace('claude-opus-4-6', 'claude-opus-4.6')
    .replace('claude-sonnet-4-5', 'claude-sonnet-4.5');
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
  const formattedDateTime = new Date(protocol.generatedAt).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  });

  const hasFailures = protocol.failedAgents && protocol.failedAgents.length > 0;

  return (
    <Card className="hover:shadow-lg transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <FileText className="h-5 w-5 text-primary shrink-0" />
            <span className="break-words line-clamp-2" title={protocol.name}>{protocol.name}</span>
          </CardTitle>
          {protocol.status && (
            <Badge variant={protocol.status === 'SUCCESS' ? 'default' : 'destructive'} className="shrink-0 text-xs">
              {protocol.status}
            </Badge>
          )}
        </div>
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
      <CardContent className="pt-0">
        {/* Stats row */}
        <div className="grid grid-cols-3 gap-x-4 gap-y-1.5 text-sm text-muted-foreground mb-3">
          <span>{protocol.epochCount} epochs</span>
          <span>{protocol.encounterCount} encounters</span>
          <span>{protocol.activityCount} activities</span>
          {protocol.duration != null && (
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {formatDuration(protocol.duration)}
            </span>
          )}
          {protocol.totalTokens != null && (
            <span className="flex items-center gap-1">
              <Coins className="h-3 w-3" />
              {formatTokens(protocol.totalTokens)} tokens
            </span>
          )}
        </div>

        {/* Models */}
        {protocol.models && (
          <div className="mb-3">
            <div className="flex items-center gap-1 text-xs text-muted-foreground mb-1">
              <Cpu className="h-3 w-3" />
              <span>Models</span>
            </div>
            <div className="flex flex-wrap gap-1">
              <Badge variant="outline" className="text-xs font-normal">
                {shortenModelName(protocol.models.model)}
              </Badge>
              {protocol.models.fastModel && protocol.models.fastModel !== protocol.models.model && (
                <Badge variant="outline" className="text-xs font-normal">
                  fast: {shortenModelName(protocol.models.fastModel)}
                </Badge>
              )}
              {protocol.models.visionModel && protocol.models.visionModel !== protocol.models.model && (
                <Badge variant="outline" className="text-xs font-normal">
                  vision: {shortenModelName(protocol.models.visionModel)}
                </Badge>
              )}
            </div>
          </div>
        )}

        {/* Failed agents warning */}
        {hasFailures && (
          <div className="mb-3 p-2 bg-destructive/10 rounded-md">
            <div className="flex items-center gap-1 text-xs text-destructive font-medium mb-1">
              <AlertTriangle className="h-3 w-3" />
              {protocol.failedAgents!.length} failed agent{protocol.failedAgents!.length > 1 ? 's' : ''}
            </div>
            <div className="text-xs text-destructive/80">
              {protocol.failedAgents!.map((a) => a.id).join(', ')}
            </div>
          </div>
        )}

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
