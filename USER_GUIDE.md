# Protocol2USDM User Guide

## Installation

### Prerequisites
- Python 3.9+
- 4GB RAM minimum
- Internet connection (for LLM API calls and NCI EVS enrichment)

### Setup

```bash
git clone https://github.com/anusambath/Protocol2USDM_Agentic.git
cd Protocol2USDM_Agentic

python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows

pip install -r requirements.txt
```

### API Keys

Create a `.env` file (or copy from `.env.example`):

```bash
cp .env.example .env
```

You need at least one LLM provider configured:

| Provider | Environment Variable | How to Get |
|----------|---------------------|------------|
| Google Vertex AI | `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` | [Google Cloud Console](https://console.cloud.google.com/) — enable Vertex AI API |
| Google AI Studio | `GOOGLE_API_KEY` | [AI Studio](https://aistudio.google.com/) — may block clinical content |
| Anthropic | `CLAUDE_API_KEY` | [Anthropic Console](https://console.anthropic.com/) |
| OpenAI | `OPENAI_API_KEY` | [OpenAI Platform](https://platform.openai.com/api-keys) |
| CDISC | `CDISC_API_KEY` | [CDISC Library](https://library.cdisc.org/) — requires membership |

Use Vertex AI for Gemini models when processing clinical protocols. AI Studio's safety filters may block medical text.

### CDISC CORE Engine (Optional)

For conformance validation against CDISC rules:

```bash
python tools/core/download_core.py
```

---

## Running the Pipeline

### Basic Usage

```bash
python run_extraction.py protocol.pdf
```

This runs the full extraction pipeline with default settings (`gemini-2.5-pro`, 4 workers, vision enabled, enrichment enabled).

### CLI Options

```bash
python run_extraction.py protocol.pdf [options]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--model` | `gemini-2.5-pro` | Primary LLM model |
| `--fast-model` | (same as model) | Lighter model for straightforward extraction tasks |
| `--vision-model` | (same as model) | Model for SoA vision extraction |
| `--output-dir` | `output` | Output directory |
| `--workers` | `4` | Parallel workers per wave |
| `--no-vision` | off | Disable SoA vision extraction |
| `--no-enrichment` | off | Disable NCI EVS terminology enrichment |
| `--skip` | none | Agent IDs to skip (space-separated) |
| `--verbose` / `-v` | off | Verbose logging |

### Examples

```bash
# Use Claude with verbose logging
python run_extraction.py protocol.pdf --model claude-opus-4 --verbose

# Fast extraction with separate models
python run_extraction.py protocol.pdf --model gemini-2.5-pro --fast-model gemini-2.5-flash --vision-model gemini-2.5-flash

# Skip scheduling and execution agents
python run_extraction.py protocol.pdf --skip scheduling_agent execution_agent

# Batch processing
python run_extraction.py input/trial/*/Protocol.pdf --workers 2
```

### Checkpoint Resume

The pipeline creates checkpoints after each wave. If extraction is interrupted:

```bash
# List available checkpoints
python run_extraction.py --list-checkpoints

# Resume from a checkpoint
python run_extraction.py --resume-from-checkpoint checkpoints/checkpoint_<id>_<wave>.json

# Clean up old checkpoints
python run_extraction.py --clean-checkpoints
```


---

## Understanding the Output

### Output Directory

Each run creates a timestamped directory:

```
output/<protocol_name>_<timestamp>/
├── <protocol_name>_usdm.json           # Primary USDM v4.0 output
├── <protocol_name>_provenance.json     # Entity-level provenance (page sources)
├── 9_final_soa_provenance.json         # SoA cell-level provenance
├── id_mapping.json                     # Simple ID → UUID mapping
├── conformance_report.json             # CDISC CORE validation results
├── result.md                           # Extraction summary
└── <protocol_name>.pdf                 # Copy of source PDF
```

### USDM JSON Structure

The primary output follows the USDM v4.0 hierarchy:

```
Study
└── StudyVersion
    ├── titles[], studyIdentifiers[], studyPhase
    ├── organizations[], roles[]
    ├── narrativeContentItems[], abbreviations[]
    ├── amendments[], dateValues[]
    ├── biomedicalConcepts[], bcCategories[]
    ├── administrableProducts[], medicalDevices[]
    └── StudyDesign
        ├── arms[], epochs[], studyCells[]
        ├── objectives[], endpoints[], estimands[]
        ├── indications[], eligibilityCriteria[]
        ├── activities[], encounters[], procedures[]
        ├── studyInterventions[]
        ├── scheduleTimelines[] (with timings, instances)
        ├── analysisPopulations[], elements[]
        └── geographicScopes[]
```

### Provenance

Two provenance systems track extraction sources:

**Entity-level** (`<protocol>_provenance.json`): Maps each entity ID to the PDF pages it was extracted from and which agent produced it.

**Cell-level** (`9_final_soa_provenance.json`): Per-cell provenance for the SoA table. Each cell is tagged:

| Source | Meaning |
|--------|---------|
| `both` | Confirmed by text AND vision extraction |
| `text` | Text extraction only |
| `vision` | Vision extraction only |

---

## Model Selection

### Recommended Models

| Model | Provider | Speed | Notes |
|-------|----------|-------|-------|
| `gemini-2.5-pro` | Google | Fast | Default. Good accuracy, low cost. |
| `gemini-2.5-flash` | Google | Very fast | Good as `--fast-model` for simpler tasks. |
| `claude-opus-4` | Anthropic | Medium | High accuracy, higher cost. |
| `claude-sonnet-4` | Anthropic | Fast | Good balance. |
| `gpt-4o` | OpenAI | Medium | Good alternative. |

### LLM Configuration

Task-specific LLM parameters are defined in `llm_config.yaml`:

| Category | Temperature | Used For |
|----------|-------------|----------|
| `deterministic` | 0.0 | Factual extraction (SoA, metadata, eligibility) |
| `semantic` | 0.1 | Entity resolution, footnote conditions |
| `structured_gen` | 0.2 | State machines, endpoint algorithms |
| `narrative` | 0.3 | Amendments, narrative sections |

Override at runtime:

```bash
LLM_TEMPERATURE=0.1 python run_extraction.py protocol.pdf
```

---

## Web UI

### Launch

```bash
cd web-ui
npm install   # first time only
npm run dev
```

Open http://localhost:3000.

### Features

- **Protocol selector**: Choose from all pipeline runs
- **SoA table**: Color-coded cells by provenance (green = both, blue = text, orange = vision, red = no data)
- **Tabbed entity views**: Metadata, Eligibility, Objectives, Design, Interventions, Procedures, Narrative, Advanced
- **Source page preview**: Click any entity to see the PDF page it was extracted from
- **Validation results**: Schema validation and CDISC CORE conformance - NOT DONE
- **Raw JSON viewer**: Inspect the full USDM output - NOT DONE

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `GOOGLE_API_KEY not set` | Check `.env` file exists and has correct keys. Restart terminal. |
| Gemini blocks clinical content | Use Vertex AI instead of AI Studio. Set `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION`. |
| Missing visits in SoA | Check if correct pages were detected. Try `--verbose` to see page detection logs. |
| JSON parse errors | Try a different model (`--model gemini-2.5-pro` or `--model claude-opus-4`). |
| Schema validation errors | Most are auto-fixed during post-processing. Check `conformance_report.json` for details. |
| Vision validation issues | Low quality PDFs or complex table layouts. Try `--no-vision` to skip vision validation. |
| Pipeline interrupted | Use `--resume-from-checkpoint` to continue from last completed wave. |

---

## Extraction Pipeline Details

For a comprehensive breakdown of:
- Agent execution order (wave-based)
- Entity types produced by each agent
- Entity-to-USDM placement mapping
- Quality pipeline (post-processing, validation, reconciliation, enrichment)
- Biomedical concept generation
- USDM assembly and post-processing steps
- Gaps and unmapped protocol sections

See [docs/extraction-pipeline.md](docs/extraction-pipeline.md).
