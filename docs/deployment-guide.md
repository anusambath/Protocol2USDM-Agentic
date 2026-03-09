# Deployment Guide

## Prerequisites

- Python 3.9+
- Google API key (for Gemini models) or OpenAI/Anthropic keys
- PDF protocol files

## Installation

```bash
pip install -r requirements.txt
```

Required packages:
- `google-generativeai` — Gemini API client
- `PyPDF2` / `pdfplumber` — PDF parsing
- `Pillow` — Image processing
- `requests` — NCI EVS API calls
- `pytest` — Testing

## Environment Variables

```bash
# Required
GOOGLE_API_KEY=your-gemini-api-key

# Optional (for multi-model support)
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
```

Create a `.env` file in the project root or export these variables.

## Running the Pipeline

### Single Protocol

```python
from agents.pipeline import ExtractionPipeline, PipelineConfig

config = PipelineConfig(
    model="gemini-2.5-pro",
    output_dir="output",
    max_workers=4,
    enable_vision=True,
    enable_enrichment=True,
)

pipeline = ExtractionPipeline(config)
pipeline.initialize()
result = pipeline.run("input/test_trials/NCT12345/NCT12345_Protocol.pdf")
pipeline.shutdown()

print(f"Success: {result.success}")
print(f"Entities: {result.entity_count}")
print(f"USDM: {result.usdm_path}")
```

### Batch Processing

```python
import glob

pdfs = glob.glob("input/test_trials/*/*.pdf")
pipeline = ExtractionPipeline(config)
pipeline.initialize()

for pdf in pdfs:
    result = pipeline.run(pdf)
    print(f"{result.protocol_id}: {'OK' if result.success else 'FAIL'}")

pipeline.shutdown()
```

## Output Structure

```
output/
  {protocol_name}_{YYYYMMDD_HHMMSS}/
    01_extraction_metadata.json        # Step 1: Metadata
    02_extraction_soa_vision.json      # Step 2: SoA Vision
    ...                                # Steps 3-13: Other extraction agents
    14_quality_postprocessing.json     # Step 14: Post-processing
    15_quality_reconciliation.json     # Step 15: Reconciliation
    16_quality_validation.json         # Step 16: Validation
    17_quality_enrichment.json         # Step 17: Enrichment
    18_support_usdm_generator.json     # Step 18: USDM generation
    19_support_provenance.json         # Step 19: Provenance
    {protocol_name}_usdm.json         # USDM v4.0 JSON
    {protocol_name}_provenance.json   # Entity provenance
    result.md                          # Execution summary with timing/tokens
```

## Running Tests

```bash
# Unit tests (fast, no API keys needed)
python -m pytest tests/test_agents/ -v

# Golden file tests (requires API key + PDFs)
python -m pytest tests/test_agents/golden/test_golden.py --run-golden -v

# With coverage
python -m pytest tests/test_agents/ --cov=agents --cov-report=term-missing
```

## Production Considerations

- Set `max_workers` based on available CPU cores and API rate limits
- Use `skip_agents` to disable agents not needed for your use case
- Set `enable_vision=False` if protocols don't have SoA table images
- Set `enable_enrichment=False` if NCI EVS is not available
- Enable checkpoints (`enable_checkpoints=True`) for long-running batches
- Monitor `output/` directory size for large batch runs
