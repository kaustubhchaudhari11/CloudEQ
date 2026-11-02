"""Supervisor for the six SDLC stages and the bounded Developer–Tester loop."""

import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from cloudeq.plane2_agents.agents.offline import OfflineStageWorker
from cloudeq.plane2_agents.agents.stage_client import CrewStageClient
from cloudeq.plane2_agents.config_loader import (
    DEFAULT_AGENTS_CONFIG,
    AgentConfigError,
    load_agent_team,
)
from cloudeq.plane2_agents.models import (
    PREPARATION_STAGES,
    AgentRunResult,
    RepairIteration,
    RepairState,
    StageName,
    StageOutput,
)
from cloudeq.plane2_agents.runtime_checks import runtime_problem
from cloudeq.plane2_agents.settings import AgentSettings
from cloudeq.shared.contracts.models import (
    ExecutionRequest,
    HandoffRequest,
    PlaneName,
    RuntimeOperation,
    TelemetryEnvelope,
)
from cloudeq.shared.ports.errors import RuntimeExecutionError
from cloudeq.shared.ports.protocols import RuntimeExecutor, TelemetrySink

logger = logging.getLogger(__name__)


class CancelToken:
    def __init__(self) -> None:
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True


class Supervisor:
    def __init__(
        self,
        *,
        config_path: Path | None = None,
        runtime: RuntimeExecutor,
        sink: TelemetrySink,
        max_iterations: int = 3,
        engine: str = "offline",
        token: CancelToken | None = None,
        worker: OfflineStageWorker | None = None,
        settings: AgentSettings | None = None,
        crew_client: CrewStageClient | None = None,
    ) -> None:
        self._config_path = config_path or DEFAULT_AGENTS_CONFIG
        self._runtime = runtime
        self._sink = sink
        self._max_iterations = max_iterations
        self._engine = engine
        self._token = token or CancelToken()
        self._worker = worker or OfflineStageWorker()
        self._settings = settings
        self._crew_client = crew_client

    @property
    def token(self) -> CancelToken:
        return self._token

    @property
    def settings(self) -> AgentSettings:
        return self._settings or AgentSettings()

    @property
    def crew_client(self) -> CrewStageClient | None:
        return self._crew_client

    @property
    def runtime(self) -> RuntimeExecutor:
        return self._runtime

    @property
    def max_iterations(self) -> int:
        return self._max_iterations

    def run(self, handoff: HandoffRequest) -> AgentRunResult:
        if self._max_iterations < 1:
            return self._finish(
                handoff,
                state=RepairState.ERROR,
                stages=[],
                iterations=[],
                devops_ran=False,
                reason="Repair maximum must be at least 1.",
                simulation=self._engine == "offline",
                engine=self._engine_label(),
            )
        try:
            team = load_agent_team(self._config_path)
        except AgentConfigError as exc:
            return self._finish(
                handoff,
                state=RepairState.ERROR,
                stages=[],
                iterations=[],
                devops_ran=False,
                reason=exc.reason,
                simulation=False,
                engine=self._engine_label(),
            )
        if self._engine == "crewai":
            from cloudeq.plane2_agents.crew_run import run_crew

            return run_crew(self, handoff, team)
        if self._token.cancelled:
            return self._finish(
                handoff,
                state=RepairState.CANCELLED,
                stages=[],
                iterations=[],
                devops_ran=False,
                reason="Cancelled before the first stage.",
                simulation=True,
                engine="offline-simulation",
            )

        stages: list[StageOutput] = []
        for stage in PREPARATION_STAGES:
            if self._token.cancelled:
                return self._finish(
                    handoff,
                    state=RepairState.CANCELLED,
                    stages=stages,
                    iterations=[],
                    devops_ran=False,
                    reason=f"Cancelled before {stage.value}.",
                    simulation=True,
                    engine="offline-simulation",
                )
            stages.append(
                self._record_stage(handoff, stage, self._worker.summarize(stage, handoff.prompt))
            )

        iterations: list[RepairIteration] = []
        state = RepairState.RUNNING
        reason = ""
        for iteration in range(1, self._max_iterations + 1):
            if self._token.cancelled:
                state = RepairState.CANCELLED
                reason = "Cancelled before the next repair iteration."
                break
            try:
                written = self._runtime.execute(
                    ExecutionRequest(
                        task_id=handoff.task_id,
                        trace_id=handoff.trace_id,
                        operation=RuntimeOperation.WRITE_FILE,
                        iteration=iteration,
                    )
                )
                problem = runtime_problem(
                    written,
                    handoff=handoff,
                    operation=RuntimeOperation.WRITE_FILE,
                    expect_simulation=True,
                )
                if problem is not None:
                    raise RuntimeExecutionError(problem)
                tested = self._runtime.execute(
                    ExecutionRequest(
                        task_id=handoff.task_id,
                        trace_id=handoff.trace_id,
                        operation=RuntimeOperation.RUN_TESTS,
                        iteration=iteration,
                    )
                )
            except RuntimeExecutionError as exc:
                return self._finish(
                    handoff,
                    state=RepairState.ERROR,
                    stages=stages,
                    iterations=iterations,
                    devops_ran=False,
                    reason=exc.reason,
                    simulation=True,
                    engine="offline-simulation",
                )
            problem = runtime_problem(
                tested,
                handoff=handoff,
                operation=RuntimeOperation.RUN_TESTS,
                expect_simulation=True,
            )
            if problem is not None:
                return self._finish(
                    handoff,
                    state=RepairState.ERROR,
                    stages=stages,
                    iterations=iterations,
                    devops_ran=False,
                    reason=problem,
                    simulation=True,
                    engine="offline-simulation",
                )
            if not isinstance(tested.passed, bool):
                return self._finish(
                    handoff,
                    state=RepairState.ERROR,
                    stages=stages,
                    iterations=iterations,
                    devops_ran=False,
                    reason="Runtime did not return a test pass or fail.",
                    simulation=True,
                    engine="offline-simulation",
                )
            passed = tested.passed
            diff_summary = (
                written.artifact_refs[0]
                if written.artifact_refs
                else self._worker.diff_summary(handoff.task_id, iteration)
            )
            feedback = tested.stdout or tested.stderr
            final_reason = None
            if passed:
                final_reason = f"Tests passed on iteration {iteration}."
            elif self._token.cancelled:
                final_reason = "Cancelled after a failing test."
            elif iteration == self._max_iterations:
                final_reason = f"Repair budget of {self._max_iterations} iterations was exhausted."
            record = RepairIteration(
                iteration=iteration,
                trace_id=handoff.trace_id,
                diff_summary=diff_summary,
                tester_feedback=feedback,
                passed=passed,
                termination_reason=final_reason,
            )
            iterations.append(record)
            self._emit(
                handoff,
                "agents.repair_iteration",
                {
                    "iteration": iteration,
                    "passed": passed,
                    "trace_id": handoff.trace_id,
                    "termination_reason": final_reason,
                },
            )
            self._emit(
                handoff,
                "agents.test_result",
                {"iteration": iteration, "passed": passed, "feedback_present": bool(feedback)},
            )
            if passed:
                state = RepairState.PASSED
                reason = final_reason or "Tests passed."
                break
            if self._token.cancelled:
                state = RepairState.CANCELLED
                reason = final_reason or "Cancelled after a failing test."
                break
            if iteration == self._max_iterations:
                state = RepairState.FAILED_BUDGET_EXHAUSTED
                reason = final_reason or "Repair budget was exhausted."

        if iterations:
            stages.append(
                self._record_stage(handoff, StageName.DEVELOPMENT, iterations[-1].diff_summary)
            )
            stages.append(
                self._record_stage(handoff, StageName.TESTING, iterations[-1].tester_feedback)
            )
        devops_ran = False
        if state is RepairState.PASSED:
            if self._token.cancelled:
                state = RepairState.CANCELLED
                reason = "Cancelled before DevOps."
            else:
                stages.append(
                    self._record_stage(
                        handoff,
                        StageName.DEVOPS,
                        "DevOps accepted the passing test result. No host command was run.",
                    )
                )
                devops_ran = True
        return self._finish(
            handoff,
            state=state,
            stages=stages,
            iterations=iterations,
            devops_ran=devops_ran,
            reason=reason,
            simulation=True,
            engine="offline-simulation",
        )

    def _record_stage(
        self,
        handoff: HandoffRequest,
        stage: StageName,
        summary: str,
        *,
        simulation: bool = True,
    ) -> StageOutput:
        output = StageOutput(
            stage=stage,
            task_id=handoff.task_id,
            trace_id=handoff.trace_id,
            summary=summary,
            simulation=simulation,
        )
        self._emit(
            handoff,
            "agents.stage_completed",
            {"stage": stage.value, "trace_id": handoff.trace_id},
        )
        self._emit(
            handoff,
            "agents.decision",
            {"stage": stage.value, "summary_length": len(summary), "simulation": simulation},
        )
        logger.info(
            "stage completed",
            extra={"trace_id": handoff.trace_id, "task_id": handoff.task_id, "status": stage.value},
        )
        return output

    def _finish(
        self,
        handoff: HandoffRequest,
        *,
        state: RepairState,
        stages: list[StageOutput],
        iterations: list[RepairIteration],
        devops_ran: bool,
        reason: str,
        simulation: bool,
        engine: str,
        execution_kind: str = "simulated",
        live_crewai: bool = False,
        live_gemini: bool = False,
    ) -> AgentRunResult:
        result = AgentRunResult(
            task_id=handoff.task_id,
            trace_id=handoff.trace_id,
            state=state,
            stages=stages,
            iterations=iterations,
            devops_ran=devops_ran,
            simulation=simulation,
            live_crewai=live_crewai,
            live_gemini=live_gemini,
            host_execution=False,
            termination_reason=reason,
            engine=engine,
            execution_kind=execution_kind,
        )
        self._emit(
            handoff,
            "agents.run_finished",
            {
                "state": state.value,
                "devops_ran": devops_ran,
                "iterations": len(iterations),
                "simulation": simulation,
                "live_crewai": live_crewai,
                "live_gemini": live_gemini,
                "execution_kind": execution_kind,
                "reason_present": bool(reason),
            },
        )
        return result

    def _emit(self, handoff: HandoffRequest, event_name: str, payload: dict[str, object]) -> None:
        envelope = TelemetryEnvelope(
            event_id=str(uuid4()),
            trace_id=handoff.trace_id,
            source=PlaneName.PLANE2_AGENTS,
            event_name=event_name,
            occurred_at=datetime.now(UTC),
            payload=payload,
            task_id=handoff.task_id,
        )
        self._sink.emit(envelope)

    def _engine_label(self) -> str:
        if self._engine == "crewai":
            return "crewai-not-executed"
        return "offline-simulation"
