"""Fake CrewAI client plus the container executor. No Gemini call and no Docker daemon."""

from pathlib import Path

import pytest
from tests.plane2.test_crewai_boundary import FakeCrew, _ready
from tests.plane2.test_supervisor import _handoff

from cloudeq.composition import container_executor, supervising_runtime
from cloudeq.plane2_agents.models import RepairState, StageName
from cloudeq.plane2_agents.settings import AgentSettings
from cloudeq.plane3_runtime.policy import ContainerSpec
from cloudeq.plane3_runtime.runner import ContainerOutput
from cloudeq.shared.contracts.models import ExecutionRequest, ExecutionResult
from cloudeq.shared.ports.errors import RuntimeExecutionError


class RecordingRunner:
    def __init__(self, code: int = 0) -> None:
        self.specs: list[ContainerSpec] = []
        self.code = code

    def run(self, spec: ContainerSpec) -> ContainerOutput:
        self.specs.append(spec)
        return ContainerOutput(
            exit_code=self.code,
            stdout="",
            stderr="",
            timed_out=False,
            duration_ms=4,
        )

    def remove(self, name: str) -> None:
        if not name.startswith("cloudeq-"):
            raise RuntimeExecutionError("Refusing to remove a container this runtime did not name.")


class LiveFlagCrew(FakeCrew):
    uses_live_provider = True
    live_crewai = False
    live_gemini = False


class IdleRuntime:
    execution_backend = "mock"

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        raise AssertionError(request.operation)


def _forbid_live_kickoff(*_args: object, **_kwargs: object) -> str:
    raise AssertionError("live kickoff")


def test_fake_client_reaches_devops_only_after_a_container_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "cloudeq.plane2_agents.agents.crewai_live.live_kickoff",
        _forbid_live_kickoff,
    )
    runner = RecordingRunner()
    crew = FakeCrew()
    supervisor = supervising_runtime(
        container_executor(runner, workspace_root=tmp_path / "workspaces"),
        engine="crewai",
        crew_client=crew,
    )
    result = supervisor.run(_handoff())
    assert result.state is RepairState.PASSED
    assert result.engine == "crewai-mocked"
    assert result.execution_kind == "mocked"
    assert result.simulation is True
    assert result.live_crewai is False
    assert result.live_gemini is False
    assert result.devops_ran is True
    assert result.host_execution is False
    assert StageName.DEVOPS in {stage.stage for stage in result.stages}
    assert runner.specs[0].command == ("python", "-m", "pytest")
    assert runner.specs[0].network == "none"

    failing = RecordingRunner(code=1)
    failed_crew = FakeCrew()
    failed = supervising_runtime(
        container_executor(failing, workspace_root=tmp_path / "failed"),
        engine="crewai",
        crew_client=failed_crew,
        max_iterations=1,
    ).run(_handoff())
    assert failed.state is RepairState.FAILED_BUDGET_EXHAUSTED
    assert failed.devops_ran is False
    assert StageName.DEVOPS not in {call.stage for call in failed_crew.calls}


def test_live_stage_client_runs_only_with_container_and_gemini_gates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "cloudeq.plane2_agents.agents.crewai_live.live_kickoff",
        _forbid_live_kickoff,
    )
    blocked = LiveFlagCrew()
    unavailable = supervising_runtime(
        IdleRuntime(),
        engine="crewai",
        crew_client=blocked,
        agent_settings=_ready(),
    ).run(_handoff())
    assert unavailable.engine == "crewai-execution-unavailable"
    assert unavailable.live_crewai is False
    assert blocked.calls == []

    class SimulatedRuntime:
        execution_backend = "simulation"

        def execute(self, request: ExecutionRequest) -> ExecutionResult:
            raise AssertionError(request.operation)

    simulated = LiveFlagCrew()
    simulated_result = supervising_runtime(
        SimulatedRuntime(),
        engine="crewai",
        crew_client=simulated,
        agent_settings=_ready(),
    ).run(_handoff())
    assert simulated_result.engine == "crewai-execution-unavailable"
    assert simulated.calls == []

    missing_model = LiveFlagCrew()
    missing = supervising_runtime(
        container_executor(RecordingRunner(), workspace_root=tmp_path / "missing"),
        engine="crewai",
        crew_client=missing_model,
        agent_settings=AgentSettings(
            cloudeq_gemini_live_calls=True,
            gemini_api_key="test-key",
            gemini_agent_model="",
        ),
    ).run(_handoff())
    assert missing.engine == "crewai-execution-unavailable"
    assert missing_model.calls == []

    unconfigured = LiveFlagCrew()
    configured = supervising_runtime(
        container_executor(RecordingRunner(), workspace_root=tmp_path / "live"),
        engine="crewai",
        crew_client=unconfigured,
        agent_settings=AgentSettings(),
    ).run(_handoff())
    assert configured.engine == "crewai-execution-unavailable"
    assert unconfigured.calls == []

    ready = LiveFlagCrew()
    passed = supervising_runtime(
        container_executor(RecordingRunner(), workspace_root=tmp_path / "ready"),
        engine="crewai",
        crew_client=ready,
        agent_settings=_ready(),
    ).run(_handoff())
    assert passed.state is RepairState.ERROR
    assert passed.engine == "crewai-execution-unavailable"
    assert passed.execution_kind == "unavailable"
    assert passed.live_crewai is False
    assert passed.live_gemini is False
    assert passed.devops_ran is False
    assert ready.calls == []
