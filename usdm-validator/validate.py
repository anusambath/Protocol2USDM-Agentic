#!/usr/bin/env python3
"""
USDM Validator — Validate a USDM v4.0 JSON file using the CDISC CORE engine.

Usage:
    python validate.py <usdm_json_file> [--output-dir <dir>] [--api-key <key>]

Examples:
    python validate.py my_protocol_usdm.json
    python validate.py my_protocol_usdm.json --output-dir results/
    python validate.py my_protocol_usdm.json --api-key YOUR_CDISC_KEY

Prerequisites:
    Run 'python download_core.py' once to install the CDISC CORE engine.
    Set CDISC_LIBRARY_API_KEY (or pass --api-key) for first-run cache setup.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent


def find_core_exe() -> Path:
    """Locate the CORE engine executable."""
    if sys.platform == "win32":
        candidates = [
            SCRIPT_DIR / "core" / "core" / "core.exe",
            SCRIPT_DIR / "core" / "core.exe",
        ]
    else:
        candidates = [
            SCRIPT_DIR / "core" / "core" / "core",
            SCRIPT_DIR / "core" / "core",
        ]
    for p in candidates:
        if p.exists():
            return p
    return None


def ensure_cache(core_exe: Path, api_key: str = None) -> bool:
    """Run update-cache if rules dictionary is missing."""
    cache_file = core_exe.parent / "resources" / "cache" / "rules_dictionary.pkl"
    if cache_file.exists():
        return True

    key = api_key or os.environ.get("CDISC_LIBRARY_API_KEY") or os.environ.get("CDISC_API_KEY")
    if not key:
        print("ERROR: CDISC rules cache not found.")
        print("Set CDISC_LIBRARY_API_KEY environment variable or pass --api-key.")
        print("Get a free key at: https://www.cdisc.org/cdisc-library")
        return False

    print("Downloading CDISC rules cache (first run, may take 2-3 minutes)...")
    result = subprocess.run(
        [str(core_exe), "update-cache", "--apikey", key],
        capture_output=True, text=True, timeout=300,
        cwd=str(core_exe.parent),
    )
    if result.returncode == 0:
        print("Rules cache downloaded successfully.")
        return True
    else:
        print(f"Cache download failed: {result.stderr}")
        return False


def validate(json_path: str, output_dir: str = ".", api_key: str = None) -> dict:
    """Run CDISC CORE validation on a USDM JSON file."""
    json_path = os.path.abspath(json_path)
    output_dir = os.path.abspath(output_dir)

    if not os.path.exists(json_path):
        return {"success": False, "error": f"File not found: {json_path}"}

    core_exe = find_core_exe()
    if not core_exe:
        return {
            "success": False,
            "error": "CORE engine not found. Run: python download_core.py",
        }

    if not ensure_cache(core_exe, api_key):
        return {"success": False, "error": "CDISC rules cache not available."}

    os.makedirs(output_dir, exist_ok=True)
    output_base = os.path.join(output_dir, "conformance_report")
    output_file = output_base + ".json"

    print(f"Validating: {os.path.basename(json_path)}")
    print(f"Engine: CDISC CORE v0.14.1")
    print(f"Standard: USDM v4.0")
    print()

    try:
        result = subprocess.run(
            [
                str(core_exe),
                "validate",
                "-s", "usdm",
                "-v", "4-0",
                "-dp", json_path,
                "-o", output_base,
                "-of", "JSON",
                "-p", "disabled",
            ],
            capture_output=True, text=True, timeout=120,
            cwd=str(core_exe.parent),
        )

        if result.returncode == 0 and os.path.exists(output_file):
            with open(output_file, "r", encoding="utf-8") as f:
                report = json.load(f)

            # Parse summary
            issue_summary = report.get("Issue_Summary", [])
            issue_details = report.get("Issue_Details", [])
            total_issues = sum(i.get("issues", 0) for i in issue_summary)

            print(f"Total issues: {total_issues}")
            print()
            if issue_summary:
                print(f"{'Entity':<30} {'Rule':<15} {'Count':>5}  Message")
                print("-" * 100)
                for item in issue_summary:
                    print(
                        f"{item.get('entity',''):<30} "
                        f"{item.get('core_id',''):<15} "
                        f"{item.get('issues',0):>5}  "
                        f"{item.get('message','')[:60]}"
                    )
            else:
                print("No issues found. USDM file is conformant.")

            print()
            print(f"Full report: {output_file}")

            return {
                "success": True,
                "total_issues": total_issues,
                "summary": issue_summary,
                "details_count": len(issue_details),
                "report_path": output_file,
            }
        else:
            error = result.stderr or result.stdout or "Unknown error"
            print(f"Validation failed: {error[:200]}")
            return {"success": False, "error": error}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "CORE engine timed out (>120s)"}
    except FileNotFoundError:
        return {"success": False, "error": "CORE engine executable not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(
        description="Validate a USDM v4.0 JSON file using the CDISC CORE engine."
    )
    parser.add_argument("json_file", help="Path to the USDM JSON file to validate")
    parser.add_argument(
        "--output-dir", "-o", default=".",
        help="Directory for the conformance report (default: current directory)"
    )
    parser.add_argument(
        "--api-key", "-k", default=None,
        help="CDISC Library API key (or set CDISC_LIBRARY_API_KEY env var)"
    )
    args = parser.parse_args()

    result = validate(args.json_file, args.output_dir, args.api_key)
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
