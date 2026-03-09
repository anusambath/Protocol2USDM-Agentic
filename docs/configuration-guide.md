# Configuration Guide

## PipelineConfig Options

| Parameter | Type | Default | Description |
|---|---|---|---|
| `model` | str | `"gemini-2.5-pro"` | LLM model for extraction agents |
| `output_dir` | str | `"output"` | Directory for USDM/provenance output |
| `checkpoints_dir` | str | `"checkpoints"` | Directory for checkpoint files |
| `max_workers` | int | `4` | Max parallel agent threads |
| `dpi` | int | `100` | DPI for PDF image extraction |
| `enable_vision` | bool | `True` | Enable SoA vision extraction |
| `enable_enrichment` | bool | `True` | Enable NCI EVS enrichment |
| `enable_checkpoints` | bool | `True` | Enable checkpoint saving |
| `skip_agents` | list | `[]` | Agent IDs to skip |
| `fast_model` | str | `None` | Faster model for less-critical agents (narrative, docstructure, etc.) |
| `vision_model` | str | `None` | Model for SoA vision extraction (default: same as `model`) |

## Agent Execution Waves

The pipeline executes agents in dependency-ordered waves:

| Wave | Agents | Dependencies |
|---|---|---|
| 0 | pdf-parser, metadata, soa_vision, narrative, docstructure | None |
| 1 | soa_text, eligibility, objectives, studydesign, advanced | soa_vision / metadata |
| 2 | interventions, procedures | metadata + SoA/design |
| 3 | biomedical_concept, scheduling, execution | SoA + procedures |
| 4 | postprocessing, reconciliation, validation, enrichment | All extraction |
| 5 | usdm-generator, provenance | Quality agents |

Waves are computed dynamically from agent dependency declarations. Agents within the same wave run in parallel (up to `max_workers` threads).

## Skipping Agents

To skip specific agents, pass their IDs:

```python
config = PipelineConfig(
    skip_agents=["advanced_agent", "narrative_agent"]
)
```

## Model Selection

Supported models (set via `model` parameter or `--model` CLI flag):
- `gemini-2.5-pro` — Default, good balance of quality/cost (via Vertex AI)
- `gemini-2.5-flash` — Fast and cheap (via Vertex AI)
- `gemini-3-flash` — Latest Gemini preview (via Vertex AI)
- `claude-opus-4-6` — Anthropic, highest quality
- `claude-sonnet-4` — Anthropic, good balance of speed/accuracy
- `gpt-4o` — OpenAI alternative

Each extraction agent passes the model config to the underlying extractor. Use `fast_model` to assign a cheaper model to less-critical agents, and `vision_model` to use a specific model for SoA vision extraction.

## Checkpoint Recovery

When `enable_checkpoints=True`, the orchestrator saves a checkpoint after each wave. To resume from a checkpoint:

```python
from agents.support.checkpoint_agent import EnhancedCheckpoint

cp = EnhancedCheckpoint.load("checkpoints/checkpoint_wave_3.json")
# Inspect completed tasks, restore context store, etc.
```

## Logging

The pipeline uses Python's `logging` module. Configure verbosity:

```python
import logging
logging.basicConfig(level=logging.INFO)

# For debug output from specific agents:
logging.getLogger("agents.extraction").setLevel(logging.DEBUG)
```
