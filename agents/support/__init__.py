"""
Support Agents - PDF Parsing, USDM Generation, Provenance, Checkpoint, and Error Handling.

These agents provide infrastructure support for the extraction pipeline:
- PDFParserAgent: PDF text/image extraction
- USDMGeneratorAgent: Context Store → USDM v4.0 JSON
- ProvenanceAgent: Provenance metadata and confidence tracking
- CheckpointAgent: Enhanced checkpoint and recovery
- ErrorHandler: Error classification, retry, and graceful degradation
"""
