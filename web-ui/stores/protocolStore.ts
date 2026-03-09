import { create } from 'zustand';
import { ProvenanceDataExtended } from '@/lib/provenance/types';

interface ProtocolMetadata {
  usdmVersion?: string;
  generatedAt?: string;
}

// USDM v4.0 entity types used by adapters and components
export interface USDMActivity {
  id?: string;
  name?: string;
  label?: string;
  activityGroupId?: string;
  biomedicalConceptIds?: string[];
  [key: string]: unknown;
}

export interface USDMActivityGroup {
  id?: string;
  name?: string;
  label?: string;
  activityIds?: string[];
  [key: string]: unknown;
}

export interface USDMEncounter {
  id?: string;
  name?: string;
  label?: string;
  epochId?: string;
  [key: string]: unknown;
}

export interface USDMEpoch {
  id?: string;
  name?: string;
  label?: string;
  [key: string]: unknown;
}

export interface USDMTiming {
  id?: string;
  type?: string;
  value?: number | string;
  unit?: string;
  [key: string]: unknown;
}

export interface USDMScheduledInstance {
  id?: string;
  activityId?: string;
  encounterId?: string;
  timelineEntryId?: string;
  timelineExitId?: string;
  timing?: USDMTiming[];
  [key: string]: unknown;
}

export interface USDMScheduleTimeline {
  id?: string;
  name?: string;
  scheduledInstances?: USDMScheduledInstance[];
  [key: string]: unknown;
}

export interface USDMStudyDesign {
  id?: string;
  name?: string;
  arms?: unknown[];
  epochs?: USDMEpoch[];
  encounters?: USDMEncounter[];
  activities?: USDMActivity[];
  activityGroups?: USDMActivityGroup[];
  activityTimepoints?: unknown[];
  studyCells?: unknown[];
  objectives?: unknown[];
  endpoints?: unknown[];
  eligibilityCriteria?: unknown[];
  scheduleTimelines?: USDMScheduleTimeline[];
  [key: string]: unknown;
}

interface ProtocolStore {
  protocolId: string | null;
  usdm: Record<string, unknown> | null;
  metadata: ProtocolMetadata | null;
  revision: string | null;
  provenance: ProvenanceDataExtended | null;
  setProtocol: (id: string, usdm: Record<string, unknown>, revision: string) => void;
  setProvenance: (provenance: ProvenanceDataExtended | null) => void;
  clearProtocol: () => void;
}

export const useProtocolStore = create<ProtocolStore>((set) => ({
  protocolId: null,
  usdm: null,
  metadata: null,
  revision: null,
  provenance: null,

  setProtocol: (id, usdm, revision) => {
    const metadata: ProtocolMetadata = {
      usdmVersion: usdm.usdmVersion as string | undefined,
      generatedAt: usdm.generatedAt as string | undefined,
    };
    set({ protocolId: id, usdm, metadata, revision });
  },

  setProvenance: (provenance) => {
    set({ provenance });
  },

  clearProtocol: () =>
    set({ protocolId: null, usdm: null, metadata: null, revision: null, provenance: null }),
}));

// Selector: navigate usdm.study.versions[0].studyDesigns[0]
export function selectStudyDesign(state: ProtocolStore): USDMStudyDesign | null {
  const usdm = state.usdm as Record<string, unknown> | null;
  const study = usdm?.study as Record<string, unknown> | undefined;
  const versions = study?.versions as Record<string, unknown>[] | undefined;
  const studyDesigns = versions?.[0]?.studyDesigns as USDMStudyDesign[] | undefined;
  return studyDesigns?.[0] ?? null;
}
