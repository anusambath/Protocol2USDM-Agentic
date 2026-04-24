# TODO / Backlog

## Web UI

- [ ] Wire up Save Draft / Publish / Reset to Published buttons in `Workbench.tsx`
  - The `overlayStore` (Zustand) already has in-memory state transitions (`promoteDraftToPublished`, `resetToPublished`, `markDirty`/`markClean`)
  - Handlers in `Workbench.tsx` are `console.log` stubs (lines ~148-162)
  - Needs: persistence layer (API or local storage) to save/load overlay documents
  - Related files: `web-ui/stores/overlayStore.ts`, `web-ui/components/workbench/Workbench.tsx`, `web-ui/components/workbench/StatusBar.tsx`

- [ ] Wire up Export buttons (CSV, JSON, PDF) — also stubs in `Workbench.tsx`

- [ ] Fix styling for provenance info across all tabs — currently looks too much like normal content, needs visual differentiation (e.g. distinct background, border, or badge treatment)

- [ ] SoA table right sidebar (Properties/Provenance/Footnotes) cleanup:
  1. Remove or reposition "Source Pages" info — takes up space without adding much value in current position
  2. Hide internal IDs from the selected cell display — not useful to end users

## Pipeline / Enrichment

- [ ] Integrate CDISC Biomedical Concepts (BC) library for BC enrichment
  - Currently the BC agent uses LLM generation with a hardcoded table of ~27 NCI codes
  - Should query the CDISC Library BC API (https://library.cdisc.org) to look up official BC entries for each SoA activity
  - Would provide validated NCI codes, correct CDASH/SDTM property mappings, and proper domain assignments instead of LLM guesses
  - Related files: `extraction/biomedical_concepts/extractor.py`, `extraction/biomedical_concepts/prompts.py`
