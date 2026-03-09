# Protocol2USDM

An agentic pipeline that extracts structured clinical trial data from protocol PDF documents and produces [CDISC USDM v4.0](https://www.cdisc.org/ddf) JSON output.

The system uses a wave-based multi-agent architecture where specialized extraction agents run in parallel, writing entities into a shared context store. A USDM generator then assembles the final JSON, followed by terminology enrichment, schema validation, and optional CDISC CORE conformance checking.

## What It Does

- Parses clinical trial protocol PDFs (text + vision)
- Extracts 40+ USDM entity types: metadata, eligibility criteria, objectives, endpoints, study design, interventions, Schedule of Assessments, and more
- Produces USDM v4.0 JSON aligned with the official CDISC schema
- Enriches entities with NCI EVS terminology codes
- Tracks provenance (which PDF pages each entity came from)
- Validates output against USDM schema and CDISC CORE rules
- Provides a web UI for reviewing results with color-coded provenance

## Quick Start

```bash
# Clone
git clone https://github.com/anusambath/Protocol2USDM_Agentic.git
cd Protocol2USDM_Agentic

# Install
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# Configure (Vertex AI recommended for clinical content)
cp .env.example .env
# Edit .env with your API keys

# Run
python run_extraction.py your_protocol.pdf
```

Output lands in `output/<protocol_name>/` with the primary file being `<protocol_name>_usdm.json`.

## Requirements

- Python 3.9+
- At least one LLM API key (Google Vertex AI, Anthropic, or OpenAI)
- Internet connection for API calls and NCI EVS enrichment

## Configuration

Create a `.env` file:

```bash
# Google Cloud Vertex AI (recommended for Gemini — avoids safety filter issues with clinical text)
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1

# Alternative: Google AI Studio (may block medical content)
GOOGLE_API_KEY=AIzaSy...

# Anthropic
CLAUDE_API_KEY=sk-ant-...

# OpenAI
OPENAI_API_KEY=sk-proj-...

# CDISC (optional, for conformance validation)
CDISC_API_KEY=...
```

## Usage

```bash
# Default: full extraction with gemini-2.5-pro
python run_extraction.py protocol.pdf

# Specify model
python run_extraction.py protocol.pdf --model claude-opus-4

# Use separate models for different tasks
python run_extraction.py protocol.pdf --model gemini-2.5-pro --fast-model gemini-2.5-flash --vision-model gemini-2.5-flash

# Parallel workers
python run_extraction.py protocol.pdf --workers 4

# Disable optional features
python run_extraction.py protocol.pdf --no-vision --no-enrichment

# Skip specific agents
python run_extraction.py protocol.pdf --skip scheduling_agent execution_agent

# Resume from checkpoint after interruption
python run_extraction.py --list-checkpoints
python run_extraction.py --resume-from-checkpoint checkpoints/checkpoint_<id>_<wave>.json

# Verbose logging
python run_extraction.py protocol.pdf --verbose
```

## Supported Models

| Model | Provider | Notes |
|-------|----------|-------|
| `gemini-2.5-pro` | Google | Default. Fast, good accuracy. |
| `gemini-2.5-flash` | Google | Lighter, good for fast-model tasks. |
| `claude-opus-4` | Anthropic | High accuracy, higher cost. |
| `claude-sonnet-4` | Anthropic | Good balance of speed and accuracy. |
| `gpt-4o` | OpenAI | Good alternative. |

Use Vertex AI (not AI Studio) for Gemini models when processing clinical content to avoid safety filter blocks.

## Pipeline Architecture

```
run_extraction.py
  └─ ExtractionPipeline
       ├─ Wave 0: PDF Parser, Metadata, Narrative, Doc Structure, SoA Vision
       ├─ Wave 1: Eligibility, Objectives, Study Design, Advanced, SoA Text
       ├─ Wave 2: Interventions, Procedures, Execution Model
       ├─ Wave 3: Scheduling, Biomedical Concepts, Post-Processing, Validation, Reconciliation, Enrichment
       ├─ USDM Generator (assembles all entities into USDM v4.0 JSON)
       ├─ Provenance Generator
       └─ CDISC CORE Validation (optional)
```

Agents within each wave run in parallel. See [docs/extraction-pipeline.md](docs/extraction-pipeline.md) for the full breakdown of agents, entity types, and USDM placement mapping.

## Output

```
output/<protocol_name>_<timestamp>/
├── <protocol_name>_usdm.json           # Primary USDM v4.0 output
├── <protocol_name>_provenance.json     # Entity-level provenance
├── 9_final_soa_provenance.json         # SoA cell-level provenance
├── id_mapping.json                     # Simple ID → UUID mapping
├── conformance_report.json             # CDISC CORE validation results
├── schema_validation.json              # Schema validation results
└── result.md                           # Extraction summary
```

## Web UI

A React/Next.js viewer for reviewing extraction results:

```bash
cd web-ui
npm install
npm run dev
# Open http://localhost:3000
```

Features:
- SoA table with color-coded provenance (green = confirmed by text+vision, blue = text only, orange = vision only)
- Tabbed views for Metadata, Eligibility, Objectives, Design, Interventions, etc.
- Source page preview with PDF page rendering
- Validation and conformance results
- Raw USDM JSON viewer

## Testing

```bash
pytest tests/ -q
```

## Documentation

- [Extraction Pipeline](docs/extraction-pipeline.md) — agent execution order, entity-to-USDM mapping, quality pipeline, gaps
- [Architecture](docs/ARCHITECTURE.md) — system design and component overview
- [User Guide](USER_GUIDE.md) — detailed usage instructions, model selection, troubleshooting
- [API Reference](docs/api-reference.md) — module and function reference
- [Configuration Guide](docs/configuration-guide.md) — LLM config, environment variables
- [Deployment Guide](docs/deployment-guide.md) — Docker, infrastructure

## Project Structure

```
Protocol2USDM_Agentic/
├── run_extraction.py         # CLI entry point
├── llm_providers.py          # LLM provider abstraction
├── llm_config.yaml           # LLM task-specific parameters
├── agents/                   # Agent framework
│   ├── orchestrator.py       # Wave-based execution planner
│   ├── pipeline.py           # Pipeline config and runner
│   ├── context_store.py      # Shared entity store
│   ├── extraction/           # 14 extraction agents
│   ├── quality/              # Post-processing, validation, reconciliation, enrichment
│   └── support/              # PDF parser, USDM generator, provenance
├── extraction/               # Domain extractors (called by agents)
├── core/                     # USDM types, schema, validation, provenance
├── enrichment/               # NCI EVS terminology enrichment
├── validation/               # USDM and CDISC CORE validation
├── web-ui/                   # React/Next.js protocol viewer
├── tools/                    # CDISC CORE engine download
├── testing/                  # Benchmarking and integration tests
├── tests/                    # Unit tests
└── docs/                     # Documentation
```

## License

Contact author for permission to use.
