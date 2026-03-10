# Pipeline Result: NCT04649359_Pfizer-Inc_C1071003_10

**Status:** SUCCESS
**PDF:** `NCT04649359_Pfizer-Inc_C1071003_10.pdf`
**Model:** claude-opus-4-6
**Started:** 2026-03-10 10:14:33
**Finished:** 2026-03-10 10:28:17
**Duration:** 824.0s
**Entities:** 1087
**Waves:** 4

## Statistics

| Metric | Value |
|--------|-------|
| Total Agents | 21 |
| Succeeded | 21 |
| Failed | 0 |
| Total Entities | 1087 |
| Total Tokens | 260,330 |
| Total API Calls | 96 |
| Total Duration | 824.0s |

## Execution Flow

```
Wave 0  (260.6s)
  [OK] docstructure_agent (260.6s)  ->  05_extraction_document_structure.json
  [OK] metadata_agent (10.8s)  ->  01_extraction_metadata.json
  [OK] narrative_agent (49.7s)  ->  04_extraction_narrative.json
  [OK] pdf-parser (2.4s)
  [OK] provenance (0.0s)  ->  20_support_provenance.json
  [OK] soa_vision_agent (38.1s)  ->  02_extraction_soa_vision.json
  [OK] usdm-generator (0.0s)  ->  19_support_usdm_generator.json
  |
Wave 1  (148.1s)
  [OK] advanced_agent (57.2s)  ->  13_extraction_advanced_entities.json
  [OK] eligibility_agent (42.1s)  ->  06_extraction_eligibility.json
  [OK] objectives_agent (50.2s)  ->  07_extraction_objectives.json
  [OK] procedures_agent (74.7s)  ->  09_extraction_procedures_devices.json
  [OK] soa_text_agent (148.1s)  ->  03_extraction_soa_text.json
  [OK] studydesign_agent (21.7s)  ->  08_extraction_study_design.json
  |
Wave 2  (187.4s)
  [OK] biomedical_concept_agent (75.8s)  ->  14_extraction_biomedical_concepts.json
  [OK] execution_agent (187.4s)  ->  12_extraction_execution_model.json
  [OK] interventions_agent (32.7s)  ->  10_extraction_interventions.json
  [OK] scheduling_agent (87.2s)  ->  11_extraction_scheduling_logic.json
  |
Wave 3  (191.0s)
  [OK] enrichment_agent (191.0s)  ->  18_quality_enrichment.json
  [OK] postprocessing_agent (0.0s)  ->  15_quality_postprocessing.json
  [OK] reconciliation_agent (1.6s)  ->  16_quality_reconciliation.json
  [OK] validation_agent (0.0s)  ->  17_quality_validation.json
  |
Output
  [OK] NCT04649359_Pfizer-Inc_C1071003_10_usdm.json
  [OK] NCT04649359_Pfizer-Inc_C1071003_10_provenance.json
```

## Agent Results

| Step | Agent | Category | Status | Time (s) | Tokens | API Calls | Pages | Output File |
|------|-------|----------|--------|----------|--------|-----------|-------|-------------|
| 01 | metadata_agent | extraction | OK | 10.8 | 4,493 | 1 | 0-2 | `01_extraction_metadata.json` |
| 02 | soa_vision_agent | extraction | OK | 38.1 | 6,866 | 1 | 20-29 | `02_extraction_soa_vision.json` |
| 03 | soa_text_agent | extraction | OK | 148.1 | 36,863 | 2 | 20-29 | `03_extraction_soa_text.json` |
| 04 | narrative_agent | extraction | OK | 49.7 | 8,418 | 2 | 3,10,17,21 | `04_extraction_narrative.json` |
| 05 | docstructure_agent | extraction | OK | 260.6 | 31,256 | 1 | 0-10,14-16,19,21-25 | `05_extraction_document_structure.json` |
| 06 | eligibility_agent | extraction | OK | 42.1 | 10,694 | 1 | 40-44 | `06_extraction_eligibility.json` |
| 07 | objectives_agent | extraction | OK | 50.2 | 21,928 | 2 | 7-14,16-20 | `07_extraction_objectives.json` |
| 08 | studydesign_agent | extraction | OK | 21.7 | 7,463 | 1 | 0-1,9-12,17-19 | `08_extraction_study_design.json` |
| 09 | procedures_agent | extraction | OK | 74.7 | 15,520 | 1 | 1-7,11-13,15,21-22,26,29 | `09_extraction_procedures_devices.json` |
| 10 | interventions_agent | extraction | OK | 32.7 | 32,505 | 1 | 0-1,4-40,43-49 | `10_extraction_interventions.json` |
| 11 | scheduling_agent | extraction | OK | 87.2 | 21,838 | 1 | 2,6-7,11,21-30,34-35,44,46,50-51 | `11_extraction_scheduling_logic.json` |
| 12 | execution_agent | extraction | OK | 187.4 | 26,915 | 11 | 0-41,43-44,46-48,52-53,55-58,60,63-65,74-75,77-78,135,138,140 | `12_extraction_execution_model.json` |
| 13 | advanced_agent | extraction | OK | 57.2 | 23,624 | 1 | 0-29 | `13_extraction_advanced_entities.json` |
| 14 | biomedical_concept_agent | extraction | OK | 75.8 | 11,947 | 1 |  | `14_extraction_biomedical_concepts.json` |
| 15 | postprocessing_agent | quality | OK | 0.0 | 0 | 0 |  | `15_quality_postprocessing.json` |
| 16 | reconciliation_agent | quality | OK | 1.6 | 0 | 0 |  | `16_quality_reconciliation.json` |
| 17 | validation_agent | quality | OK | 0.0 | 0 | 0 |  | `17_quality_validation.json` |
| 18 | enrichment_agent | quality | OK | 191.0 | 0 | 69 |  | `18_quality_enrichment.json` |
| 19 | usdm-generator | support | OK | 0.0 | 0 | 0 |  | `19_support_usdm_generator.json` |
| 20 | provenance | support | OK | 0.0 | 0 | 0 |  | `20_support_provenance.json` |
| 00 | pdf-parser | support | OK | 2.4 | 0 | 0 | | |

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
