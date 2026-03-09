# Pipeline Result: Alexion_NCT04573309_Wilsons

**Status:** SUCCESS
**PDF:** `Alexion_NCT04573309_Wilsons.pdf`
**Model:** claude-opus-4-6
**Started:** 2026-03-08 21:44:25
**Finished:** 2026-03-08 22:06:59
**Duration:** 1353.7s
**Entities:** 900
**Waves:** 4

## Statistics

| Metric | Value |
|--------|-------|
| Total Agents | 21 |
| Succeeded | 21 |
| Failed | 0 |
| Total Entities | 900 |
| Total Tokens | 244,380 |
| Total API Calls | 86 |
| Total Duration | 1353.7s |

## Execution Flow

```
Wave 0  (60.6s)
  [OK] docstructure_agent (36.1s)  ->  05_extraction_document_structure.json
  [OK] metadata_agent (14.9s)  ->  01_extraction_metadata.json
  [OK] narrative_agent (49.2s)  ->  04_extraction_narrative.json
  [OK] pdf-parser (0.7s)
  [OK] provenance (0.0s)  ->  20_support_provenance.json
  [OK] soa_vision_agent (60.6s)  ->  02_extraction_soa_vision.json
  [OK] usdm-generator (0.0s)  ->  19_support_usdm_generator.json
  |
Wave 1  (972.9s)
  [OK] advanced_agent (20.9s)  ->  13_extraction_advanced_entities.json
  [OK] eligibility_agent (44.0s)  ->  06_extraction_eligibility.json
  [OK] objectives_agent (43.2s)  ->  07_extraction_objectives.json
  [OK] procedures_agent (48.7s)  ->  09_extraction_procedures_devices.json
  [OK] soa_text_agent (972.9s)  ->  03_extraction_soa_text.json
  [OK] studydesign_agent (16.0s)  ->  08_extraction_study_design.json
  |
Wave 2  (100.1s)
  [OK] biomedical_concept_agent (86.4s)  ->  14_extraction_biomedical_concepts.json
  [OK] execution_agent (100.1s)  ->  12_extraction_execution_model.json
  [OK] interventions_agent (21.7s)  ->  10_extraction_interventions.json
  [OK] scheduling_agent (98.8s)  ->  11_extraction_scheduling_logic.json
  |
Wave 3  (169.1s)
  [OK] enrichment_agent (169.1s)  ->  18_quality_enrichment.json
  [OK] postprocessing_agent (0.0s)  ->  15_quality_postprocessing.json
  [OK] reconciliation_agent (0.4s)  ->  16_quality_reconciliation.json
  [OK] validation_agent (0.0s)  ->  17_quality_validation.json
  |
Output
  [OK] Alexion_NCT04573309_Wilsons_usdm.json
  [OK] Alexion_NCT04573309_Wilsons_provenance.json
```

## Agent Results

| Step | Agent | Category | Status | Time (s) | Tokens | API Calls | Pages | Output File |
|------|-------|----------|--------|----------|--------|-----------|-------|-------------|
| 01 | metadata_agent | extraction | OK | 14.9 | 3,989 | 1 | 0-2 | `01_extraction_metadata.json` |
| 02 | soa_vision_agent | extraction | OK | 60.6 | 9,166 | 1 | 9-14,24,32,38,43 | `02_extraction_soa_vision.json` |
| 03 | soa_text_agent | extraction | OK | 972.9 | 34,849 | 1 | 9-14,24,32,38,43 | `03_extraction_soa_text.json` |
| 04 | narrative_agent | extraction | OK | 49.2 | 19,211 | 2 | 2-3,6,8,12-13,15-16,20,29 | `04_extraction_narrative.json` |
| 05 | docstructure_agent | extraction | OK | 36.1 | 12,631 | 1 | 0-4,6-7,20,25-26,34,41,45,47-50,52,54 | `05_extraction_document_structure.json` |
| 06 | eligibility_agent | extraction | OK | 44.0 | 12,458 | 1 | 29-35 | `06_extraction_eligibility.json` |
| 07 | objectives_agent | extraction | OK | 43.2 | 16,419 | 2 | 7-9,26-29 | `07_extraction_objectives.json` |
| 08 | studydesign_agent | extraction | OK | 16.0 | 13,109 | 1 | 0-5,7-11,19-21,23-27 | `08_extraction_study_design.json` |
| 09 | procedures_agent | extraction | OK | 48.7 | 18,809 | 1 | 2,4,9,13-16,18,20,22,30,37,41,43-44 | `09_extraction_procedures_devices.json` |
| 10 | interventions_agent | extraction | OK | 21.7 | 32,112 | 1 | 2-7,9-17,19-22,24-27,29-38,40-48 | `10_extraction_interventions.json` |
| 11 | scheduling_agent | extraction | OK | 98.8 | 22,374 | 1 | 2,4,10,12,15,17,20,25,27,29,32,37,39-42,57 | `11_extraction_scheduling_logic.json` |
| 12 | execution_agent | extraction | OK | 100.1 | 19,602 | 9 | 0-41,50-53,68 | `12_extraction_execution_model.json` |
| 13 | advanced_agent | extraction | OK | 20.9 | 19,535 | 1 | 0-29,69-71 | `13_extraction_advanced_entities.json` |
| 14 | biomedical_concept_agent | extraction | OK | 86.4 | 10,116 | 1 |  | `14_extraction_biomedical_concepts.json` |
| 15 | postprocessing_agent | quality | OK | 0.0 | 0 | 0 |  | `15_quality_postprocessing.json` |
| 16 | reconciliation_agent | quality | OK | 0.4 | 0 | 0 |  | `16_quality_reconciliation.json` |
| 17 | validation_agent | quality | OK | 0.0 | 0 | 0 |  | `17_quality_validation.json` |
| 18 | enrichment_agent | quality | OK | 169.1 | 0 | 62 |  | `18_quality_enrichment.json` |
| 19 | usdm-generator | support | OK | 0.0 | 0 | 0 |  | `19_support_usdm_generator.json` |
| 20 | provenance | support | OK | 0.0 | 0 | 0 |  | `20_support_provenance.json` |
| 00 | pdf-parser | support | OK | 0.7 | 0 | 0 | | |

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
- `Alexion_NCT04573309_Wilsons.pdf`
- `Alexion_NCT04573309_Wilsons_provenance.json`
- `Alexion_NCT04573309_Wilsons_usdm.json`
- `conformance_report.json`
- `id_mapping.json`
- `soa_page_010.png`
- `soa_page_011.png`
- `soa_page_012.png`
- `soa_page_013.png`
- `soa_page_014.png`
- `soa_page_015.png`
- `soa_page_025.png`
- `soa_page_033.png`
- `soa_page_039.png`
- `soa_page_044.png`
- `usdm_validation.json`
