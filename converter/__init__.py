"""Prodigy-to-USDM 4.0 Converter.

A standalone converter that transforms Prodigy JSON files into
USDM 4.0 compliant JSON output.
"""

from converter.constants import (
    CONVERTER_VERSION,
    KNOWN_INSTANCE_TYPES,
    PRODIGY_METADATA_FIELDS,
    SCOPEID_WHITELIST_TYPES,
    USDM_VERSION,
)
from converter.models import ConversionStats, ProdigyDocument, USDMDocument

__all__ = [
    "CONVERTER_VERSION",
    "KNOWN_INSTANCE_TYPES",
    "PRODIGY_METADATA_FIELDS",
    "SCOPEID_WHITELIST_TYPES",
    "USDM_VERSION",
    "ConversionStats",
    "ProdigyDocument",
    "USDMDocument",
]
