# Pipeline Result: NCT03155997_Eli-Lilly-and-Company_I3Y-MC-JPCF_e

**Status:** SUCCESS
**PDF:** `NCT03155997_Eli-Lilly-and-Company_I3Y-MC-JPCF_e.pdf`
**Model:** claude-opus-4-6
**Started:** 2026-03-10 11:15:22
**Finished:** 2026-03-10 11:28:19
**Duration:** 776.9s
**Entities:** 717
**Waves:** 4

## Statistics

| Metric | Value |
|--------|-------|
| Total Agents | 21 |
| Succeeded | 21 |
| Failed | 0 |
| Total Entities | 717 |
| Total Tokens | 215,194 |
| Total API Calls | 112 |
| Total Duration | 776.9s |

## Execution Flow

```
Wave 0  (57.8s)
  [OK] docstructure_agent (57.8s)  ->  05_extraction_document_structure.json
  [OK] metadata_agent (12.2s)  ->  01_extraction_metadata.json
  [OK] narrative_agent (31.6s)  ->  04_extraction_narrative.json
  [OK] pdf-parser (0.8s)
  [OK] provenance (0.0s)  ->  20_support_provenance.json
  [OK] soa_vision_agent (41.2s)  ->  02_extraction_soa_vision.json
  [OK] usdm-generator (1.4s)  ->  19_support_usdm_generator.json
  |
Wave 1  (148.2s)
  [OK] advanced_agent (10.8s)  ->  13_extraction_advanced_entities.json
  [OK] eligibility_agent (19.0s)  ->  06_extraction_eligibility.json
  [OK] objectives_agent (47.0s)  ->  07_extraction_objectives.json
  [OK] procedures_agent (38.0s)  ->  09_extraction_procedures_devices.json
  [OK] soa_text_agent (148.2s)  ->  03_extraction_soa_text.json
  [OK] studydesign_agent (15.9s)  ->  08_extraction_study_design.json
  |
Wave 2  (306.3s)
  [OK] biomedical_concept_agent (53.4s)  ->  14_extraction_biomedical_concepts.json
  [OK] execution_agent (306.3s)  ->  12_extraction_execution_model.json
  [OK] interventions_agent (43.9s)  ->  10_extraction_interventions.json
  [OK] scheduling_agent (101.1s)  ->  11_extraction_scheduling_logic.json
  |
Wave 3  (235.4s)
  [OK] enrichment_agent (235.4s)  ->  18_quality_enrichment.json
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
| 01 | metadata_agent | extraction | OK | 12.2 | 4,739 | 1 | 0-2 | `01_extraction_metadata.json` |
| 02 | soa_vision_agent | extraction | OK | 41.2 | 6,661 | 1 | 9-18 | `02_extraction_soa_vision.json` |
| 03 | soa_text_agent | extraction | OK | 148.2 | 26,071 | 2 | 9-18 | `03_extraction_soa_text.json` |
| 04 | narrative_agent | extraction | OK | 31.6 | 10,973 | 2 | 2,5,8,10,12,19,27 | `04_extraction_narrative.json` |
| 05 | docstructure_agent | extraction | OK | 57.8 | 17,016 | 1 | 0-4,14-19,21,31,34,36-37,42-43,45,47 | `05_extraction_document_structure.json` |
| 06 | eligibility_agent | extraction | OK | 19.0 | 4,707 | 1 | 28-30 | `06_extraction_eligibility.json` |
| 07 | objectives_agent | extraction | OK | 47.0 | 15,008 | 2 | 7-9,23-28 | `07_extraction_objectives.json` |
| 08 | studydesign_agent | extraction | OK | 15.9 | 19,907 | 1 | 0-3,5-28 | `08_extraction_study_design.json` |
| 09 | procedures_agent | extraction | OK | 38.0 | 13,383 | 1 | 11,13-16,19,24,42,44-45,47,49-51 | `09_extraction_procedures_devices.json` |
| 10 | interventions_agent | extraction | OK | 43.9 | 29,201 | 1 | 1-3,8-20,25-27,30-49 | `10_extraction_interventions.json` |
| 11 | scheduling_agent | extraction | OK | 101.1 | 23,775 | 1 | 9-10,12-19,26,31,34-35,37,39-42,45 | `11_extraction_scheduling_logic.json` |
| 12 | execution_agent | extraction | OK | 306.3 | 31,439 | 11 | 0-40,42-43,46-49,60,62,66,88 | `12_extraction_execution_model.json` |
| 13 | advanced_agent | extraction | OK | 10.8 | 4,680 | 1 | 0-3 | `13_extraction_advanced_entities.json` |
| 14 | biomedical_concept_agent | extraction | OK | 53.4 | 7,634 | 1 |  | `14_extraction_biomedical_concepts.json` |
| 15 | postprocessing_agent | quality | OK | 0.0 | 0 | 0 |  | `15_quality_postprocessing.json` |
| 16 | reconciliation_agent | quality | OK | 0.3 | 0 | 0 |  | `16_quality_reconciliation.json` |
| 17 | validation_agent | quality | OK | 0.0 | 0 | 0 |  | `17_quality_validation.json` |
| 18 | enrichment_agent | quality | OK | 235.4 | 0 | 85 |  | `18_quality_enrichment.json` |
| 19 | usdm-generator | support | OK | 1.4 | 0 | 0 |  | `19_support_usdm_generator.json` |
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
