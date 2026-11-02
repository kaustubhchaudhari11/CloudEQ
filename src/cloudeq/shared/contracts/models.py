"""Typed contracts shared by FORGE SPAN planes.

These models are the intake, feasibility, handoff, and telemetry shapes from
``docs/architecture/contracts.md``. They do not depend on FastAPI or a model SDK.
"""

import re
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


TEST_COMMAND_ALLOWLIST: tuple[str, ...] = ("python -m pytest",)
MAX_RUNTIME_FILES = 20
MAX_RUNTIME_FILE_CHARS = 100_000
_ARTIFACT_REF = re.compile(r"[A-Za-z0-9_./-]{1,256}")


def normalize_relative_path(value: str) -> str:
    """Accept a workspace-relative POSIX path and reject escapes."""

    if not isinstance(value, str) or value == "" or "\\" in value or "\x00" in value:
        raise ValueError("Runtime paths must be non-empty relative POSIX paths.")
    if value.startswith("/") or re.match(r"^[A-Za-z]:", value):
        raise ValueError("Runtime paths must stay inside the task workspace.")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError("Runtime paths cannot contain empty, current, or parent segments.")
    return "/".join(parts)


class RuntimeFile(BaseModel):
    """A file the future container runtime may write. Plane 2 does not write it."""

    model_config = ConfigDict(extra="forbid")

    relative_path: str
    content: str | None = None
    artifact_ref: str | None = None

    @model_validator(mode="after")
    def _safe_file(self) -> "RuntimeFile":
        self.relative_path = normalize_relative_path(self.relative_path)
        has_content = self.content is not None
        reference = (self.artifact_ref or "").strip()
        if has_content == bool(reference):
            raise ValueError(
                "A runtime file needs exactly one of content or an artifact reference."
            )
        if self.content is not None and len(self.content) > MAX_RUNTIME_FILE_CHARS:
            raise ValueError("Runtime file content exceeds the contract limit.")
        if reference:
            if _ARTIFACT_REF.fullmatch(reference) is None:
                raise ValueError("Artifact references must be safe relative references.")
            normalize_relative_path(reference)
            self.artifact_ref = reference
        return self


class TestPlan(BaseModel):
    """Commands a future container may run. The allowlist is exact, not a shell."""

    model_config = ConfigDict(extra="forbid")

    commands: list[str]

    @model_validator(mode="after")
    def _allowlisted(self) -> "TestPlan":
        if not self.commands or len(self.commands) > 5:
            raise ValueError("A test plan needs one to five allowlisted commands.")
        for command in self.commands:
            if command not in TEST_COMMAND_ALLOWLIST:
                raise ValueError(f"Command is not allowlisted: {command}")
        return self


class ExecutionRequest(BaseModel):
    """One sandbox operation. Plane 2 sends it; Plane 3 will execute it."""

    model_config = ConfigDict(extra="forbid")

    task_id: str
    trace_id: str
    operation: RuntimeOperation
    iteration: int | None = None
    files: list[RuntimeFile] = Field(default_factory=list)
    test_plan: TestPlan | None = None

    @model_validator(mode="after")
    def _file_count(self) -> "ExecutionRequest":
        if len(self.files) > MAX_RUNTIME_FILES:
            raise ValueError("An execution request has too many files.")
        return self


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
