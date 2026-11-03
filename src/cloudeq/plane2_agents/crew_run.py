"""CrewAI supervisor path. A mocked client is not a live Gemini call."""

from typing import Any

from cloudeq.plane2_agents.agents.stage_client import (
    CrewConfigurationError,
    CrewIdentityError,
    CrewProviderError,
    CrewStageClient,
    CrewStageTimeout,
    MalformedStageOutput,
    StageDraft,
    StageRunRequest,
    require_live_gemini,
)
from cloudeq.plane2_agents.models import (
    AgentRunResult,
    AgentTeam,
    RepairIteration,
    RepairState,
    StageName,
    StageOutput,
)
from cloudeq.plane2_agents.runtime_checks import runtime_problem
from cloudeq.shared.contracts.models import (
    ExecutionRequest,
    HandoffRequest,
    RuntimeOperation,
    TestPlan,
)
from cloudeq.shared.ports.errors import RuntimeExecutionError


def _as_result(value: object) -> AgentRunResult:
    if not isinstance(value, AgentRunResult):
        raise TypeError("Supervisor returned an unexpected result.")
    return value


def _as_stage(value: object) -> StageOutput:
    if not isinstance(value, StageOutput):
        raise TypeError("Supervisor returned an unexpected stage.")
    return value


def run_crew(supervisor: Any, handoff: HandoffRequest, team: AgentTeam) -> AgentRunResult:
    client = supervisor.crew_client
    backend = getattr(supervisor.runtime, "execution_backend", "simulation")
    if client is None:
        try:
            require_live_gemini(supervisor.settings)
        except CrewConfigurationError as exc:
            return _error(supervisor, handoff, exc.reason, "crewai-configuration-error")
        return _error(
            supervisor,
            handoff,
            "Container execution is unavailable. Live CrewAI kickoff was not run, "
            "and this is not an end-to-end success.",
            "crewai-execution-unavailable",
        )
    if client.uses_live_provider:
        if backend != "container":
            return _error(
                supervisor,
                handoff,
                "Container execution is unavailable. A live stage client runs only "
                "with the container backend, and this is not an end-to-end success.",
                "crewai-execution-unavailable",
            )
        try:
            require_live_gemini(supervisor.settings)
        except CrewConfigurationError as exc:
            return _error(supervisor, handoff, exc.reason, "crewai-configuration-error")
    elif backend not in {"mock", "container", "container-mock"}:
        return _error(
            supervisor,
            handoff,
            "Container execution is unavailable. The offline simulation cannot "
            "satisfy CrewAI mode.",
            "crewai-execution-unavailable",
        )
    run_engine = "crewai-container" if backend == "container" else "crewai-mocked"
    run_kind = "container" if backend == "container" else "mocked"

    stages: list[StageOutput] = []
    try:
        for stage in (StageName.REQUIREMENTS, StageName.PLANNING, StageName.ARCHITECTURE):
            if supervisor.token.cancelled:
                return _as_result(
                    supervisor._finish(
                        handoff,
                        state=RepairState.CANCELLED,
                        stages=stages,
                        iterations=[],
                        devops_ran=False,
                        reason=f"Cancelled before {stage.value}.",
                        simulation=False,
                        engine=run_engine,
                        execution_kind=run_kind,
                    )
                )
            draft = _draft(client, team, handoff, stage, None, "")
            stages.append(_stage(supervisor, handoff, draft))
    except (
        MalformedStageOutput,
        CrewStageTimeout,
        CrewProviderError,
        CrewIdentityError,
        CrewConfigurationError,
    ) as exc:
        return _error(
            supervisor, handoff, exc.reason, _client_error_engine(exc, run_engine), stages=stages
        )

    iterations: list[RepairIteration] = []
    state = RepairState.RUNNING
    reason = ""
    feedback = ""
    try:
        for iteration in range(1, supervisor.max_iterations + 1):
            if supervisor.token.cancelled:
                state = RepairState.CANCELLED
                reason = "Cancelled before the next repair iteration."
                break
            developer = _draft(client, team, handoff, StageName.DEVELOPMENT, iteration, feedback)
            write = supervisor.runtime.execute(
                ExecutionRequest(
                    task_id=handoff.task_id,
                    trace_id=handoff.trace_id,
                    operation=RuntimeOperation.WRITE_FILE,
                    iteration=iteration,
                    files=developer.files,
                )
            )
            problem = runtime_problem(
                write,
                handoff=handoff,
                operation=RuntimeOperation.WRITE_FILE,
                expect_simulation=backend == "container-mock",
            )
            if problem is not None:
                raise RuntimeExecutionError(problem)
            tester = _draft(client, team, handoff, StageName.TESTING, iteration, feedback)
            tested = supervisor.runtime.execute(
                ExecutionRequest(
                    task_id=handoff.task_id,
                    trace_id=handoff.trace_id,
                    operation=RuntimeOperation.RUN_TESTS,
                    iteration=iteration,
                    test_plan=TestPlan(commands=tester.test_commands),
                )
            )
            problem = runtime_problem(
                tested,
                handoff=handoff,
                operation=RuntimeOperation.RUN_TESTS,
                expect_simulation=backend == "container-mock",
            )
            if problem is not None:
                raise RuntimeExecutionError(problem)
            passed = bool(tested.passed)
            feedback = tested.stdout or tested.stderr
            final_reason = None
            if passed:
                final_reason = f"Tests passed on iteration {iteration}."
            elif supervisor.token.cancelled:
                final_reason = "Cancelled after a failing test."
            elif iteration == supervisor.max_iterations:
                final_reason = (
                    f"Repair budget of {supervisor.max_iterations} iterations was exhausted."
                )
            iterations.append(
                RepairIteration(
                    iteration=iteration,
                    trace_id=handoff.trace_id,
                    diff_summary=developer.files[0].relative_path,
                    tester_feedback=feedback,
                    passed=passed,
                    termination_reason=final_reason,
                )
            )
            supervisor._emit(
                handoff,
                "agents.repair_iteration",
                {
                    "iteration": iteration,
                    "passed": passed,
                    "trace_id": handoff.trace_id,
                    "termination_reason": final_reason,
                },
            )
            supervisor._emit(
                handoff,
                "agents.test_result",
                {"iteration": iteration, "passed": passed, "feedback_present": bool(feedback)},
            )
            if passed:
                state = RepairState.PASSED
                reason = final_reason or "Tests passed."
                break
            if supervisor.token.cancelled:
                state = RepairState.CANCELLED
                reason = final_reason or "Cancelled after a failing test."
                break
            if iteration == supervisor.max_iterations:
                state = RepairState.FAILED_BUDGET_EXHAUSTED
                reason = final_reason or "Repair budget was exhausted."
    except (
        MalformedStageOutput,
        CrewStageTimeout,
        CrewProviderError,
        CrewIdentityError,
        CrewConfigurationError,
    ) as exc:
        return _error(
            supervisor,
            handoff,
            exc.reason,
            _client_error_engine(exc, run_engine),
            stages=stages,
            iterations=iterations,
        )
    except RuntimeExecutionError as exc:
        return _error(
            supervisor,
            handoff,
            exc.reason,
            run_engine,
            stages=stages,
            iterations=iterations,
        )

    if iterations:
        stages.append(
            _stage_summary(
                supervisor,
                handoff,
                StageName.DEVELOPMENT,
                iterations[-1].diff_summary,
            )
        )
        stages.append(
            _stage_summary(supervisor, handoff, StageName.TESTING, iterations[-1].tester_feedback)
        )
    devops_ran = False
    if state is RepairState.PASSED and not supervisor.token.cancelled:
        try:
            _draft(client, team, handoff, StageName.DEVOPS, None, feedback)
        except (
            MalformedStageOutput,
            CrewStageTimeout,
            CrewProviderError,
            CrewIdentityError,
            CrewConfigurationError,
        ) as exc:
            return _error(
                supervisor,
                handoff,
                exc.reason,
                _client_error_engine(exc, run_engine),
                stages=stages,
                iterations=iterations,
            )
        stages.append(
            _stage_summary(
                supervisor,
                handoff,
                StageName.DEVOPS,
                "Runtime tests passed. The DevOps role did not decide the pass, "
                "and no host command was run.",
            )
        )
        devops_ran = True
    elif state is RepairState.PASSED and supervisor.token.cancelled:
        state = RepairState.CANCELLED
        reason = "Cancelled before DevOps."
    return _as_result(
        supervisor._finish(
            handoff,
            state=state,
            stages=stages,
            iterations=iterations,
            devops_ran=devops_ran,
            reason=reason,
            simulation=backend == "container-mock",
            engine=run_engine,
            execution_kind=run_kind,
        )
    )


def _draft(
    client: CrewStageClient,
    team: AgentTeam,
    handoff: HandoffRequest,
    stage: StageName,
    iteration: int | None,
    feedback: str,
) -> StageDraft:
    role = next(item for item in team.roles if item.name is stage)
    request = StageRunRequest(
        task_id=handoff.task_id,
        trace_id=handoff.trace_id,
        stage=stage,
        role_goal=role.goal,
        diagram_label=role.diagram_label,
        prompt=handoff.prompt,
        iteration=iteration,
        prior_feedback=feedback,
    )
    draft = client.run_stage(request)
    if not isinstance(draft, StageDraft):
        raise MalformedStageOutput("Crew client did not return a stage draft.")
    if (
        draft.task_id != handoff.task_id
        or draft.trace_id != handoff.trace_id
        or draft.stage is not stage
    ):
        raise CrewIdentityError("Crew stage draft returned a mismatched identity.")
    return draft


def _stage(supervisor: Any, handoff: HandoffRequest, draft: StageDraft) -> StageOutput:
    return _stage_summary(supervisor, handoff, draft.stage, draft.summary)


def _stage_summary(
    supervisor: Any,
    handoff: HandoffRequest,
    stage: StageName,
    summary: str,
) -> StageOutput:
    return _as_stage(supervisor._record_stage(handoff, stage, summary, simulation=False))


def _error(
    supervisor: Any,
    handoff: HandoffRequest,
    reason: str,
    engine: str,
    *,
    stages: list[StageOutput] | None = None,
    iterations: list[RepairIteration] | None = None,
) -> AgentRunResult:
    kind = "configuration-error" if engine == "crewai-configuration-error" else "unavailable"
    if engine == "crewai-mocked":
        kind = "mocked"
    elif engine == "crewai-container":
        kind = "container"
    return _as_result(
        supervisor._finish(
            handoff,
            state=RepairState.ERROR,
            stages=stages or [],
            iterations=iterations or [],
            devops_ran=False,
            reason=reason,
            simulation=False,
            engine=engine,
            execution_kind=kind,
        )
    )


def _client_error_engine(exc: Exception, engine: str) -> str:
    if isinstance(exc, CrewConfigurationError):
        return "crewai-configuration-error"
    return engine
