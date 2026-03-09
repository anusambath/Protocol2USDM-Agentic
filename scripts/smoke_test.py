"""
Production smoke test for Protocol2USDM.

Validates that the pipeline can initialize, create execution plans,
and run a basic extraction workflow. Does NOT require API keys or PDFs.
"""

import sys
import os
import json
import tempfile

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_imports():
    """Verify all agent modules can be imported."""
    print("[1/6] Testing imports...", end=" ")
    from agents.base import BaseAgent, AgentTask, AgentResult, AgentCapabilities
    from agents.registry import AgentRegistry
    from agents.context_store import ContextStore, ContextEntity
    from agents.message_queue import MessageQueue
    from agents.orchestrator import OrchestratorAgent
    from agents.pipeline import ExtractionPipeline, PipelineConfig, WAVE_CONFIG, create_all_agents
    from agents.metrics import MetricsCollector
    from agents.production import RedisContextStore, RabbitMQMessageQueue
    print("OK")


def test_agent_creation():
    """Verify all agents can be instantiated."""
    print("[2/6] Testing agent creation...", end=" ")
    from agents.pipeline import create_all_agents, PipelineConfig
    agents = create_all_agents(PipelineConfig())
    assert len(agents) >= 18, f"Expected 18+ agents, got {len(agents)}"
    print(f"OK ({len(agents)} agents)")


def test_pipeline_init():
    """Verify pipeline can initialize."""
    print("[3/6] Testing pipeline initialization...", end=" ")
    from agents.pipeline import ExtractionPipeline, PipelineConfig
    config = PipelineConfig(max_workers=2)
    pipeline = ExtractionPipeline(config)
    results = pipeline.initialize()
    agent_count = pipeline.get_agent_count()
    assert agent_count >= 18, f"Expected 18+ agents, got {agent_count}"
    pipeline.shutdown()
    print(f"OK ({agent_count} agents registered)")


def test_execution_plan():
    """Verify execution plan creation."""
    print("[4/6] Testing execution plan...", end=" ")
    from agents.pipeline import ExtractionPipeline, PipelineConfig
    pipeline = ExtractionPipeline(PipelineConfig(max_workers=2))
    pipeline.initialize()
    plan = pipeline.orchestrator.create_execution_plan(protocol_id="smoke-test")
    assert len(plan.waves) >= 3, f"Expected 3+ waves, got {len(plan.waves)}"
    pipeline.shutdown()
    print(f"OK ({len(plan.waves)} waves)")


def test_metrics():
    """Verify metrics collection works."""
    print("[5/6] Testing metrics...", end=" ")
    from agents.metrics import MetricsCollector
    collector = MetricsCollector()
    collector.record_agent_execution("test-agent", True, 150.0, 0.9)
    collector.record_extraction_complete("NCT-SMOKE", 5000.0, 42, True)
    output = collector.format_prometheus()
    assert "p2u_agent_executions_total" in output
    assert "p2u_uptime_seconds" in output
    print("OK")


def test_context_store_roundtrip():
    """Verify Context Store serialize/deserialize."""
    print("[6/6] Testing Context Store roundtrip...", end=" ")
    from agents.context_store import ContextStore, ContextEntity, EntityProvenance
    store = ContextStore()
    store.add_entity(ContextEntity(
        id="smoke-1", entity_type="metadata",
        data={"name": "Smoke Test Study"},
        provenance=EntityProvenance(entity_id="smoke-1", source_agent_id="test"),
    ))
    serialized = json.dumps(store.serialize())
    restored = ContextStore.deserialize(json.loads(serialized))
    assert restored.entity_count == 1
    print("OK")


def main():
    print("=" * 50)
    print("Protocol2USDM — Production Smoke Test")
    print("=" * 50)

    tests = [
        test_imports,
        test_agent_creation,
        test_pipeline_init,
        test_execution_plan,
        test_metrics,
        test_context_store_roundtrip,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

    print("=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 50)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
