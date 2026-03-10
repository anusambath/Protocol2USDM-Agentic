"""Shared fixtures for agent evals."""
import json
import os
import pytest


def _find_latest_output(protocol_prefix: str, output_dir: str) -> str | None:
    """Find the most recent output directory matching a protocol prefix."""
    candidates = []
    for d in os.listdir(output_dir):
        if d.startswith(protocol_prefix) and os.path.isdir(os.path.join(output_dir, d)):
            candidates.append(d)
    if not candidates:
        return None
    # Sort by timestamp suffix (YYYYMMDD_HHMMSS)
    candidates.sort(reverse=True)
    return os.path.join(output_dir, candidates[0])


def _load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def pytest_addoption(parser):
    parser.addoption("--golden", default=None, help="Path to golden USDM JSON")
    parser.addoption("--output-dir", default=None, help="Path to pipeline output directory")
    parser.addoption(
        "--protocol",
        default="Alexion_NCT04573309_Wilsons",
        help="Protocol prefix to auto-discover golden and output",
    )


@pytest.fixture(scope="session")
def golden(request) -> dict:
    """Load the golden USDM JSON."""
    path = request.config.getoption("--golden")
    if not path:
        protocol = request.config.getoption("--protocol")
        path = os.path.join("input", f"{protocol}_golden.json")
    if not os.path.exists(path):
        pytest.skip(f"Golden file not found: {path}")
    return _load_json(path)


@pytest.fixture(scope="session")
def pipeline_output_dir(request) -> str:
    """Resolve the pipeline output directory."""
    path = request.config.getoption("--output-dir")
    if not path:
        protocol = request.config.getoption("--protocol")
        path = _find_latest_output(protocol, "output")
    if not path or not os.path.isdir(path):
        pytest.skip(f"Output directory not found: {path}")
    return path
