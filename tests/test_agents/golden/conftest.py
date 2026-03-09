"""
Golden file test configuration and fixtures.

Golden file tests validate extraction agents against real protocol PDFs.
They are skipped by default (require LLM API calls). Run with:

    pytest tests/test_agents/golden/ -m golden --run-golden

To regenerate golden reference files from existing pipeline output:

    python tests/test_agents/golden/generate_golden.py
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# 15 diverse protocols from input/test_trials/
GOLDEN_PROTOCOLS = [
    "NCT02864992",   # EMD Serono - Phase 2, NSCLC (MET)
    "NCT03019588",   # Merck - Phase 3, Gastric/GEJ
    "NCT03155997",   # Lilly - Phase 3, Breast cancer
    "NCT03235752",   # I-Mab - Phase 2, Ulcerative colitis
    "NCT03421431",   # Enanta - Phase 2, NASH
    "NCT03961204",   # EMD Serono - Phase 4, Multiple sclerosis
    "NCT04205812",   # Incyte - Phase 3, Oncology
    "NCT04573972",   # Carnegie Mellon - Physical activity
    "NCT04649359",   # Pfizer - Phase 2, Multiple myeloma
    "NCT04972110",   # Repare - Phase 1b/2, Solid tumors
    "NCT05327491",   # Amgen - PK, Healthy volunteers
    "NCT05499130",   # Teva - Phase 2b, UC/Crohn's
    "NCT05592275",   # Lilly - Phase 2, HFpEF
    "NCT05763147",   # BD - Device flushing syringes
    "NCT05999994",   # Lilly - Pediatrics master protocol
]

TRIAL_DIR = Path("input/test_trials")
GOLDEN_DIR = Path("tests/test_agents/golden/references")
OUTPUT_BASE = Path("output")


def _find_protocol_pdf(trial_name: str) -> Optional[Path]:
    """Find the protocol PDF for a given NCT ID in the flat test_trials dir."""
    matches = list(TRIAL_DIR.glob(f"{trial_name}_*.pdf"))
    return matches[0] if matches else None


def _find_latest_output(trial_name: str) -> Optional[Path]:
    """Find the most recent output directory for a trial (NCT ID prefix match)."""
    matches = sorted(OUTPUT_BASE.glob(f"{trial_name}_*"), reverse=True)
    matches = [m for m in matches if m.is_dir()]
    return matches[0] if matches else None


def _load_golden(trial_name: str, phase_file: str) -> Optional[Dict[str, Any]]:
    """Load a golden reference file."""
    golden_path = GOLDEN_DIR / trial_name / phase_file
    if golden_path.exists():
        with open(golden_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


# ---------------------------------------------------------------------------
# Pytest configuration
# ---------------------------------------------------------------------------

def pytest_addoption(parser):
    parser.addoption(
        "--run-golden",
        action="store_true",
        default=False,
        help="Run golden file tests (requires LLM API access)",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "golden: mark test as golden file test")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-golden"):
        skip_golden = pytest.mark.skip(reason="need --run-golden option to run")
        for item in items:
            if "golden" in item.keywords:
                item.add_marker(skip_golden)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(params=GOLDEN_PROTOCOLS)
def protocol_info(request):
    """Provide protocol PDF path and trial name for each golden protocol."""
    trial_name = request.param
    pdf_path = _find_protocol_pdf(trial_name)
    if pdf_path is None:
        pytest.skip(f"Protocol PDF not found for {trial_name}")
    return {
        "trial_name": trial_name,
        "pdf_path": str(pdf_path),
    }


@pytest.fixture
def golden_dir():
    """Return the golden references directory, creating it if needed."""
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    return GOLDEN_DIR
