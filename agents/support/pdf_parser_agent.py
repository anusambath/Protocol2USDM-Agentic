"""
PDF Parser Agent - Wraps existing PyMuPDF (fitz) utilities.

Provides a unified agent interface for:
- Text extraction from specified pages
- Image/page rendering for vision analysis
- Table region detection via text pattern heuristics
- Page-level metadata (page count, dimensions)
"""

import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from agents.base import AgentCapabilities, AgentResult, AgentState, AgentTask, BaseAgent

logger = logging.getLogger(__name__)


@dataclass
class PageText:
    """Extracted text from a single PDF page."""
    page_number: int  # 0-indexed
    text: str
    char_count: int = 0
    has_tables: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "text": self.text,
            "char_count": self.char_count,
            "has_tables": self.has_tables,
        }


@dataclass
class TableRegion:
    """Detected table region on a page."""
    page_number: int
    start_line: int
    end_line: int
    line_count: int
    confidence: float = 0.0
    header_hint: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "line_count": self.line_count,
            "confidence": self.confidence,
            "header_hint": self.header_hint,
        }


@dataclass
class PDFParseResult:
    """Result of PDF parsing operation."""
    pdf_path: str
    page_count: int = 0
    pages: List[PageText] = field(default_factory=list)
    table_regions: List[TableRegion] = field(default_factory=list)
    image_paths: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pdf_path": self.pdf_path,
            "page_count": self.page_count,
            "pages": [p.to_dict() for p in self.pages],
            "table_regions": [t.to_dict() for t in self.table_regions],
            "image_paths": self.image_paths,
            "errors": self.errors,
        }


# Table detection heuristics
_TABLE_INDICATORS = [
    "visit", "week", "day", "month", "screening", "baseline",
    "randomization", "follow-up", "end of", "treatment",
]
_COLUMN_SEPARATOR_CHARS = {"|", "\t"}
_MIN_TABLE_LINES = 3


def detect_table_regions(text: str, page_number: int) -> List[TableRegion]:
    """
    Detect table-like regions in page text using heuristics.

    Looks for:
    - Lines with multiple column separators (|, tabs)
    - Consecutive lines with similar column counts
    - Header-like keywords (Visit, Week, Day, etc.)
    """
    lines = text.split("\n")
    regions: List[TableRegion] = []
    current_start: Optional[int] = None
    current_col_count = 0
    header_hint = ""

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            # Empty line may end a table region
            if current_start is not None and (i - current_start) >= _MIN_TABLE_LINES:
                regions.append(TableRegion(
                    page_number=page_number,
                    start_line=current_start,
                    end_line=i - 1,
                    line_count=i - current_start,
                    confidence=min(0.9, 0.5 + 0.1 * (i - current_start)),
                    header_hint=header_hint,
                ))
            current_start = None
            current_col_count = 0
            header_hint = ""
            continue

        # Count separators
        sep_count = sum(1 for c in stripped if c in _COLUMN_SEPARATOR_CHARS)
        # Also check for multiple whitespace-separated columns
        tokens = stripped.split()
        has_many_tokens = len(tokens) >= 4

        is_table_line = sep_count >= 2 or has_many_tokens

        if is_table_line:
            if current_start is None:
                current_start = i
                # Check for header keywords
                lower = stripped.lower()
                for kw in _TABLE_INDICATORS:
                    if kw in lower:
                        header_hint = kw
                        break
            current_col_count = max(current_col_count, sep_count)
        else:
            if current_start is not None and (i - current_start) >= _MIN_TABLE_LINES:
                regions.append(TableRegion(
                    page_number=page_number,
                    start_line=current_start,
                    end_line=i - 1,
                    line_count=i - current_start,
                    confidence=min(0.9, 0.5 + 0.1 * (i - current_start)),
                    header_hint=header_hint,
                ))
            current_start = None
            current_col_count = 0
            header_hint = ""

    # Handle region at end of text
    if current_start is not None and (len(lines) - current_start) >= _MIN_TABLE_LINES:
        regions.append(TableRegion(
            page_number=page_number,
            start_line=current_start,
            end_line=len(lines) - 1,
            line_count=len(lines) - current_start,
            confidence=min(0.9, 0.5 + 0.1 * (len(lines) - current_start)),
            header_hint=header_hint,
        ))

    return regions


class PDFParserAgent(BaseAgent):
    """
    Agent for PDF parsing operations.

    Wraps existing core/pdf_utils.py functions (fitz/PyMuPDF) and adds:
    - Table region detection via text heuristics
    - Batch page extraction
    - Image rendering for vision agents
    - Context Store integration for page metadata
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id="pdf-parser", config=config or {})
        self._default_dpi = (config or {}).get("dpi", 150)
        self._max_chars_per_page = (config or {}).get("max_chars_per_page", 10000)

    def initialize(self) -> None:
        self.set_state(AgentState.READY)
        self._logger.info(f"[{self.agent_id}] Initialized")

    def terminate(self) -> None:
        self.set_state(AgentState.TERMINATED)

    def get_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            agent_type="support",
            input_types=["pdf"],
            output_types=["text", "image", "table_region"],
        )

    def execute(self, task: AgentTask) -> AgentResult:
        """
        Execute a PDF parsing task.

        Supported task_type values:
        - "pdf_parse": Full parse (text + tables + optional images)
        - "pdf_text_extract": Text extraction only
        - "pdf_image_extract": Render pages to images
        - "pdf_table_detect": Detect table regions
        - "pdf_page_count": Get page count only

        Input data:
        - pdf_path (str): Path to PDF file
        - pages (list[int], optional): Specific pages (0-indexed). Default: all
        - output_dir (str, optional): Directory for rendered images
        - dpi (int, optional): DPI for image rendering
        - detect_tables (bool, optional): Whether to detect tables. Default: True
        """
        pdf_path = task.input_data.get("pdf_path", "")
        if not pdf_path:
            return AgentResult(
                task_id=task.task_id, agent_id=self.agent_id,
                success=False, error="No pdf_path provided",
            )

        task_type = task.task_type

        try:
            if task_type == "pdf_page_count":
                return self._handle_page_count(task, pdf_path)
            elif task_type == "pdf_text_extract":
                return self._handle_text_extract(task, pdf_path)
            elif task_type == "pdf_image_extract":
                return self._handle_image_extract(task, pdf_path)
            elif task_type == "pdf_table_detect":
                return self._handle_table_detect(task, pdf_path)
            else:
                # Default: full parse
                return self._handle_full_parse(task, pdf_path)
        except Exception as e:
            self._logger.error(f"[{self.agent_id}] PDF parsing failed: {e}")
            return AgentResult(
                task_id=task.task_id, agent_id=self.agent_id,
                success=False, error=str(e),
            )

    # --- Task Handlers ---

    def _handle_page_count(self, task: AgentTask, pdf_path: str) -> AgentResult:
        from core.pdf_utils import get_page_count
        count = get_page_count(pdf_path)
        return AgentResult(
            task_id=task.task_id, agent_id=self.agent_id,
            success=True, data={"page_count": count, "pdf_path": pdf_path},
        )

    def _handle_text_extract(self, task: AgentTask, pdf_path: str) -> AgentResult:
        pages = task.input_data.get("pages")
        result = self._extract_text(pdf_path, pages)
        return AgentResult(
            task_id=task.task_id, agent_id=self.agent_id,
            success=True,
            data=result.to_dict(),
        )

    def _handle_image_extract(self, task: AgentTask, pdf_path: str) -> AgentResult:
        pages = task.input_data.get("pages")
        output_dir = task.input_data.get("output_dir", "")
        dpi = task.input_data.get("dpi", self._default_dpi)

        if not output_dir:
            return AgentResult(
                task_id=task.task_id, agent_id=self.agent_id,
                success=False, error="No output_dir provided for image extraction",
            )

        image_paths = self._render_images(pdf_path, pages, output_dir, dpi)
        return AgentResult(
            task_id=task.task_id, agent_id=self.agent_id,
            success=True,
            data={"image_paths": image_paths, "pdf_path": pdf_path},
        )

    def _handle_table_detect(self, task: AgentTask, pdf_path: str) -> AgentResult:
        pages = task.input_data.get("pages")
        parse_result = self._extract_text(pdf_path, pages)
        all_regions = []
        for page in parse_result.pages:
            regions = detect_table_regions(page.text, page.page_number)
            all_regions.extend(regions)
        return AgentResult(
            task_id=task.task_id, agent_id=self.agent_id,
            success=True,
            data={
                "table_regions": [r.to_dict() for r in all_regions],
                "pdf_path": pdf_path,
            },
        )

    def _handle_full_parse(self, task: AgentTask, pdf_path: str) -> AgentResult:
        pages = task.input_data.get("pages")
        output_dir = task.input_data.get("output_dir", "")
        dpi = task.input_data.get("dpi", self._default_dpi)
        detect_tables = task.input_data.get("detect_tables", True)

        result = self._extract_text(pdf_path, pages)

        # Detect tables
        if detect_tables:
            for page in result.pages:
                regions = detect_table_regions(page.text, page.page_number)
                result.table_regions.extend(regions)
                if regions:
                    page.has_tables = True

        # Render images if output_dir provided
        # NOTE: Skip image rendering during full parse — SoA vision agent
        # handles its own image extraction for only the SoA pages.
        # Rendering all pages is expensive and unnecessary.
        # Use task_type="pdf_image_extract" for explicit image rendering.

        # Store page metadata in Context Store
        self._store_page_metadata(result)

        return AgentResult(
            task_id=task.task_id, agent_id=self.agent_id,
            success=True,
            data=result.to_dict(),
            confidence_score=1.0,  # PDF parsing is deterministic
            provenance={
                "agent_id": self.agent_id,
                "pdf_path": pdf_path,
                "pages_extracted": len(result.pages),
                "tables_detected": len(result.table_regions),
                "timestamp": datetime.now().isoformat(),
            },
        )

    # --- Internal Methods ---

    def _extract_text(self, pdf_path: str,
                      pages: Optional[List[int]] = None) -> PDFParseResult:
        """Extract text from PDF pages using core.pdf_utils."""
        from core.pdf_utils import get_page_count, extract_text_from_pages

        result = PDFParseResult(pdf_path=pdf_path)
        result.page_count = get_page_count(pdf_path)

        if result.page_count == 0:
            result.errors.append("Could not read PDF or PDF has 0 pages")
            return result

        if pages is None:
            pages = list(range(result.page_count))

        # Extract text page by page for granular results
        for page_num in pages:
            if page_num < 0 or page_num >= result.page_count:
                result.errors.append(f"Page {page_num} out of range (0-{result.page_count - 1})")
                continue

            text = extract_text_from_pages(
                pdf_path, [page_num],
                max_chars_per_page=self._max_chars_per_page,
            )
            if text is not None:
                # Strip the "--- Page N ---" header added by extract_text_from_pages
                clean_text = text
                if clean_text.startswith("--- Page"):
                    newline_idx = clean_text.find("\n")
                    if newline_idx >= 0:
                        clean_text = clean_text[newline_idx + 1:]

                result.pages.append(PageText(
                    page_number=page_num,
                    text=clean_text,
                    char_count=len(clean_text),
                ))
            else:
                result.pages.append(PageText(
                    page_number=page_num,
                    text="",
                    char_count=0,
                ))

        return result

    def _render_images(self, pdf_path: str, pages: Optional[List[int]],
                       output_dir: str, dpi: int) -> List[str]:
        """Render PDF pages to images using core.pdf_utils."""
        from core.pdf_utils import get_page_count, render_pages_to_images

        if pages is None:
            count = get_page_count(pdf_path)
            pages = list(range(count))

        return render_pages_to_images(pdf_path, pages, output_dir, dpi=dpi)

    def _store_page_metadata(self, result: PDFParseResult) -> None:
        """Store page metadata in Context Store if available."""
        if not self._context_store:
            return

        from agents.context_store import ContextEntity, EntityProvenance

        for page in result.pages:
            entity_id = f"pdf-page-{page.page_number}"
            try:
                entity = ContextEntity(
                    id=entity_id,
                    entity_type="pdf_page",
                    data={
                        "page_number": page.page_number,
                        "char_count": page.char_count,
                        "has_tables": page.has_tables,
                        "pdf_path": result.pdf_path,
                    },
                    provenance=EntityProvenance(
                        entity_id=entity_id,
                        source_agent_id=self.agent_id,
                        confidence_score=1.0,
                        source_pages=[page.page_number],
                    ),
                )
                self._context_store.add_entity(entity)
            except ValueError:
                pass  # Entity already exists
