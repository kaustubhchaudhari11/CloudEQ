"""Docker RuntimeExecutor. File bytes are written; generated code runs only in a container."""

import os
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from cloudeq.plane3_runtime.policy import allowlisted_argv, spec_from_settings
from cloudeq.plane3_runtime.runner import DockerRunner, SubprocessDockerRunner
from cloudeq.plane3_runtime.settings import RuntimeSettings
from cloudeq.plane3_runtime.workspace import (
    assert_file_budget,
    destination_for,
    prepare_workspace_root,
    task_directory,
    validate_task_id,
)
from cloudeq.shared.contracts.models import (
    MAX_RUNTIME_FILE_CHARS,
    ExecutionRequest,
    ExecutionResult,
    PlaneName,
    RuntimeOperation,
    TelemetryEnvelope,
)
from cloudeq.shared.ports.errors import RuntimeExecutionError
from cloudeq.shared.ports.protocols import TelemetrySink

_OUTPUT_NOTICE = "\n[truncated]"


class DockerRuntimeExecutor:
    """Container backend. ``simulation`` stays false only for operations this class performs."""

    def __init__(
        self,
        settings: RuntimeSettings,
        runner: DockerRunner,
        sink: TelemetrySink,
        *,
        workspace_root: Path | None = None,
    ) -> None:
        try:
            settings.validate_policy()
        except ValueError as exc:
            raise RuntimeExecutionError(str(exc)) from exc
        root = (
            workspace_root
            if workspace_root is not None
            else Path(settings.cloudeq_runtime_workspace_root)
        )
        self._settings = settings
        self._runner = runner
        self.execution_backend = (
            "container" if type(runner) is SubprocessDockerRunner else "container-mock"
        )
        self._sink = sink
        self._root = prepare_workspace_root(root)
        self._created: dict[str, str] = {}

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        started = time.perf_counter()
        try:
            validate_task_id(request.task_id)
            if not request.trace_id.strip():
                raise RuntimeExecutionError("Trace id is required.")
            if request.operation is RuntimeOperation.WRITE_FILE:
                result = self._write(request, started)
            elif request.operation is RuntimeOperation.RUN_TESTS:
                result = self._test(request, started)
            elif request.operation is RuntimeOperation.GIT_COMMIT:
                result = self._git(request)
            else:
                raise RuntimeExecutionError("Runtime operation is not supported.")
        except RuntimeExecutionError:
            self._emit_rejected(request)
            raise
        self._emit_completed(result)
        return result

    def cleanup(self, task_id: str) -> None:
        validate_task_id(task_id)
        if task_id not in self._created:
            raise RuntimeExecutionError(
                "Refusing to delete a workspace this executor did not create."
            )
        workspace = task_directory(self._root, task_id, create=False)
        shutil.rmtree(workspace)
        self._created.pop(task_id, None)

    def _write(self, request: ExecutionRequest, started: float) -> ExecutionResult:
        if request.test_plan is not None:
            raise RuntimeExecutionError("A file write cannot carry a test plan.")
        assert_file_budget(len(request.files))
        for item in request.files:
            if item.artifact_ref is not None:
                raise RuntimeExecutionError(
                    "Artifact references are rejected until a safe resolver exists."
                )
            if item.content is None or len(item.content) > MAX_RUNTIME_FILE_CHARS:
                raise RuntimeExecutionError("Runtime file content exceeds the contract limit.")
        if request.task_id in self._created:
            if self._created[request.task_id] != request.trace_id:
                raise RuntimeExecutionError("Task workspace belongs to a different trace id.")
            workspace = task_directory(self._root, request.task_id, create=False)
        else:
            workspace = task_directory(self._root, request.task_id, create=True)
            self._created[request.task_id] = request.trace_id
            try:
                workspace.chmod(0o755)
            except OSError:
                pass
        written: list[str] = []
        for item in request.files:
            target = destination_for(workspace, item.relative_path)
            if item.content is None:
                raise RuntimeExecutionError("Runtime file content is missing.")
            temporary = target.parent / f".cloudeq-{uuid4().hex}.tmp"
            try:
                with temporary.open("x", encoding="utf-8") as stream:
                    stream.write(item.content)
                os.replace(temporary, target)
            except OSError as exc:
                raise RuntimeExecutionError("Runtime file could not be written.") from exc
            finally:
                temporary.unlink(missing_ok=True)
            if not target.resolve().is_relative_to(workspace.resolve()):
                raise RuntimeExecutionError("Runtime path escaped the task workspace.")
            written.append(item.relative_path)
        return self._result(
            request,
            exit_code=0,
            passed=None,
            stdout="",
            stderr="",
            timed_out=False,
            duration_ms=_elapsed(started),
            artifact_refs=written,
        )

    def _test(self, request: ExecutionRequest, started: float) -> ExecutionResult:
        if request.files:
            raise RuntimeExecutionError("A test run cannot carry files to write.")
        if request.test_plan is None:
            raise RuntimeExecutionError("A test run needs an allowlisted test plan.")
        if len(request.test_plan.commands) != 1:
            raise RuntimeExecutionError("A test run accepts one allowlisted command.")
        try:
            command = allowlisted_argv(request.test_plan.commands[0])
        except ValueError as exc:
            raise RuntimeExecutionError("Command is not allowlisted.") from exc
        if request.task_id not in self._created:
            raise RuntimeExecutionError("Tests require a workspace this executor created.")
        if self._created[request.task_id] != request.trace_id:
            raise RuntimeExecutionError("Task workspace belongs to a different trace id.")
        workspace = task_directory(self._root, request.task_id, create=False)
        name = _container_name(request)
        spec = spec_from_settings(
            self._settings,
            name=name,
            workspace_host=str(workspace),
            command=command,
        )
        output = self._runner.run(spec)
        passed = output.exit_code == 0 and not output.timed_out
        return self._result(
            request,
            exit_code=output.exit_code,
            passed=passed,
            stdout=_bound(output.stdout, self._settings.cloudeq_runtime_output_limit),
            stderr=_bound(output.stderr, self._settings.cloudeq_runtime_output_limit),
            timed_out=output.timed_out,
            duration_ms=output.duration_ms or _elapsed(started),
            artifact_refs=[],
        )

    def _git(self, request: ExecutionRequest) -> ExecutionResult:
        if request.files or request.test_plan is not None:
            raise RuntimeExecutionError("Git commit does not accept files or a test plan.")
        if self._settings.cloudeq_runtime_allow_git_commit:
            raise RuntimeExecutionError(
                "Git commit inside the container is not available. "
                "The runtime does not run Git on the host."
            )
        raise RuntimeExecutionError(
            "Git commit is disabled. The runtime does not run Git on the host."
        )

    def _result(
        self,
        request: ExecutionRequest,
        *,
        exit_code: int,
        passed: bool | None,
        stdout: str,
        stderr: str,
        timed_out: bool,
        duration_ms: int,
        artifact_refs: list[str],
    ) -> ExecutionResult:
        return ExecutionResult(
            task_id=request.task_id,
            trace_id=request.trace_id,
            operation=request.operation,
            exit_code=exit_code,
            timed_out=timed_out,
            passed=passed,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
            artifact_refs=artifact_refs,
            simulation=self.execution_backend != "container",
            host_execution=False,
        )

    def _emit_completed(self, result: ExecutionResult) -> None:
        self._emit(
            result.task_id,
            result.trace_id,
            "runtime.operation_completed",
            {
                "operation": result.operation.value,
                "exit_code": result.exit_code,
                "passed": result.passed,
                "timed_out": result.timed_out,
                "duration_ms": result.duration_ms,
                "simulation": result.simulation,
                "host_execution": False,
                "file_count": len(result.artifact_refs),
            },
        )

    def _emit_rejected(self, request: ExecutionRequest) -> None:
        trace = request.trace_id.strip() or "missing-trace"
        self._emit(
            request.task_id,
            trace,
            "runtime.operation_rejected",
            {"operation": request.operation.value, "rejected": True},
        )

    def _emit(
        self, task_id: str, trace_id: str, event_name: str, payload: dict[str, object]
    ) -> None:
        envelope = TelemetryEnvelope(
            event_id=str(uuid4()),
            trace_id=trace_id,
            source=PlaneName.PLANE3_RUNTIME,
            event_name=event_name,
            occurred_at=datetime.now(UTC),
            payload=payload,
            task_id=task_id,
        )
        self._sink.emit(envelope)


def _container_name(request: ExecutionRequest) -> str:
    return f"cloudeq-{uuid4().hex}"


def _bound(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    keep = max(0, limit - len(_OUTPUT_NOTICE))
    return text[:keep] + _OUTPUT_NOTICE


def _elapsed(started: float) -> int:
    return max(0, int((time.perf_counter() - started) * 1000))
