# Pipeline Result: NCT02864992_EMD-Serono-Research-and-Development-Institute_MS200095-0022_NA

**Status:** SUCCESS
**PDF:** `NCT02864992_EMD-Serono-Research-and-Development-Institute_MS200095-0022_NA.pdf`
**Model:** claude-opus-4-6
**Started:** 2026-03-10 10:35:44
**Finished:** 2026-03-10 10:45:37
**Duration:** 593.0s
**Entities:** 818
**Waves:** 4

## Statistics

| Metric | Value |
|--------|-------|
| Total Agents | 21 |
| Succeeded | 21 |
| Failed | 0 |
| Total Entities | 818 |
| Total Tokens | 225,084 |
| Total API Calls | 86 |
| Total Duration | 593.0s |

## Execution Flow

```
Wave 0  (84.8s)
  [OK] docstructure_agent (84.8s)  ->  05_extraction_document_structure.json
  [OK] metadata_agent (14.8s)  ->  01_extraction_metadata.json
  [OK] narrative_agent (25.0s)  ->  04_extraction_narrative.json
  [OK] pdf-parser (2.5s)
  [OK] provenance (0.0s)  ->  20_support_provenance.json
  [OK] soa_vision_agent (63.9s)  ->  02_extraction_soa_vision.json
  [OK] usdm-generator (0.3s)  ->  19_support_usdm_generator.json
  |
Wave 1  (138.1s)
  [OK] advanced_agent (7.9s)  ->  13_extraction_advanced_entities.json
  [OK] eligibility_agent (121.6s)  ->  06_extraction_eligibility.json
  [OK] objectives_agent (92.1s)  ->  07_extraction_objectives.json
  [OK] procedures_agent (70.8s)  ->  09_extraction_procedures_devices.json
  [OK] soa_text_agent (138.1s)  ->  03_extraction_soa_text.json
  [OK] studydesign_agent (27.3s)  ->  08_extraction_study_design.json
  |
Wave 2  (179.7s)
  [OK] biomedical_concept_agent (54.6s)  ->  14_extraction_biomedical_concepts.json
  [OK] execution_agent (179.7s)  ->  12_extraction_execution_model.json
  [OK] interventions_agent (29.6s)  ->  10_extraction_interventions.json
  [OK] scheduling_agent (96.2s)  ->  11_extraction_scheduling_logic.json
  |
Wave 3  (169.1s)
  [OK] enrichment_agent (169.1s)  ->  18_quality_enrichment.json
  [OK] postprocessing_agent (0.0s)  ->  15_quality_postprocessing.json
  [OK] reconciliation_agent (0.1s)  ->  16_quality_reconciliation.json
  [OK] validation_agent (0.0s)  ->  17_quality_validation.json
  |
Output
  [OK] NCT02864992_EMD-Serono-Research-and-Development-Institute_MS200095-0022_NA_usdm.json
  [OK] NCT02864992_EMD-Serono-Research-and-Development-Institute_MS200095-0022_NA_provenance.json
```

## Agent Results

| Step | Agent | Category | Status | Time (s) | Tokens | API Calls | Pages | Output File |
|------|-------|----------|--------|----------|--------|-----------|-------|-------------|
| 01 | metadata_agent | extraction | OK | 14.8 | 5,535 | 1 | 0-2 | `01_extraction_metadata.json` |
| 02 | soa_vision_agent | extraction | OK | 63.9 | 9,063 | 1 | 5-6,21-25,54-56 | `02_extraction_soa_vision.json` |
| 03 | soa_text_agent | extraction | OK | 138.1 | 38,316 | 2 | 5-6,21-25,54-56 | `03_extraction_soa_text.json` |
| 04 | narrative_agent | extraction | OK | 25.0 | 6,571 | 2 | 1,7,10 | `04_extraction_narrative.json` |
| 05 | docstructure_agent | extraction | OK | 84.8 | 15,153 | 1 | 0-5,11,15,23-24,26,30,32,37,40-41,43-44,47-48 | `05_extraction_document_structure.json` |
| 06 | eligibility_agent | extraction | OK | 121.6 | 16,949 | 1 | 15-17,39-44,46-48 | `06_extraction_eligibility.json` |
| 07 | objectives_agent | extraction | OK | 92.1 | 29,730 | 2 | 0-5,10-16,19-21 | `07_extraction_objectives.json` |
| 08 | studydesign_agent | extraction | OK | 27.3 | 12,930 | 1 | 0-5,12-14,25-29 | `08_extraction_study_design.json` |
| 09 | procedures_agent | extraction | OK | 70.8 | 15,971 | 1 | 2-3,7-9,11-12,15-16,19,21-25 | `09_extraction_procedures_devices.json` |
| 10 | interventions_agent | extraction | OK | 29.6 | 12,142 | 1 | 8-10,39-41,43-49 | `10_extraction_interventions.json` |
| 11 | scheduling_agent | extraction | OK | 96.2 | 24,863 | 1 | 1-2,14,23-24,28,36-37,40-41,43-47,53-56,58 | `11_extraction_scheduling_logic.json` |
| 12 | execution_agent | extraction | OK | 179.7 | 24,105 | 11 | 0-40,42,45,54-60,62,64,68-70,78,111,115 | `12_extraction_execution_model.json` |
| 13 | advanced_agent | extraction | OK | 7.9 | 4,794 | 1 | 0-3,5 | `13_extraction_advanced_entities.json` |
| 14 | biomedical_concept_agent | extraction | OK | 54.6 | 8,962 | 1 |  | `14_extraction_biomedical_concepts.json` |
| 15 | postprocessing_agent | quality | OK | 0.0 | 0 | 0 |  | `15_quality_postprocessing.json` |
| 16 | reconciliation_agent | quality | OK | 0.1 | 0 | 0 |  | `16_quality_reconciliation.json` |
| 17 | validation_agent | quality | OK | 0.0 | 0 | 0 |  | `17_quality_validation.json` |
| 18 | enrichment_agent | quality | OK | 169.1 | 0 | 59 |  | `18_quality_enrichment.json` |
| 19 | usdm-generator | support | OK | 0.3 | 0 | 0 |  | `19_support_usdm_generator.json` |
| 20 | provenance | support | OK | 0.0 | 0 | 0 |  | `20_support_provenance.json` |
| 00 | pdf-parser | support | OK | 2.5 | 0 | 0 | | |

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
