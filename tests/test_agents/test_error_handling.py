"""
Tests for Error Handling Framework.
"""

import pytest
from unittest.mock import MagicMock

from agents.base import AgentTask, AgentResult, AgentState
from agents.support.error_handler import (
    ErrorHandlerAgent,
    ErrorCategory,
    ErrorSeverity,
    ErrorRecord,
    ErrorReport,
    GracefulDegradation,
    classify_error,
    get_remediation,
    retry_with_backoff,
)


# --- Error Classification Tests ---

class TestClassifyError:
    def test_timeout_is_transient(self):
        cat, sev = classify_error(Exception("Connection timed out"))
        assert cat == ErrorCategory.TRANSIENT
        assert sev == ErrorSeverity.MEDIUM

    def test_rate_limit_is_transient(self):
        cat, _ = classify_error(Exception("Rate limit exceeded (429)"))
        assert cat == ErrorCategory.TRANSIENT

    def test_503_is_transient(self):
        cat, _ = classify_error(Exception("Service unavailable 503"))
        assert cat == ErrorCategory.TRANSIENT

    def test_api_key_is_configuration(self):
        cat, sev = classify_error(Exception("Invalid API key"))
        assert cat == ErrorCategory.CONFIGURATION
        assert sev == ErrorSeverity.HIGH

    def test_unauthorized_is_configuration(self):
        cat, _ = classify_error(Exception("401 Unauthorized"))
        assert cat == ErrorCategory.CONFIGURATION

    def test_model_not_found_is_configuration(self):
        cat, _ = classify_error(Exception("Model not found: gpt-5"))
        assert cat == ErrorCategory.CONFIGURATION

    def test_out_of_memory_is_resource(self):
        cat, sev = classify_error(Exception("Out of memory"))
        assert cat == ErrorCategory.RESOURCE
        assert sev == ErrorSeverity.CRITICAL

    def test_value_error_is_permanent(self):
        cat, sev = classify_error(ValueError("Invalid input"))
        assert cat == ErrorCategory.PERMANENT
        assert sev == ErrorSeverity.HIGH

    def test_type_error_is_permanent(self):
        cat, _ = classify_error(TypeError("Expected str, got int"))
        assert cat == ErrorCategory.PERMANENT

    def test_key_error_is_permanent(self):
        cat, _ = classify_error(KeyError("missing_key"))
        assert cat == ErrorCategory.PERMANENT

    def test_file_not_found_is_permanent(self):
        cat, _ = classify_error(FileNotFoundError("No such file"))
        assert cat == ErrorCategory.PERMANENT

    def test_unknown_error(self):
        cat, sev = classify_error(RuntimeError("Something weird"))
        assert cat == ErrorCategory.UNKNOWN
        assert sev == ErrorSeverity.MEDIUM

    def test_connection_refused_is_transient(self):
        cat, _ = classify_error(Exception("Connection refused"))
        assert cat == ErrorCategory.TRANSIENT

    def test_throttle_is_transient(self):
        cat, _ = classify_error(Exception("Request throttled"))
        assert cat == ErrorCategory.TRANSIENT


class TestGetRemediation:
    def test_transient(self):
        r = get_remediation(ErrorCategory.TRANSIENT)
        assert "retry" in r.lower() or "Retry" in r

    def test_permanent(self):
        r = get_remediation(ErrorCategory.PERMANENT)
        assert "input" in r.lower()

    def test_configuration(self):
        r = get_remediation(ErrorCategory.CONFIGURATION)
        assert "key" in r.lower() or "config" in r.lower()

    def test_resource(self):
        r = get_remediation(ErrorCategory.RESOURCE)
        assert "resource" in r.lower() or "memory" in r.lower()

    def test_unknown(self):
        r = get_remediation(ErrorCategory.UNKNOWN)
        assert len(r) > 0


# --- Retry Tests ---

class TestRetryWithBackoff:
    def test_succeeds_first_try(self):
        result = retry_with_backoff(lambda: 42, max_retries=3, base_delay=0.01)
        assert result == 42

    def test_succeeds_after_retry(self):
        call_count = {"n": 0}

        def flaky():
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise Exception("Connection timed out")
            return "ok"

        result = retry_with_backoff(flaky, max_retries=3, base_delay=0.01)
        assert result == "ok"
        assert call_count["n"] == 3

    def test_raises_after_max_retries(self):
        def always_fail():
            raise Exception("Connection timed out")

        with pytest.raises(Exception, match="timed out"):
            retry_with_backoff(always_fail, max_retries=2, base_delay=0.01)

    def test_no_retry_for_permanent_error(self):
        call_count = {"n": 0}

        def permanent_fail():
            call_count["n"] += 1
            raise ValueError("Bad input")

        with pytest.raises(ValueError):
            retry_with_backoff(permanent_fail, max_retries=3, base_delay=0.01)
        assert call_count["n"] == 1  # No retries for permanent errors

    def test_custom_retryable_categories(self):
        call_count = {"n": 0}

        def config_fail():
            call_count["n"] += 1
            raise Exception("Invalid API key")

        # By default, configuration errors are not retried
        with pytest.raises(Exception):
            retry_with_backoff(config_fail, max_retries=3, base_delay=0.01)
        assert call_count["n"] == 1

        # But if we add CONFIGURATION to retryable, it should retry
        call_count["n"] = 0
        with pytest.raises(Exception):
            retry_with_backoff(
                config_fail, max_retries=2, base_delay=0.01,
                retryable_categories={ErrorCategory.CONFIGURATION},
            )
        assert call_count["n"] == 3  # 1 initial + 2 retries


# --- ErrorRecord Tests ---

class TestErrorRecord:
    def test_to_dict(self):
        r = ErrorRecord(
            agent_id="test-agent",
            task_id="t1",
            category=ErrorCategory.TRANSIENT,
            severity=ErrorSeverity.MEDIUM,
            message="Timeout",
        )
        d = r.to_dict()
        assert d["agent_id"] == "test-agent"
        assert d["category"] == "transient"
        assert d["severity"] == "medium"

    def test_defaults(self):
        r = ErrorRecord()
        assert r.error_id != ""
        assert r.resolved is False
        assert r.retry_count == 0


class TestErrorReport:
    def test_to_dict(self):
        r = ErrorReport(
            execution_id="exec-1",
            total_errors=5,
            resolved_count=2,
            unresolved_count=3,
        )
        d = r.to_dict()
        assert d["total_errors"] == 5
        assert d["resolved_count"] == 2


# --- GracefulDegradation Tests ---

class TestGracefulDegradation:
    def setup_method(self):
        self.gd = GracefulDegradation()

    def test_record_failure(self):
        error = ErrorRecord(agent_id="agent-a", message="Failed")
        self.gd.record_failure("agent-a", error)
        assert self.gd.is_failed("agent-a")
        assert not self.gd.is_failed("agent-b")

    def test_record_partial_result(self):
        result = AgentResult(task_id="t1", agent_id="agent-a", success=True)
        self.gd.record_partial_result("agent-a", result)
        partials = self.gd.get_partial_results()
        assert "agent-a" in partials

    def test_should_continue_non_critical(self):
        error = ErrorRecord(agent_id="agent-a", severity=ErrorSeverity.MEDIUM)
        self.gd.record_failure("agent-a", error)
        assert self.gd.should_continue("agent-a") is True

    def test_should_not_continue_critical_agent(self):
        error = ErrorRecord(agent_id="agent-a", severity=ErrorSeverity.MEDIUM)
        self.gd.record_failure("agent-a", error)
        assert self.gd.should_continue("agent-a", critical_agents={"agent-a"}) is False

    def test_should_not_continue_critical_severity(self):
        error = ErrorRecord(agent_id="agent-a", severity=ErrorSeverity.CRITICAL)
        self.gd.record_failure("agent-a", error)
        assert self.gd.should_continue("agent-a") is False

    def test_degradation_summary(self):
        error = ErrorRecord(agent_id="agent-a", message="Failed")
        self.gd.record_failure("agent-a", error)
        result = AgentResult(task_id="t1", agent_id="agent-b", success=True)
        self.gd.record_partial_result("agent-b", result)

        summary = self.gd.get_degradation_summary()
        assert summary["failed_agent_count"] == 1
        assert summary["partial_result_count"] == 1

    def test_get_failed_agents(self):
        error1 = ErrorRecord(agent_id="a1", message="Fail 1")
        error2 = ErrorRecord(agent_id="a2", message="Fail 2")
        self.gd.record_failure("a1", error1)
        self.gd.record_failure("a2", error2)
        failed = self.gd.get_failed_agents()
        assert len(failed) == 2


# --- ErrorHandlerAgent Tests ---

class TestErrorHandlerAgent:
    def setup_method(self):
        self.agent = ErrorHandlerAgent()
        self.agent.initialize()

    def test_init(self):
        assert self.agent.agent_id == "error-handler"
        assert self.agent.state == AgentState.READY

    def test_get_capabilities(self):
        caps = self.agent.get_capabilities()
        assert caps.agent_type == "support"
        assert "error_report" in caps.output_types

    def test_terminate(self):
        self.agent.terminate()
        assert self.agent.state == AgentState.TERMINATED

    def test_record_transient_error(self):
        task = AgentTask(
            task_id="t1", agent_id="error-handler",
            task_type="error_record",
            input_data={
                "agent_id": "metadata-agent",
                "message": "Connection timed out",
                "exception_type": "TimeoutError",
            },
        )
        result = self.agent.execute(task)
        assert result.success
        assert result.data["error_record"]["category"] == "transient"
        assert result.data["should_retry"] is True

    def test_record_permanent_error(self):
        task = AgentTask(
            task_id="t1", agent_id="error-handler",
            task_type="error_record",
            input_data={
                "agent_id": "metadata-agent",
                "message": "Invalid PDF format",
            },
        )
        result = self.agent.execute(task)
        assert result.success
        # Generic exception → unknown category
        assert result.data["should_retry"] is False

    def test_record_increments_count(self):
        assert self.agent.error_count == 0
        for i in range(3):
            task = AgentTask(
                task_id=f"t{i}", agent_id="error-handler",
                task_type="error_record",
                input_data={"agent_id": "test", "message": f"Error {i}"},
            )
            self.agent.execute(task)
        assert self.agent.error_count == 3

    def test_generate_report(self):
        # Record some errors
        for msg in ["Connection timed out", "Invalid API key", "Bad input"]:
            task = AgentTask(
                task_id="t1", agent_id="error-handler",
                task_type="error_record",
                input_data={"agent_id": "test-agent", "message": msg},
            )
            self.agent.execute(task)

        # Generate report
        report_task = AgentTask(
            task_id="t2", agent_id="error-handler",
            task_type="error_report",
            input_data={"execution_id": "exec-1"},
        )
        result = self.agent.execute(report_task)
        assert result.success
        report = result.data["report"]
        assert report["total_errors"] == 3
        assert report["execution_id"] == "exec-1"
        assert len(report["records"]) == 3

    def test_classify_error(self):
        task = AgentTask(
            task_id="t1", agent_id="error-handler",
            task_type="error_classify",
            input_data={"message": "Rate limit exceeded"},
        )
        result = self.agent.execute(task)
        assert result.success
        assert result.data["category"] == "transient"
        assert result.data["should_retry"] is True

    def test_classify_configuration_error(self):
        task = AgentTask(
            task_id="t1", agent_id="error-handler",
            task_type="error_classify",
            input_data={"message": "Missing API key for Gemini"},
        )
        result = self.agent.execute(task)
        assert result.success
        assert result.data["category"] == "configuration"

    def test_unknown_task_type(self):
        task = AgentTask(
            task_id="t1", agent_id="error-handler",
            task_type="unknown_op", input_data={},
        )
        result = self.agent.execute(task)
        assert not result.success

    def test_degradation_property(self):
        assert isinstance(self.agent.degradation, GracefulDegradation)

    def test_get_and_clear_errors(self):
        task = AgentTask(
            task_id="t1", agent_id="error-handler",
            task_type="error_record",
            input_data={"agent_id": "test", "message": "Error"},
        )
        self.agent.execute(task)
        assert len(self.agent.get_errors()) == 1

        self.agent.clear_errors()
        assert len(self.agent.get_errors()) == 0
        assert self.agent.error_count == 0

    def test_record_updates_degradation(self):
        task = AgentTask(
            task_id="t1", agent_id="error-handler",
            task_type="error_record",
            input_data={"agent_id": "metadata-agent", "message": "Failed"},
        )
        self.agent.execute(task)
        assert self.agent.degradation.is_failed("metadata-agent")

    def test_can_continue_in_response(self):
        task = AgentTask(
            task_id="t1", agent_id="error-handler",
            task_type="error_record",
            input_data={"agent_id": "metadata-agent", "message": "Timeout"},
        )
        result = self.agent.execute(task)
        assert result.success
        assert "can_continue" in result.data

    def test_remediation_in_record(self):
        task = AgentTask(
            task_id="t1", agent_id="error-handler",
            task_type="error_record",
            input_data={"agent_id": "test", "message": "Connection timed out"},
        )
        result = self.agent.execute(task)
        assert result.data["error_record"]["remediation"] != ""
