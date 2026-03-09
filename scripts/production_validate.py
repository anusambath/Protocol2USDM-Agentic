"""
Production validation script for Protocol2USDM.

Runs a comprehensive validation before go-live:
1. Smoke tests (no API key needed)
2. Infrastructure connectivity (Redis, RabbitMQ)
3. Metrics endpoint health
4. Single protocol extraction (requires API key + PDF)

Usage:
    python scripts/production_validate.py [--full]
"""

import argparse
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def check_imports():
    """Validate all modules import correctly."""
    print("[1/7] Checking imports...", end=" ")
    try:
        from agents.pipeline import ExtractionPipeline, PipelineConfig, create_all_agents
        from agents.metrics import MetricsCollector, start_metrics_server
        from agents.production import (
            RedisContextStore, RabbitMQMessageQueue,
            create_production_context_store, create_production_message_queue,
        )
        print("OK")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def check_agent_creation():
    """Validate all agents can be created."""
    print("[2/7] Creating agents...", end=" ")
    try:
        from agents.pipeline import create_all_agents, PipelineConfig
        agents = create_all_agents(PipelineConfig())
        print(f"OK ({len(agents)} agents)")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def check_pipeline_init():
    """Validate pipeline initialization."""
    print("[3/7] Initializing pipeline...", end=" ")
    try:
        from agents.pipeline import ExtractionPipeline, PipelineConfig
        pipeline = ExtractionPipeline(PipelineConfig(max_workers=2))
        pipeline.initialize()
        count = pipeline.get_agent_count()
        pipeline.shutdown()
        print(f"OK ({count} agents)")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def check_redis():
    """Check Redis connectivity."""
    print("[4/7] Checking Redis...", end=" ")
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        print("SKIP (REDIS_URL not set)")
        return True  # Not required
    try:
        from agents.production import RedisContextStore
        store = RedisContextStore(redis_url)
        connected = store.connect()
        print("OK" if connected else "FAIL")
        return connected
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def check_rabbitmq():
    """Check RabbitMQ connectivity."""
    print("[5/7] Checking RabbitMQ...", end=" ")
    rabbitmq_url = os.environ.get("RABBITMQ_URL")
    if not rabbitmq_url:
        print("SKIP (RABBITMQ_URL not set)")
        return True  # Not required
    try:
        from agents.production import RabbitMQMessageQueue
        mq = RabbitMQMessageQueue(rabbitmq_url)
        connected = mq.connect()
        if connected:
            mq.close()
        print("OK" if connected else "FAIL")
        return connected
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def check_metrics():
    """Validate metrics collection and formatting."""
    print("[6/7] Checking metrics...", end=" ")
    try:
        from agents.metrics import MetricsCollector
        collector = MetricsCollector()
        collector.record_agent_execution("test", True, 100.0, 0.9)
        output = collector.format_prometheus()
        assert "p2u_agent_executions_total" in output
        assert "p2u_uptime_seconds" in output
        print("OK")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def check_extraction(pdf_path: str = None):
    """Run a single extraction (requires API key + PDF)."""
    print("[7/7] Running extraction...", end=" ")
    if not pdf_path:
        # Try to find a protocol
        import glob
        pdfs = glob.glob("input/test_trials/*/*.pdf")
        if not pdfs:
            print("SKIP (no PDFs found)")
            return True
        pdf_path = pdfs[0]

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("SKIP (GOOGLE_API_KEY not set)")
        return True

    try:
        from agents.pipeline import ExtractionPipeline, PipelineConfig
        pipeline = ExtractionPipeline(PipelineConfig(max_workers=2))
        pipeline.initialize()
        result = pipeline.run(pdf_path)
        pipeline.shutdown()
        status = "OK" if result.success else "PARTIAL"
        print(f"{status} ({result.entity_count} entities, {result.execution_time_ms:.0f}ms)")
        return result.success or result.entity_count > 0
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Production Validation")
    parser.add_argument("--full", action="store_true", help="Run full validation including extraction")
    parser.add_argument("--pdf", help="Path to protocol PDF for extraction test")
    args = parser.parse_args()

    print("=" * 60)
    print("Protocol2USDM — Production Validation")
    print("=" * 60)

    checks = [
        check_imports,
        check_agent_creation,
        check_pipeline_init,
        check_redis,
        check_rabbitmq,
        check_metrics,
    ]

    if args.full:
        checks.append(lambda: check_extraction(args.pdf))
    else:
        checks.append(lambda: (print("[7/7] Extraction... SKIP (use --full)"), True)[1])

    passed = sum(1 for check in checks if check())
    failed = len(checks) - passed

    print("=" * 60)
    print(f"Results: {passed}/{len(checks)} passed")
    if failed:
        print("PRODUCTION VALIDATION FAILED")
    else:
        print("PRODUCTION VALIDATION PASSED")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
