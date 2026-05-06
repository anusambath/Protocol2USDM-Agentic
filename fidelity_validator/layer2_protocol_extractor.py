"""
Layer 2 — Protocol Extractor

Extracts structured content from the protocol PDF, organized by section.
Uses pdfplumber for text-heavy extraction with fitz (PyMuPDF) as fallback.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .models import SectionMap
from .layer1_section_map import resolve_section

logger = logging.getLogger(__name__)


@dataclass
class ExtractedTable:
    """A table extracted from the PDF."""
    page: int
    headers: List[str]
    rows: List[List[str]]
    caption: Optional[str] = None


@dataclass
class ExtractedSection:
    """Content extracted from one protocol section."""
    section_id: str
    section_name: str
    page_start: int
    page_end: int
    raw_text: str
    tables: List[ExtractedTable] = field(default_factory=list)
    is_soa: bool = False


@dataclass
class ProtocolContent:
    """Complete structured extraction of the protocol PDF."""
    pdf_path: str
    total_pages: int
    sections: Dict[str, ExtractedSection] = field(default_factory=dict)
    toc_pages: List[int] = field(default_factory=list)


def extract_protocol(
    pdf_path: str,
    section_map: SectionMap,
) -> ProtocolContent:
    """
    Extract structured content from a protocol PDF.

    Process:
    1. Detect ToC and parse section headings with page numbers.
    2. For each section, extract raw text and tables.
    3. Map detected sections to canonical section IDs via the section map.
    4. Special handling for SoA tables.
    """
    import fitz

    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    doc.close()

    content = ProtocolContent(pdf_path=pdf_path, total_pages=total_pages)

    # Step 1: Detect ToC
    toc_entries = detect_toc(pdf_path)
    if toc_entries:
        content.toc_pages = list(set(toc_entries.values()))
        logger.info(f"Detected {len(toc_entries)} ToC entries")
    else:
        # Fallback: scan for headings
        toc_entries = detect_headings_by_scan(pdf_path)
        logger.info(f"Heading scan found {len(toc_entries)} sections")

    # Step 2: Build page ranges for each section
    sorted_entries = sorted(toc_entries.items(), key=lambda x: x[1])
    section_ranges: List[Tuple[str, int, int]] = []
    for i, (heading, start_page) in enumerate(sorted_entries):
        end_page = sorted_entries[i + 1][1] - 1 if i + 1 < len(sorted_entries) else total_pages - 1
        # Ensure end_page >= start_page
        end_page = max(end_page, start_page)
        section_ranges.append((heading, start_page, end_page))

    # Step 3: Extract text and map to canonical sections
    for heading, page_start, page_end in section_ranges:
        spec = resolve_section(section_map, heading)
        if not spec:
            continue

        raw_text = extract_section_text(pdf_path, page_start, page_end)
        tables = extract_tables_from_pages(pdf_path, page_start, page_end)

        is_soa = spec.id == "schedule_of_activities"

        section = ExtractedSection(
            section_id=spec.id,
            section_name=heading,
            page_start=page_start,
            page_end=page_end,
            raw_text=raw_text,
            tables=tables,
            is_soa=is_soa,
        )
        content.sections[spec.id] = section

    logger.info(f"Extracted {len(content.sections)} sections from {total_pages} pages")
    return content


def detect_toc(pdf_path: str) -> Dict[str, int]:
    """
    Detect the Table of Contents and extract section → page mappings.

    Returns:
        Dict mapping section heading text to starting page number (0-indexed).
    """
    import fitz

    doc = fitz.open(pdf_path)
    toc_entries: Dict[str, int] = {}

    # Strategy 1: Use PDF bookmarks/outline
    toc = doc.get_toc()
    if toc:
        for level, title, page_num in toc:
            if level <= 2:  # Only top-level and second-level headings
                clean_title = title.strip()
                if clean_title:
                    toc_entries[clean_title] = page_num - 1  # Convert to 0-indexed
        doc.close()
        if toc_entries:
            return toc_entries

    # Strategy 2: Parse ToC pages (look for "Table of Contents" heading)
    toc_pattern = re.compile(
        r'^(.+?)\s*[.…·]{3,}\s*(\d+)\s*$', re.MULTILINE
    )

    for page_num in range(min(15, len(doc))):
        text = doc[page_num].get_text()
        if "table of contents" in text.lower() or "contents" in text.lower()[:200]:
            matches = toc_pattern.findall(text)
            for heading, page_str in matches:
                heading = heading.strip()
                heading = re.sub(r'^\d+(\.\d+)*\s*', '', heading)  # Strip section numbers
                if heading and len(heading) > 3:
                    try:
                        toc_entries[heading] = int(page_str) - 1  # Convert to 0-indexed
                    except ValueError:
                        pass

    doc.close()
    return toc_entries


def detect_headings_by_scan(pdf_path: str) -> Dict[str, int]:
    """
    Fallback: scan pages for heading-like text patterns.

    Returns:
        Dict mapping heading text to page number (0-indexed).
    """
    import fitz

    doc = fitz.open(pdf_path)
    headings: Dict[str, int] = {}

    # Common protocol section heading patterns
    heading_patterns = [
        re.compile(r'^\d+\.\s+([A-Z][A-Za-z\s&/]+)$', re.MULTILINE),
        re.compile(r'^(?:SECTION\s+)?\d+\s*[-–]\s*(.+)$', re.MULTILINE),
    ]

    for page_num in range(len(doc)):
        text = doc[page_num].get_text()
        for pattern in heading_patterns:
            for match in pattern.finditer(text):
                heading = match.group(1).strip()
                if heading and len(heading) > 5 and heading not in headings:
                    headings[heading] = page_num

    doc.close()
    return headings


def extract_section_text(
    pdf_path: str,
    page_start: int,
    page_end: int,
) -> str:
    """
    Extract raw text from a page range using PyMuPDF.
    """
    import fitz

    doc = fitz.open(pdf_path)
    texts = []

    for page_num in range(page_start, min(page_end + 1, len(doc))):
        page = doc[page_num]
        texts.append(page.get_text())

    doc.close()
    return "\n".join(texts)


def extract_tables_from_pages(
    pdf_path: str,
    page_start: int,
    page_end: int,
) -> List[ExtractedTable]:
    """
    Extract tables from a page range using pdfplumber.
    """
    tables = []

    try:
        import pdfplumber

        with pdfplumber.open(pdf_path) as pdf:
            for page_num in range(page_start, min(page_end + 1, len(pdf.pages))):
                page = pdf.pages[page_num]
                page_tables = page.extract_tables()
                for tbl in page_tables:
                    if not tbl or len(tbl) < 2:
                        continue
                    headers = [str(c or "").strip() for c in tbl[0]]
                    rows = [[str(c or "").strip() for c in row] for row in tbl[1:]]
                    tables.append(ExtractedTable(
                        page=page_num,
                        headers=headers,
                        rows=rows,
                    ))
    except ImportError:
        logger.warning("pdfplumber not installed — table extraction skipped")
    except Exception as e:
        logger.warning(f"Table extraction failed: {e}")

    return tables


def save_protocol_content(content: ProtocolContent, output_path: str) -> None:
    """Save extracted protocol content to JSON."""
    data = {
        "pdf_path": content.pdf_path,
        "total_pages": content.total_pages,
        "toc_pages": content.toc_pages,
        "sections": {},
    }
    for sid, section in content.sections.items():
        data["sections"][sid] = {
            "section_id": section.section_id,
            "section_name": section.section_name,
            "page_start": section.page_start,
            "page_end": section.page_end,
            "raw_text_length": len(section.raw_text),
            "raw_text": section.raw_text[:5000],  # Truncate for readability
            "table_count": len(section.tables),
            "is_soa": section.is_soa,
        }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
