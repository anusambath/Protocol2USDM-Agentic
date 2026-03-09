# Protocol2USDM Extraction Pipeline

This document describes how the extraction pipeline converts a clinical trial protocol PDF into a USDM v4.0 JSON document, including agent execution order, entity-to-USDM mapping, quality processing, and enrichment.

---

## Entry Point

```
python run_extraction.py <pdf_path> [options]
```

Key CLI options:
- `--model` — primary LLM (default: `gemini-2.5-pro`)
- `--fast-model` — lighter model for straightforward extraction agents
- `--vision-model` — model for SoA vision extraction
- `--workers` — parallel workers (default: 4)
- `--no-vision` — disable SoA vision extraction
- `--no-enrichment` — disable NCI EVS terminology enrichment
- `--skip` — agent IDs to skip
- `--resume-from-checkpoint` — resume from a saved checkpoint

The CLI creates an `ExtractionPipeline`, calls `pipeline.initialize()`, then `pipeline.run(pdf_path)`.

---

## Pipeline Architecture

```
run_extraction.py
  └─ ExtractionPipeline.run()
       ├─ OrchestratorAgent.create_execution_plan()   ← builds wave-based DAG
       ├─ OrchestratorAgent.execute_plan()            ← runs agents wave by wave
       ├─ USDMGeneratorAgent.execute()                ← assembles USDM JSON from ContextStore
       ├─ ProvenanceAgent.execute()                   ← generates provenance JSON
       └─ CDISC CORE engine validation                ← optional conformance check
```

All extraction agents write entities into a shared **ContextStore**. After all waves complete, the USDM Generator reads every entity from the store and places it into the USDM v4.0 JSON skeleton.

---

## Wave-Based Execution Order

The orchestrator builds a dependency graph from each agent's `get_capabilities().dependencies` and groups agents into waves. Agents within a wave run in parallel.


### Wave 0 — No Dependencies (Parallel)

| Agent | Agent ID | Protocol Section | Entity Types Produced |
|-------|----------|------------------|-----------------------|
| PDF Parser | `pdf-parser` | Entire PDF | `pdf_page` (text, images, table regions) |
| Metadata | `metadata_agent` | Title page, headers, protocol synopsis | `metadata`, `study_title`, `study_identifier`, `organization`, `study_role`, `indication`, `study_phase`, `governance_date` |
| Narrative | `narrative_agent` | Table of contents, section headings, abbreviation lists | `narrative_content`, `narrative_content_item`, `abbreviation` |
| Doc Structure | `docstructure_agent` | TOC, footnotes, version history | `document_content_reference`, `comment_annotation`, `document_version` |
| SoA Vision | `soa_vision_agent` | Schedule of Assessments table (page images) | `epoch`, `encounter`, `activity`, `header_structure`, `footnote` |

### Wave 1 — Depends on Metadata / Vision

| Agent | Agent ID | Dependencies | Protocol Section | Entity Types Produced |
|-------|----------|-------------|------------------|-----------------------|
| Eligibility | `eligibility_agent` | `metadata_extraction` | Inclusion/exclusion criteria sections | `eligibility_criterion`, `criterion_item`, `study_population` |
| Objectives | `objectives_agent` | `metadata_extraction` | Objectives & endpoints sections | `objective`, `endpoint`, `estimand`, `analysis_population` |
| Study Design | `studydesign_agent` | `metadata_extraction` | Study design section | `study_design`, `study_arm`, `study_cohort`, `study_cell`, `study_element` |
| Advanced | `advanced_agent` | `metadata_extraction` | Amendments, geographic scope sections | `study_amendment`, `amendment_reason`, `geographic_scope`, `country`, `study_site` |
| SoA Text | `soa_text_agent` | `soa_vision_extraction` | SoA table (text extraction using vision header structure) | `soa_text_extraction`, `activity`, `scheduled_instance` |

### Wave 2 — Depends on Vision + Text + Design

| Agent | Agent ID | Dependencies | Protocol Section | Entity Types Produced |
|-------|----------|-------------|------------------|-----------------------|
| Interventions | `interventions_agent` | `metadata_extraction`, `studydesign_extraction` | Investigational product, dosing sections | `study_intervention`, `administrable_product`, `administration`, `substance`, `medical_device` |
| Procedures | `procedures_agent` | `metadata_extraction`, `soa_vision_extraction` | Procedures, lab tests, assessments sections | `procedure`, `medical_device`, `ingredient`, `strength` |
| Execution | `execution_agent` | `soa_vision_extraction`, `soa_text_extraction` | Visit windows, dosing regimens, footnotes | `time_anchor`, `repetition`, `execution_type`, `traversal_constraint`, `footnote_condition`, `state_machine`, `dosing_regimen`, `visit_window` |

### Wave 3 — Depends on Execution + All Prior

| Agent | Agent ID | Dependencies | Protocol Section | Entity Types Produced |
|-------|----------|-------------|------------------|-----------------------|
| Scheduling | `scheduling_agent` | `soa_vision_extraction`, `procedures_extraction` | Timing rules, visit schedule | `timing`, `condition`, `transition_rule`, `schedule_exit`, `decision_instance` |
| Biomedical Concepts | `biomedical_concept_agent` | `soa_vision_extraction`, `soa_text_extraction`, `procedures_extraction` | Derived from Activity entities | `biomedical_concept`, `biomedical_concept_category` |
| Post-Processing | `postprocessing_agent` | `execution_extraction` | N/A (operates on ContextStore) | Modifies existing entities in-place |
| Validation | `validation_agent` | `execution_extraction` | N/A (operates on ContextStore) | Produces `validation_report` |
| Reconciliation | `reconciliation_agent` | `execution_extraction` | N/A (operates on ContextStore) | Produces `reconciliation_report` |
| Enrichment | `enrichment_agent` | `execution_extraction` | N/A (queries NCI EVS API) | Enriches existing entities with terminology codes |

### Post-Plan (Called Directly After Plan Execution)

| Agent | Agent ID | Purpose |
|-------|----------|---------|
| USDM Generator | `usdm-generator` | Assembles all ContextStore entities into USDM v4.0 JSON |
| Provenance | `provenance` | Generates provenance JSON mapping entities to source pages |


---

## Entity Type → USDM Placement Mapping

Every entity extracted by agents is placed into the USDM v4.0 JSON hierarchy by the USDM Generator. The mapping is defined in `ENTITY_TYPE_PLACEMENT`:

| Entity Type | USDM JSON Path |
|-------------|----------------|
| `metadata` | `study` (sets `name`, `description`, `label`, `versionIdentifier`) |
| `study_identifier` | `study.versions[0].studyIdentifiers[]` |
| `study_phase` | `study.versions[0].studyPhase` |
| `study_title` | `study.versions[0].titles[]` |
| `indication` | `study.versions[0].studyDesigns[0].indications[]` |
| `objective` | `study.versions[0].studyDesigns[0].objectives[]` |
| `endpoint` | `study.versions[0].studyDesigns[0].endpoints[]` |
| `estimand` | `study.versions[0].studyDesigns[0].estimands[]` |
| `study_arm` | `study.versions[0].studyDesigns[0].arms[]` |
| `study_epoch` / `epoch` | `study.versions[0].studyDesigns[0].epochs[]` |
| `study_cell` | `study.versions[0].studyDesigns[0].studyCells[]` |
| `eligibility_criterion` | `study.versions[0].studyDesigns[0].eligibilityCriteria[]` |
| `criterion_item` | `study.versions[0].eligibilityCriterionItems[]` |
| `study_population` | `study.versions[0].studyDesigns[0].population` (merged) |
| `activity` | `study.versions[0].studyDesigns[0].activities[]` |
| `encounter` | `study.versions[0].studyDesigns[0].encounters[]` |
| `study_intervention` / `intervention` | `study.versions[0].studyDesigns[0].studyInterventions[]` |
| `substance` | `study.versions[0].studyDesigns[0].studyInterventions[].substances[]` |
| `administrable_product` | `study.versions[0].administrableProducts[]` |
| `medical_device` | `study.versions[0].medicalDevices[]` |
| `study_element` | `study.versions[0].studyDesigns[0].elements[]` |
| `analysis_population` | `study.versions[0].studyDesigns[0].analysisPopulations[]` |
| `governance_date` | `study.versions[0].dateValues[]` |
| `biomedical_concept` | `study.versions[0].biomedicalConcepts[]` |
| `biomedical_concept_category` | `study.versions[0].bcCategories[]` |
| `timing` | `study.versions[0].studyDesigns[0].scheduleTimelines[].timings[]` |
| `schedule_timeline` | `study.versions[0].studyDesigns[0].scheduleTimelines[]` |
| `scheduled_instance` | `study.versions[0].studyDesigns[0].scheduleTimelines[].instances[]` |
| `narrative_content` / `narrative_content_item` | `study.versions[0].narrativeContentItems[]` |
| `abbreviation` | `study.versions[0].abbreviations[]` |
| `amendment` / `study_amendment` | `study.versions[0].amendments[]` |
| `geographic_scope` | `study.versions[0].studyDesigns[0].geographicScopes[]` |
| `country` | `study.versions[0].studyDesigns[0].geographicScopes[].countries[]` |
| `document_section` | `study.documentVersions[0].sections[]` |
| `organization` | `study.versions[0].organizations[]` |
| `study_role` | `study.versions[0].roles[]` |
| `schedule_exit` | `study.versions[0].studyDesigns[0]._pendingExits` (internal) |
| `comment_annotation` | `study.versions[0].studyDesigns[0].notes[]` |


---

## Quality Pipeline

After all extraction agents complete, four quality agents process the ContextStore entities in sequence.

### 1. Post-Processing (`postprocessing_agent`)

Cleans and normalizes extracted entities:

1. **ID Standardization** — normalizes entity IDs to consistent format
2. **Name Normalization** — cleans entity names (removes timing text, extra whitespace). Encounters are excluded from name normalization to preserve timepoint information.
3. **Superscript Stripping** — removes footnote reference superscripts from names
4. **Required Field Fill** — adds default values for missing required USDM fields
5. **Epoch/Encounter Injection** — injects epochs and encounters from the SoA header structure into entities that reference them
6. **Activity Group Resolution** — links activities to their parent groups from the header structure
7. **Timing Code Normalization** — standardizes timing codes to ISO 8601

### 2. Validation (`validation_agent`)

Iterative validation with auto-fix (up to 3 iterations):

- **Schema Validation** — checks required fields, data types, cardinality against USDM v4.0 schema
- **Entity Reference Validation** — verifies all ID references resolve to existing entities
- **CDISC CORE Conformance** — runs built-in CDISC CORE rules
- **Auto-Fix** — automatically fixes common violations (missing required fields, type coercion)
- **Provenance Updates** — records all auto-fixes in entity provenance

### 3. Reconciliation (`reconciliation_agent`)

Deduplicates and merges entities from multiple extraction sources:

- **Duplicate Detection** — finds entities with similar names/content. For encounters, timepoint-aware comparison prevents merging encounters with different timing (e.g., "Visit 1 (Day 1)" vs "Visit 1 (Week 4)").
- **Conflict Resolution** — when multiple agents extract the same entity, reconciles differences
- **Source Tracking** — maintains `_sources` metadata showing which agents contributed

### 4. Enrichment (`enrichment_agent`)

Enriches entities with NCI EVS (Enterprise Vocabulary Services) terminology codes:

- **Enrichable Entity Types**: `indication`, `procedure`, `study_intervention`, `medical_device`, `investigational_product`
- **Process**: For each enrichable entity, queries the NCI EVS API (`api-evsrest.nci.nih.gov`) by entity name, ranks results by relevance score, and attaches the best-matching NCI concept code
- **Caching**: Results are cached in-memory (up to 1000 terms) to avoid redundant API calls
- **Retry Logic**: Failed API calls are retried with backoff

---

## Biomedical Concept Generation

The `biomedical_concept_agent` (Wave 3) generates formal BiomedicalConcept entities from SoA activities:

1. Collects all unique activity names from the ContextStore (stored by `soa_vision_agent`, `soa_text_agent`, and `procedures_agent`)
2. Calls the LLM to generate `biomedical_concept` and `biomedical_concept_category` entities for each activity
3. Backfills `biomedicalConceptIds` on each Activity entity in the ContextStore, linking activities to their formal biomedical concepts

These are placed at:
- `study.versions[0].biomedicalConcepts[]`
- `study.versions[0].bcCategories[]`

---

## USDM Assembly & Post-Processing

After all agents complete, the USDM Generator assembles the final JSON:

### Assembly

1. Builds an empty USDM v4.0 skeleton with all required arrays/objects
2. Iterates every entity in the ContextStore
3. Places each entity into the correct USDM path using `ENTITY_TYPE_PLACEMENT`
4. Strips internal properties (`raw`, `source`, `_reconciled`, `_sources`, `_enrichment_confidence`, `_validation_fixes`, `order`, `entity_type`)
5. Strips entity-type-specific non-schema properties (e.g., `epochId` from encounters, `endpointIds` from objectives)
6. Applies USDM-specific fixes: epoch type inference, arm defaults, organization instanceType

### Post-Assembly Normalization

1. **Type Normalization** (`normalize_usdm_data`) — infers and sets `instanceType` on all USDM objects
2. **Post-Normalize Cleanup** — strips any non-schema fields re-added by normalization
3. **UUID Conversion** (`convert_ids_to_uuids`) — converts all simple IDs (e.g., `epoch_v_1`, `activity_t_3`) to UUID format, updating all cross-references. Saves `id_mapping.json` for traceability.
4. **Schema Validation** (`validate_and_fix_schema`) — final validation pass with auto-fix

### Additional Assembly Fixes

- `_normalize_codelists` — maps extracted codes to CDISC-standard code values
- `_fix_activity_names` — cleans repr-string artifacts from activity names
- `_link_activities_to_procedures` — links Activity entities to their Procedure entities
- `_deduplicate_intercurrent_event_names` — deduplicates IntercurrentEvent names across estimands
- `_sanitize_narrative_xhtml` — ensures NarrativeContentItem text is valid XHTML
- `_fix_duplicate_code_decodes` — fixes code/decode one-to-one relationship violations
- `_ensure_primary_objective` — ensures at least one primary objective exists and links to primary endpoints
- `_ensure_sponsor_identifier` — ensures sponsor identifier and role exist
- `_populate_therapeutic_areas` — derives `businessTherapeuticAreas` from indications
- `_ensure_study_design_type` — sets correct `instanceType` and `studyType` on the study design
- `_fix_required_fields` — final pass to fill any remaining required fields

---

## CDISC CORE Engine Validation

After the USDM JSON is written to disk, the pipeline optionally runs the external CDISC CORE validation engine:

- Produces a `conformance_report.json` with errors, warnings, and info-level issues
- This is separate from the built-in validation agent's CDISC CORE rules

---

## Provenance

Two provenance systems operate in parallel:

### Entity-Level Provenance
Each entity stored in the ContextStore carries `source_pages` metadata indicating which PDF pages it was extracted from. The Provenance Agent aggregates this into a `{protocol_id}_provenance.json` file mapping entity IDs to page numbers and extraction sources.

### Cell-Level Provenance (SoA)
The SoA Text Agent generates `9_final_soa_provenance.json` with per-cell provenance for the Schedule of Assessments table. Cell keys use the format `activity_t_N|encounter_v_N` (pre-UUID) or `uuid|uuid` (post-UUID conversion). Each cell is tagged with its extraction source: `text`, `vision`, or `both` (confirmed by cross-validation).

---

## Gaps & Unmapped Sections

### Entity Types Extracted but Not in USDM Placement

These entity types are extracted by agents but have no direct USDM placement path (they are used internally or for enrichment):

| Entity Type | Source Agent | Purpose |
|-------------|-------------|---------|
| `pdf_page` | PDF Parser | Internal — raw page text/images for other agents |
| `header_structure` | SoA Vision | Internal — SoA table structure used by SoA Text agent |
| `soa_text_extraction` | SoA Text | Internal — raw text extraction result |
| `study_design` | Study Design | Special handling — properties merged into skeleton design object |
| `time_anchor` | Execution | Execution model metadata (not directly in USDM v4.0) |
| `repetition` | Execution | Execution model metadata |
| `execution_type` | Execution | Execution model metadata |
| `traversal_constraint` | Execution | Execution model metadata |
| `footnote_condition` | Execution | Execution model metadata |
| `state_machine` | Execution | Execution model metadata |
| `dosing_regimen` | Execution | Execution model metadata |
| `visit_window` | Execution | Execution model metadata |
| `condition` | Scheduling | Scheduling metadata |
| `transition_rule` | Scheduling | Scheduling metadata |
| `decision_instance` | Scheduling | Scheduling metadata |
| `study_cohort` | Study Design | Not in USDM v4.0 schema |
| `study_site` | Advanced | Not in USDM v4.0 schema |
| `amendment_reason` | Advanced | Not in USDM v4.0 schema |
| `ingredient` | Procedures | Not in USDM v4.0 schema |
| `strength` | Procedures | Not in USDM v4.0 schema |
| `administration` | Interventions | Not in USDM v4.0 schema |
| `document_content_reference` | Doc Structure | Not in USDM v4.0 schema |
| `document_version` | Doc Structure | Not in USDM v4.0 schema |
| `footnote` | SoA Vision | Internal — used for cell annotation |

### USDM Sections Left Empty

These USDM skeleton arrays/fields are initialized but may remain empty if the protocol doesn't contain the relevant information or if no agent extracts them:

| USDM Path | Condition |
|-----------|-----------|
| `study.versions[0].studyDesigns[0].estimands[]` | Only populated if protocol has ICH E9(R1) estimand framework |
| `study.versions[0].studyDesigns[0].analysisPopulations[]` | Only if objectives agent finds analysis population definitions |
| `study.versions[0].studyDesigns[0].studyCells[]` | Only if study design agent extracts arm×epoch cell assignments |
| `study.versions[0].studyDesigns[0].elements[]` | Only if study design agent extracts study elements |
| `study.versions[0].studyDesigns[0].scheduleTimelines[]` | Only if scheduling agent successfully extracts timing rules |
| `study.versions[0].amendments[]` | Only if protocol contains amendment history |
| `study.versions[0].studyDesigns[0].geographicScopes[]` | Only if advanced agent finds geographic scope information |
| `study.documentVersions[0].sections[]` | Only if doc structure agent extracts document sections |
| `study.versions[0].studyDesigns[0].notes[]` | Only if doc structure agent extracts comment annotations |

### Protocol Sections Not Extracted

| Protocol Section | Notes |
|-----------------|-------|
| Statistical Analysis Plan (SAP) details | SAP PDF can be provided to execution agent but detailed statistical methods are not extracted into USDM |
| Pharmacokinetic sampling details | Not extracted as separate entities |
| Adverse event reporting procedures | Not extracted into USDM structure |
| Data monitoring committee details | Not extracted |
| Informed consent details | Not extracted |
| Publication policy | Not extracted |
| Regulatory references | Not extracted as structured entities |
