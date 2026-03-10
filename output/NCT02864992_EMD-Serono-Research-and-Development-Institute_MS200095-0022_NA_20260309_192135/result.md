# Pipeline Result: NCT02864992_EMD-Serono-Research-and-Development-Institute_MS200095-0022_NA

**Status:** SUCCESS
**PDF:** `NCT02864992_EMD-Serono-Research-and-Development-Institute_MS200095-0022_NA.pdf`
**Model:** claude-opus-4-6
**Started:** 2026-03-09 19:21:35
**Finished:** 2026-03-09 19:31:53
**Duration:** 618.0s
**Entities:** 789
**Waves:** 4

## Statistics

| Metric | Value |
|--------|-------|
| Total Agents | 21 |
| Succeeded | 21 |
| Failed | 0 |
| Total Entities | 789 |
| Total Tokens | 221,435 |
| Total API Calls | 90 |
| Total Duration | 618.0s |

## Execution Flow

```
Wave 0  (64.0s)
  [OK] docstructure_agent (38.9s)  ->  05_extraction_document_structure.json
  [OK] metadata_agent (13.1s)  ->  01_extraction_metadata.json
  [OK] narrative_agent (19.0s)  ->  04_extraction_narrative.json
  [OK] pdf-parser (5.7s)
  [OK] provenance (0.0s)  ->  20_support_provenance.json
  [OK] soa_vision_agent (64.0s)  ->  02_extraction_soa_vision.json
  [OK] usdm-generator (0.0s)  ->  19_support_usdm_generator.json
  |
Wave 1  (139.5s)
  [OK] advanced_agent (13.6s)  ->  13_extraction_advanced_entities.json
  [OK] eligibility_agent (34.3s)  ->  06_extraction_eligibility.json
  [OK] objectives_agent (63.7s)  ->  07_extraction_objectives.json
  [OK] procedures_agent (49.2s)  ->  09_extraction_procedures_devices.json
  [OK] soa_text_agent (139.5s)  ->  03_extraction_soa_text.json
  [OK] studydesign_agent (16.5s)  ->  08_extraction_study_design.json
  |
Wave 2  (150.9s)
  [OK] biomedical_concept_agent (43.6s)  ->  14_extraction_biomedical_concepts.json
  [OK] execution_agent (150.9s)  ->  12_extraction_execution_model.json
  [OK] interventions_agent (28.2s)  ->  10_extraction_interventions.json
  [OK] scheduling_agent (103.5s)  ->  11_extraction_scheduling_logic.json
  |
Wave 3  (174.5s)
  [OK] enrichment_agent (174.5s)  ->  18_quality_enrichment.json
  [OK] postprocessing_agent (0.0s)  ->  15_quality_postprocessing.json
  [OK] reconciliation_agent (0.5s)  ->  16_quality_reconciliation.json
  [OK] validation_agent (0.0s)  ->  17_quality_validation.json
  |
Output
  [OK] NCT02864992_EMD-Serono-Research-and-Development-Institute_MS200095-0022_NA_usdm.json
  [OK] NCT02864992_EMD-Serono-Research-and-Development-Institute_MS200095-0022_NA_provenance.json
```

## Agent Results

| Step | Agent | Category | Status | Time (s) | Tokens | API Calls | Pages | Output File |
|------|-------|----------|--------|----------|--------|-----------|-------|-------------|
| 01 | metadata_agent | extraction | OK | 13.1 | 5,130 | 1 | 0-2 | `01_extraction_metadata.json` |
| 02 | soa_vision_agent | extraction | OK | 64.0 | 8,161 | 1 | 5-6,21-25,54-56 | `02_extraction_soa_vision.json` |
| 03 | soa_text_agent | extraction | OK | 139.5 | 37,920 | 2 | 5-6,21-25,54-56 | `03_extraction_soa_text.json` |
| 04 | narrative_agent | extraction | OK | 19.0 | 6,606 | 2 | 1,7,10 | `04_extraction_narrative.json` |
| 05 | docstructure_agent | extraction | OK | 38.9 | 15,327 | 1 | 0-5,11,15,23-24,26,30,32,37,40-41,43-44,47-48 | `05_extraction_document_structure.json` |
| 06 | eligibility_agent | extraction | OK | 34.3 | 16,969 | 1 | 15-17,39-44,46-48 | `06_extraction_eligibility.json` |
| 07 | objectives_agent | extraction | OK | 63.7 | 29,334 | 2 | 0-5,10-16,19-21 | `07_extraction_objectives.json` |
| 08 | studydesign_agent | extraction | OK | 16.5 | 12,928 | 1 | 0-5,12-14,25-29 | `08_extraction_study_design.json` |
| 09 | procedures_agent | extraction | OK | 49.2 | 15,498 | 1 | 2-3,7-9,11-12,15-16,19,21-25 | `09_extraction_procedures_devices.json` |
| 10 | interventions_agent | extraction | OK | 28.2 | 12,187 | 1 | 8-10,39-41,43-49 | `10_extraction_interventions.json` |
| 11 | scheduling_agent | extraction | OK | 103.5 | 25,251 | 1 | 1-2,14,23-24,28,36-37,40-41,43-47,53-56,58 | `11_extraction_scheduling_logic.json` |
| 12 | execution_agent | extraction | OK | 150.9 | 24,447 | 11 | 0-40,42,45,54-60,62,64,68-70,78,111,115 | `12_extraction_execution_model.json` |
| 13 | advanced_agent | extraction | OK | 13.6 | 4,636 | 1 | 0-3,5 | `13_extraction_advanced_entities.json` |
| 14 | biomedical_concept_agent | extraction | OK | 43.6 | 7,041 | 1 |  | `14_extraction_biomedical_concepts.json` |
| 15 | postprocessing_agent | quality | OK | 0.0 | 0 | 0 |  | `15_quality_postprocessing.json` |
| 16 | reconciliation_agent | quality | OK | 0.5 | 0 | 0 |  | `16_quality_reconciliation.json` |
| 17 | validation_agent | quality | OK | 0.0 | 0 | 0 |  | `17_quality_validation.json` |
| 18 | enrichment_agent | quality | OK | 174.5 | 0 | 63 |  | `18_quality_enrichment.json` |
| 19 | usdm-generator | support | OK | 0.0 | 0 | 0 |  | `19_support_usdm_generator.json` |
| 20 | provenance | support | OK | 0.0 | 0 | 0 |  | `20_support_provenance.json` |
| 00 | pdf-parser | support | OK | 5.7 | 0 | 0 | | |

## Output Files

- `01_extraction_metadata.json`
- `02_extraction_soa_vision.json`
- `03_extraction_soa_text.json`
- `04_extraction_narrative.json`
- `05_extraction_document_structure.json`
- `06_extraction_eligibility.json`
- `07_extraction_objectives.json`
- `08_extraction_study_design.json`
- `09_extraction_procedures_devices.json`
- `10_extraction_interventions.json`
- `11_extraction_scheduling_logic.json`
- `12_extraction_execution_model.json`
- `13_extraction_advanced_entities.json`
- `14_extraction_biomedical_concepts.json`
- `15_quality_postprocessing.json`
- `16_quality_reconciliation.json`
- `17_quality_validation.json`
- `18_quality_enrichment.json`
- `19_support_usdm_generator.json`
- `20_support_provenance.json`
- `9_final_soa_provenance.json`
- `NCT02864992_EMD-Serono-Research-and-Development-Institute_MS200095-0022_NA.pdf`
- `NCT02864992_EMD-Serono-Research-and-Development-Institute_MS200095-0022_NA_provenance.json`
- `NCT02864992_EMD-Serono-Research-and-Development-Institute_MS200095-0022_NA_usdm.json`
- `conformance_report.json`
- `id_mapping.json`
- `soa_page_006.png`
- `soa_page_007.png`
- `soa_page_022.png`
- `soa_page_023.png`
- `soa_page_024.png`
- `soa_page_025.png`
- `soa_page_026.png`
- `soa_page_055.png`
- `soa_page_056.png`
- `soa_page_057.png`
- `usdm_validation.json`
