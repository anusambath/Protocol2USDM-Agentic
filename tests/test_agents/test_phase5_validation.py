"""
Phase 5 Validation Tests - Support Agent Integration.

Tests that all support agents work together correctly:
- PDF parsing → Context Store → USDM generation
- Provenance tracking across the pipeline
- Checkpoint and recovery
- Error handling and graceful degradation
"""

import json
import os
import tempfile
import pytest
from unittest.mock import patch

from agents.base import AgentTask, AgentResult, AgentState
from agents.context_store import ContextStore, ContextEntity, EntityProvenance
from agents.support.pdf_parser_agent import PDFParserAgent
from agents.support.usdm_generator_agent import USDMGeneratorAgent
from agents.support.provenance_agent import ProvenanceAgent
from agents.support.checkpoint_agent import CheckpointAgent, EnhancedCheckpoint
from agents.support.error_handler import (
    ErrorHandlerAgent, ErrorCategory, ErrorSeverity,
    GracefulDegradation, ErrorRecord,
)


# --- Helpers ---

def _populate_store(store):
    """Add realistic entities to a Context Store."""
    entities = [
        ("m1", "metadata", {"name": "ADAURA Study", "description": "Phase III"}),
        ("si1", "study_identifier", {"identifier": "NCT03036124", "type": "NCT"}),
        ("obj1", "objective", {"text": "Primary: DFS", "level": "primary"}),
        ("obj2", "objective", {"text": "Secondary: OS", "level": "secondary"}),
        ("arm1", "study_arm", {"name": "Osimertinib", "type": "experimental"}),
        ("arm2", "study_arm", {"name": "Placebo", "type": "control"}),
        ("ep1", "study_epoch", {"name": "Screening", "order": 1}),
        ("ep2", "study_epoch", {"name": "Treatment", "order": 2}),
        ("ec1", "eligibility_criterion", {"text": "Age >= 18", "category": "inclusion"}),
        ("ec2", "eligibility_criterion", {"text": "EGFR mutation", "category": "inclusion"}),
        ("act1", "activity", {"name": "Physical Exam"}),
        ("enc1", "encounter", {"name": "Visit 1"}),
    ]
    for eid, etype, data in entities:
        entity = ContextEntity(
            id=eid, entity_type=etype, data=data,
            provenance=EntityProvenance(
                entity_id=eid, source_agent_id=f"{etype}-agent",
                confidence_score=0.9, source_pages=[1, 2],
                model_used="gemini-2.5-pro",
            ),
        )
        store.add_entity(entity)
    return store


# --- PDF Parser Validation ---

class TestPDFParserValidation:
    """Task 26.1.1: Test PDF parsing accuracy."""

    @patch("core.pdf_utils.extract_text_from_pages")
    @patch("core.pdf_utils.get_page_count", return_value=50)
    def test_multi_page_extraction(self, mock_count, mock_extract):
        mock_extract.return_value = "--- Page 1 ---\nClinical trial protocol text"
        agent = PDFParserAgent()
        agent.initialize()

        task = AgentTask(
            task_id="t1", agent_id="pdf-parser",
            task_type="pdf_parse",
            input_data={"pdf_path": "protocol.pdf", "pages": list(range(5))},
        )
        result = agent.execute(task)
        assert result.success
        assert len(result.data["pages"]) == 5
        assert result.data["page_count"] == 50

    @patch("core.pdf_utils.extract_text_from_pages")
    @patch("core.pdf_utils.get_page_count", return_value=10)
    def test_table_detection_in_soa_pages(self, mock_count, mock_extract):
        soa_text = (
            "--- Page 1 ---\n"
            "Schedule of Assessments\n"
            "Visit | Screening | Baseline | Week 4 | Week 8\n"
            "Lab tests | X | X | X | X\n"
            "Vitals | X | X | X | X\n"
            "ECG | | X | | X\n"
            "CT Scan | | X | | X\n"
        )
        mock_extract.return_value = soa_text
        agent = PDFParserAgent()
        agent.initialize()

        task = AgentTask(
            task_id="t1", agent_id="pdf-parser",
            task_type="pdf_parse",
            input_data={"pdf_path": "protocol.pdf", "pages": [5]},
        )
        result = agent.execute(task)
        assert result.success
        assert len(result.data["table_regions"]) >= 1

    @patch("core.pdf_utils.extract_text_from_pages")
    @patch("core.pdf_utils.get_page_count", return_value=10)
    def test_context_store_integration(self, mock_count, mock_extract):
        mock_extract.return_value = "--- Page 1 ---\nText content"
        store = ContextStore()
        agent = PDFParserAgent()
        agent.initialize()
        agent.set_context_store(store)

        task = AgentTask(
            task_id="t1", agent_id="pdf-parser",
            task_type="pdf_parse",
            input_data={"pdf_path": "protocol.pdf", "pages": [0, 1]},
        )
        result = agent.execute(task)
        assert result.success
        # Should store page metadata
        pages = store.query_entities(entity_type="pdf_page")
        assert len(pages) == 2


# --- USDM Generation Validation ---

class TestUSDMGenerationValidation:
    """Task 26.1.2: Test USDM generation correctness."""

    def test_full_usdm_generation(self):
        store = ContextStore()
        _populate_store(store)

        agent = USDMGeneratorAgent()
        agent.initialize()
        agent.set_context_store(store)

        task = AgentTask(
            task_id="t1", agent_id="usdm-generator",
            task_type="usdm_generate", input_data={},
        )
        result = agent.execute(task)
        assert result.success
        assert result.data["entity_count"] == 12

        usdm = result.data["usdm"]
        assert usdm["study"]["name"] == "ADAURA Study"
        assert len(usdm["study"]["versions"][0]["studyIdentifiers"]) == 1
        assert len(usdm["study"]["versions"][0]["studyDesigns"][0]["objectives"]) == 2
        assert len(usdm["study"]["versions"][0]["studyDesigns"][0]["arms"]) == 2
        assert len(usdm["study"]["versions"][0]["studyDesigns"][0]["epochs"]) == 2

    def test_usdm_json_serializable(self):
        store = ContextStore()
        _populate_store(store)

        agent = USDMGeneratorAgent()
        agent.initialize()
        agent.set_context_store(store)

        task = AgentTask(
            task_id="t1", agent_id="usdm-generator",
            task_type="usdm_generate", input_data={},
        )
        result = agent.execute(task)
        # Must be JSON serializable
        json_str = json.dumps(result.data["usdm"])
        assert len(json_str) > 100

    def test_usdm_file_output(self):
        store = ContextStore()
        _populate_store(store)

        agent = USDMGeneratorAgent()
        agent.initialize()
        agent.set_context_store(store)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "usdm.json")
            task = AgentTask(
                task_id="t1", agent_id="usdm-generator",
                task_type="usdm_generate",
                input_data={"output_path": output_path},
            )
            result = agent.execute(task)
            assert result.success
            assert os.path.exists(output_path)

            with open(output_path) as f:
                usdm = json.load(f)
            assert usdm["study"]["name"] == "ADAURA Study"


# --- Provenance Validation ---

class TestProvenanceValidation:
    """Task 26.1.3: Test provenance completeness (100% entities tracked)."""

    def test_all_entities_tracked(self):
        store = ContextStore()
        _populate_store(store)

        agent = ProvenanceAgent()
        agent.initialize()
        agent.set_context_store(store)

        task = AgentTask(
            task_id="t1", agent_id="provenance",
            task_type="provenance_generate", input_data={},
        )
        result = agent.execute(task)
        assert result.success

        summary = result.data["summary"]
        assert summary["total_entities"] == 12
        assert summary["entities_with_provenance"] == 12
        assert summary["coverage_percent"] == 100.0

    def test_provenance_has_source_pages(self):
        store = ContextStore()
        _populate_store(store)

        agent = ProvenanceAgent()
        agent.initialize()
        agent.set_context_store(store)

        task = AgentTask(
            task_id="t1", agent_id="provenance",
            task_type="provenance_generate", input_data={},
        )
        result = agent.execute(task)
        records = result.data["provenance"]["records"]
        for r in records:
            assert len(r["source_pages"]) > 0

    def test_provenance_json_output(self):
        store = ContextStore()
        _populate_store(store)

        agent = ProvenanceAgent()
        agent.initialize()
        agent.set_context_store(store)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "provenance.json")
            task = AgentTask(
                task_id="t1", agent_id="provenance",
                task_type="provenance_generate",
                input_data={"output_path": output_path},
            )
            result = agent.execute(task)
            assert result.success
            assert os.path.exists(output_path)


# --- Checkpoint Recovery Validation ---

class TestCheckpointRecoveryValidation:
    """Task 26.1.4: Test checkpoint recovery (resume from any wave)."""

    def test_checkpoint_preserves_full_state(self):
        store = ContextStore()
        _populate_store(store)

        with tempfile.TemporaryDirectory() as tmpdir:
            agent = CheckpointAgent(config={"checkpoints_dir": tmpdir})
            agent.initialize()
            agent.set_context_store(store)

            # Create checkpoint at wave 2
            task = AgentTask(
                task_id="t1", agent_id="checkpoint",
                task_type="checkpoint_create",
                input_data={
                    "execution_id": "exec-1",
                    "wave_number": 2,
                    "completed_tasks": ["t1", "t2", "t3"],
                    "failed_tasks": ["t4"],
                    "total_tasks": 10,
                    "agent_states": {"metadata": "READY", "eligibility": "READY"},
                },
            )
            result = agent.execute(task)
            assert result.success
            filepath = result.data["filepath"]

            # Load and verify
            cp = EnhancedCheckpoint.load(filepath)
            assert cp.wave_number == 2
            assert len(cp.completed_tasks) == 3
            assert len(cp.failed_tasks) == 1
            assert cp.agent_states["metadata"] == "READY"
            assert "entities" in cp.context_store_snapshot

    def test_recovery_restores_context_store(self):
        store = ContextStore()
        _populate_store(store)

        with tempfile.TemporaryDirectory() as tmpdir:
            agent = CheckpointAgent(config={"checkpoints_dir": tmpdir})
            agent.initialize()
            agent.set_context_store(store)

            # Create checkpoint
            create_task = AgentTask(
                task_id="t1", agent_id="checkpoint",
                task_type="checkpoint_create",
                input_data={
                    "execution_id": "exec-1",
                    "wave_number": 3,
                    "completed_tasks": ["t1", "t2"],
                    "total_tasks": 5,
                },
            )
            create_result = agent.execute(create_task)

            # Switch to empty store (simulating restart)
            new_store = ContextStore()
            agent.set_context_store(new_store)
            assert new_store.entity_count == 0

            # Recover
            load_task = AgentTask(
                task_id="t2", agent_id="checkpoint",
                task_type="checkpoint_load",
                input_data={"checkpoint_path": create_result.data["filepath"]},
            )
            load_result = agent.execute(load_task)
            assert load_result.success
            assert new_store.entity_count == 12  # All entities restored

    def test_multi_wave_checkpoint_recovery(self):
        """Test creating checkpoints at multiple waves and recovering from each."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = CheckpointAgent(config={"checkpoints_dir": tmpdir})
            agent.initialize()

            filepaths = []
            for wave in range(4):
                store = ContextStore()
                for i in range(wave + 1):
                    store.add_entity(ContextEntity(
                        id=f"e-w{wave}-{i}", entity_type="objective",
                        data={"wave": wave, "idx": i},
                        provenance=EntityProvenance(
                            entity_id=f"e-w{wave}-{i}", source_agent_id="test"),
                    ))
                agent.set_context_store(store)

                task = AgentTask(
                    task_id=f"t{wave}", agent_id="checkpoint",
                    task_type="checkpoint_create",
                    input_data={
                        "execution_id": "exec-1",
                        "wave_number": wave,
                        "completed_tasks": [f"t{i}" for i in range(wave)],
                        "total_tasks": 10,
                    },
                )
                result = agent.execute(task)
                filepaths.append(result.data["filepath"])

            # Recover from wave 2
            new_store = ContextStore()
            agent.set_context_store(new_store)
            load_task = AgentTask(
                task_id="tl", agent_id="checkpoint",
                task_type="checkpoint_load",
                input_data={"checkpoint_path": filepaths[2]},
            )
            load_result = agent.execute(load_task)
            assert load_result.success
            assert load_result.data["checkpoint"]["wave_number"] == 2


# --- Error Handling Validation ---

class TestErrorHandlingValidation:
    """Task 26.1.5: Test error handling and graceful degradation."""

    def test_transient_error_retry_recommendation(self):
        agent = ErrorHandlerAgent()
        agent.initialize()

        task = AgentTask(
            task_id="t1", agent_id="error-handler",
            task_type="error_record",
            input_data={
                "agent_id": "metadata-agent",
                "message": "Connection timed out after 30s",
            },
        )
        result = agent.execute(task)
        assert result.success
        assert result.data["should_retry"] is True
        assert result.data["can_continue"] is True

    def test_graceful_degradation_non_critical(self):
        gd = GracefulDegradation()

        # Non-critical agent fails
        error = ErrorRecord(
            agent_id="narrative-agent",
            severity=ErrorSeverity.MEDIUM,
            message="Extraction timeout",
        )
        gd.record_failure("narrative-agent", error)

        # Pipeline should continue
        assert gd.should_continue("narrative-agent") is True

        # But with partial results
        partial = AgentResult(
            task_id="t1", agent_id="narrative-agent",
            success=False, error="Timeout",
        )
        gd.record_partial_result("narrative-agent", partial)

        summary = gd.get_degradation_summary()
        assert summary["failed_agent_count"] == 1
        assert summary["partial_result_count"] == 1

    def test_critical_agent_stops_pipeline(self):
        gd = GracefulDegradation()

        error = ErrorRecord(
            agent_id="metadata-agent",
            severity=ErrorSeverity.CRITICAL,
            message="Out of memory",
        )
        gd.record_failure("metadata-agent", error)

        # Critical severity → pipeline should stop
        assert gd.should_continue("metadata-agent") is False

    def test_error_report_generation(self):
        agent = ErrorHandlerAgent()
        agent.initialize()

        # Record various errors
        errors = [
            ("metadata-agent", "Connection timed out"),
            ("eligibility-agent", "Invalid API key"),
            ("soa-vision-agent", "Rate limit exceeded"),
        ]
        for agent_id, msg in errors:
            task = AgentTask(
                task_id="t1", agent_id="error-handler",
                task_type="error_record",
                input_data={"agent_id": agent_id, "message": msg},
            )
            agent.execute(task)

        # Generate report
        report_task = AgentTask(
            task_id="t2", agent_id="error-handler",
            task_type="error_report",
            input_data={"execution_id": "exec-1"},
        )
        result = agent.execute(report_task)
        assert result.success
        report = result.data["report"]
        assert report["total_errors"] == 3
        assert len(report["errors_by_agent"]) >= 2


# --- Cross-Agent Integration ---

class TestSupportAgentIntegration:
    """Test support agents working together."""

    def test_pdf_to_usdm_pipeline(self):
        """PDF Parser → Context Store → USDM Generator."""
        store = ContextStore()

        # Simulate PDF parser storing page metadata
        pdf_agent = PDFParserAgent()
        pdf_agent.initialize()
        pdf_agent.set_context_store(store)

        # Manually add extraction results (simulating extraction agents)
        _populate_store(store)

        # Generate USDM
        usdm_agent = USDMGeneratorAgent()
        usdm_agent.initialize()
        usdm_agent.set_context_store(store)

        task = AgentTask(
            task_id="t1", agent_id="usdm-generator",
            task_type="usdm_generate", input_data={},
        )
        result = usdm_agent.execute(task)
        assert result.success
        assert result.data["entity_count"] >= 10

    def test_usdm_then_provenance(self):
        """USDM generation followed by provenance tracking."""
        store = ContextStore()
        _populate_store(store)

        # Generate USDM
        usdm_agent = USDMGeneratorAgent()
        usdm_agent.initialize()
        usdm_agent.set_context_store(store)
        usdm_task = AgentTask(
            task_id="t1", agent_id="usdm-generator",
            task_type="usdm_generate", input_data={},
        )
        usdm_result = usdm_agent.execute(usdm_task)
        assert usdm_result.success

        # Generate provenance
        prov_agent = ProvenanceAgent()
        prov_agent.initialize()
        prov_agent.set_context_store(store)
        prov_task = AgentTask(
            task_id="t2", agent_id="provenance",
            task_type="provenance_generate", input_data={},
        )
        prov_result = prov_agent.execute(prov_task)
        assert prov_result.success
        assert prov_result.data["summary"]["coverage_percent"] == 100.0

    def test_checkpoint_after_usdm_generation(self):
        """Checkpoint captures state after USDM generation."""
        store = ContextStore()
        _populate_store(store)

        with tempfile.TemporaryDirectory() as tmpdir:
            cp_agent = CheckpointAgent(config={"checkpoints_dir": tmpdir})
            cp_agent.initialize()
            cp_agent.set_context_store(store)

            task = AgentTask(
                task_id="t1", agent_id="checkpoint",
                task_type="checkpoint_create",
                input_data={
                    "execution_id": "exec-1",
                    "wave_number": 5,
                    "completed_tasks": ["pdf", "extract", "quality", "usdm", "provenance"],
                    "total_tasks": 5,
                },
            )
            result = cp_agent.execute(task)
            assert result.success
            assert result.data["completed_tasks"] == 5

    def test_error_handler_with_degradation(self):
        """Error handler manages degradation across agents."""
        error_agent = ErrorHandlerAgent()
        error_agent.initialize()

        # Simulate non-critical agent failure
        task = AgentTask(
            task_id="t1", agent_id="error-handler",
            task_type="error_record",
            input_data={
                "agent_id": "narrative-agent",
                "message": "Extraction timed out",
            },
        )
        result = error_agent.execute(task)
        assert result.data["can_continue"] is True

        # Pipeline continues, but narrative data is missing
        # USDM generation should still work with partial data
        store = ContextStore()
        _populate_store(store)  # Has everything except narrative

        usdm_agent = USDMGeneratorAgent()
        usdm_agent.initialize()
        usdm_agent.set_context_store(store)

        usdm_task = AgentTask(
            task_id="t2", agent_id="usdm-generator",
            task_type="usdm_generate", input_data={},
        )
        usdm_result = usdm_agent.execute(usdm_task)
        assert usdm_result.success  # Works with partial data
