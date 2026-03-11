# Pipeline Result: NCT03155997_Eli-Lilly-and-Company_I3Y-MC-JPCF_e

**Status:** SUCCESS
**PDF:** `NCT03155997_Eli-Lilly-and-Company_I3Y-MC-JPCF_e.pdf`
**Model:** claude-opus-4-6
**Started:** 2026-03-10 16:08:28
**Finished:** 2026-03-10 16:20:02
**Duration:** 693.6s
**Entities:** 723
**Waves:** 4

## Statistics

| Metric | Value |
|--------|-------|
| Total Agents | 21 |
| Succeeded | 21 |
| Failed | 0 |
| Total Entities | 723 |
| Total Tokens | 216,076 |
| Total API Calls | 120 |
| Total Duration | 693.6s |

## Execution Flow

```
Wave 0  (39.8s)
  [OK] docstructure_agent (29.8s)  ->  05_extraction_document_structure.json
  [OK] metadata_agent (13.3s)  ->  01_extraction_metadata.json
  [OK] narrative_agent (39.8s)  ->  04_extraction_narrative.json
  [OK] pdf-parser (1.3s)
  [OK] provenance (0.0s)  ->  20_support_provenance.json
  [OK] soa_vision_agent (33.9s)  ->  02_extraction_soa_vision.json
  [OK] usdm-generator (0.5s)  ->  19_support_usdm_generator.json
  |
Wave 1  (107.8s)
  [OK] advanced_agent (9.2s)  ->  13_extraction_advanced_entities.json
  [OK] eligibility_agent (19.4s)  ->  06_extraction_eligibility.json
  [OK] objectives_agent (59.0s)  ->  07_extraction_objectives.json
  [OK] procedures_agent (39.1s)  ->  09_extraction_procedures_devices.json
  [OK] soa_text_agent (107.8s)  ->  03_extraction_soa_text.json
  [OK] studydesign_agent (14.8s)  ->  08_extraction_study_design.json
  |
Wave 2  (271.7s)
  [OK] biomedical_concept_agent (46.6s)  ->  14_extraction_biomedical_concepts.json
  [OK] execution_agent (271.7s)  ->  12_extraction_execution_model.json
  [OK] interventions_agent (49.4s)  ->  10_extraction_interventions.json
  [OK] scheduling_agent (98.6s)  ->  11_extraction_scheduling_logic.json
  |
Wave 3  (255.3s)
  [OK] enrichment_agent (255.3s)  ->  18_quality_enrichment.json
  [OK] postprocessing_agent (0.0s)  ->  15_quality_postprocessing.json
  [OK] reconciliation_agent (0.3s)  ->  16_quality_reconciliation.json
  [OK] validation_agent (0.0s)  ->  17_quality_validation.json
  |
Output
  [OK] NCT03155997_Eli-Lilly-and-Company_I3Y-MC-JPCF_e_usdm.json
  [OK] NCT03155997_Eli-Lilly-and-Company_I3Y-MC-JPCF_e_provenance.json
```

## Agent Results

| Step | Agent | Category | Status | Time (s) | Tokens | API Calls | Pages | Output File |
|------|-------|----------|--------|----------|--------|-----------|-------|-------------|
| 01 | metadata_agent | extraction | OK | 13.3 | 4,739 | 1 | 0-2 | `01_extraction_metadata.json` |
| 02 | soa_vision_agent | extraction | OK | 33.9 | 6,124 | 1 | 9-18 | `02_extraction_soa_vision.json` |
| 03 | soa_text_agent | extraction | OK | 107.8 | 26,124 | 2 | 9-18 | `03_extraction_soa_text.json` |
| 04 | narrative_agent | extraction | OK | 39.8 | 10,973 | 2 | 2,5,8,10,12,19,27 | `04_extraction_narrative.json` |
| 05 | docstructure_agent | extraction | OK | 29.8 | 15,410 | 1 | 0-4,14-19,21,31,34,36-37,42-43,45,47 | `05_extraction_document_structure.json` |
| 06 | eligibility_agent | extraction | OK | 19.4 | 4,713 | 1 | 28-30 | `06_extraction_eligibility.json` |
| 07 | objectives_agent | extraction | OK | 59.0 | 18,045 | 2 | 7-9,23-28 | `07_extraction_objectives.json` |
| 08 | studydesign_agent | extraction | OK | 14.8 | 19,928 | 1 | 0-3,5-28 | `08_extraction_study_design.json` |
| 09 | procedures_agent | extraction | OK | 39.1 | 13,383 | 1 | 11,13-16,19,24,42,44-45,47,49-51 | `09_extraction_procedures_devices.json` |
| 10 | interventions_agent | extraction | OK | 49.4 | 29,660 | 1 | 1-3,8-20,25-27,30-49 | `10_extraction_interventions.json` |
| 11 | scheduling_agent | extraction | OK | 98.6 | 23,835 | 1 | 9-10,12-19,26,31,34-35,37,39-42,45 | `11_extraction_scheduling_logic.json` |
| 12 | execution_agent | extraction | OK | 271.7 | 31,980 | 11 | 0-40,42-43,46-49,60,62,66,88 | `12_extraction_execution_model.json` |
| 13 | advanced_agent | extraction | OK | 9.2 | 4,289 | 1 | 0-3 | `13_extraction_advanced_entities.json` |
| 14 | biomedical_concept_agent | extraction | OK | 46.6 | 6,873 | 1 |  | `14_extraction_biomedical_concepts.json` |
| 15 | postprocessing_agent | quality | OK | 0.0 | 0 | 0 |  | `15_quality_postprocessing.json` |
| 16 | reconciliation_agent | quality | OK | 0.3 | 0 | 0 |  | `16_quality_reconciliation.json` |
| 17 | validation_agent | quality | OK | 0.0 | 0 | 0 |  | `17_quality_validation.json` |
| 18 | enrichment_agent | quality | OK | 255.3 | 0 | 93 |  | `18_quality_enrichment.json` |
| 19 | usdm-generator | support | OK | 0.5 | 0 | 0 |  | `19_support_usdm_generator.json` |
| 20 | provenance | support | OK | 0.0 | 0 | 0 |  | `20_support_provenance.json` |
| 00 | pdf-parser | support | OK | 1.3 | 0 | 0 | | |

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
- `NCT03155997_Eli-Lilly-and-Company_I3Y-MC-JPCF_e.pdf`
- `NCT03155997_Eli-Lilly-and-Company_I3Y-MC-JPCF_e_provenance.json`
- `NCT03155997_Eli-Lilly-and-Company_I3Y-MC-JPCF_e_usdm.json`
- `conformance_report.json`
- `id_mapping.json`
- `soa_page_010.png`
- `soa_page_011.png`
- `soa_page_012.png`
- `soa_page_013.png`
- `soa_page_014.png`
- `soa_page_015.png`
- `soa_page_016.png`
- `soa_page_017.png`
- `soa_page_018.png`
- `soa_page_019.png`
- `usdm_validation.json`
