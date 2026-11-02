"""Stage-client contract for CrewAI. Model text is data, never a test pass."""

import json
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from cloudeq.plane2_agents.models import StageName
from cloudeq.plane2_agents.settings import AgentSettings
from cloudeq.shared.contracts.models import TEST_COMMAND_ALLOWLIST, RuntimeFile, TestPlan


class CrewConfigurationError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class MalformedStageOutput(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class CrewStageTimeout(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class CrewProviderError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class CrewIdentityError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class StageRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    trace_id: str
    stage: StageName
    role_goal: str
    diagram_label: str
    prompt: str
    iteration: int | None = None
    prior_feedback: str = ""


class StageDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    trace_id: str
    stage: StageName
    summary: str
    files: list[RuntimeFile] = Field(default_factory=list)
    test_commands: list[str] = Field(default_factory=list)


class CrewStageClient(Protocol):
    uses_live_provider: bool

    def run_stage(self, request: StageRunRequest) -> StageDraft:
        """Return one stage draft. The caller decides whether tests passed."""


def require_live_gemini(settings: AgentSettings) -> None:
    reason = settings.live_gemini_ready()
    if reason is not None:
        raise CrewConfigurationError(reason)


def parse_stage_text(raw: str, request: StageRunRequest) -> StageDraft:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise MalformedStageOutput("Crew output was not a JSON object.") from exc
    if not isinstance(payload, dict):
        raise MalformedStageOutput("Crew output was not a JSON object.")
    claimed_task = payload.get("task_id")
    claimed_trace = payload.get("trace_id")
    if isinstance(claimed_task, str) and claimed_task != request.task_id:
        raise CrewIdentityError("Crew output returned a mismatched task id.")
    if isinstance(claimed_trace, str) and claimed_trace != request.trace_id:
        raise CrewIdentityError("Crew output returned a mismatched trace id.")
    summary = payload.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        raise MalformedStageOutput("Crew output is missing a summary.")
    if len(summary) > 2_000:
        raise MalformedStageOutput("Crew output summary is too long.")
    files = _files(payload.get("files", []), request.stage)
    commands = _commands(payload.get("test_commands", []))
    return StageDraft(
        task_id=request.task_id,
        trace_id=request.trace_id,
        stage=request.stage,
        summary=summary.strip(),
        files=files,
        test_commands=commands,
    )


def _files(value: object, stage: StageName) -> list[RuntimeFile]:
    if stage is not StageName.DEVELOPMENT:
        return []
    if value is None:
        value = []
    if not isinstance(value, list):
        raise MalformedStageOutput("Crew files were not a list.")
    parsed: list[RuntimeFile] = []
    for item in value:
        if not isinstance(item, dict):
            raise MalformedStageOutput("A crew file was not an object.")
        try:
            parsed.append(
                RuntimeFile(
                    relative_path=str(item.get("relative_path", "")),
                    content=item.get("content") if isinstance(item.get("content"), str) else None,
                )
            )
        except ValidationError as exc:
            raise MalformedStageOutput("Crew output contained an unsafe file.") from exc
    if not parsed:
        raise MalformedStageOutput("The developer stage did not return a file.")
    return parsed


def _commands(value: object) -> list[str]:
    if value is None:
        value = []
    if not isinstance(value, list):
        raise MalformedStageOutput("Crew test commands were not a list.")
    if not value:
        return [TEST_COMMAND_ALLOWLIST[0]]
    commands: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise MalformedStageOutput("A crew test command was not text.")
        commands.append(item)
    try:
        TestPlan(commands=commands)
    except ValidationError as exc:
        raise MalformedStageOutput(
            "Crew output contained a command that is not allowlisted."
        ) from exc
    return commands
