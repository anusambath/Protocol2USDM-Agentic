# Pipeline Result: Alexion_NCT04573309_Wilsons

**Status:** SUCCESS
**PDF:** `Alexion_NCT04573309_Wilsons.pdf`
**Model:** claude-opus-4-6
**Started:** 2026-03-10 10:50:42
**Finished:** 2026-03-10 11:03:32
**Duration:** 770.0s
**Entities:** 1037
**Waves:** 4

## Statistics

| Metric | Value |
|--------|-------|
| Total Agents | 21 |
| Succeeded | 21 |
| Failed | 0 |
| Total Entities | 1037 |
| Total Tokens | 273,009 |
| Total API Calls | 105 |
| Total Duration | 770.0s |

## Execution Flow

```
Wave 0  (59.1s)
  [OK] docstructure_agent (59.1s)  ->  05_extraction_document_structure.json
  [OK] metadata_agent (10.9s)  ->  01_extraction_metadata.json
  [OK] narrative_agent (52.5s)  ->  04_extraction_narrative.json
  [OK] pdf-parser (0.8s)
  [OK] provenance (0.0s)  ->  20_support_provenance.json
  [OK] soa_vision_agent (48.7s)  ->  02_extraction_soa_vision.json
  [OK] usdm-generator (1.7s)  ->  19_support_usdm_generator.json
  |
Wave 1  (330.9s)
  [OK] advanced_agent (27.4s)  ->  13_extraction_advanced_entities.json
  [OK] eligibility_agent (46.8s)  ->  06_extraction_eligibility.json
  [OK] objectives_agent (61.2s)  ->  07_extraction_objectives.json
  [OK] procedures_agent (89.0s)  ->  09_extraction_procedures_devices.json
  [OK] soa_text_agent (330.9s)  ->  03_extraction_soa_text.json
  [OK] studydesign_agent (22.0s)  ->  08_extraction_study_design.json
  |
Wave 2  (116.0s)
  [OK] biomedical_concept_agent (56.9s)  ->  14_extraction_biomedical_concepts.json
  [OK] execution_agent (116.0s)  ->  12_extraction_execution_model.json
  [OK] interventions_agent (27.8s)  ->  10_extraction_interventions.json
  [OK] scheduling_agent (103.7s)  ->  11_extraction_scheduling_logic.json
  |
Wave 3  (214.2s)
  [OK] enrichment_agent (214.2s)  ->  18_quality_enrichment.json
  [OK] postprocessing_agent (0.0s)  ->  15_quality_postprocessing.json
  [OK] reconciliation_agent (0.3s)  ->  16_quality_reconciliation.json
  [OK] validation_agent (0.0s)  ->  17_quality_validation.json
  |
Output
  [OK] Alexion_NCT04573309_Wilsons_usdm.json
  [OK] Alexion_NCT04573309_Wilsons_provenance.json
```

## Agent Results

| Step | Agent | Category | Status | Time (s) | Tokens | API Calls | Pages | Output File |
|------|-------|----------|--------|----------|--------|-----------|-------|-------------|
| 01 | metadata_agent | extraction | OK | 10.9 | 3,985 | 1 | 0-2 | `01_extraction_metadata.json` |
| 02 | soa_vision_agent | extraction | OK | 48.7 | 9,082 | 1 | 9-14,24,32,38,43 | `02_extraction_soa_vision.json` |
| 03 | soa_text_agent | extraction | OK | 330.9 | 57,891 | 2 | 9-14,24,32,38,43 | `03_extraction_soa_text.json` |
| 04 | narrative_agent | extraction | OK | 52.5 | 19,020 | 2 | 2-3,6,8,12-13,15-16,20,29 | `04_extraction_narrative.json` |
| 05 | docstructure_agent | extraction | OK | 59.1 | 18,277 | 1 | 0-4,6-7,20,25-26,34,41,45,47-50,52,54 | `05_extraction_document_structure.json` |
| 06 | eligibility_agent | extraction | OK | 46.8 | 12,418 | 1 | 29-35 | `06_extraction_eligibility.json` |
| 07 | objectives_agent | extraction | OK | 61.2 | 17,356 | 2 | 7-9,26-29 | `07_extraction_objectives.json` |
| 08 | studydesign_agent | extraction | OK | 22.0 | 13,266 | 1 | 0-5,7-11,19-21,23-27 | `08_extraction_study_design.json` |
| 09 | procedures_agent | extraction | OK | 89.0 | 20,691 | 1 | 2,4,9,13-16,18,20,22,30,37,41,43-44 | `09_extraction_procedures_devices.json` |
| 10 | interventions_agent | extraction | OK | 27.8 | 32,506 | 1 | 2-7,9-17,19-22,24-27,29-38,40-48 | `10_extraction_interventions.json` |
| 11 | scheduling_agent | extraction | OK | 103.7 | 22,722 | 1 | 2,4,10,12,15,17,20,25,27,29,32,37,39-42,57 | `11_extraction_scheduling_logic.json` |
| 12 | execution_agent | extraction | OK | 116.0 | 19,717 | 9 | 0-41,50-53,68 | `12_extraction_execution_model.json` |
| 13 | advanced_agent | extraction | OK | 27.4 | 16,836 | 1 | 0-29,69-71 | `13_extraction_advanced_entities.json` |
| 14 | biomedical_concept_agent | extraction | OK | 56.9 | 9,242 | 1 |  | `14_extraction_biomedical_concepts.json` |
| 15 | postprocessing_agent | quality | OK | 0.0 | 0 | 0 |  | `15_quality_postprocessing.json` |
| 16 | reconciliation_agent | quality | OK | 0.3 | 0 | 0 |  | `16_quality_reconciliation.json` |
| 17 | validation_agent | quality | OK | 0.0 | 0 | 0 |  | `17_quality_validation.json` |
| 18 | enrichment_agent | quality | OK | 214.2 | 0 | 80 |  | `18_quality_enrichment.json` |
| 19 | usdm-generator | support | OK | 1.7 | 0 | 0 |  | `19_support_usdm_generator.json` |
| 20 | provenance | support | OK | 0.0 | 0 | 0 |  | `20_support_provenance.json` |
| 00 | pdf-parser | support | OK | 0.8 | 0 | 0 | | |

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
