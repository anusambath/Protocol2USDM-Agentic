import { create } from 'zustand';
import { type OverlayDoc, type OverlayPayload, createEmptyOverlay } from '@/lib/overlay/schema';

interface OverlayStore {
  protocolId: string | null;
  revision: string | null;
  published: OverlayDoc | null;
  draft: OverlayDoc | null;
  isDirty: boolean;
  needsReconciliation: boolean;

  loadOverlays: (
    protocolId: string,
    revision: string,
    published: OverlayDoc | null,
    draft: OverlayDoc | null
  ) => void;
  markClean: () => void;
  markDirty: () => void;
  promoteDraftToPublished: () => void;
  resetToPublished: () => void;
  updateDraftTableOrder: (
    rowOrder: string[] | undefined,
    columnOrder: string[] | undefined
  ) => void;
}

export const useOverlayStore = create<OverlayStore>((set, get) => ({
  protocolId: null,
  revision: null,
  published: null,
  draft: null,
  isDirty: false,
  needsReconciliation: false,

  loadOverlays: (protocolId, revision, published, draft) => {
    const resolvedDraft =
      draft ?? createEmptyOverlay(protocolId, revision, 'system');

    const needsReconciliation =
      published != null && published.usdmRevision !== revision;

    set({
      protocolId,
      revision,
      published,
      draft: resolvedDraft,
      isDirty: false,
      needsReconciliation,
    });
  },

  markClean: () => set({ isDirty: false }),

  markDirty: () => set({ isDirty: true }),

  promoteDraftToPublished: () => {
    const { draft } = get();
    if (!draft) return;
    set({
      published: { ...draft, status: 'published', updatedAt: new Date().toISOString() },
      isDirty: false,
      needsReconciliation: false,
    });
  },

  resetToPublished: () => {
    const { protocolId, revision, published } = get();
    if (!protocolId || !revision) return;
    const resetDraft: OverlayDoc = published
      ? { ...published, status: 'draft' }
      : createEmptyOverlay(protocolId, revision, 'system');
    set({ draft: resetDraft, isDirty: false });
  },

  updateDraftTableOrder: (rowOrder, columnOrder) => {
    const { draft } = get();
    if (!draft) return;
    set({
      draft: {
        ...draft,
        payload: {
          ...draft.payload,
          table: {
            ...draft.payload.table,
            ...(rowOrder !== undefined && { rowOrder }),
            ...(columnOrder !== undefined && { columnOrder }),
          },
        },
      },
      isDirty: true,
    });
  },
}));

// Selector: returns the draft overlay's payload (diagram + table)
export function selectDraftPayload(state: OverlayStore): OverlayPayload | null {
  return state.draft?.payload ?? null;
}

// Selector: returns the snap grid size from the draft diagram globals
export function selectSnapGrid(state: OverlayStore): number {
  return state.draft?.payload?.diagram?.globals?.snapGrid ?? 5;
}
