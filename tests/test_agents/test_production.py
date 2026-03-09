"""
Tests for Phase 7 — Production modules (metrics, production config).
"""

import json
import threading
import time
import urllib.request
from unittest.mock import MagicMock, patch

import pytest

from agents.metrics import MetricsCollector, MetricsHTTPHandler, start_metrics_server
from agents.production import (
    RedisContextStore,
    RabbitMQMessageQueue,
    create_production_context_store,
    create_production_message_queue,
)
from agents.context_store import ContextStore, ContextEntity, EntityProvenance
from agents.message_queue import MessageQueue


# ============================================================
# MetricsCollector Tests
# ============================================================

class TestMetricsCollector:

    def test_create_collector(self):
        c = MetricsCollector()
        assert c is not None

    def test_inc_counter(self):
        c = MetricsCollector()
        c.inc_counter("test_counter")
        c.inc_counter("test_counter")
        output = c.format_prometheus()
        assert "test_counter 2" in output

    def test_inc_counter_with_labels(self):
        c = MetricsCollector()
        c.inc_counter("test_counter", labels={"agent_id": "meta"})
        output = c.format_prometheus()
        assert 'test_counter{agent_id="meta"} 1' in output

    def test_set_gauge(self):
        c = MetricsCollector()
        c.set_gauge("test_gauge", 42.5)
        output = c.format_prometheus()
        assert "test_gauge 42.5" in output

    def test_set_gauge_with_labels(self):
        c = MetricsCollector()
        c.set_gauge("test_gauge", 3.14, labels={"protocol": "NCT1"})
        output = c.format_prometheus()
        assert 'test_gauge{protocol="NCT1"} 3.14' in output

    def test_record_agent_execution_success(self):
        c = MetricsCollector()
        c.record_agent_execution("metadata_agent", True, 150.0, 0.92)
        output = c.format_prometheus()
        assert "p2u_agent_executions_total" in output
        assert "metadata_agent" in output

    def test_record_agent_execution_failure(self):
        c = MetricsCollector()
        c.record_agent_execution("soa_agent", False, 500.0)
        output = c.format_prometheus()
        assert "p2u_agent_failures_total" in output
        assert "soa_agent" in output

    def test_record_extraction_complete(self):
        c = MetricsCollector()
        c.record_extraction_complete("NCT12345", 5000.0, 142, True)
        output = c.format_prometheus()
        assert "p2u_extraction_duration_seconds" in output
        assert "p2u_context_store_entities" in output

    def test_format_prometheus_includes_help(self):
        c = MetricsCollector()
        c.inc_counter("p2u_agent_executions_total")
        output = c.format_prometheus()
        assert "# HELP p2u_agent_executions_total" in output
        assert "# TYPE p2u_agent_executions_total counter" in output

    def test_format_prometheus_includes_uptime(self):
        c = MetricsCollector()
        output = c.format_prometheus()
        assert "p2u_uptime_seconds" in output

    def test_thread_safety(self):
        c = MetricsCollector()
        errors = []

        def increment(n):
            try:
                for _ in range(100):
                    c.inc_counter("concurrent_counter")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=increment, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        output = c.format_prometheus()
        assert "concurrent_counter 400" in output

    def test_multiple_metrics(self):
        c = MetricsCollector()
        c.inc_counter("c1", labels={"a": "1"})
        c.inc_counter("c1", labels={"a": "2"})
        c.set_gauge("g1", 10.0)
        c.set_gauge("g2", 20.0)
        output = c.format_prometheus()
        assert 'c1{a="1"} 1' in output
        assert 'c1{a="2"} 1' in output
        assert "g1 10" in output
        assert "g2 20" in output


# ============================================================
# RedisContextStore Tests (without actual Redis)
# ============================================================

class TestRedisContextStore:

    def test_create_without_redis(self):
        store = RedisContextStore("redis://localhost:6379/0")
        assert store._connected is False

    def test_connect_without_redis_package(self):
        store = RedisContextStore()
        with patch.dict("sys.modules", {"redis": None}):
            result = store.connect()
        # Should fall back gracefully
        assert store._connected is False or result is False

    def test_add_entity_without_redis(self):
        """Should work as in-memory store when Redis is unavailable."""
        store = RedisContextStore()
        entity = ContextEntity(
            id="test-1", entity_type="metadata",
            data={"name": "Test"},
            provenance=EntityProvenance(entity_id="test-1", source_agent_id="test"),
        )
        store.add_entity(entity)
        assert store.entity_count == 1

    def test_query_entities_without_redis(self):
        store = RedisContextStore()
        store.add_entity(ContextEntity(
            id="e1", entity_type="arm", data={"name": "Arm A"},
        ))
        results = store.query_entities(entity_type="arm")
        assert len(results) == 1

    def test_sync_to_redis_not_connected(self):
        store = RedisContextStore()
        store.add_entity(ContextEntity(id="e1", entity_type="test", data={}))
        count = store.sync_to_redis()
        assert count == 0

    def test_sync_from_redis_not_connected(self):
        store = RedisContextStore()
        count = store.sync_from_redis()
        assert count == 0


# ============================================================
# RabbitMQMessageQueue Tests (without actual RabbitMQ)
# ============================================================

class TestRabbitMQMessageQueue:

    def test_create_without_rabbitmq(self):
        mq = RabbitMQMessageQueue("amqp://localhost:5672/")
        assert mq._connected is False

    def test_connect_without_pika_package(self):
        mq = RabbitMQMessageQueue()
        with patch.dict("sys.modules", {"pika": None}):
            result = mq.connect()
        assert mq._connected is False or result is False

    def test_publish_not_connected(self):
        mq = RabbitMQMessageQueue()
        result = mq.publish("agent.test", {"data": "test"})
        assert result is False

    def test_close_not_connected(self):
        mq = RabbitMQMessageQueue()
        mq.close()  # Should not raise

    def test_inherits_message_queue(self):
        mq = RabbitMQMessageQueue()
        assert isinstance(mq, MessageQueue)


# ============================================================
# Factory Function Tests
# ============================================================

class TestProductionFactories:

    def test_create_production_context_store_no_redis(self):
        with patch.dict("os.environ", {}, clear=True):
            store = create_production_context_store()
            assert isinstance(store, ContextStore)

    def test_create_production_message_queue_no_rabbitmq(self):
        with patch.dict("os.environ", {}, clear=True):
            mq = create_production_message_queue()
            assert isinstance(mq, MessageQueue)

    def test_create_production_context_store_with_redis_url(self):
        """When REDIS_URL is set but Redis is unavailable, falls back to in-memory."""
        with patch.dict("os.environ", {"REDIS_URL": "redis://fake:6379/0"}):
            store = create_production_context_store()
            assert isinstance(store, ContextStore)

    def test_create_production_mq_with_rabbitmq_url(self):
        """When RABBITMQ_URL is set but RabbitMQ is unavailable, falls back to in-memory."""
        with patch.dict("os.environ", {"RABBITMQ_URL": "amqp://fake:5672/"}):
            mq = create_production_message_queue()
            assert isinstance(mq, MessageQueue)
