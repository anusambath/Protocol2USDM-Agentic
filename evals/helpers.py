"""Shared helpers for eval comparisons."""
import json
import os
from difflib import SequenceMatcher


def load_agent_output(output_dir: str, prefix: str) -> dict:
    """Load a numbered agent output JSON (e.g. '01_extraction_metadata')."""
    for f in os.listdir(output_dir):
        if f.startswith(prefix) and f.endswith(".json"):
            with open(os.path.join(output_dir, f), encoding="utf-8") as fh:
                return json.load(fh)
    raise FileNotFoundError(f"No file matching {prefix}*.json in {output_dir}")


def load_usdm(output_dir: str) -> dict:
    """Load the final USDM JSON from the output directory."""
    for f in os.listdir(output_dir):
        if f.endswith("_usdm.json"):
            with open(os.path.join(output_dir, f), encoding="utf-8") as fh:
                return json.load(fh)
    raise FileNotFoundError(f"No *_usdm.json in {output_dir}")


def get_study_design(usdm: dict) -> dict:
    """Extract the first studyDesign from a USDM JSON."""
    return usdm["study"]["versions"][0]["studyDesigns"][0]


def get_study_version(usdm: dict) -> dict:
    """Extract the first study version."""
    return usdm["study"]["versions"][0]


def normalize(text: str) -> str:
    """Normalize text for fuzzy comparison: lowercase, strip, collapse whitespace."""
    import re
    return re.sub(r"\s+", " ", text.strip().lower())


def fuzzy_match(a: str, b: str) -> float:
    """Return similarity ratio between two strings (0.0 to 1.0)."""
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def name_set(items: list[dict], key: str = "name") -> set[str]:
    """Extract a set of normalized names from a list of dicts."""
    return {normalize(item.get(key, "")) for item in items if item.get(key)}


def count_match_score(expected: int, actual: int) -> float:
    """Score how close actual count is to expected (1.0 = exact, 0.0 = way off)."""
    if expected == 0:
        return 1.0 if actual == 0 else 0.0
    return max(0.0, 1.0 - abs(expected - actual) / expected)


def set_overlap_score(expected: set, actual: set) -> float:
    """Jaccard similarity between two sets."""
    if not expected and not actual:
        return 1.0
    if not expected or not actual:
        return 0.0
    return len(expected & actual) / len(expected | actual)


def fuzzy_set_match_score(expected: set[str], actual: set[str], threshold: float = 0.8) -> float:
    """Match sets using fuzzy string matching. Returns fraction of expected items matched."""
    if not expected:
        return 1.0
    matched = 0
    actual_list = list(actual)
    for exp in expected:
        best = max((fuzzy_match(exp, act) for act in actual_list), default=0.0)
        if best >= threshold:
            matched += 1
    return matched / len(expected)
