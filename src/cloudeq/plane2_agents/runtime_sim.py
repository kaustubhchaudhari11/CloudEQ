"""Offline stand-in for the Plane 3 runtime port.

Every result is marked as a simulation. This adapter does not start Docker,
does not run generated code, and does not invoke Git on the host.
"""

from collections.abc import Callable

from cloudeq.shared.contracts.models import ExecutionRequest, ExecutionResult, RuntimeOperation
from cloudeq.shared.ports.errors import RuntimeExecutionError


class OfflineRuntimeSimulation:
    """Scripted Plane 3 double. `simulation` is always true."""

    execution_backend = "simulation"

    def __init__(
        self,
        *,
        test_outcomes: list[bool] | None = None,
        raise_on_execute: bool = False,
        report_host_execution: bool = False,
        after_test: Callable[[bool], None] | None = None,
    ) -> None:
        self._outcomes = [True] if test_outcomes is None else list(test_outcomes)
        self._raise = raise_on_execute
        self._report_host_execution = report_host_execution
        self._after_test = after_test
        self.calls: list[ExecutionRequest] = []

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        self.calls.append(request)
        if request.operation is RuntimeOperation.GIT_COMMIT:
            return self._result(
                request,
                exit_code=1,
                passed=None,
                stdout="",
                stderr="Git commit is disabled. The offline adapter does not run Git.",
                artifact_refs=[],
            )
        if self._raise:
            raise RuntimeExecutionError("Simulated runtime failure before any host command.")
        if request.operation is RuntimeOperation.RUN_TESTS:
            passed = False if not self._outcomes else self._outcomes.pop(0)
            if self._after_test is not None:
                self._after_test(passed)
            return self._result(
                request,
                exit_code=0 if passed else 1,
                passed=passed,
                stdout="simulated test passed" if passed else "simulated test failed",
                stderr="",
                artifact_refs=[],
            )
        iteration = request.iteration if request.iteration is not None else 0
        return self._result(
            request,
            exit_code=0,
            passed=None,
            stdout="simulated file write",
            stderr="",
            artifact_refs=[f"simulated://{request.task_id}/iteration-{iteration}.diff"],
        )

    def _result(
        self,
        request: ExecutionRequest,
        *,
        exit_code: int,
        passed: bool | None,
        stdout: str,
        stderr: str,
        artifact_refs: list[str],
    ) -> ExecutionResult:
        return ExecutionResult(
            task_id=request.task_id,
            trace_id=request.trace_id,
            operation=request.operation,
            exit_code=exit_code,
            timed_out=False,
            passed=passed,
            stdout=stdout,
            stderr=stderr,
            duration_ms=0,
            artifact_refs=artifact_refs,
            simulation=True,
            host_execution=self._report_host_execution,
        )
