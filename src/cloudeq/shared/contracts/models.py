"""Typed contracts shared by FORGE SPAN planes.

These models are the intake, feasibility, handoff, and telemetry shapes from
``docs/architecture/contracts.md``. They do not depend on FastAPI or a model SDK.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SubmissionSource(StrEnum):
    API = "api"
    CLI = "cli"
    GITHUB_ISSUES = "github_issues"
    JIRA = "jira"


class TaskStatus(StrEnum):
    REJECTED = "rejected"
    ACCEPTED = "accepted"
    ROUTED = "routed"
    HANDED_OFF = "handed_off"


class FeasibilityStatus(StrEnum):
    FEASIBLE = "feasible"
    INFEASIBLE = "infeasible"
    ERROR = "error"


class DatasetCheck(StrEnum):
    NOT_APPLICABLE = "not_applicable"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class RouterKind(StrEnum):
    OFFLINE = "offline"
    GEMINI = "gemini"


class PlaneName(StrEnum):
    PLANE1_INTAKE = "plane1_intake"
    PLANE2_AGENTS = "plane2_agents"
    PLANE3_RUNTIME = "plane3_runtime"
    PLANE4_OBSERVABILITY = "plane4_observability"


class TaskSubmission(BaseModel):
    """A prompt intake request. Plane 1 assigns ``task_id``; callers cannot."""

    model_config = ConfigDict(extra="forbid")

    source: SubmissionSource
    prompt: str
    external_ref: dict[str, Any] | None = None


class FeasibilityResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: FeasibilityStatus
    dataset_check: DatasetCheck
    reasons: list[str]
    router: RouterKind
    model_id: str = ""


class RoutingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    trace_id: str
    prompt: str
    external_ref: dict[str, Any] | None = None


class HandoffRequest(BaseModel):
    """Contract passed to Plane 2. Acceptance is not code execution."""

    model_config = ConfigDict(extra="forbid")

    task_id: str
    trace_id: str
    prompt: str
    feasibility: FeasibilityResult


class HandoffAcknowledgement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    trace_id: str
    accepted: bool
    execution_started: bool = False


class TaskResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: TaskStatus
    trace_id: str
    task_id: str | None = None
    source: SubmissionSource | None = None
    prompt: str | None = None
    reasons: list[str] = Field(default_factory=list)
    feasibility: FeasibilityResult | None = None
    handoff_accepted: bool | None = None
    execution_started: bool = False


class TelemetryEnvelope(BaseModel):
    """Transport envelope. ``payload`` is schema-agnostic."""

    model_config = ConfigDict(extra="forbid")

    envelope_version: str = "1"
    event_id: str
    trace_id: str
    source: PlaneName
    event_name: str
    occurred_at: datetime
    payload: Any
    task_id: str | None = None
    span_id: str | None = None
    parent_span_id: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class EnvelopeRejected(Exception):
    """The envelope failed transport validation and was not retained."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class RuntimeOperation(StrEnum):
    WRITE_FILE = "write_file"
    RUN_TESTS = "run_tests"
    GIT_COMMIT = "git_commit"


class ExecutionRequest(BaseModel):
    """One sandbox operation. Plane 2 sends it; Plane 3 will execute it."""

    model_config = ConfigDict(extra="forbid")

    task_id: str
    trace_id: str
    operation: RuntimeOperation
    iteration: int | None = None


class ExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    trace_id: str
    operation: RuntimeOperation
    exit_code: int
    timed_out: bool = False
    passed: bool | None = None
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = 0
    artifact_refs: list[str] = Field(default_factory=list)
    simulation: bool
    host_execution: bool = False
