#!/usr/bin/env python
"""Run agent evals from the command line.

Usage:
    python evals/run_evals.py
    python evals/run_evals.py --protocol Alexion_NCT04573309_Wilsons
    python evals/run_evals.py --golden input/golden.json --output-dir output/some_run/
    python evals/run_evals.py -k test_metadata  # run only metadata evals
    python evals/run_evals.py -v  # verbose output
"""
import sys
import subprocess


def main():
    args = ["python", "-m", "pytest", "evals/", "-v", "--tb=short"]

    # Pass through any CLI args
    extra = sys.argv[1:]
    args.extend(extra)

    print(f"Running: {' '.join(args)}")
    result = subprocess.run(args)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
