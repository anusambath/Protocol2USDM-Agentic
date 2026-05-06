"""
CLI entry point for the USDM Fidelity Validator.

Usage:
    python -m fidelity_validator protocol.pdf study_usdm.json [--map section_map.yaml] [--output-dir ./results]
"""

import argparse
import sys
from pathlib import Path


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="USDM 4.0 Fidelity Validator — evaluates extraction faithfulness"
    )
    parser.add_argument("protocol_pdf", help="Path to the source protocol PDF")
    parser.add_argument("usdm_json", help="Path to the USDM 4.0 JSON file")
    parser.add_argument(
        "--map", "-m",
        default=None,
        help="Path to section map YAML (default: bundled usdm_section_map.yaml)"
    )
    parser.add_argument(
        "--output-dir", "-o",
        default=".",
        help="Directory for output reports (default: current directory)"
    )
    parser.add_argument(
        "--model",
        default="claude-sonnet-4",
        help="LLM model for judge calls (default: claude-sonnet-4)"
    )
    parser.add_argument(
        "--sections",
        nargs="*",
        default=None,
        help="Evaluate only these section IDs (default: all)"
    )
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="Skip LLM-based evaluation (presence and placement only)"
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    if not Path(args.protocol_pdf).exists():
        sys.exit(f"Error: Protocol PDF not found: {args.protocol_pdf}")
    if not Path(args.usdm_json).exists():
        sys.exit(f"Error: USDM JSON not found: {args.usdm_json}")
    
    # Run the pipeline
    from .layer1_section_map import load_section_map
    from .layer2_protocol_extractor import extract_protocol
    from .layer3_usdm_indexer import index_usdm
    from .layer4_comparator import evaluate_fidelity, generate_html_report, generate_json_report
    
    print(f"Loading section map...")
    section_map = load_section_map(args.map)
    
    print(f"Extracting protocol: {args.protocol_pdf}")
    protocol = extract_protocol(args.protocol_pdf, section_map)
    
    print(f"Indexing USDM: {args.usdm_json}")
    usdm_index = index_usdm(args.usdm_json, section_map)
    
    print(f"Evaluating fidelity (model={args.model})...")
    report = evaluate_fidelity(
        protocol=protocol,
        usdm_index=usdm_index,
        section_map=section_map,
        model=args.model,
        output_dir=args.output_dir,
    )
    
    # Generate outputs
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    json_path = str(output_dir / "fidelity_report.json")
    html_path = str(output_dir / "fidelity_report.html")
    
    generate_json_report(report, json_path)
    generate_html_report(report, html_path)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"FIDELITY REPORT SUMMARY")
    print(f"{'='*60}")
    print(f"Overall Score: {report.overall_score:.1%}")
    print(f"Findings: {report.critical_findings} critical, {report.major_findings} major, {report.minor_findings} minor")
    print(f"\nDimension Scores:")
    for dim, score in report.dimension_scores.items():
        print(f"  {dim:<15} {score:.1%}")
    print(f"\nReports saved to:")
    print(f"  {json_path}")
    print(f"  {html_path}")


if __name__ == "__main__":
    main()
