"""Stage names and run records for the Dynamic Agent Engine."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class StageName(StrEnum):
    REQUIREMENTS = "Requirements"
    PLANNING = "Planning"
    ARCHITECTURE = "Architecture"
    DEVELOPMENT = "Development"
    TESTING = "Testing"
    DEVOPS = "DevOps"


STAGE_ORDER: tuple[StageName, ...] = (
    StageName.REQUIREMENTS,
    StageName.PLANNING,
    StageName.ARCHITECTURE,
    StageName.DEVELOPMENT,
    StageName.TESTING,
    StageName.DEVOPS,
)

PREPARATION_STAGES: tuple[StageName, ...] = (
    StageName.REQUIREMENTS,
    StageName.PLANNING,
    StageName.ARCHITECTURE,
)


class RepairState(StrEnum):
    RUNNING = "running"
    PASSED = "passed"
    FAILED_BUDGET_EXHAUSTED = "failed_budget_exhausted"
    CANCELLED = "cancelled"
    ERROR = "error"


class RoleSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: StageName
    diagram_label: str
    goal: str


class AgentTeam(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int
    roles: list[RoleSpec]


class StageOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: StageName
    task_id: str
    trace_id: str
    summary: str
    simulation: bool


class RepairIteration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    iteration: int
    trace_id: str
    diff_summary: str
    tester_feedback: str
    passed: bool
    termination_reason: str | None = None


class AgentRunResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    trace_id: str
    state: RepairState
    stages: list[StageOutput] = Field(default_factory=list)
    iterations: list[RepairIteration] = Field(default_factory=list)
    devops_ran: bool
    simulation: bool
    live_crewai: bool
    live_gemini: bool
    host_execution: bool
    termination_reason: str
    engine: str
    execution_kind: str = "simulated"
