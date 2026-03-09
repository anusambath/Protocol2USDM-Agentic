# API Reference — Agent Architecture

## Core Classes

### BaseAgent (`agents/base.py`)

Abstract base class for all agents.

```python
class BaseAgent:
    def __init__(self, agent_id: str, config: dict = None)
    def initialize(self) -> None
    def execute(self, task: AgentTask) -> AgentResult
    def terminate(self) -> None
    def get_capabilities(self) -> AgentCapabilities
    def set_context_store(self, store: ContextStore) -> None
    def set_message_queue(self, mq: MessageQueue) -> None
    def set_state(self, state: AgentState) -> None
```

**Properties:**
- `agent_id: str` — Unique identifier
- `state: AgentState` — Current lifecycle state (INITIALIZING, READY, EXECUTING, ERROR, TERMINATED)
- `metrics: dict` — Execution metrics (execution_time_ms, api_calls, token_usage)

### AgentTask

```python
@dataclass
class AgentTask:
    task_id: str
    agent_id: str
    task_type: str
    input_data: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    timeout_seconds: int = 300
```

### AgentResult

```python
@dataclass
class AgentResult:
    task_id: str
    agent_id: str
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    confidence_score: float = 0.0
    execution_time_ms: float = 0.0
```

### AgentCapabilities

```python
@dataclass
class AgentCapabilities:
    agent_type: str
    input_types: List[str]
    output_types: List[str]
    dependencies: List[str] = field(default_factory=list)
    supports_parallel: bool = True
    max_retries: int = 3
    timeout_seconds: int = 300
```

---

## Infrastructure

### AgentRegistry (`agents/registry.py`)

Manages agent registration, discovery, and lifecycle.

```python
class AgentRegistry:
    def register(self, agent: BaseAgent) -> None
    def unregister(self, agent_id: str) -> None
    def get(self, agent_id: str) -> Optional[BaseAgent]
    def get_all(self) -> List[BaseAgent]
    def get_by_capability(self, agent_type: str) -> List[BaseAgent]
    def get_dependency_map(self) -> Dict[str, Set[str]]
    def initialize_all(self) -> Dict[str, bool]
    def terminate_all(self) -> None
    @property
    def count(self) -> int
```

### ContextStore (`agents/context_store.py`)

In-memory entity storage with versioning, provenance, and query support.

```python
class ContextStore:
    def add_entity(self, entity: ContextEntity) -> None
    def get_entity(self, entity_id: str) -> Optional[ContextEntity]
    def update_entity(self, entity_id: str, data: dict) -> None
    def delete_entity(self, entity_id: str) -> None
    def query_entities(self, entity_type: str = None, **kwargs) -> List[ContextEntity]
    def add_relationship(self, source_id: str, target_id: str, rel_type: str) -> None
    def get_relationships(self, entity_id: str) -> List[EntityRelationship]
    def serialize(self) -> dict
    @classmethod
    def deserialize(cls, data: dict) -> "ContextStore"
    @property
    def entity_count(self) -> int
    @property
    def entity_types(self) -> List[str]
```

### MessageQueue (`agents/message_queue.py`)

Priority-based message passing between agents.

```python
class MessageQueue:
    def send(self, message: Message) -> None
    def receive(self, agent_id: str, timeout: float = None) -> Optional[Message]
    def broadcast(self, message: Message) -> None
    def get_dead_letters(self) -> List[Message]
    @property
    def pending_count(self) -> int
```

**Message Types:** REQUEST, RESPONSE, BROADCAST, ERROR, STATUS

### OrchestratorAgent (`agents/orchestrator.py`)

Coordinates agent execution via wave-based dependency resolution.

```python
class OrchestratorAgent(BaseAgent):
    def register_agent(self, agent: BaseAgent) -> None
    def build_dependency_graph(self) -> Dict[str, Set[str]]
    def create_execution_plan(self, protocol_id: str = "") -> ExecutionPlan
    def execute_plan(self, plan: ExecutionPlan) -> ExecutionStatus
```

---

## Extraction Agents (`agents/extraction/`)

All extraction agents extend `BaseExtractionAgent` which extends `BaseAgent`.

```python
class BaseExtractionAgent(BaseAgent):
    def extract(self, task: AgentTask) -> AgentResult  # Template method
    def execute(self, task: AgentTask) -> AgentResult   # Calls extract()
```

| Agent | ID | Wave | Output Types | Dependencies |
|---|---|---|---|---|
| MetadataAgent | `metadata_agent` | 0 | study_title, study_identifier, organization, indication, study_phase | None |
| SoAVisionAgent | `soa_vision_agent` | 0 | epoch, encounter, activity, soa_cell, header_structure, footnote | None |
| NarrativeAgent | `narrative_agent` | 0 | narrative_content | None |
| DocStructureAgent | `docstructure_agent` | 0 | document_section | None |
| SoATextAgent | `soa_text_agent` | 1 | soa_cell_text | soa_vision_extraction |
| EligibilityAgent | `eligibility_agent` | 1 | eligibility_criterion | metadata_extraction |
| ObjectivesAgent | `objectives_agent` | 1 | objective, endpoint | metadata_extraction |
| StudyDesignAgent | `studydesign_agent` | 1 | study_arm, study_epoch | metadata_extraction |
| AdvancedAgent | `advanced_agent` | 1 | amendment, geographic_scope | metadata_extraction |
| InterventionsAgent | `interventions_agent` | 2 | intervention | metadata_extraction, studydesign_extraction |
| ProceduresAgent | `procedures_agent` | 2 | procedure | metadata_extraction, soa_vision_extraction |
| BiomedicalConceptAgent | `biomedical_concept_agent` | 3 | biomedical_concept, biomedical_concept_category | soa_vision_extraction, soa_text_extraction, procedures_extraction |
| SchedulingAgent | `scheduling_agent` | 3 | timing | soa_vision_extraction, procedures_extraction |
| ExecutionAgent | `execution_agent` | 3 | execution_model | soa_vision_extraction, soa_text_extraction |

Each agent wraps an existing extractor in `extraction/{domain}/extractor.py` via lazy imports.

### BaseExtractionAgent Output Saving

All extraction agents automatically save their output to the timestamped output directory using the naming convention:

```
{step_number}_{category}_{agent_name}.json
```

Examples: `01_extraction_metadata.json`, `06_extraction_eligibility.json`

Step numbers are zero-padded and assigned per agent in `_AGENT_FILE_PREFIX` within `BaseExtractionAgent`.

---

## Quality Agents (`agents/quality/`)

| Agent | ID | Wave | Purpose |
|---|---|---|---|
| PostprocessingAgent | `postprocessing_agent` | 4 | SoA post-processing, superscript/footnote normalization, activity-group linking, name cleanup |
| ReconciliationAgent | `reconciliation_agent` | 4 | Duplicate detection, SoA vision/text merging, timepoint-aware encounter deduplication |
| ValidationAgent | `validation_agent` | 4 | USDM schema validation, CDISC CORE conformance, UUID conversion, provenance sync |
| EnrichmentAgent | `enrichment_agent` | 4 | NCI EVS terminology code assignment (concurrent, `max_concurrent=8`) |

Quality agents save output as `{step}_quality_{name}.json` (steps 14-17).

---

## Support Agents (`agents/support/`)

| Agent | ID | Wave | Purpose |
|---|---|---|---|
| PDFParserAgent | `pdf-parser` | 0 | PDF text/image extraction |
| USDMGeneratorAgent | `usdm-generator` | 5 | Context Store → USDM v4.0 JSON |
| ProvenanceAgent | `provenance` | 5 | Entity provenance tracking and reporting |
| CheckpointAgent | `checkpoint` | — | Execution state checkpointing and recovery |
| ErrorHandlerAgent | `error-handler` | — | Error classification, retry, graceful degradation |

Support agents save output as `{step}_support_{name}.json` (steps 18-19).

---

## Pipeline (`agents/pipeline.py`)

High-level API for running the complete extraction workflow.

```python
class ExtractionPipeline:
    def __init__(self, config: PipelineConfig = None)
    def initialize(self) -> Dict[str, bool]
    def run(self, pdf_path: str, protocol_id: str = "") -> PipelineResult
    def get_dependency_graph(self) -> Dict[str, List[str]]
    def get_agent_count(self) -> int
    def shutdown(self) -> None

class PipelineConfig:
    model: str = "gemini-2.5-pro"
    output_dir: str = "output"
    checkpoints_dir: str = "checkpoints"
    max_workers: int = 4
    dpi: int = 100
    enable_vision: bool = True
    enable_enrichment: bool = True
    enable_checkpoints: bool = True
    skip_agents: List[str] = field(default_factory=list)
    fast_model: Optional[str] = None    # Faster model for less-critical agents
    vision_model: Optional[str] = None  # Model for SoA vision extraction

class PipelineResult:
    execution_id: str
    protocol_id: str
    success: bool
    usdm_path: Optional[str]
    provenance_path: Optional[str]
    entity_count: int
    agent_results: Dict[str, bool]
    failed_agents: List[str]
    execution_time_ms: float
```

### Output Directory Structure

The pipeline creates a timestamped output directory per run:

```
output/{protocol_name}_{YYYYMMDD_HHMMSS}/
  # Extraction agents (steps 01-13)
  01_extraction_metadata.json
  02_extraction_soa_vision.json
  03_extraction_soa_text.json
  04_extraction_narrative.json
  05_extraction_document_structure.json
  06_extraction_eligibility.json
  07_extraction_objectives.json
  08_extraction_study_design.json
  09_extraction_procedures_devices.json
  10_extraction_interventions.json
  11_extraction_scheduling_logic.json
  12_extraction_execution_model.json
  13_extraction_advanced_entities.json
  # Quality agents (steps 14-17)
  14_quality_postprocessing.json
  15_quality_reconciliation.json
  16_quality_validation.json
  17_quality_enrichment.json
  # Support agents (steps 18-19)
  18_support_usdm_generator.json
  19_support_provenance.json
  # Final outputs
  {protocol_name}_usdm.json
  {protocol_name}_provenance.json
  result.md                          # Execution summary with timing/tokens
  soa_page_*.png                     # SoA page images
```

### result.md

The pipeline automatically generates a `result.md` markdown file containing:
- Execution flow diagram with per-wave and per-agent timing
- Agent results table (Step, Agent, Category, Status, Time, Tokens, API Calls, Output File)
- Statistics section (totals for agents, tokens, API calls, duration)
- Failed agents section (if any)
- Output files listing
