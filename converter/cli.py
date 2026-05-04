"""CLI entry point for the Prodigy-to-USDM 4.0 converter.

Wires the full conversion pipeline: parse args → read JSON →
parse_prodigy → strip_metadata → map_to_usdm → enrich +
normalize_codes → validate_id_references → serialize → write output.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any

from converter.enricher import enrich, normalize_codes, validate_id_references
from converter.mapper import map_to_usdm
from converter.parser import parse_prodigy
from converter.serializer import serialize
from converter.stripper import count_stripped, strip_metadata

logger = logging.getLogger(__name__)


def derive_output_path(input_path: str) -> str:
    """Derive the default output path from the input path.

    Replaces ``_Prodigy.json`` with ``_USDM40.json`` in the filename.
    If the input filename does not contain ``_Prodigy.json``, appends
    ``_USDM40.json`` to the stem.
    """
    if input_path.endswith("_Prodigy.json"):
        return input_path[: -len("_Prodigy.json")] + "_USDM40.json"
    # Fallback: replace .json extension
    if input_path.endswith(".json"):
        return input_path[: -len(".json")] + "_USDM40.json"
    return input_path + "_USDM40.json"


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse CLI arguments.

    Parameters
    ----------
    argv:
        Command-line argument list (without the program name).

    Returns
    -------
    argparse.Namespace
        Parsed arguments with ``input_file``, ``output``, and ``verbose``.
    """
    parser = argparse.ArgumentParser(
        prog="prodigy-to-usdm",
        description="Convert Prodigy JSON to USDM 4.0 compliant JSON.",
    )
    parser.add_argument(
        "input_file",
        help="Path to the Prodigy JSON input file.",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output file path. Defaults to input filename with _USDM40.json suffix.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        default=False,
        help="Enable verbose (DEBUG level) logging.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry point for the Prodigy-to-USDM converter.

    Parameters
    ----------
    argv:
        Command-line arguments. If ``None``, uses ``sys.argv[1:]``.

    Returns
    -------
    int
        0 on success, non-zero on failure.
    """
    if argv is None:
        argv = sys.argv[1:]

    # --- No arguments → usage to stderr ---
    if not argv:
        # Build parser just to get usage text, print to stderr
        parser = argparse.ArgumentParser(
            prog="prodigy-to-usdm",
            description="Convert Prodigy JSON to USDM 4.0 compliant JSON.",
        )
        parser.add_argument("input_file", help="Path to the Prodigy JSON input file.")
        parser.add_argument("--output", "-o", default=None)
        parser.add_argument("--verbose", "-v", action="store_true", default=False)
        print(parser.format_usage().strip(), file=sys.stderr)
        print(
            "Error: the following arguments are required: input_file",
            file=sys.stderr,
        )
        return 2

    try:
        args = parse_args(argv)
    except SystemExit as exc:
        # argparse calls sys.exit on --help or error
        return exc.code if isinstance(exc.code, int) else 1

    # --- Configure logging ---
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(levelname)s: %(name)s: %(message)s",
        stream=sys.stderr,
    )

    input_path: str = args.input_file
    output_path: str = args.output or derive_output_path(input_path)

    # --- Read input file ---
    try:
        with open(input_path, encoding="utf-8") as f:
            raw_text = f.read()
    except FileNotFoundError:
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Error: Cannot read input file: {exc}", file=sys.stderr)
        return 1

    # --- Parse JSON ---
    try:
        raw: dict[str, Any] = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        print(f"Error: Invalid JSON in {input_path}: {exc}", file=sys.stderr)
        return 1

    if not isinstance(raw, dict):
        print(
            f"Error: Expected a JSON object in {input_path}, got {type(raw).__name__}",
            file=sys.stderr,
        )
        return 1

    # --- Pipeline ---
    try:
        # Step 1: Parse Prodigy JSON into ProdigyDocument
        doc = parse_prodigy(raw)

        # Step 2: Count metadata fields for logging (before stripping)
        stripped_counts = count_stripped(doc.study)

        # Step 3: Strip metadata from the entire ProdigyDocument
        doc.study = strip_metadata(doc.study)
        doc.identifiers = strip_metadata(doc.identifiers)
        doc.population_definition = strip_metadata(doc.population_definition)
        doc.scheduled_instances = strip_metadata(doc.scheduled_instances)
        doc.syntax_templates = strip_metadata(doc.syntax_templates)
        doc.metadata = strip_metadata(doc.metadata)
        doc.relationships = strip_metadata(doc.relationships)
        doc.domain_modules = strip_metadata(doc.domain_modules)
        doc.auxiliary = strip_metadata(doc.auxiliary)

        # Step 4: Map to USDM
        usdm_doc = map_to_usdm(doc)

        # Step 5: Enrich — inject extensionAttributes, validate instanceType, ensure IDs
        enrich(usdm_doc.study)

        # Step 6: Normalize Code entities
        normalize_codes(usdm_doc.study)

        # Step 7: Validate ID references
        dangling_warnings = validate_id_references(usdm_doc)
        usdm_doc.warnings.extend(dangling_warnings)

        # Step 8: Serialize to JSON string
        output_json = serialize(usdm_doc)

    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    # --- Write output ---
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output_json)
            f.write("\n")
    except OSError as exc:
        print(f"Error: Cannot write output file: {exc}", file=sys.stderr)
        return 1

    # --- Log conversion stats ---
    stats = usdm_doc.stats
    stats.metadata_fields_stripped = stripped_counts

    logger.info("Conversion complete: %s → %s", input_path, output_path)
    if stripped_counts:
        logger.info("Metadata fields stripped: %s", stripped_counts)
    logger.info(
        "Relationships: %d processed, %d discarded",
        stats.relationships_processed,
        stats.relationships_discarded,
    )
    if usdm_doc.warnings:
        logger.info("Warnings (%d):", len(usdm_doc.warnings))
        for w in usdm_doc.warnings:
            logger.warning("  %s", w)

    return 0


if __name__ == "__main__":
    sys.exit(main())
