"""
Prometheus metrics exporter for Protocol2USDM agent pipeline.

Exposes agent execution metrics, quality metrics, and system health
via a /metrics HTTP endpoint compatible with Prometheus scraping.
"""

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """A single metric data point."""
    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    metric_type: str = "gauge"  # gauge, counter, histogram
    help_text: str = ""
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()


class MetricsCollector:
    """
    Collects and exposes Prometheus-compatible metrics.

    Tracks:
    - Agent execution counts, durations, success/failure rates
    - Context Store entity counts by type
    - Message queue depth
    - Quality metrics (validation pass rate, enrichment coverage)
    - System health (uptime, memory)
    """

    def __init__(self):
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = {}
        self._help: Dict[str, str] = {}
        self._types: Dict[str, str] = {}
        self._lock = threading.Lock()
        self._start_time = time.time()

        # Register default metrics
        self._register_defaults()

    def _register_defaults(self):
        """Register default metric definitions."""
        self._help["p2u_agent_executions_total"] = "Total agent executions"
        self._types["p2u_agent_executions_total"] = "counter"

        self._help["p2u_agent_failures_total"] = "Total agent failures"
        self._types["p2u_agent_failures_total"] = "counter"

        self._help["p2u_agent_duration_seconds"] = "Agent execution duration in seconds"
        self._types["p2u_agent_duration_seconds"] = "gauge"

        self._help["p2u_agent_confidence_score"] = "Agent confidence score"
        self._types["p2u_agent_confidence_score"] = "gauge"

        self._help["p2u_context_store_entities"] = "Number of entities in Context Store"
        self._types["p2u_context_store_entities"] = "gauge"

        self._help["p2u_message_queue_depth"] = "Current message queue depth"
        self._types["p2u_message_queue_depth"] = "gauge"

        self._help["p2u_extraction_duration_seconds"] = "Full extraction pipeline duration"
        self._types["p2u_extraction_duration_seconds"] = "gauge"

        self._help["p2u_usdm_validation_failures_total"] = "USDM validation failures"
        self._types["p2u_usdm_validation_failures_total"] = "counter"

        self._help["p2u_enrichment_coverage_ratio"] = "NCI EVS enrichment coverage ratio"
        self._types["p2u_enrichment_coverage_ratio"] = "gauge"

        self._help["p2u_uptime_seconds"] = "Application uptime in seconds"
        self._types["p2u_uptime_seconds"] = "gauge"

    def _label_key(self, name: str, labels: Dict[str, str]) -> str:
        """Create a unique key from metric name + labels."""
        if not labels:
            return name
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def inc_counter(self, name: str, value: float = 1.0, labels: Dict[str, str] = None):
        """Increment a counter metric."""
        key = self._label_key(name, labels or {})
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + value

    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge metric."""
        key = self._label_key(name, labels or {})
        with self._lock:
            self._gauges[key] = value

    def record_agent_execution(self, agent_id: str, success: bool,
                                duration_ms: float, confidence: float = 0.0):
        """Record an agent execution event."""
        labels = {"agent_id": agent_id}
        self.inc_counter("p2u_agent_executions_total", labels=labels)
        if not success:
            self.inc_counter("p2u_agent_failures_total", labels=labels)
        self.set_gauge("p2u_agent_duration_seconds", duration_ms / 1000.0, labels=labels)
        if confidence > 0:
            self.set_gauge("p2u_agent_confidence_score", confidence, labels=labels)

    def record_extraction_complete(self, protocol_id: str, duration_ms: float,
                                    entity_count: int, success: bool):
        """Record a full extraction pipeline completion."""
        labels = {"protocol_id": protocol_id}
        self.set_gauge("p2u_extraction_duration_seconds", duration_ms / 1000.0, labels=labels)
        self.set_gauge("p2u_context_store_entities", entity_count, labels=labels)

    def format_prometheus(self) -> str:
        """Format all metrics in Prometheus text exposition format."""
        lines = []
        seen_help = set()

        # Uptime
        self.set_gauge("p2u_uptime_seconds", time.time() - self._start_time)

        with self._lock:
            # Counters
            for key, value in sorted(self._counters.items()):
                base_name = key.split("{")[0]
                if base_name not in seen_help:
                    if base_name in self._help:
                        lines.append(f"# HELP {base_name} {self._help[base_name]}")
                    lines.append(f"# TYPE {base_name} counter")
                    seen_help.add(base_name)
                lines.append(f"{key} {value}")

            # Gauges
            for key, value in sorted(self._gauges.items()):
                base_name = key.split("{")[0]
                if base_name not in seen_help:
                    if base_name in self._help:
                        lines.append(f"# HELP {base_name} {self._help[base_name]}")
                    lines.append(f"# TYPE {base_name} gauge")
                    seen_help.add(base_name)
                lines.append(f"{key} {value}")

        return "\n".join(lines) + "\n"


class MetricsHTTPHandler(BaseHTTPRequestHandler):
    """HTTP handler that serves Prometheus metrics."""

    collector: Optional[MetricsCollector] = None

    def do_GET(self):
        if self.path == "/metrics":
            body = self.collector.format_prometheus() if self.collector else ""
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "healthy"}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Suppress default request logging."""
        pass


def start_metrics_server(collector: MetricsCollector, port: int = 8000) -> HTTPServer:
    """Start a background HTTP server for Prometheus metrics scraping."""
    MetricsHTTPHandler.collector = collector
    server = HTTPServer(("0.0.0.0", port), MetricsHTTPHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"Metrics server started on port {port}")
    return server
