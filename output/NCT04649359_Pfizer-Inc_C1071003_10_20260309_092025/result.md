# Pipeline Result: NCT04649359_Pfizer-Inc_C1071003_10

**Status:** SUCCESS
**PDF:** `NCT04649359_Pfizer-Inc_C1071003_10.pdf`
**Model:** claude-opus-4-6
**Started:** 2026-03-09 09:20:25
**Finished:** 2026-03-09 09:31:51
**Duration:** 686.4s
**Entities:** 1036
**Waves:** 4

## Statistics

| Metric | Value |
|--------|-------|
| Total Agents | 21 |
| Succeeded | 21 |
| Failed | 0 |
| Total Entities | 1036 |
| Total Tokens | 241,476 |
| Total API Calls | 100 |
| Total Duration | 686.4s |

## Execution Flow

```
Wave 0  (86.6s)
  [OK] docstructure_agent (86.6s)  ->  05_extraction_document_structure.json
  [OK] metadata_agent (11.0s)  ->  01_extraction_metadata.json
  [OK] narrative_agent (35.6s)  ->  04_extraction_narrative.json
  [OK] pdf-parser (2.2s)
  [OK] provenance (0.0s)  ->  20_support_provenance.json
  [OK] soa_vision_agent (41.5s)  ->  02_extraction_soa_vision.json
  [OK] usdm-generator (2.5s)  ->  19_support_usdm_generator.json
  |
Wave 1  (176.3s)
  [OK] advanced_agent (46.9s)  ->  13_extraction_advanced_entities.json
  [OK] eligibility_agent (34.6s)  ->  06_extraction_eligibility.json
  [OK] objectives_agent (41.4s)  ->  07_extraction_objectives.json
  [OK] procedures_agent (41.2s)  ->  09_extraction_procedures_devices.json
  [OK] soa_text_agent (176.3s)  ->  03_extraction_soa_text.json
  [OK] studydesign_agent (18.1s)  ->  08_extraction_study_design.json
  |
Wave 2  (152.7s)
  [OK] biomedical_concept_agent (91.9s)  ->  14_extraction_biomedical_concepts.json
  [OK] execution_agent (152.7s)  ->  12_extraction_execution_model.json
  [OK] interventions_agent (24.9s)  ->  10_extraction_interventions.json
  [OK] scheduling_agent (83.9s)  ->  11_extraction_scheduling_logic.json
  |
Wave 3  (212.7s)
  [OK] enrichment_agent (212.7s)  ->  18_quality_enrichment.json
  [OK] postprocessing_agent (0.0s)  ->  15_quality_postprocessing.json
  [OK] reconciliation_agent (0.6s)  ->  16_quality_reconciliation.json
  [OK] validation_agent (0.0s)  ->  17_quality_validation.json
  |
Output
  [OK] NCT04649359_Pfizer-Inc_C1071003_10_usdm.json
  [OK] NCT04649359_Pfizer-Inc_C1071003_10_provenance.json
```

## Agent Results

| Step | Agent | Category | Status | Time (s) | Tokens | API Calls | Pages | Output File |
|------|-------|----------|--------|----------|--------|-----------|-------|-------------|
| 01 | metadata_agent | extraction | OK | 11.0 | 4,769 | 1 | 0-2 | `01_extraction_metadata.json` |
| 02 | soa_vision_agent | extraction | OK | 41.5 | 6,546 | 1 | 20-29 | `02_extraction_soa_vision.json` |
| 03 | soa_text_agent | extraction | OK | 176.3 | 37,888 | 2 | 20-29 | `03_extraction_soa_text.json` |
| 04 | narrative_agent | extraction | OK | 35.6 | 8,482 | 2 | 3,10,17,21 | `04_extraction_narrative.json` |
| 05 | docstructure_agent | extraction | OK | 86.6 | 19,692 | 1 | 0-10,14-16,19,21-25 | `05_extraction_document_structure.json` |
| 06 | eligibility_agent | extraction | OK | 34.6 | 10,868 | 1 | 40-44 | `06_extraction_eligibility.json` |
| 07 | objectives_agent | extraction | OK | 41.4 | 21,057 | 2 | 7-14,16-20 | `07_extraction_objectives.json` |
| 08 | studydesign_agent | extraction | OK | 18.1 | 7,545 | 1 | 0-1,9-12,17-19 | `08_extraction_study_design.json` |
| 09 | procedures_agent | extraction | OK | 41.2 | 14,970 | 1 | 1-7,11-13,15,21-22,26,29 | `09_extraction_procedures_devices.json` |
| 10 | interventions_agent | extraction | OK | 24.9 | 31,928 | 1 | 0-1,4-40,43-49 | `10_extraction_interventions.json` |
| 11 | scheduling_agent | extraction | OK | 83.9 | 21,684 | 1 | 2,6-7,11,21-30,34-35,44,46,50-51 | `11_extraction_scheduling_logic.json` |
| 12 | execution_agent | extraction | OK | 152.7 | 26,761 | 11 | 0-41,43-44,46-48,52-53,55-58,60,63-65,74-75,77-78,135,138,140 | `12_extraction_execution_model.json` |
| 13 | advanced_agent | extraction | OK | 46.9 | 19,066 | 1 | 0-29 | `13_extraction_advanced_entities.json` |
| 14 | biomedical_concept_agent | extraction | OK | 91.9 | 10,220 | 1 |  | `14_extraction_biomedical_concepts.json` |
| 15 | postprocessing_agent | quality | OK | 0.0 | 0 | 0 |  | `15_quality_postprocessing.json` |
| 16 | reconciliation_agent | quality | OK | 0.6 | 0 | 0 |  | `16_quality_reconciliation.json` |
| 17 | validation_agent | quality | OK | 0.0 | 0 | 0 |  | `17_quality_validation.json` |
| 18 | enrichment_agent | quality | OK | 212.7 | 0 | 73 |  | `18_quality_enrichment.json` |
| 19 | usdm-generator | support | OK | 2.5 | 0 | 0 |  | `19_support_usdm_generator.json` |
| 20 | provenance | support | OK | 0.0 | 0 | 0 |  | `20_support_provenance.json` |
| 00 | pdf-parser | support | OK | 2.2 | 0 | 0 | | |

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
- `NCT04649359_Pfizer-Inc_C1071003_10.pdf`
- `NCT04649359_Pfizer-Inc_C1071003_10_provenance.json`
- `NCT04649359_Pfizer-Inc_C1071003_10_usdm.json`
- `conformance_report.json`
- `id_mapping.json`
- `soa_page_021.png`
- `soa_page_022.png`
- `soa_page_023.png`
- `soa_page_024.png`
- `soa_page_025.png`
- `soa_page_026.png`
- `soa_page_027.png`
- `soa_page_028.png`
- `soa_page_029.png`
- `soa_page_030.png`
- `usdm_validation.json`
