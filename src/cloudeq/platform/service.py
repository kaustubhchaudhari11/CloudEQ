"""End-to-end orchestration: Plane 1 -> Plane 2 -> Plane 3, all telemetry -> Plane 4.

Every plane receives the same ``TelemetrySink`` (Plane 4's federated sink), so
one ``trace_id`` links intake, agent, runtime, and observability records.
"""

import json
import logging
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from cloudeq.plane1_intake.service import IntakeService
from cloudeq.plane1_intake.settings import Settings as IntakeSettings
from cloudeq.plane2_agents.agents.crewai import CrewAIGeminiStageClient
from cloudeq.plane2_agents.agents.stage_client import CrewStageClient
from cloudeq.plane2_agents.agents.template import TemplateStageClient
from cloudeq.plane2_agents.models import AgentRunResult
from cloudeq.plane2_agents.runtime_sim import OfflineRuntimeSimulation
from cloudeq.plane2_agents.settings import AgentSettings
from cloudeq.plane2_agents.supervisor import Supervisor
from cloudeq.plane3_runtime.executor import DockerRuntimeExecutor
from cloudeq.plane3_runtime.render_runner import RenderRuntimeSettings, RenderSandboxRunner
from cloudeq.plane3_runtime.runner import DockerRunner, SubprocessDockerRunner
from cloudeq.plane3_runtime.settings import RuntimeSettings
from cloudeq.plane4_observability.factory import ObservabilityStack, build_observability
from cloudeq.platform.settings import PlatformSettings
from cloudeq.shared.contracts.models import (
    ExecutionRequest,
    ExecutionResult,
    HandoffAcknowledgement,
    HandoffRequest,
    PlaneName,
    SubmissionSource,
    TaskResult,
    TaskSubmission,
    TelemetryEnvelope,
)
from cloudeq.shared.ports.errors import RuntimeExecutionError
from cloudeq.shared.ports.protocols import RuntimeExecutor, TelemetrySink

logger = logging.getLogger(__name__)


@dataclass
class RunOptions:
    simulated_failures: int = 0
    use_template: bool = False


@dataclass
class _Pending:
    options: RunOptions = field(default_factory=RunOptions)
    agent_run: AgentRunResult | None = None
    details: dict[str, Any] = field(default_factory=dict)


class PlatformHandoff:
    """Plane 2 side of the handoff port: runs the supervisor for the accepted task.

    The acknowledgement keeps ``execution_started`` false because Plane 1 must not
    claim execution; the agent result is reported separately by the platform.
    """

    def __init__(self, platform: "Platform") -> None:
        self._platform = platform

    def submit(self, handoff: HandoffRequest) -> HandoffAcknowledgement:
        self._platform._run_agents(handoff)
        return HandoffAcknowledgement(
            task_id=handoff.task_id,
            trace_id=handoff.trace_id,
            accepted=True,
            execution_started=False,
        )


class ObservedSimulation:
    """Wraps the offline runtime simulation so its operations reach Plane 4 too.

    Events carry ``simulation: true``; they never claim container execution.
    """

    def __init__(self, inner: OfflineRuntimeSimulation, sink: TelemetrySink) -> None:
        self.inner = inner
        self.execution_backend = inner.execution_backend
        self._sink = sink

    @property
    def calls(self) -> list[ExecutionRequest]:
        return self.inner.calls

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        started = time.perf_counter()
        try:
            result = self.inner.execute(request)
        except RuntimeExecutionError:
            self._emit(
                request,
                "runtime.operation_rejected",
                {"operation": request.operation.value, "rejected": True, "simulation": True},
            )
            raise
        self._emit(
            request,
            "runtime.operation_completed",
            {
                "operation": result.operation.value,
                "exit_code": result.exit_code,
                "passed": result.passed,
                "timed_out": result.timed_out,
                "duration_ms": int((time.perf_counter() - started) * 1000),
                "simulation": True,
                "host_execution": False,
                "iteration": request.iteration,
            },
        )
        return result

    def _emit(self, request: ExecutionRequest, name: str, payload: dict[str, object]) -> None:
        self._sink.emit(
            TelemetryEnvelope(
                event_id=str(uuid4()),
                trace_id=request.trace_id,
                source=PlaneName.PLANE3_RUNTIME,
                event_name=name,
                occurred_at=datetime.now(UTC),
                payload=payload,
                task_id=request.task_id,
            )
        )


def docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        done = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return done.returncode == 0 and bool(done.stdout.strip())


class Platform:
    def __init__(
        self,
        *,
        settings: PlatformSettings | None = None,
        observability: ObservabilityStack | None = None,
        intake_settings: IntakeSettings | None = None,
        agent_settings: AgentSettings | None = None,
        runtime_settings: RuntimeSettings | None = None,
        docker_runner: DockerRunner | None = None,
        runs_file: Path | None = None,
    ) -> None:
        self.settings = settings or PlatformSettings()
        self.observability = observability or build_observability()
        self.agent_settings = agent_settings or AgentSettings()
        self.runtime_settings = runtime_settings or RuntimeSettings()
        self._docker_runner = docker_runner
        self.intake = IntakeService.from_settings(
            intake_settings or IntakeSettings(),
            handoff=PlatformHandoff(self),
            sink=self.observability.sink,
        )
        self._lock = threading.Lock()
        self._pending = _Pending()
        self._runs: dict[str, dict[str, Any]] = {}
        self._order: list[str] = []
        self._runs_file = runs_file or Path(self.settings.cloudeq_runs_file).expanduser()
        self._executor: DockerRuntimeExecutor | None = None
        self._load_runs()

    # ------------------------------------------------------------ config
    @property
    def mode(self) -> str:
        return self.settings.cloudeq_execution_mode

    def stage_client_label(self) -> str:
        if self.mode not in {"docker", "render"}:
            return "offline simulation (no LLM)"
        if self._live_gemini():
            return "CrewAI + Gemini (live)"
        return TemplateStageClient.label

    def _live_gemini(self) -> bool:
        return (
            self.agent_settings.cloudeq_agent_engine == "crewai"
            and self.agent_settings.live_gemini_ready() is None
        )

    def describe(self) -> dict[str, Any]:
        return {
            "product": "FORGE SPAN",
            "team": "Cloud EQ",
            "execution_mode": self.mode,
            "stage_client": self.stage_client_label(),
            "router_mode": self.intake.settings.cloudeq_router_mode,
            "live_gemini": self._live_gemini(),
            "repair_max_iterations": self.settings.cloudeq_repair_max_iterations,
            "runtime_image": self.runtime_settings.cloudeq_runtime_image,
            "observability": self.observability.describe(),
        }

    # -------------------------------------------------------------- runs
    def run(
        self,
        prompt: str,
        *,
        dataset: str | None = None,
        simulated_failures: int = 0,
        use_template: bool = False,
    ) -> dict[str, Any]:
        """Submit one prompt through every plane and return the combined record."""

        external = {"dataset": dataset} if dataset else None
        failures = max(0, min(int(simulated_failures), 10))
        with self._lock:
            self._pending = _Pending(
                options=RunOptions(simulated_failures=failures, use_template=use_template)
            )
            started = datetime.now(UTC)
            intake_service = self.intake
            if use_template:
                intake_service = IntakeService.from_settings(
                    self.intake.settings.model_copy(update={"cloudeq_router_mode": "offline"}),
                    handoff=PlatformHandoff(self),
                    sink=self.observability.sink,
                )
            intake = intake_service.submit(
                TaskSubmission(source=SubmissionSource.API, prompt=prompt, external_ref=external),
                expected_source=SubmissionSource.API,
            )
            pending = self._pending
            self._pending = _Pending()
        record = self._record(intake, pending, started, failures)
        if intake.task_id:
            self._save(record)
        return record

    def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        ids = list(reversed(self._order))[:limit]
        return [_summary(self._runs[i]) for i in ids]

    def get_run(self, task_id: str) -> dict[str, Any] | None:
        return self._runs.get(task_id)

    # ----------------------------------------------------------- planes 2+3
    def _run_agents(self, handoff: HandoffRequest) -> None:
        options = self._pending.options
        runtime: RuntimeExecutor
        client: CrewStageClient | None = None
        details: dict[str, Any] = {"stage_client": self.stage_client_label()}
        if self.mode in {"docker", "render"}:
            try:
                runtime = self._docker_executor()
            except RuntimeExecutionError as exc:
                details["runtime_error"] = exc.reason
                runtime = OfflineRuntimeSimulation(raise_on_execute=True)
            template: TemplateStageClient | None = None
            if self._live_gemini() and not options.use_template:
                client = CrewAIGeminiStageClient(self.agent_settings)
            else:
                template = TemplateStageClient(fail_first=options.simulated_failures)
                client = template
                details["stage_client"] = TemplateStageClient.label
            engine = "crewai"
        else:
            outcomes = [False] * options.simulated_failures + [True]
            runtime = ObservedSimulation(
                OfflineRuntimeSimulation(test_outcomes=outcomes), self.observability.sink
            )
            template = None
            engine = "offline"
        supervisor = Supervisor(
            runtime=runtime,
            sink=self.observability.sink,
            max_iterations=self.settings.cloudeq_repair_max_iterations,
            engine=engine,
            crew_client=client,
            settings=self.agent_settings,
        )
        result = supervisor.run(handoff)
        if self._executor is not None:
            details["generated_files"] = self._executor.files_for(handoff.task_id)
        if template is not None:
            files = template.generated.get(handoff.task_id, [])
            details["generated_files"] = [
                {"path": f.relative_path, "content": f.content or ""} for f in files
            ]
        if isinstance(runtime, ObservedSimulation | OfflineRuntimeSimulation):
            details["runtime_backend"] = runtime.execution_backend
            details["runtime_calls"] = len(runtime.calls)
        else:
            details["runtime_backend"] = getattr(runtime, "execution_backend", "unknown")
        self._pending.agent_run = result
        self._pending.details = details

    def _docker_executor(self) -> DockerRuntimeExecutor:
        if self._executor is None:
            runner: DockerRunner = self._docker_runner or (
                RenderSandboxRunner(RenderRuntimeSettings())
                if self.mode == "render"
                else SubprocessDockerRunner()
            )
            self._executor = DockerRuntimeExecutor(
                self.runtime_settings, runner, self.observability.sink
            )
        return self._executor

    # ------------------------------------------------------------ storage
    def _record(
        self, intake: TaskResult, pending: _Pending, started: datetime, failures: int
    ) -> dict[str, Any]:
        agent = pending.agent_run
        finished = datetime.now(UTC)
        return {
            "task_id": intake.task_id,
            "trace_id": intake.trace_id,
            "prompt": intake.prompt,
            "created_at": started.isoformat(),
            "duration_ms": int((finished - started).total_seconds() * 1000),
            "execution_mode": self.mode,
            "requested_simulated_failures": failures,
            "intake": intake.model_dump(mode="json"),
            "agents": agent.model_dump(mode="json") if agent else None,
            "details": pending.details,
            "outcome": _outcome(intake, agent),
        }

    def _save(self, record: dict[str, Any]) -> None:
        task_id = str(record["task_id"])
        self._runs[task_id] = record
        self._order.append(task_id)
        try:
            self._runs_file.parent.mkdir(parents=True, exist_ok=True)
            with self._runs_file.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError:
            logger.warning("could not append run record to %s", self._runs_file)

    def _load_runs(self) -> None:
        if not self._runs_file.is_file():
            return
        for line in self._runs_file.read_text(encoding="utf-8").splitlines():
            try:
                record = json.loads(line)
            except ValueError:
                continue
            task_id = record.get("task_id")
            if isinstance(task_id, str) and task_id not in self._runs:
                self._runs[task_id] = record
                self._order.append(task_id)


def _outcome(intake: TaskResult, agent: AgentRunResult | None) -> str:
    if agent is not None:
        return agent.state.value
    return intake.status.value


def _summary(record: dict[str, Any]) -> dict[str, Any]:
    agents = record.get("agents") or {}
    return {
        "task_id": record.get("task_id"),
        "trace_id": record.get("trace_id"),
        "prompt": record.get("prompt"),
        "created_at": record.get("created_at"),
        "execution_mode": record.get("execution_mode"),
        "outcome": record.get("outcome"),
        "iterations": len(agents.get("iterations") or []),
        "devops_ran": agents.get("devops_ran", False),
        "engine": agents.get("engine"),
    }
