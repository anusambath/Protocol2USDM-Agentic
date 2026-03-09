# Developer Guide — Adding New Agents

## Overview

The agent architecture is designed to be extensible. Adding a new agent involves:

1. Creating the agent class
2. Registering it with the pipeline
3. Writing tests

## Step 1: Create the Agent Class

Create a new file in the appropriate directory:
- `agents/extraction/` — For extraction agents
- `agents/quality/` — For quality/validation agents
- `agents/support/` — For support/utility agents

### Extraction Agent Template

```python
"""MyDomain extraction agent."""

from agents.extraction.base_extraction_agent import BaseExtractionAgent
from agents.base import AgentCapabilities, AgentResult, AgentTask


class MyDomainAgent(BaseExtractionAgent):
    """Extracts my_domain entities from clinical trial protocols."""

    def __init__(self, config: dict = None):
        super().__init__(agent_id="mydomain_agent", config=config)

    def get_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            agent_type="mydomain_extraction",
            input_types=["pdf_text"],
            output_types=["my_entity_type"],
            dependencies=["metadata_extraction"],  # List agent_types this depends on
            supports_parallel=True,
            max_retries=3,
            timeout_seconds=300,
        )

    def extract(self, task: AgentTask) -> AgentResult:
        """Extract my_domain entities from the protocol."""
        # Lazy import to avoid circular dependencies
        from extraction.mydomain.extractor import extract_mydomain

        pdf_path = task.input_data.get("pdf_path", "")
        model = task.input_data.get("model", self._config.get("model", "gemini-2.5-pro"))

        try:
            raw_result = extract_mydomain(pdf_path, model=model)

            # Store entities in Context Store
            if self._context_store:
                for item in raw_result.get("entities", []):
                    entity = ContextEntity(
                        id=f"mydomain-{item['id']}",
                        entity_type="my_entity_type",
                        data=item,
                        provenance=EntityProvenance(
                            entity_id="", source_agent_id=self.agent_id,
                            confidence_score=0.85,
                        ),
                    )
                    self._context_store.add_entity(entity)

            return AgentResult(
                task_id=task.task_id, agent_id=self.agent_id,
                success=True, data=raw_result,
                confidence_score=0.85,
            )
        except Exception as e:
            return AgentResult(
                task_id=task.task_id, agent_id=self.agent_id,
                success=False, error=str(e),
            )
```

## Step 2: Register with the Pipeline

Add the agent to `agents/pipeline.py`:

1. Add to `WAVE_CONFIG` with the correct wave number:
```python
WAVE_CONFIG = {
    ...
    "mydomain_agent": 1,  # Wave based on dependencies
}
```

2. Add to `create_all_agents()`:
```python
from agents.extraction.mydomain_agent import MyDomainAgent
agents.append(MyDomainAgent(config=agent_config))
```

## Step 3: Write Tests

Create `tests/test_agents/test_mydomain_agent.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from agents.extraction.mydomain_agent import MyDomainAgent
from agents.base import AgentTask
from agents.context_store import ContextStore

class TestMyDomainAgent:
    def setup_method(self):
        self.agent = MyDomainAgent(config={"model": "test"})
        self.agent.initialize()
        self.store = ContextStore()
        self.agent.set_context_store(self.store)

    def test_capabilities(self):
        caps = self.agent.get_capabilities()
        assert caps.agent_type == "mydomain_extraction"
        assert "metadata_extraction" in caps.dependencies

    @patch("extraction.mydomain.extractor.extract_mydomain")
    def test_extract_success(self, mock_extract):
        mock_extract.return_value = {"entities": [{"id": "1", "name": "Test"}]}
        task = AgentTask(
            task_id="t1", agent_id="mydomain_agent",
            task_type="extract",
            input_data={"pdf_path": "test.pdf"},
        )
        result = self.agent.execute(task)
        assert result.success
```

## Key Patterns

- **Lazy imports:** Always import extractors inside `extract()`, not at module level
- **Mock targets:** When testing, mock `extraction.{domain}.extractor.{function}`, not the agent module
- **Context Store:** Use `self._context_store` (set via `set_context_store()`)
- **AgentCapabilities:** Only use fields: `agent_type`, `input_types`, `output_types`, `dependencies`, `supports_parallel`, `max_retries`, `timeout_seconds`
- **entity_count / entity_types:** These are `@property` on ContextStore (no parentheses needed)

## Architecture Diagram

```
PDF Input
    │
    ▼
┌─────────────────────────────────────────────┐
│  Wave 0: Independent Agents                 │
│  pdf-parser, metadata, soa_vision,          │
│  narrative, docstructure                    │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│  Wave 1: Metadata/SoA-Vision-dependent      │
│  soa_text, eligibility, objectives,         │
│  studydesign, advanced                      │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│  Wave 2-3: Multi-dependency                 │
│  interventions, procedures,                 │
│  biomedical_concept, scheduling, execution  │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│  Wave 4: Quality                            │
│  postprocessing, reconciliation,            │
│  validation, enrichment                     │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│  Wave 5: Output                             │
│  usdm-generator, provenance                │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
    USDM v4.0 JSON + Provenance JSON
```
