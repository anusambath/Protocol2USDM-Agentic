"""
Tests for PDFParserAgent.
"""

import pytest
from unittest.mock import patch, MagicMock

from agents.base import AgentTask, AgentState
from agents.context_store import ContextStore
from agents.support.pdf_parser_agent import (
    PDFParserAgent,
    PageText,
    TableRegion,
    PDFParseResult,
    detect_table_regions,
)


# --- Data Model Tests ---

class TestPageText:
    def test_to_dict(self):
        pt = PageText(page_number=0, text="hello", char_count=5, has_tables=True)
        d = pt.to_dict()
        assert d["page_number"] == 0
        assert d["text"] == "hello"
        assert d["char_count"] == 5
        assert d["has_tables"] is True

    def test_defaults(self):
        pt = PageText(page_number=1, text="x")
        assert pt.char_count == 0
        assert pt.has_tables is False


class TestTableRegion:
    def test_to_dict(self):
        tr = TableRegion(page_number=0, start_line=5, end_line=15,
                         line_count=10, confidence=0.8, header_hint="visit")
        d = tr.to_dict()
        assert d["page_number"] == 0
        assert d["start_line"] == 5
        assert d["end_line"] == 15
        assert d["confidence"] == 0.8
        assert d["header_hint"] == "visit"


class TestPDFParseResult:
    def test_to_dict_empty(self):
        r = PDFParseResult(pdf_path="test.pdf")
        d = r.to_dict()
        assert d["pdf_path"] == "test.pdf"
        assert d["pages"] == []
        assert d["table_regions"] == []

    def test_to_dict_with_data(self):
        r = PDFParseResult(
            pdf_path="test.pdf",
            page_count=5,
            pages=[PageText(page_number=0, text="hi", char_count=2)],
            table_regions=[TableRegion(page_number=0, start_line=0, end_line=5, line_count=5)],
            image_paths=["/tmp/page_000.png"],
        )
        d = r.to_dict()
        assert d["page_count"] == 5
        assert len(d["pages"]) == 1
        assert len(d["table_regions"]) == 1
        assert d["image_paths"] == ["/tmp/page_000.png"]


# --- Table Detection Tests ---

class TestDetectTableRegions:
    def test_no_tables_in_plain_text(self):
        text = "This is a paragraph.\nAnother line.\nShort."
        regions = detect_table_regions(text, page_number=0)
        assert regions == []

    def test_detects_pipe_separated_table(self):
        lines = [
            "Visit | Screening | Baseline | Week 4 | Week 8",
            "Lab tests | X | X | X | X",
            "Vitals | X | X | X | X",
            "ECG | | X | | X",
        ]
        text = "\n".join(lines)
        regions = detect_table_regions(text, page_number=2)
        assert len(regions) >= 1
        assert regions[0].page_number == 2
        assert regions[0].line_count >= 3

    def test_detects_tab_separated_table(self):
        lines = [
            "Visit\tScreening\tBaseline\tWeek 4",
            "Lab\tX\tX\tX",
            "Vitals\tX\tX\tX",
            "ECG\t\tX\tX",
        ]
        text = "\n".join(lines)
        regions = detect_table_regions(text, page_number=0)
        assert len(regions) >= 1

    def test_detects_multi_token_table(self):
        lines = [
            "Assessment  Screening  Baseline  Week4  Week8  Week12",
            "Height      X          X         X      X      X",
            "Weight      X          X         X      X      X",
            "BMI         X          X         X      X      X",
        ]
        text = "\n".join(lines)
        regions = detect_table_regions(text, page_number=0)
        assert len(regions) >= 1

    def test_header_hint_detection(self):
        lines = [
            "Visit | Screening | Baseline | Week 4",
            "Test1 | X | X | X",
            "Test2 | X | X | X",
            "Test3 | X | X | X",
        ]
        text = "\n".join(lines)
        regions = detect_table_regions(text, page_number=0)
        assert len(regions) >= 1
        assert regions[0].header_hint == "visit"

    def test_empty_lines_split_regions(self):
        lines = [
            "A | B | C | D",
            "1 | 2 | 3 | 4",
            "5 | 6 | 7 | 8",
            "",
            "X | Y | Z | W",
            "a | b | c | d",
            "e | f | g | h",
        ]
        text = "\n".join(lines)
        regions = detect_table_regions(text, page_number=0)
        assert len(regions) == 2

    def test_region_at_end_of_text(self):
        lines = [
            "Some text here",
            "",
            "A | B | C | D",
            "1 | 2 | 3 | 4",
            "5 | 6 | 7 | 8",
        ]
        text = "\n".join(lines)
        regions = detect_table_regions(text, page_number=0)
        assert len(regions) >= 1

    def test_confidence_increases_with_lines(self):
        short_lines = ["A | B | C"] * 3
        long_lines = ["A | B | C"] * 10
        short_regions = detect_table_regions("\n".join(short_lines), 0)
        long_regions = detect_table_regions("\n".join(long_lines), 0)
        if short_regions and long_regions:
            assert long_regions[0].confidence >= short_regions[0].confidence


# --- PDFParserAgent Tests ---

class TestPDFParserAgent:
    def setup_method(self):
        self.agent = PDFParserAgent()
        self.agent.initialize()

    def test_init_defaults(self):
        assert self.agent.agent_id == "pdf-parser"
        assert self.agent.state == AgentState.READY

    def test_init_custom_config(self):
        agent = PDFParserAgent(config={"dpi": 300, "max_chars_per_page": 5000})
        assert agent._default_dpi == 300
        assert agent._max_chars_per_page == 5000

    def test_get_capabilities(self):
        caps = self.agent.get_capabilities()
        assert caps.agent_type == "support"
        assert "pdf" in caps.input_types

    def test_terminate(self):
        self.agent.terminate()
        assert self.agent.state == AgentState.TERMINATED

    def test_execute_no_pdf_path(self):
        task = AgentTask(task_id="t1", agent_id="pdf-parser",
                         task_type="pdf_parse", input_data={})
        result = self.agent.execute(task)
        assert not result.success
        assert "pdf_path" in result.error

    @patch("core.pdf_utils.get_page_count", return_value=10)
    def test_handle_page_count(self, mock_count):
        task = AgentTask(task_id="t1", agent_id="pdf-parser",
                         task_type="pdf_page_count",
                         input_data={"pdf_path": "test.pdf"})
        result = self.agent.execute(task)
        assert result.success
        assert result.data["page_count"] == 10

    @patch("core.pdf_utils.extract_text_from_pages")
    @patch("core.pdf_utils.get_page_count", return_value=3)
    def test_handle_text_extract(self, mock_count, mock_extract):
        mock_extract.return_value = "--- Page 1 ---\nSample text here"
        task = AgentTask(task_id="t1", agent_id="pdf-parser",
                         task_type="pdf_text_extract",
                         input_data={"pdf_path": "test.pdf", "pages": [0, 1]})
        result = self.agent.execute(task)
        assert result.success
        assert len(result.data["pages"]) == 2

    @patch("core.pdf_utils.render_pages_to_images", return_value=["/tmp/p0.png"])
    @patch("core.pdf_utils.get_page_count", return_value=3)
    def test_handle_image_extract(self, mock_count, mock_render):
        task = AgentTask(task_id="t1", agent_id="pdf-parser",
                         task_type="pdf_image_extract",
                         input_data={"pdf_path": "test.pdf", "pages": [0],
                                     "output_dir": "/tmp/images"})
        result = self.agent.execute(task)
        assert result.success
        assert result.data["image_paths"] == ["/tmp/p0.png"]

    def test_handle_image_extract_no_output_dir(self):
        task = AgentTask(task_id="t1", agent_id="pdf-parser",
                         task_type="pdf_image_extract",
                         input_data={"pdf_path": "test.pdf", "pages": [0]})
        result = self.agent.execute(task)
        assert not result.success
        assert "output_dir" in result.error

    @patch("core.pdf_utils.extract_text_from_pages")
    @patch("core.pdf_utils.get_page_count", return_value=2)
    def test_handle_table_detect(self, mock_count, mock_extract):
        mock_extract.return_value = "--- Page 1 ---\nA | B | C\n1 | 2 | 3\n4 | 5 | 6"
        task = AgentTask(task_id="t1", agent_id="pdf-parser",
                         task_type="pdf_table_detect",
                         input_data={"pdf_path": "test.pdf", "pages": [0]})
        result = self.agent.execute(task)
        assert result.success
        assert "table_regions" in result.data

    @patch("core.pdf_utils.extract_text_from_pages")
    @patch("core.pdf_utils.get_page_count", return_value=2)
    def test_handle_full_parse(self, mock_count, mock_extract):
        mock_extract.return_value = "--- Page 1 ---\nVisit | Screen | Base\nA | X | X\nB | X | X"
        task = AgentTask(task_id="t1", agent_id="pdf-parser",
                         task_type="pdf_parse",
                         input_data={"pdf_path": "test.pdf", "pages": [0]})
        result = self.agent.execute(task)
        assert result.success
        assert result.confidence_score == 1.0
        assert result.provenance is not None

    @patch("core.pdf_utils.extract_text_from_pages")
    @patch("core.pdf_utils.get_page_count", return_value=2)
    def test_full_parse_stores_in_context(self, mock_count, mock_extract):
        mock_extract.return_value = "--- Page 1 ---\nSome text"
        store = ContextStore()
        self.agent.set_context_store(store)

        task = AgentTask(task_id="t1", agent_id="pdf-parser",
                         task_type="pdf_parse",
                         input_data={"pdf_path": "test.pdf", "pages": [0]})
        result = self.agent.execute(task)
        assert result.success
        assert store.entity_count >= 1

    @patch("core.pdf_utils.extract_text_from_pages", return_value=None)
    @patch("core.pdf_utils.get_page_count", return_value=0)
    def test_zero_page_pdf(self, mock_count, mock_extract):
        task = AgentTask(task_id="t1", agent_id="pdf-parser",
                         task_type="pdf_text_extract",
                         input_data={"pdf_path": "empty.pdf"})
        result = self.agent.execute(task)
        assert result.success
        assert len(result.data["pages"]) == 0

    @patch("core.pdf_utils.extract_text_from_pages", return_value=None)
    @patch("core.pdf_utils.get_page_count", return_value=5)
    def test_out_of_range_pages(self, mock_count, mock_extract):
        task = AgentTask(task_id="t1", agent_id="pdf-parser",
                         task_type="pdf_text_extract",
                         input_data={"pdf_path": "test.pdf", "pages": [10, 20]})
        result = self.agent.execute(task)
        assert result.success
        # Out of range pages should produce errors
        assert len(result.data["errors"]) >= 1

    @patch("core.pdf_utils.extract_text_from_pages", side_effect=Exception("PDF corrupt"))
    @patch("core.pdf_utils.get_page_count", return_value=5)
    def test_extraction_exception(self, mock_count, mock_extract):
        task = AgentTask(task_id="t1", agent_id="pdf-parser",
                         task_type="pdf_text_extract",
                         input_data={"pdf_path": "bad.pdf", "pages": [0]})
        result = self.agent.execute(task)
        assert not result.success
        assert "PDF corrupt" in result.error

    @patch("core.pdf_utils.extract_text_from_pages")
    @patch("core.pdf_utils.get_page_count", return_value=3)
    def test_strips_page_header(self, mock_count, mock_extract):
        mock_extract.return_value = "--- Page 1 ---\nActual content here"
        task = AgentTask(task_id="t1", agent_id="pdf-parser",
                         task_type="pdf_text_extract",
                         input_data={"pdf_path": "test.pdf", "pages": [0]})
        result = self.agent.execute(task)
        assert result.success
        page_text = result.data["pages"][0]["text"]
        assert not page_text.startswith("--- Page")
        assert "Actual content here" in page_text

    @patch("core.pdf_utils.extract_text_from_pages", return_value=None)
    @patch("core.pdf_utils.get_page_count", return_value=3)
    def test_null_text_returns_empty_page(self, mock_count, mock_extract):
        task = AgentTask(task_id="t1", agent_id="pdf-parser",
                         task_type="pdf_text_extract",
                         input_data={"pdf_path": "test.pdf", "pages": [0]})
        result = self.agent.execute(task)
        assert result.success
        assert result.data["pages"][0]["text"] == ""
        assert result.data["pages"][0]["char_count"] == 0

    @patch("core.pdf_utils.extract_text_from_pages")
    @patch("core.pdf_utils.get_page_count", return_value=3)
    def test_all_pages_when_none_specified(self, mock_count, mock_extract):
        mock_extract.return_value = "--- Page 1 ---\nText"
        task = AgentTask(task_id="t1", agent_id="pdf-parser",
                         task_type="pdf_text_extract",
                         input_data={"pdf_path": "test.pdf"})
        result = self.agent.execute(task)
        assert result.success
        assert len(result.data["pages"]) == 3
