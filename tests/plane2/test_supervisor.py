"""Supervisor outcomes for the offline Dynamic Agent Engine."""

import ast
from pathlib import Path

import yaml

from cloudeq.plane2_agents.models import STAGE_ORDER, RepairState, StageName
from cloudeq.plane2_agents.runtime_sim import OfflineRuntimeSimulation
from cloudeq.plane2_agents.supervisor import CancelToken, Supervisor
from cloudeq.plane2_agents.telemetry import MemoryTelemetrySink
from cloudeq.shared.contracts.models import (
    DatasetCheck,
    ExecutionRequest,
    ExecutionResult,
    FeasibilityResult,
    FeasibilityStatus,
    HandoffRequest,
    RouterKind,
    RuntimeOperation,
)


def _handoff(prompt: str = "Add a health check") -> HandoffRequest:
    return HandoffRequest(
        task_id="task-1",
        trace_id="trace-1",
        prompt=prompt,
        feasibility=FeasibilityResult(
            status=FeasibilityStatus.FEASIBLE,
            dataset_check=DatasetCheck.NOT_APPLICABLE,
            reasons=["feasible"],
            router=RouterKind.OFFLINE,
            model_id="",
        ),
    )


def _supervisor(
    runtime: OfflineRuntimeSimulation,
    *,
    max_iterations: int = 3,
    engine: str = "offline",
    token: CancelToken | None = None,
    config_path: Path | None = None,
    sink: MemoryTelemetrySink | None = None,
) -> tuple[Supervisor, MemoryTelemetrySink]:
    memory = sink or MemoryTelemetrySink()
    supervisor = Supervisor(
        config_path=config_path,
        runtime=runtime,
        sink=memory,
        max_iterations=max_iterations,
        engine=engine,
        token=token,
    )
    return supervisor, memory


def test_successful_run_uses_the_six_stages_in_order() -> None:
    runtime = OfflineRuntimeSimulation(test_outcomes=[True])
    supervisor, sink = _supervisor(runtime)
    result = supervisor.run(_handoff())
    assert result.state is RepairState.PASSED
    assert result.devops_ran is True
    assert result.simulation is True
    assert result.live_crewai is False
    assert result.live_gemini is False
    assert result.host_execution is False
    assert [stage.stage for stage in result.stages] == list(STAGE_ORDER)
    assert len(result.iterations) == 1
    assert result.iterations[0].passed is True
    assert result.iterations[0].trace_id == "trace-1"
    assert all(stage.trace_id == "trace-1" for stage in result.stages)
    assert {event.trace_id for event in sink.events} == {"trace-1"}
    assert {event.task_id for event in sink.events} == {"task-1"}
    assert RuntimeOperation.GIT_COMMIT not in {call.operation for call in runtime.calls}
    names = [event.event_name for event in sink.events]
    assert "agents.stage_completed" in names
    assert "agents.decision" in names
    assert "agents.repair_iteration" in names
    assert "agents.test_result" in names
    assert names[-1] == "agents.run_finished"


def test_fail_then_pass_records_both_iterations_and_then_devops() -> None:
    runtime = OfflineRuntimeSimulation(test_outcomes=[False, True])
    supervisor, _sink = _supervisor(runtime)
    result = supervisor.run(_handoff())
    assert result.state is RepairState.PASSED
    assert [item.passed for item in result.iterations] == [False, True]
    assert result.iterations[0].termination_reason is None
    assert result.iterations[1].termination_reason is not None
    assert result.devops_ran is True
    assert result.stages[-1].stage is StageName.DEVOPS
    assert [call.operation for call in runtime.calls].count(RuntimeOperation.RUN_TESTS) == 2


def test_budget_exhaustion_stops_at_three_and_skips_devops() -> None:
    runtime = OfflineRuntimeSimulation(test_outcomes=[False, False, False, False])
    supervisor, _sink = _supervisor(runtime, max_iterations=3)
    result = supervisor.run(_handoff())
    assert result.state is RepairState.FAILED_BUDGET_EXHAUSTED
    assert len(result.iterations) == 3
    assert all(not item.passed for item in result.iterations)
    assert result.devops_ran is False
    assert StageName.DEVOPS not in {stage.stage for stage in result.stages}
    assert [call.operation for call in runtime.calls].count(RuntimeOperation.RUN_TESTS) == 3


def test_cancellation_after_a_failure_does_not_reach_devops() -> None:
    token = CancelToken()
    runtime = OfflineRuntimeSimulation(
        test_outcomes=[False, True],
        after_test=lambda passed: token.cancel() if not passed else None,
    )
    supervisor, _sink = _supervisor(runtime, token=token)
    result = supervisor.run(_handoff())
    assert result.state is RepairState.CANCELLED
    assert len(result.iterations) == 1
    assert result.iterations[0].passed is False
    assert result.devops_ran is False
    assert StageName.DEVOPS not in {stage.stage for stage in result.stages}


def test_runtime_failure_is_an_error_and_skips_devops() -> None:
    runtime = OfflineRuntimeSimulation(raise_on_execute=True)
    supervisor, sink = _supervisor(runtime)
    result = supervisor.run(_handoff())
    assert result.state is RepairState.ERROR
    assert result.devops_ran is False
    assert "runtime failure" in result.termination_reason.lower()
    assert sink.events[-1].event_name == "agents.run_finished"
    assert sink.events[-1].payload["state"] == "error"


def test_host_execution_report_is_rejected() -> None:
    runtime = OfflineRuntimeSimulation(report_host_execution=True)
    supervisor, _sink = _supervisor(runtime)
    result = supervisor.run(_handoff())
    assert result.state is RepairState.ERROR
    assert result.host_execution is False
    assert result.devops_ran is False
    assert "host" in result.termination_reason.lower()


def test_repair_maximum_below_one_runs_no_stages() -> None:
    runtime = OfflineRuntimeSimulation()
    supervisor, _sink = _supervisor(runtime, max_iterations=0)
    result = supervisor.run(_handoff())
    assert result.state is RepairState.ERROR
    assert result.stages == []
    assert result.iterations == []
    assert runtime.calls == []


def test_missing_and_malformed_configuration_fail_before_stages(tmp_path: Path) -> None:
    missing = tmp_path / "missing.yaml"
    runtime = OfflineRuntimeSimulation()
    supervisor, _sink = _supervisor(runtime, config_path=missing)
    result = supervisor.run(_handoff())
    assert result.state is RepairState.ERROR
    assert result.stages == []
    assert runtime.calls == []

    broken = tmp_path / "agents.yaml"
    broken.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "roles": [
                    {
                        "name": "Requirements",
                        "diagram_label": "Requirements",
                        "goal": "Collect requirements.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    supervisor, _sink = _supervisor(runtime, config_path=broken)
    malformed = supervisor.run(_handoff())
    assert malformed.state is RepairState.ERROR
    assert malformed.stages == []
    assert "Roles must be exactly" in malformed.termination_reason
    assert runtime.calls == []


def test_crewai_engine_does_not_pretend_to_run() -> None:
    runtime = OfflineRuntimeSimulation()
    supervisor, _sink = _supervisor(runtime, engine="crewai")
    result = supervisor.run(_handoff())
    assert result.state is RepairState.ERROR
    assert result.live_crewai is False
    assert result.live_gemini is False
    assert result.simulation is False
    assert result.execution_kind == "configuration-error"
    assert result.engine == "crewai-configuration-error"
    assert "live calls" in result.termination_reason.lower()
    assert result.devops_ran is False
    assert runtime.calls == []


def test_plane2_modules_do_not_import_other_planes() -> None:
    root = Path("src/cloudeq/plane2_agents")
    forbidden = ("cloudeq.plane1_intake", "cloudeq.plane3_runtime", "cloudeq.plane4_observability")
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            else:
                continue
            for name in names:
                assert not name.startswith(forbidden), f"{path} imports {name}"


class _BadRuntime:
    def __init__(self, case: str) -> None:
        self.case = case
        self.delegate = OfflineRuntimeSimulation(test_outcomes=[True])

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        result = self.delegate.execute(request)
        if request.operation is not RuntimeOperation.RUN_TESTS:
            return result
        if self.case == "wrong_task":
            return result.model_copy(update={"task_id": "different-task"})
        if self.case == "wrong_trace":
            return result.model_copy(update={"trace_id": "different-trace"})
        if self.case == "nonzero_exit":
            return result.model_copy(update={"exit_code": 1})
        if self.case == "timeout":
            return result.model_copy(update={"timed_out": True})
        if self.case == "real_execution":
            return result.model_copy(update={"simulation": False})
        raise AssertionError(self.case)


def test_untrusted_runtime_result_cannot_trigger_devops() -> None:
    for case in ("wrong_task", "wrong_trace", "nonzero_exit", "timeout", "real_execution"):
        runtime = _BadRuntime(case)
        supervisor = Supervisor(runtime=runtime, sink=MemoryTelemetrySink())
        result = supervisor.run(_handoff())
        assert result.state is RepairState.ERROR, case
        assert result.devops_ran is False, case
        assert StageName.DEVOPS not in {stage.stage for stage in result.stages}, case
        assert len(runtime.delegate.calls) == 2, case


class _FailedWriteRuntime:
    def __init__(self) -> None:
        self.calls: list[ExecutionRequest] = []

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        self.calls.append(request)
        assert request.operation is RuntimeOperation.WRITE_FILE
        return ExecutionResult(
            task_id=request.task_id,
            trace_id=request.trace_id,
            operation=request.operation,
            exit_code=2,
            simulation=True,
        )


def test_failed_write_does_not_run_tests_or_devops() -> None:
    runtime = _FailedWriteRuntime()
    result = Supervisor(runtime=runtime, sink=MemoryTelemetrySink()).run(_handoff())
    assert result.state is RepairState.ERROR
    assert result.devops_ran is False
    assert [call.operation for call in runtime.calls] == [RuntimeOperation.WRITE_FILE]


class _TestExitTwoRuntime(OfflineRuntimeSimulation):
    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        result = super().execute(request)
        if request.operation is RuntimeOperation.RUN_TESTS and result.passed is False:
            return result.model_copy(update={"exit_code": 2})
        return result


def test_failed_tests_can_return_nonstandard_nonzero_exit() -> None:
    runtime = _TestExitTwoRuntime(test_outcomes=[False, True])
    result = Supervisor(runtime=runtime, sink=MemoryTelemetrySink()).run(_handoff())
    assert result.state is RepairState.PASSED
    assert [item.passed for item in result.iterations] == [False, True]
