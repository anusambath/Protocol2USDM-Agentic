"""
CLI entry point for Protocol2USDM extraction pipeline.

Usage:
    # Run extraction on a PDF
    python run_extraction.py path/to/protocol.pdf
    python run_extraction.py path/to/protocol.pdf --model gemini-2.0-flash
    python run_extraction.py input/test_trials/*.pdf --workers 2
    
    # List available checkpoints
    python run_extraction.py --list-checkpoints
    
    # Resume from a checkpoint
    python run_extraction.py --resume-from-checkpoint checkpoints/checkpoint_<id>_<wave>.json
"""

import argparse
import glob
import logging
import os
import sys

from dotenv import load_dotenv
load_dotenv()

from agents.pipeline import ExtractionPipeline, PipelineConfig


def clean_checkpoints():
    """Delete all checkpoint files."""
    checkpoints_dir = "checkpoints"
    if not os.path.exists(checkpoints_dir):
        print("No checkpoints directory found.")
        return 0

    checkpoint_files = glob.glob(os.path.join(checkpoints_dir, "checkpoint_*.json"))
    
    if not checkpoint_files:
        print("No checkpoint files found.")
        return 0

    print(f"Found {len(checkpoint_files)} checkpoint file(s).")
    print("This will delete ALL checkpoint files.")
    
    # Ask for confirmation
    response = input("Are you sure you want to delete all checkpoints? (yes/no): ").strip().lower()
    
    if response not in ['yes', 'y']:
        print("Cleanup cancelled.")
        return 0
    
    deleted_count = 0
    failed_count = 0
    
    for filepath in checkpoint_files:
        try:
            os.remove(filepath)
            deleted_count += 1
        except Exception as e:
            print(f"Failed to delete {filepath}: {e}")
            failed_count += 1
    
    print(f"\nCleanup complete:")
    print(f"  Deleted: {deleted_count} file(s)")
    if failed_count > 0:
        print(f"  Failed: {failed_count} file(s)")
    
    return 0


def list_checkpoints():
    """List all available checkpoint files."""
    checkpoints_dir = "checkpoints"
    if not os.path.exists(checkpoints_dir):
        print("No checkpoints directory found.")
        return 0

    checkpoint_files = sorted(glob.glob(os.path.join(checkpoints_dir, "checkpoint_*.json")))
    
    if not checkpoint_files:
        print("No checkpoint files found.")
        return 0

    print(f"Available checkpoints ({len(checkpoint_files)} files):")
    print("-" * 80)
    
    # Group by execution_id
    from collections import defaultdict
    import json
    from datetime import datetime
    
    executions = defaultdict(list)
    for filepath in checkpoint_files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            execution_id = data.get("execution_id", "unknown")
            wave_number = data.get("wave_number", 0)
            timestamp = data.get("timestamp", "")
            completed_tasks = len(data.get("completed_tasks", []))
            
            executions[execution_id].append({
                "filepath": filepath,
                "wave": wave_number,
                "timestamp": timestamp,
                "completed_tasks": completed_tasks,
            })
        except Exception as e:
            print(f"Warning: Could not read {filepath}: {e}")
    
    # Display grouped by execution
    for execution_id, checkpoints in sorted(executions.items()):
        checkpoints.sort(key=lambda x: x["wave"])
        latest = checkpoints[-1]
        timestamp_str = latest["timestamp"][:19] if latest["timestamp"] else "unknown"
        
        print(f"\nExecution: {execution_id}")
        print(f"  Latest checkpoint: Wave {latest['wave']} ({latest['completed_tasks']} tasks completed)")
        print(f"  Timestamp: {timestamp_str}")
        print(f"  Resume command:")
        print(f"    python run_extraction.py --resume-from-checkpoint {latest['filepath']}")
        
        if len(checkpoints) > 1:
            print(f"  Other waves: {', '.join(str(c['wave']) for c in checkpoints[:-1])}")
    
    print("\n" + "-" * 80)
    print(f"Total: {len(executions)} execution(s), {len(checkpoint_files)} checkpoint(s)")
    return 0


def resume_from_checkpoint(checkpoint_path: str, args):
    """Resume extraction from a checkpoint file."""
    if not os.path.exists(checkpoint_path):
        print(f"Error: Checkpoint file not found: {checkpoint_path}")
        return 1
    
    print(f"Resuming from checkpoint: {checkpoint_path}")
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)
    
    # Load checkpoint to get execution info
    import json
    try:
        with open(checkpoint_path, "r", encoding="utf-8") as f:
            checkpoint_data = json.load(f)
        execution_id = checkpoint_data.get("execution_id", "unknown")
        wave_number = checkpoint_data.get("wave_number", 0)
        completed_tasks = len(checkpoint_data.get("completed_tasks", []))
        
        print(f"Checkpoint info:")
        print(f"  Execution ID: {execution_id}")
        print(f"  Wave: {wave_number}")
        print(f"  Completed tasks: {completed_tasks}")
        print("-" * 50)
    except Exception as e:
        print(f"Error reading checkpoint: {e}")
        return 1
    
    # Initialize pipeline
    config = PipelineConfig(
        model=args.model,
        fast_model=args.fast_model,
        vision_model=args.vision_model,
        output_dir=args.output_dir,
        max_workers=args.workers,
        enable_vision=not args.no_vision,
        enable_enrichment=not args.no_enrichment,
        skip_agents=args.skip,
    )
    
    pipeline = ExtractionPipeline(config)
    pipeline.initialize()
    print(f"Pipeline ready: {pipeline.get_agent_count()} agents\n")
    
    # Resume from checkpoint
    try:
        status = pipeline.orchestrator.resume_from_checkpoint(checkpoint_path)
        print(f"Resumed execution: {status.execution_id}")
        print(f"State: {status.state}")
        print(f"Progress: {status.completed_tasks}/{status.total_tasks} tasks")
        print("-" * 50)
        
        # Note: The actual continuation of execution would need to be implemented
        # in the pipeline. For now, this demonstrates the checkpoint loading.
        print("\nNote: Checkpoint loaded successfully.")
        print("Full resume execution is not yet implemented in the pipeline.")
        print("You can re-run the extraction from scratch with the fast model instead.")
        
        return 0
    except Exception as e:
        print(f"Error resuming from checkpoint: {e}")
        return 1
    finally:
        pipeline.shutdown()


def main():
    parser = argparse.ArgumentParser(
        description="Extract USDM from clinical trial protocol PDFs"
    )
    parser.add_argument("pdfs", nargs="*", help="Path(s) to protocol PDF(s). Supports glob patterns.")
    parser.add_argument("--model", default="gemini-2.5-pro", help="LLM model (default: gemini-2.5-pro)")
    parser.add_argument("--fast-model", default=None, dest="fast_model",
                        help="Faster model for less-critical agents like narrative/docstructure")
    parser.add_argument("--vision-model", default=None, dest="vision_model",
                        help="Model for SoA vision extraction (default: same as --model)")
    parser.add_argument("--output-dir", default="output", help="Output directory (default: output)")
    parser.add_argument("--workers", type=int, default=4, help="Parallel workers (default: 4)")
    parser.add_argument("--no-vision", action="store_true", help="Disable SoA vision extraction")
    parser.add_argument("--no-enrichment", action="store_true", help="Disable NCI EVS enrichment")
    parser.add_argument("--skip", nargs="*", default=[], help="Agent IDs to skip")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    parser.add_argument("--resume-from-checkpoint", dest="resume_checkpoint", 
                        help="Resume extraction from a checkpoint file (e.g., checkpoints/checkpoint_<id>_<wave>.json)")
    parser.add_argument("--list-checkpoints", action="store_true", dest="list_checkpoints",
                        help="List available checkpoint files and exit")
    parser.add_argument("--clean-checkpoints", action="store_true", dest="clean_checkpoints",
                        help="Delete all checkpoint files and exit")
    args = parser.parse_args()

    # Handle --list-checkpoints
    if args.list_checkpoints:
        return list_checkpoints()

    # Handle --clean-checkpoints
    if args.clean_checkpoints:
        return clean_checkpoints()

    # Handle --resume-from-checkpoint
    if args.resume_checkpoint:
        return resume_from_checkpoint(args.resume_checkpoint, args)

    # Configure logging so agent progress is visible
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )
    # Quiet noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)

    # Expand glob patterns
    pdf_files = []
    for pattern in args.pdfs:
        expanded = glob.glob(pattern)
        if expanded:
            pdf_files.extend(expanded)
        elif os.path.isfile(pattern):
            pdf_files.append(pattern)
        else:
            print(f"Warning: {pattern} not found, skipping")
    pdf_files = sorted(set(pdf_files))

    if not pdf_files:
        print("No PDF files found.")
        return 1

    print(f"Protocol2USDM — Extracting {len(pdf_files)} protocol(s)")
    print(f"Model: {args.model} | Fast: {args.fast_model or chr(45)} | Vision: {args.vision_model or chr(45)} | Workers: {args.workers}")
    print("-" * 50)

    config = PipelineConfig(
        model=args.model,
        fast_model=args.fast_model,
        vision_model=args.vision_model,
        output_dir=args.output_dir,
        max_workers=args.workers,
        enable_vision=not args.no_vision,
        enable_enrichment=not args.no_enrichment,
        skip_agents=args.skip,
    )

    pipeline = ExtractionPipeline(config)
    pipeline.initialize()
    print(f"Pipeline ready: {pipeline.get_agent_count()} agents\n")

    success_count = 0
    for i, pdf_path in enumerate(pdf_files, 1):
        protocol_id = os.path.splitext(os.path.basename(pdf_path))[0]
        print(f"[{i}/{len(pdf_files)}] {protocol_id}...", end=" ", flush=True)

        try:
            result = pipeline.run(pdf_path, protocol_id=protocol_id)
            if result.success:
                print(f"OK — {result.entity_count} entities, {result.execution_time_ms:.0f}ms")
                print(f"         USDM: {result.usdm_path}")
                success_count += 1
            else:
                print(f"PARTIAL — {result.entity_count} entities, failed: {result.failed_agents}")
        except Exception as e:
            print(f"ERROR — {e}")

    pipeline.shutdown()

    print("-" * 50)
    print(f"Done: {success_count}/{len(pdf_files)} successful")
    return 0 if success_count == len(pdf_files) else 1


if __name__ == "__main__":
    sys.exit(main())
