"""Mocked CrewAI boundary. These tests do not call Gemini or CrewAI kickoff."""

import json

import pytest
from pydantic import ValidationError
from tests.plane2.test_supervisor import _handoff

from cloudeq.plane2_agents.agents.crewai import CrewAIGeminiStageClient
from cloudeq.plane2_agents.agents.stage_client import (
    CrewConfigurationError,
    CrewIdentityError,
    CrewProviderError,
    CrewStageTimeout,
    MalformedStageOutput,
    StageDraft,
    StageRunRequest,
    parse_stage_text,
    require_live_gemini,
)
from cloudeq.plane2_agents.models import STAGE_ORDER, RepairState, StageName
from cloudeq.plane2_agents.runtime_sim import OfflineRuntimeSimulation
from cloudeq.plane2_agents.settings import AgentSettings
from cloudeq.plane2_agents.supervisor import CancelToken, Supervisor
from cloudeq.plane2_agents.telemetry import MemoryTelemetrySink
from cloudeq.shared.contracts.models import (
    ExecutionRequest,
    ExecutionResult,
    RuntimeFile,
    RuntimeOperation,
)
from cloudeq.shared.ports.errors import RuntimeExecutionError


def _ready() -> AgentSettings:
    return AgentSettings(
        cloudeq_gemini_live_calls=True,
        gemini_api_key="test-key",
        gemini_agent_model="gemini-test-model",
    )


def _request(stage: StageName = StageName.REQUIREMENTS) -> StageRunRequest:
    return StageRunRequest(
        task_id="task-1",
        trace_id="trace-1",
        stage=stage,
        role_goal="goal",
        diagram_label="Requirements",
        prompt="Add a health check",
    )


class FakeCrew:
    uses_live_provider = False

    def __init__(self, script: list[object] | None = None) -> None:
        self.script = list(script or [])
        self.calls: list[StageRunRequest] = []

    def run_stage(self, request: StageRunRequest) -> StageDraft:
        self.calls.append(request)
        if self.script:
            item = self.script.pop(0)
            if isinstance(item, Exception):
                raise item
            if isinstance(item, StageDraft):
                return item
        files: list[RuntimeFile] = []
        commands: list[str] = []
        if request.stage is StageName.DEVELOPMENT:
            files = [RuntimeFile(relative_path="src/health.py", content="print('ok')")]
        if request.stage is StageName.TESTING:
            commands = ["python -m pytest"]
        summary = "tests passed" if request.stage is StageName.TESTING else request.stage.value
        return StageDraft(
            task_id=request.task_id,
            trace_id=request.trace_id,
            stage=request.stage,
            summary=summary,
            files=files,
            test_commands=commands,
        )


class MockRuntime:
    execution_backend = "mock"

    def __init__(self, outcomes: list[bool], *, fail_write: bool = False) -> None:
        self._outcomes = list(outcomes)
        self._fail_write = fail_write
        self.calls: list[ExecutionRequest] = []

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        self.calls.append(request)
        if request.operation is RuntimeOperation.WRITE_FILE:
            return ExecutionResult(
                task_id=request.task_id,
                trace_id=request.trace_id,
                operation=request.operation,
                exit_code=2 if self._fail_write else 0,
                passed=None,
                simulation=False,
                artifact_refs=[item.relative_path for item in request.files],
            )
        passed = False if not self._outcomes else self._outcomes.pop(0)
        return ExecutionResult(
            task_id=request.task_id,
            trace_id=request.trace_id,
            operation=request.operation,
            exit_code=0 if passed else 1,
            passed=passed,
            stdout="container test passed" if passed else "container test failed",
            simulation=False,
        )


def _run(
    runtime: MockRuntime | OfflineRuntimeSimulation,
    *,
    client: FakeCrew | CrewAIGeminiStageClient | None = None,
    settings: AgentSettings | None = None,
    max_iterations: int = 3,
    token: CancelToken | None = None,
) -> tuple[object, FakeCrew | None]:
    fake = client if isinstance(client, FakeCrew) else None
    supervisor = Supervisor(
        runtime=runtime,
        sink=MemoryTelemetrySink(),
        engine="crewai",
        max_iterations=max_iterations,
        settings=settings,
        crew_client=client,
        token=token,
    )
    return supervisor.run(_handoff()), fake


def test_missing_live_configuration_is_reported_without_a_call() -> None:
    for settings in (
        AgentSettings(),
        AgentSettings(cloudeq_gemini_live_calls=True, gemini_api_key="", gemini_agent_model=""),
        AgentSettings(
            cloudeq_gemini_live_calls=True, gemini_api_key="test-key", gemini_agent_model=""
        ),
        AgentSettings(
            cloudeq_gemini_live_calls=True,
            gemini_api_key="test-key",
            gemini_agent_model="gemini/not allowed",
        ),
    ):
        try:
            require_live_gemini(settings)
        except CrewConfigurationError as exc:
            assert (
                "key" in exc.reason.lower()
                or "model" in exc.reason.lower()
                or "disabled" in exc.reason.lower()
            )
        else:
            raise AssertionError(settings)


def test_open_gates_still_report_execution_unavailable(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def forbidden(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("live kickoff")

    monkeypatch.setattr(
        "cloudeq.plane2_agents.agents.crewai_live.live_kickoff",
        forbidden,
    )
    runtime = OfflineRuntimeSimulation()
    result, _fake = _run(runtime, settings=_ready())
    assert result.state is RepairState.ERROR
    assert result.engine == "crewai-execution-unavailable"
    assert result.execution_kind == "unavailable"
    assert result.live_crewai is False
    assert result.devops_ran is False
    assert runtime.calls == []


def test_live_provider_client_is_not_asked_to_run() -> None:
    client = CrewAIGeminiStageClient(_ready())
    assert client.uses_live_provider is True
    runtime = MockRuntime([True])
    result, _fake = _run(runtime, client=client, settings=_ready())
    assert result.execution_kind == "unavailable"
    assert result.devops_ran is False
    assert runtime.calls == []
    assert client.live_crewai is False


def test_mocked_pass_uses_runtime_result_and_all_six_roles() -> None:
    crew = FakeCrew()
    runtime = MockRuntime([True])
    result, _fake = _run(runtime, client=crew)
    assert result.state is RepairState.PASSED
    assert result.execution_kind == "mocked"
    assert result.simulation is False
    assert result.live_crewai is False
    assert result.live_gemini is False
    assert result.devops_ran is True
    assert [stage.stage for stage in result.stages] == list(STAGE_ORDER)
    assert all(stage.task_id == "task-1" and stage.trace_id == "trace-1" for stage in result.stages)
    assert [call.stage for call in crew.calls] == list(STAGE_ORDER)
    write = runtime.calls[0]
    assert write.files[0].relative_path == "src/health.py"
    assert runtime.calls[1].test_plan is not None
    assert runtime.calls[1].test_plan.commands == ["python -m pytest"]
    assert "test-key" not in json.dumps(result.model_dump(mode="json"))


def test_agent_text_cannot_count_as_a_pass() -> None:
    crew = FakeCrew()
    runtime = MockRuntime([False])
    result, _fake = _run(runtime, client=crew, max_iterations=1)
    assert result.state is RepairState.FAILED_BUDGET_EXHAUSTED
    assert result.iterations[0].passed is False
    assert result.devops_ran is False
    assert StageName.DEVOPS not in {call.stage for call in crew.calls}


def test_fail_then_pass_and_budget_and_cancellation() -> None:
    passed, _fake = _run(MockRuntime([False, True]), client=FakeCrew())
    assert passed.state is RepairState.PASSED
    assert [item.passed for item in passed.iterations] == [False, True]
    exhausted, _fake = _run(MockRuntime([False, False, False]), client=FakeCrew())
    assert exhausted.state is RepairState.FAILED_BUDGET_EXHAUSTED
    assert exhausted.devops_ran is False
    token = CancelToken()
    crew = FakeCrew()

    def cancel(request: StageRunRequest) -> None:
        if request.stage is StageName.TESTING:
            token.cancel()

    crew.run_stage = _cancel_after(crew, cancel)  # type: ignore[method-assign]
    cancelled, _fake = _run(MockRuntime([False, True]), client=crew, token=token)
    assert cancelled.state is RepairState.CANCELLED
    assert cancelled.devops_ran is False


def test_failed_write_mismatch_and_simulated_result_do_not_pass() -> None:
    failed, crew = _run(MockRuntime([True], fail_write=True), client=FakeCrew())
    assert failed.state is RepairState.ERROR
    assert "write" in failed.termination_reason.lower()
    assert crew is not None
    assert StageName.TESTING not in {call.stage for call in crew.calls}

    class Mismatch(MockRuntime):
        def execute(self, request: ExecutionRequest) -> ExecutionResult:
            result = super().execute(request)
            if request.operation is RuntimeOperation.RUN_TESTS:
                return result.model_copy(update={"trace_id": "other"})
            return result

    mismatched, _fake = _run(Mismatch([True]), client=FakeCrew())
    assert mismatched.state is RepairState.ERROR
    assert "mismatched" in mismatched.termination_reason.lower()

    class Simulated(MockRuntime):
        def execute(self, request: ExecutionRequest) -> ExecutionResult:
            result = super().execute(request)
            return result.model_copy(update={"simulation": True})

    simulated, _fake = _run(Simulated([True]), client=FakeCrew())
    assert simulated.state is RepairState.ERROR
    assert simulated.devops_ran is False
    assert "simulated" in simulated.termination_reason.lower()


def test_parser_rejects_malformed_identity_path_and_command() -> None:
    request = _request(StageName.DEVELOPMENT)
    try:
        parse_stage_text("not-json", request)
    except MalformedStageOutput as exc:
        assert "JSON" in exc.reason
    else:
        raise AssertionError("malformed")
    try:
        parse_stage_text(json.dumps({"task_id": "other", "summary": "x"}), request)
    except CrewIdentityError as exc:
        assert "task" in exc.reason.lower()
    else:
        raise AssertionError("identity")
    try:
        parse_stage_text(
            json.dumps(
                {
                    "summary": "diff",
                    "files": [{"relative_path": "../secrets.txt", "content": "nope"}],
                }
            ),
            request,
        )
    except MalformedStageOutput as exc:
        assert "unsafe" in exc.reason.lower()
    else:
        raise AssertionError("path")
    testing = _request(StageName.TESTING)
    try:
        parse_stage_text(
            json.dumps({"summary": "run", "test_commands": ["rm -rf /"]}),
            testing,
        )
    except MalformedStageOutput as exc:
        assert "allowlisted" in exc.reason.lower()
    else:
        raise AssertionError("command")


def _raise_timeout(_request: StageRunRequest) -> str:
    raise TimeoutError


def _raise_provider(_request: StageRunRequest) -> str:
    raise RuntimeError("no")


def test_injected_kickoff_maps_timeout_and_provider_errors() -> None:
    client = CrewAIGeminiStageClient(_ready(), kickoff=_raise_timeout)
    try:
        client.run_stage(_request())
    except CrewStageTimeout:
        pass
    else:
        raise AssertionError("timeout")
    failing = CrewAIGeminiStageClient(_ready(), kickoff=_raise_provider)
    try:
        failing.run_stage(_request())
    except CrewProviderError as exc:
        assert "test-key" not in exc.reason
    else:
        raise AssertionError("provider")
    assert client.live_crewai is False
    assert client.live_gemini is False


def test_injected_kickoff_parses_a_stage_without_a_network_call() -> None:
    payload = json.dumps({"summary": "requirements noted", "files": [], "test_commands": []})
    client = CrewAIGeminiStageClient(_ready(), kickoff=lambda _request: payload)
    draft = client.run_stage(_request())
    assert draft.task_id == "task-1"
    assert draft.trace_id == "trace-1"
    assert draft.summary == "requirements noted"
    assert client.live_gemini is False


def _cancel_after(crew: FakeCrew, cancel):  # type: ignore[no-untyped-def]
    original = crew.run_stage

    def wrapped(request: StageRunRequest) -> StageDraft:
        draft = original(request)
        cancel(request)
        return draft

    return wrapped


def test_mocked_client_configuration_error_is_a_result() -> None:
    crew = FakeCrew(script=[CrewConfigurationError("Missing model configuration.")])
    result, _fake = _run(MockRuntime([True]), client=crew)
    assert result.state is RepairState.ERROR
    assert result.engine == "crewai-configuration-error"
    assert result.devops_ran is False


def test_runtime_port_failure_is_a_result() -> None:
    class FailingRuntime(MockRuntime):
        def execute(self, request: ExecutionRequest) -> ExecutionResult:
            raise RuntimeExecutionError("Container is unavailable.")

    result, _fake = _run(FailingRuntime([True]), client=FakeCrew())
    assert result.state is RepairState.ERROR
    assert "Container is unavailable" in result.termination_reason
    assert result.devops_ran is False


def test_runtime_artifact_reference_is_relative_and_unambiguous() -> None:
    for reference in ("https://example.com/file", "../outside", "/absolute"):
        with pytest.raises(ValidationError):
            RuntimeFile(relative_path="src/health.py", artifact_ref=reference)
    with pytest.raises(ValidationError):
        RuntimeFile(relative_path="src/health.py", content="x", artifact_ref="artifacts/x")
    accepted = RuntimeFile(relative_path="src/health.py", artifact_ref="artifacts/x")
    assert accepted.artifact_ref == "artifacts/x"
