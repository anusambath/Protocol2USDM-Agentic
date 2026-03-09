'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { Loader2, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Workbench } from '@/components/workbench/Workbench';
import { useProtocolStore } from '@/stores/protocolStore';
import { useOverlayStore } from '@/stores/overlayStore';
import { ProvenanceDataExtended } from '@/lib/provenance/types';

export default function ProtocolDetailPage() {
  const params = useParams();
  const protocolId = params.id as string;
  
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [provenance, setProvenance] = useState<ProvenanceDataExtended | null>(null);
  const [idMapping, setIdMapping] = useState<Record<string, string> | null>(null);
  const [intermediateFiles, setIntermediateFiles] = useState<Record<string, unknown> | null>(null);

  const { setProtocol, setProvenance: setStoreProvenance, usdm } = useProtocolStore();
  const { loadOverlays } = useOverlayStore();

  // Load protocol data
  useEffect(() => {
    async function loadProtocol() {
      setIsLoading(true);
      setError(null);

      try {
        // Load USDM
        const usdmRes = await fetch(`/api/protocols/${protocolId}/usdm`);
        if (!usdmRes.ok) throw new Error('Failed to load protocol');
        const { usdm, revision, provenance: provData, idMapping: idMap, intermediateFiles: intFiles } = await usdmRes.json();
        
        setProtocol(protocolId, usdm, revision);
        setProvenance(provData);
        setStoreProvenance(provData); // Also store in protocol store
        setIdMapping(idMap);
        setIntermediateFiles(intFiles);

        // Debug: Log provenance data structure
        if (provData) {
          console.log('=== PROVENANCE DATA LOADED ===');
          console.log('Provenance structure:', {
            hasEntities: !!provData.entities,
            entityTypes: provData.entities ? Object.keys(provData.entities) : [],
            hasCells: !!provData.cells,
            cellCount: provData.cells ? Object.keys(provData.cells).length : 0,
            hasCellPageRefs: !!provData.cellPageRefs,
            cellPageRefCount: provData.cellPageRefs ? Object.keys(provData.cellPageRefs).length : 0,
          });
          
          // Log entity counts by type
          if (provData.entities) {
            console.log('Entity counts by type:');
            for (const [type, entities] of Object.entries(provData.entities)) {
              if (entities) {
                console.log(`  ${type}: ${Object.keys(entities).length} entities`);
                // Log first few entity IDs as examples
                const entityIds = Object.keys(entities).slice(0, 3);
                if (entityIds.length > 0) {
                  console.log(`    Examples: ${entityIds.join(', ')}`);
                }
              }
            }
          }
          
          // Log sample cell provenance
          if (provData.cells) {
            const cellKeys = Object.keys(provData.cells).slice(0, 3);
            if (cellKeys.length > 0) {
              console.log('Sample cell provenance keys:', cellKeys);
            }
          }
          
          console.log('Full provenance data:', provData);
          console.log('==============================');
        } else {
          console.warn('No provenance data available for this protocol');
        }

        // Load overlays
        const [publishedRes, draftRes] = await Promise.all([
          fetch(`/api/protocols/${protocolId}/overlay/published`),
          fetch(`/api/protocols/${protocolId}/overlay/draft`),
        ]);

        const published = publishedRes.ok ? await publishedRes.json() : null;
        const draftOverlay = draftRes.ok ? await draftRes.json() : null;

        loadOverlays(protocolId, revision, published, draftOverlay);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setIsLoading(false);
      }
    }

    loadProtocol();
  }, [protocolId, setProtocol, loadOverlays]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="max-w-md">
          <CardContent className="pt-6 text-center">
            <AlertCircle className="h-12 w-12 mx-auto mb-4 text-destructive" />
            <h2 className="text-lg font-semibold mb-2">Error Loading Protocol</h2>
            <p className="text-muted-foreground mb-4">{error}</p>
            <Link href="/protocols">
              <Button>Back to Protocols</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <Workbench
      protocolId={protocolId}
      usdm={usdm as Record<string, unknown>}
      provenance={provenance}
      idMapping={idMapping}
      intermediateFiles={intermediateFiles}
    />
  );
}
