"""
User Acceptance Testing (UAT) runner for Protocol2USDM.

Runs the extraction pipeline on a set of protocols and generates
a UAT report with quality metrics, entity counts, and confidence
distributions for stakeholder review.

Usage:
    python scripts/uat_runner.py [--protocols-dir input/test_trials] [--output-dir uat_results]
"""

import argparse
import glob
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.pipeline import ExtractionPipeline, PipelineConfig, PipelineResult


@dataclass
class UATProtocolResult:
    """Result for a single protocol in UAT."""
    protocol_id: str = ""
    pdf_path: str = ""
    success: bool = False
    entity_count: int = 0
    failed_agents: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0
    usdm_path: Optional[str] = None
    provenance_path: Optional[str] = None
    error: Optional[str] = None


@dataclass
class UATReport:
    """Aggregated UAT report."""
    timestamp: str = ""
    total_protocols: int = 0
    successful: int = 0
    failed: int = 0
    total_entities: int = 0
    avg_execution_time_ms: float = 0.0
    avg_entities_per_protocol: float = 0.0
    protocol_results: List[Dict] = field(default_factory=list)
    agent_failure_counts: Dict[str, int] = field(default_factory=dict)


def run_uat(protocols_dir: str, output_dir: str, max_protocols: int = 20) -> UATReport:
    """Run UAT on protocols in the given directory."""
    # Find protocol PDFs
    patterns = [
        os.path.join(protocols_dir, "*", "*_Protocol.pdf"),
        os.path.join(protocols_dir, "*", "*.pdf"),
        os.path.join(protocols_dir, "*.pdf"),
    ]
    pdf_files = []
    for pattern in patterns:
        pdf_files.extend(glob.glob(pattern))
    pdf_files = sorted(set(pdf_files))[:max_protocols]

    if not pdf_files:
        print(f"No PDF files found in {protocols_dir}")
        return UATReport(timestamp=datetime.now().isoformat())

    print(f"Found {len(pdf_files)} protocols for UAT")
    print("=" * 60)

    # Initialize pipeline
    config = PipelineConfig(
        output_dir=output_dir,
        max_workers=4,
        enable_vision=True,
        enable_enrichment=True,
    )
    pipeline = ExtractionPipeline(config)
    pipeline.initialize()

    report = UATReport(
        timestamp=datetime.now().isoformat(),
        total_protocols=len(pdf_files),
    )

    results: List[UATProtocolResult] = []

    for i, pdf_path in enumerate(pdf_files, 1):
        protocol_id = os.path.splitext(os.path.basename(pdf_path))[0]
        print(f"[{i}/{len(pdf_files)}] {protocol_id}...", end=" ", flush=True)

        uat_result = UATProtocolResult(
            protocol_id=protocol_id,
            pdf_path=pdf_path,
        )

        try:
            result = pipeline.run(pdf_path, protocol_id=protocol_id)
            uat_result.success = result.success
            uat_result.entity_count = result.entity_count
            uat_result.failed_agents = result.failed_agents
            uat_result.execution_time_ms = result.execution_time_ms
            uat_result.usdm_path = result.usdm_path
            uat_result.provenance_path = result.provenance_path

            status = "OK" if result.success else "PARTIAL"
            print(f"{status} ({result.entity_count} entities, "
                  f"{result.execution_time_ms:.0f}ms)")

            if result.success:
                report.successful += 1
            else:
                report.failed += 1

            for agent_id in result.failed_agents:
                report.agent_failure_counts[agent_id] = (
                    report.agent_failure_counts.get(agent_id, 0) + 1
                )

        except Exception as e:
            uat_result.error = str(e)
            report.failed += 1
            print(f"FAIL: {e}")

        results.append(uat_result)
        report.total_entities += uat_result.entity_count

    pipeline.shutdown()

    # Calculate averages
    successful_results = [r for r in results if r.success]
    if successful_results:
        report.avg_execution_time_ms = (
            sum(r.execution_time_ms for r in successful_results) / len(successful_results)
        )
        report.avg_entities_per_protocol = (
            sum(r.entity_count for r in successful_results) / len(successful_results)
        )

    report.protocol_results = [
        {
            "protocol_id": r.protocol_id,
            "success": r.success,
            "entity_count": r.entity_count,
            "failed_agents": r.failed_agents,
            "execution_time_ms": r.execution_time_ms,
            "error": r.error,
        }
        for r in results
    ]

    return report


def save_report(report: UATReport, output_dir: str):
    """Save UAT report as JSON."""
    os.makedirs(output_dir, exist_ok=True)
    report_path = os.path.join(output_dir, "uat_report.json")
    with open(report_path, "w") as f:
        json.dump({
            "timestamp": report.timestamp,
            "total_protocols": report.total_protocols,
            "successful": report.successful,
            "failed": report.failed,
            "total_entities": report.total_entities,
            "avg_execution_time_ms": report.avg_execution_time_ms,
            "avg_entities_per_protocol": report.avg_entities_per_protocol,
            "agent_failure_counts": report.agent_failure_counts,
            "protocol_results": report.protocol_results,
        }, f, indent=2)
    print(f"\nReport saved to {report_path}")


def print_summary(report: UATReport):
    """Print UAT summary."""
    print("\n" + "=" * 60)
    print("UAT SUMMARY")
    print("=" * 60)
    print(f"Protocols tested:    {report.total_protocols}")
    print(f"Successful:          {report.successful}")
    print(f"Failed:              {report.failed}")
    print(f"Success rate:        {report.successful / max(report.total_protocols, 1) * 100:.1f}%")
    print(f"Total entities:      {report.total_entities}")
    print(f"Avg entities/proto:  {report.avg_entities_per_protocol:.1f}")
    print(f"Avg execution time:  {report.avg_execution_time_ms:.0f}ms")

    if report.agent_failure_counts:
        print(f"\nAgent failures:")
        for agent_id, count in sorted(report.agent_failure_counts.items(), key=lambda x: -x[1]):
            print(f"  {agent_id}: {count}")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Protocol2USDM UAT Runner")
    parser.add_argument("--protocols-dir", default="input/test_trials",
                        help="Directory containing protocol PDFs")
    parser.add_argument("--output-dir", default="uat_results",
                        help="Directory for UAT output")
    parser.add_argument("--max-protocols", type=int, default=20,
                        help="Maximum protocols to test")
    args = parser.parse_args()

    report = run_uat(args.protocols_dir, args.output_dir, args.max_protocols)
    save_report(report, args.output_dir)
    print_summary(report)

    return 0 if report.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
