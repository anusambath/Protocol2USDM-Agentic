"""USDM 4.0 JSON serializer for the Prodigy-to-USDM converter."""

from __future__ import annotations

import json

from converter.constants import CONVERTER_VERSION, USDM_VERSION
from converter.models import USDMDocument


def build_wrapper(study: dict) -> dict:
    """Construct the top-level USDM 4.0 wrapper.

    Returns a dict with exactly four keys: study, usdmVersion,
    systemName, and systemVersion.
    """
    return {
        "study": study,
        "usdmVersion": USDM_VERSION,
        "systemName": "Prodigy-to-USDM Converter",
        "systemVersion": CONVERTER_VERSION,
    }


def serialize(usdm_doc: USDMDocument) -> str:
    """Produce the final USDM 4.0 JSON string.

    Wraps the study data in the top-level USDM wrapper and serializes
    to JSON with 2-space indentation, UTF-8 encoding, and no ASCII
    escaping (Unicode characters like ≥ are preserved as-is).
    """
    wrapper = build_wrapper(usdm_doc.study)
    return json.dumps(wrapper, indent=2, ensure_ascii=False)
