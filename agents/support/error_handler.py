"""
Error Handling Framework - Classification, retry, and graceful degradation.

Provides:
- Error classification (transient, permanent, configuration)
- Retry strategy with exponential backoff
- Graceful degradation logic (partial results)
- Error reports with remediation suggestions
"""

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from agents.base import AgentCapabilities, AgentResult, AgentState, AgentTask, BaseAgent

logger = logging.getLogger(__name__)


class ErrorCategory(str, Enum):
    """Classification of errors."""
    TRANSIENT = "transient"       # Temporary failures (network, rate limit)
    PERMANENT = "permanent"       # Unrecoverable (bad input, missing data)
    CONFIGURATION = "configuration"  # Config issues (missing API key, bad model)
    RESOURCE = "resource"         # Resource exhaustion (memory, disk)
    UNKNOWN = "unknown"


class ErrorSeverity(str, Enum):
    """Severity levels."""
    CRITICAL = "critical"   # Pipeline must stop
    HIGH = "high"           # Agent failed, may affect downstream
    MEDIUM = "medium"       # Partial failure, degraded results
    LOW = "low"             # Minor issue, results still usable


@dataclass
class ErrorRecord:
    """Record of an error occurrence."""
    error_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    task_id: str = ""
    category: str = ErrorCategory.UNKNOWN
    severity: str = ErrorSeverity.MEDIUM
    message: str = ""
    exception_type: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    retry_count: int = 0
    resolved: bool = False
    remediation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_id": self.error_id,
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "category": self.category,
            "severity": self.severity,
            "message": self.message,
            "exception_type": self.exception_type,
            "timestamp": self.timestamp,
            "retry_count": self.retry_count,
            "resolved": self.resolved,
            "remediation": self.remediation,
        }


@dataclass
class ErrorReport:
    """Summary error report for an execution."""
    execution_id: str = ""
    total_errors: int = 0
    errors_by_category: Dict[str, int] = field(default_factory=dict)
    errors_by_severity: Dict[str, int] = field(default_factory=dict)
    errors_by_agent: Dict[str, int] = field(default_factory=dict)
    resolved_count: int = 0
    unresolved_count: int = 0
    records: List[ErrorRecord] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "total_errors": self.total_errors,
            "errors_by_category": self.errors_by_category,
            "errors_by_severity": self.errors_by_severity,
            "errors_by_agent": self.errors_by_agent,
            "resolved_count": self.resolved_count,
            "unresolved_count": self.unresolved_count,
            "records": [r.to_dict() for r in self.records],
        }


# Error classification rules
_TRANSIENT_PATTERNS = [
    "timeout", "timed out", "rate limit", "429", "503", "502",
    "connection reset", "connection refused", "temporary",
    "service unavailable", "retry", "throttl",
]

_CONFIGURATION_PATTERNS = [
    "api key", "api_key", "apikey", "authentication", "unauthorized",
    "401", "403", "forbidden", "invalid model", "model not found",
    "missing config", "not configured",
]

_RESOURCE_PATTERNS = [
    "out of memory", "oom", "disk full", "no space", "memory error",
    "resource exhausted", "quota exceeded",
]

_REMEDIATION_MAP = {
    ErrorCategory.TRANSIENT: "Retry the operation. If persistent, check network connectivity and API status.",
    ErrorCategory.PERMANENT: "Check input data validity. This error cannot be resolved by retrying.",
    ErrorCategory.CONFIGURATION: "Check API keys, model names, and configuration settings.",
    ErrorCategory.RESOURCE: "Free up system resources (memory/disk) or reduce batch size.",
    ErrorCategory.UNKNOWN: "Investigate the error details. Check logs for more context.",
}


def classify_error(exception: Exception) -> Tuple[ErrorCategory, ErrorSeverity]:
    """
    Classify an exception into category and severity.

    Uses pattern matching on the error message and exception type.
    """
    msg = str(exception).lower()
    exc_type = type(exception).__name__.lower()

    # Check transient patterns
    for pattern in _TRANSIENT_PATTERNS:
        if pattern in msg or pattern in exc_type:
            return ErrorCategory.TRANSIENT, ErrorSeverity.MEDIUM

    # Check configuration patterns
    for pattern in _CONFIGURATION_PATTERNS:
        if pattern in msg:
            return ErrorCategory.CONFIGURATION, ErrorSeverity.HIGH

    # Check resource patterns
    for pattern in _RESOURCE_PATTERNS:
        if pattern in msg:
            return ErrorCategory.RESOURCE, ErrorSeverity.CRITICAL

    # Check common permanent errors
    if isinstance(exception, (ValueError, TypeError, KeyError, AttributeError)):
        return ErrorCategory.PERMANENT, ErrorSeverity.HIGH

    if isinstance(exception, FileNotFoundError):
        return ErrorCategory.PERMANENT, ErrorSeverity.HIGH

    return ErrorCategory.UNKNOWN, ErrorSeverity.MEDIUM


def get_remediation(category: ErrorCategory) -> str:
    """Get remediation suggestion for an error category."""
    return _REMEDIATION_MAP.get(category, _REMEDIATION_MAP[ErrorCategory.UNKNOWN])


def _classify_from_message(msg: str, exc_type: str = "") -> Tuple[ErrorCategory, ErrorSeverity]:
    """Classify an error from its message and exception type name (strings only)."""
    lower_msg = msg.lower()
    lower_type = exc_type.lower()

    # Check transient patterns
    for pattern in _TRANSIENT_PATTERNS:
        if pattern in lower_msg or pattern in lower_type:
            return ErrorCategory.TRANSIENT, ErrorSeverity.MEDIUM

    # Check configuration patterns
    for pattern in _CONFIGURATION_PATTERNS:
        if pattern in lower_msg:
            return ErrorCategory.CONFIGURATION, ErrorSeverity.HIGH

    # Check resource patterns
    for pattern in _RESOURCE_PATTERNS:
        if pattern in lower_msg:
            return ErrorCategory.RESOURCE, ErrorSeverity.CRITICAL

    # Check exception type for permanent errors
    permanent_types = {"valueerror", "typeerror", "keyerror", "attributeerror", "filenotfounderror"}
    if lower_type in permanent_types:
        return ErrorCategory.PERMANENT, ErrorSeverity.HIGH

    return ErrorCategory.UNKNOWN, ErrorSeverity.MEDIUM


def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    retryable_categories: Optional[set] = None,
) -> Any:
    """
    Execute a function with exponential backoff retry.

    Args:
        func: Callable to execute (no arguments)
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        backoff_factor: Multiplier for each retry
        retryable_categories: Error categories that should be retried.
            Defaults to {TRANSIENT, RESOURCE}.

    Returns:
        The function's return value on success

    Raises:
        The last exception if all retries fail
    """
    if retryable_categories is None:
        retryable_categories = {ErrorCategory.TRANSIENT, ErrorCategory.RESOURCE}

    last_exception = None
    delay = base_delay

    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            last_exception = e
            category, _ = classify_error(e)

            if attempt >= max_retries or category not in retryable_categories:
                raise

            logger.warning(
                f"Retry {attempt + 1}/{max_retries} after {category.value} error: {e}. "
                f"Waiting {delay:.1f}s")
            time.sleep(delay)
            delay = min(max_delay, delay * backoff_factor)

    raise last_exception  # Should not reach here


class GracefulDegradation:
    """
    Manages graceful degradation when agents fail.

    Tracks which agents have failed and provides partial results
    with appropriate confidence adjustments.
    """

    def __init__(self):
        self._failed_agents: Dict[str, ErrorRecord] = {}
        self._partial_results: Dict[str, AgentResult] = {}

    def record_failure(self, agent_id: str, error: ErrorRecord) -> None:
        """Record an agent failure."""
        self._failed_agents[agent_id] = error

    def record_partial_result(self, agent_id: str, result: AgentResult) -> None:
        """Record a partial result from a degraded agent."""
        self._partial_results[agent_id] = result

    def is_failed(self, agent_id: str) -> bool:
        """Check if an agent has failed."""
        return agent_id in self._failed_agents

    def get_failed_agents(self) -> Dict[str, ErrorRecord]:
        """Get all failed agents and their errors."""
        return dict(self._failed_agents)

    def get_partial_results(self) -> Dict[str, AgentResult]:
        """Get all partial results."""
        return dict(self._partial_results)

    def should_continue(self, failed_agent_id: str,
                         critical_agents: Optional[set] = None) -> bool:
        """
        Determine if execution should continue after an agent failure.

        Args:
            failed_agent_id: The agent that failed
            critical_agents: Set of agent IDs that are critical (pipeline stops if they fail)

        Returns:
            True if execution can continue with degraded results
        """
        if critical_agents and failed_agent_id in critical_agents:
            return False

        error = self._failed_agents.get(failed_agent_id)
        if error and error.severity == ErrorSeverity.CRITICAL:
            return False

        return True

    def get_degradation_summary(self) -> Dict[str, Any]:
        """Get a summary of degradation state."""
        return {
            "failed_agent_count": len(self._failed_agents),
            "failed_agents": list(self._failed_agents.keys()),
            "partial_result_count": len(self._partial_results),
            "partial_result_agents": list(self._partial_results.keys()),
        }


class ErrorHandlerAgent(BaseAgent):
    """
    Agent for centralized error handling and reporting.

    Provides:
    - Error recording and classification
    - Error report generation
    - Retry coordination
    - Graceful degradation management
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id="error-handler", config=config or {})
        self._errors: List[ErrorRecord] = []
        self._degradation = GracefulDegradation()

    def initialize(self) -> None:
        self.set_state(AgentState.READY)
        self._logger.info(f"[{self.agent_id}] Initialized")

    def terminate(self) -> None:
        self.set_state(AgentState.TERMINATED)

    def get_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            agent_type="support",
            input_types=["error", "exception"],
            output_types=["error_report", "error_record"],
        )

    def execute(self, task: AgentTask) -> AgentResult:
        """
        Execute error handling operations.

        Task types:
        - "error_record": Record a new error
        - "error_report": Generate error report
        - "error_classify": Classify an error

        Input data for error_record:
        - agent_id (str): Agent that encountered the error
        - task_id (str): Task that failed
        - message (str): Error message
        - exception_type (str, optional): Exception class name

        Input data for error_report:
        - execution_id (str, optional): Filter by execution

        Input data for error_classify:
        - message (str): Error message
        - exception_type (str, optional): Exception class name
        """
        try:
            task_type = task.task_type
            if task_type == "error_record":
                return self._handle_record(task)
            elif task_type == "error_report":
                return self._handle_report(task)
            elif task_type == "error_classify":
                return self._handle_classify(task)
            else:
                return AgentResult(
                    task_id=task.task_id, agent_id=self.agent_id,
                    success=False, error=f"Unknown task type: {task_type}",
                )
        except Exception as e:
            return AgentResult(
                task_id=task.task_id, agent_id=self.agent_id,
                success=False, error=str(e),
            )

    def _handle_record(self, task: AgentTask) -> AgentResult:
        """Record a new error."""
        data = task.input_data
        msg = data.get("message", "")
        exc_type = data.get("exception_type", "")

        # Classify based on message text
        category, severity = _classify_from_message(msg, exc_type)
        remediation = get_remediation(category)

        record = ErrorRecord(
            agent_id=data.get("agent_id", ""),
            task_id=data.get("task_id", task.task_id),
            category=category.value,
            severity=severity.value,
            message=msg,
            exception_type=exc_type,
            remediation=remediation,
        )
        self._errors.append(record)

        # Record in degradation tracker
        if record.agent_id:
            self._degradation.record_failure(record.agent_id, record)

        return AgentResult(
            task_id=task.task_id, agent_id=self.agent_id,
            success=True,
            data={
                "error_record": record.to_dict(),
                "should_retry": category == ErrorCategory.TRANSIENT,
                "can_continue": self._degradation.should_continue(record.agent_id),
            },
        )

    def _handle_report(self, task: AgentTask) -> AgentResult:
        """Generate an error report."""
        report = self._generate_report(task.input_data.get("execution_id", ""))
        return AgentResult(
            task_id=task.task_id, agent_id=self.agent_id,
            success=True,
            data={"report": report.to_dict()},
        )

    def _handle_classify(self, task: AgentTask) -> AgentResult:
        """Classify an error without recording it."""
        msg = task.input_data.get("message", "")
        exc = Exception(msg)
        category, severity = classify_error(exc)
        remediation = get_remediation(category)

        return AgentResult(
            task_id=task.task_id, agent_id=self.agent_id,
            success=True,
            data={
                "category": category.value,
                "severity": severity.value,
                "remediation": remediation,
                "should_retry": category == ErrorCategory.TRANSIENT,
            },
        )

    def _generate_report(self, execution_id: str = "") -> ErrorReport:
        """Generate an error report from recorded errors."""
        records = self._errors
        report = ErrorReport(execution_id=execution_id)
        report.total_errors = len(records)
        report.records = list(records)

        for r in records:
            # By category
            report.errors_by_category[r.category] = (
                report.errors_by_category.get(r.category, 0) + 1)
            # By severity
            report.errors_by_severity[r.severity] = (
                report.errors_by_severity.get(r.severity, 0) + 1)
            # By agent
            if r.agent_id:
                report.errors_by_agent[r.agent_id] = (
                    report.errors_by_agent.get(r.agent_id, 0) + 1)
            # Resolved tracking
            if r.resolved:
                report.resolved_count += 1
            else:
                report.unresolved_count += 1

        return report

    @property
    def degradation(self) -> GracefulDegradation:
        """Access the graceful degradation manager."""
        return self._degradation

    @property
    def error_count(self) -> int:
        """Get total error count."""
        return len(self._errors)

    def get_errors(self) -> List[ErrorRecord]:
        """Get all recorded errors."""
        return list(self._errors)

    def clear_errors(self) -> None:
        """Clear all recorded errors."""
        self._errors.clear()
