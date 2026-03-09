"""
Extraction module for Protocol2USDM pipeline.

This module contains the core extraction logic:
- soa_finder: Locate SoA pages in protocol PDFs
- header_analyzer: Vision-based structure extraction (epochs, encounters, timepoints)
- text_extractor: Text-based data extraction (activities, ticks)
- validator: Vision-based validation of text extraction
- pipeline: Orchestrates the complete extraction workflow
- metadata: Study identity and metadata extraction (Phase 2)
- eligibility: Inclusion/exclusion criteria extraction (Phase 1)
- objectives: Objectives and endpoints extraction (Phase 3)
- studydesign: Study design structure extraction (Phase 4)
- interventions: Interventions and products extraction (Phase 5)
- narrative: Document structure and abbreviations extraction (Phase 7)
- advanced: Amendments, geographic scope, sites extraction (Phase 8)
- execution: Execution model extraction for synthetic data (Phase 9)

Design Principle:
- Vision extracts STRUCTURE (column headers, row groups)
- Text extracts DATA (activity details, tick matrix)
- Vision validates Text (confirms ticks, flags hallucinations)

NOTE: Submodules are NOT imported here to avoid thread deadlocks during
parallel agent execution. Import directly from subpackages instead, e.g.:
  from extraction.narrative.extractor import extract_narrative_structure
"""
