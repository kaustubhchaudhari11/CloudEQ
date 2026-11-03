"""Docker executor with an injected runner. No daemon is required."""

import io
import subprocess
from pathlib import Path

import pytest

from cloudeq.plane3_runtime.executor import DockerRuntimeExecutor
from cloudeq.plane3_runtime.policy import ContainerSpec
from cloudeq.plane3_runtime.runner import ContainerOutput, SubprocessDockerRunner
from cloudeq.plane3_runtime.settings import RuntimeSettings
from cloudeq.shared.contracts.models import (
    ExecutionRequest,
    RuntimeFile,
    RuntimeOperation,
    TelemetryEnvelope,
)
from cloudeq.shared.contracts.models import (
    TestPlan as RuntimeTestPlan,
)
from cloudeq.shared.ports.errors import RuntimeExecutionError


class ListSink:
    def __init__(self) -> None:
        self.events: list[TelemetryEnvelope] = []

    def emit(self, envelope: TelemetryEnvelope) -> str:
        self.events.append(envelope)
        return envelope.event_id


class FakeRunner:
    def __init__(self, *, code: int = 0, timeout: bool = False, fail: bool = False) -> None:
        self.specs: list[ContainerSpec] = []
        self.removed: list[str] = []
        self._code = code
        self._timeout = timeout
        self._fail = fail

    def run(self, spec: ContainerSpec) -> ContainerOutput:
        self.specs.append(spec)
        if self._fail:
            raise RuntimeExecutionError("Docker could not start the container.")
        return ContainerOutput(
            exit_code=124 if self._timeout else self._code,
            stdout="SECRET_OUTPUT",
            stderr="",
            timed_out=self._timeout,
            duration_ms=7,
        )

    def remove(self, name: str) -> None:
        self.removed.append(name)


def _executor(
    tmp_path: Path,
    runner: FakeRunner,
    settings: RuntimeSettings | None = None,
) -> DockerRuntimeExecutor:
    return DockerRuntimeExecutor(
        settings or RuntimeSettings(),
        runner,
        ListSink(),
        workspace_root=tmp_path / "workspaces",
    )


def _request(
    operation: RuntimeOperation,
    *,
    files: list[RuntimeFile] | None = None,
    plan: RuntimeTestPlan | None = None,
) -> ExecutionRequest:
    return ExecutionRequest(
        task_id="task-1",
        trace_id="trace-1",
        operation=operation,
        iteration=1,
        files=files or [],
        test_plan=plan,
    )


def test_write_then_pass_and_fail_keep_identity_and_skip_the_host(tmp_path: Path) -> None:
    runner = FakeRunner()
    executor = _executor(tmp_path, runner)
    sink = executor._sink
    written = executor.execute(
        _request(
            RuntimeOperation.WRITE_FILE,
            files=[
                RuntimeFile(
                    relative_path="tests/test_health.py",
                    content="def test_ok():\n    assert True\n",
                )
            ],
        )
    )
    assert written.exit_code == 0
    assert written.passed is None
    assert written.simulation is True
    assert executor.execution_backend == "container-mock"
    assert written.host_execution is False
    assert written.task_id == "task-1"
    assert written.trace_id == "trace-1"
    assert written.artifact_refs == ["tests/test_health.py"]
    assert runner.specs == []
    assert (tmp_path / "workspaces" / "task-1" / "tests" / "test_health.py").is_file()

    passed = executor.execute(
        _request(RuntimeOperation.RUN_TESTS, plan=RuntimeTestPlan(commands=["python -m pytest"]))
    )
    assert passed.passed is True
    assert passed.simulation is True
    assert passed.host_execution is False
    assert runner.specs[0].command == ("python", "-m", "pytest")
    assert runner.specs[0].network == "none"

    failing = _executor(tmp_path / "failing", FakeRunner(code=1))
    failing.execute(
        _request(
            RuntimeOperation.WRITE_FILE,
            files=[RuntimeFile(relative_path="tests/test_health.py", content="x")],
        )
    )
    failed = failing.execute(
        _request(RuntimeOperation.RUN_TESTS, plan=RuntimeTestPlan(commands=["python -m pytest"]))
    )
    assert failed.passed is False
    assert failed.exit_code == 1
    assert isinstance(sink, ListSink)
    assert all("SECRET_OUTPUT" not in str(event.payload) for event in sink.events)
    assert all("def test_ok" not in str(event.payload) for event in sink.events)


def test_real_runner_label_for_write_without_starting_docker(tmp_path: Path) -> None:
    executor = DockerRuntimeExecutor(
        RuntimeSettings(),
        SubprocessDockerRunner(),
        ListSink(),
        workspace_root=tmp_path / "workspaces",
    )
    result = executor.execute(
        _request(
            RuntimeOperation.WRITE_FILE,
            files=[RuntimeFile(relative_path="a.py", content="x")],
        )
    )
    assert executor.execution_backend == "container"
    assert result.simulation is False
    assert result.host_execution is False


def test_rejected_operations_do_not_start_a_container(tmp_path: Path) -> None:
    runner = FakeRunner()
    executor = _executor(tmp_path, runner)
    with pytest.raises(RuntimeExecutionError):
        executor.execute(
            _request(
                RuntimeOperation.WRITE_FILE,
                files=[RuntimeFile(relative_path="a.py", artifact_ref="notes/a.py")],
            )
        )
    with pytest.raises(RuntimeExecutionError):
        executor.execute(
            _request(
                RuntimeOperation.WRITE_FILE,
                files=[RuntimeFile(relative_path="a.py", content="x")],
                plan=RuntimeTestPlan(commands=["python -m pytest"]),
            )
        )
    executor.execute(
        _request(
            RuntimeOperation.WRITE_FILE, files=[RuntimeFile(relative_path="a.py", content="x")]
        )
    )
    with pytest.raises(RuntimeExecutionError):
        executor.execute(
            _request(
                RuntimeOperation.RUN_TESTS,
                files=[RuntimeFile(relative_path="a.py", content="x")],
                plan=RuntimeTestPlan(commands=["python -m pytest"]),
            )
        )
    with pytest.raises(RuntimeExecutionError):
        executor.execute(_request(RuntimeOperation.GIT_COMMIT))
    enabled = _executor(
        tmp_path,
        runner,
        RuntimeSettings(cloudeq_runtime_allow_git_commit=True),
    )
    with pytest.raises(RuntimeExecutionError, match="does not run Git on the host"):
        enabled.execute(_request(RuntimeOperation.GIT_COMMIT))
    assert runner.specs == []


def test_startup_failure_timeout_and_cleanup(tmp_path: Path) -> None:
    failing = _executor(tmp_path, FakeRunner(fail=True))
    failing.execute(
        _request(
            RuntimeOperation.WRITE_FILE, files=[RuntimeFile(relative_path="a.py", content="x")]
        )
    )
    with pytest.raises(RuntimeExecutionError, match="could not start"):
        failing.execute(
            _request(
                RuntimeOperation.RUN_TESTS, plan=RuntimeTestPlan(commands=["python -m pytest"])
            )
        )

    timed = _executor(tmp_path / "timed", FakeRunner(timeout=True))
    timed.execute(
        _request(
            RuntimeOperation.WRITE_FILE, files=[RuntimeFile(relative_path="a.py", content="x")]
        )
    )
    result = timed.execute(
        _request(RuntimeOperation.RUN_TESTS, plan=RuntimeTestPlan(commands=["python -m pytest"]))
    )
    assert result.timed_out is True
    assert result.passed is False
    assert result.host_execution is False

    keeper = tmp_path / "workspaces" / "other-task"
    keeper.mkdir()
    (keeper / "keep.txt").write_text("stay", encoding="utf-8")
    failing.cleanup("task-1")
    assert not (tmp_path / "workspaces" / "task-1").exists()
    assert (keeper / "keep.txt").is_file()
    with pytest.raises(RuntimeExecutionError):
        failing.cleanup("other-task")


def test_failed_write_does_not_start_a_container(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = FakeRunner()
    executor = _executor(tmp_path, runner)

    def fail_replace(*_args: object, **_kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr("cloudeq.plane3_runtime.executor.os.replace", fail_replace)
    with pytest.raises(RuntimeExecutionError, match="could not be written"):
        executor.execute(
            _request(
                RuntimeOperation.WRITE_FILE, files=[RuntimeFile(relative_path="a.py", content="x")]
            )
        )
    assert runner.specs == []


def test_runner_uses_bounded_output_and_no_host_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded: dict[str, object] = {}

    class FakeProc:
        stdout = io.BytesIO(b"X" * 100_000)
        stderr = io.BytesIO(b"Y" * 100_000)

        def wait(self, *, timeout: float) -> int:
            return 0

        def kill(self) -> None:
            raise AssertionError("not timed out")

    def fake_popen(args: list[str], **kwargs: object) -> FakeProc:
        recorded["args"] = args
        recorded["shell"] = kwargs.get("shell")
        recorded["env"] = kwargs.get("env")
        return FakeProc()

    monkeypatch.setenv("GEMINI_API_KEY", "super-secret")
    monkeypatch.setenv("PATH", "C:/Windows")
    monkeypatch.setattr("cloudeq.plane3_runtime.runner.subprocess.Popen", fake_popen)
    spec = ContainerSpec(
        name="cloudeq-abc",
        image="cloudeq-runtime:py3.12-pytest9.2.0",
        command=("python", "-m", "pytest"),
        workspace_host="C:/work/task-1",
        network="none",
        memory="512m",
        cpus="1",
        pids_limit=64,
        user="65534:65534",
        timeout_seconds=5,
        output_limit=8,
    )
    output = SubprocessDockerRunner().run(spec)
    assert output.exit_code == 0
    assert output.stdout == "X" * 32
    assert output.stderr == "Y" * 32
    assert recorded["shell"] is False
    args = recorded["args"]
    assert isinstance(args, list)
    assert "docker.sock" not in " ".join(str(part) for part in args)
    env = recorded["env"]
    assert isinstance(env, dict)
    assert "super-secret" not in env.values()
    assert "GEMINI_API_KEY" not in env


def test_runner_reports_startup_failure_and_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = ContainerSpec(
        name="cloudeq-abc",
        image="cloudeq-runtime:py3.12-pytest9.2.0",
        command=("python", "-m", "pytest"),
        workspace_host="C:/work/task-1",
        network="none",
        memory="512m",
        cpus="1",
        pids_limit=64,
        user="65534:65534",
        timeout_seconds=5,
    )

    def missing(*_args: object, **_kwargs: object) -> object:
        raise FileNotFoundError

    monkeypatch.setattr("cloudeq.plane3_runtime.runner.subprocess.Popen", missing)
    with pytest.raises(RuntimeExecutionError, match="could not start"):
        SubprocessDockerRunner().run(spec)

    class FailedStart:
        def __init__(self) -> None:
            self.stdout = io.BytesIO(b"")
            self.stderr = io.BytesIO(b"secret daemon text")

        def wait(self, *, timeout: float) -> int:
            return 125

        def kill(self) -> None:
            raise AssertionError("not timed out")

    monkeypatch.setattr(
        "cloudeq.plane3_runtime.runner.subprocess.Popen",
        lambda *_args, **_kwargs: FailedStart(),
    )
    with pytest.raises(RuntimeExecutionError, match="could not start") as caught:
        SubprocessDockerRunner().run(spec)
    assert "secret daemon text" not in str(caught.value)

    class TimedProc:
        def __init__(self) -> None:
            self.stdout = io.BytesIO(b"")
            self.stderr = io.BytesIO(b"")
            self.killed = False

        def wait(self, *, timeout: float | None = None) -> int:
            if not self.killed:
                raise subprocess.TimeoutExpired(cmd=["docker", "run"], timeout=5)
            return -9

        def kill(self) -> None:
            self.killed = True

    calls: list[list[str]] = []

    class Removed:
        returncode = 0

    def remove(args: list[str], **_kwargs: object) -> Removed:
        calls.append(args)
        return Removed()

    monkeypatch.setattr(
        "cloudeq.plane3_runtime.runner.subprocess.Popen",
        lambda *_args, **_kwargs: TimedProc(),
    )
    monkeypatch.setattr("cloudeq.plane3_runtime.runner.subprocess.run", remove)
    output = SubprocessDockerRunner().run(spec)
    assert output.timed_out is True
    assert output.stdout == ""
    assert output.stderr == ""
    assert calls[-1][:3] == ["docker", "rm", "-f"]
    assert calls[-1][-1] == "cloudeq-abc"

    class FailedRemove:
        returncode = 1

    monkeypatch.setattr(
        "cloudeq.plane3_runtime.runner.subprocess.run",
        lambda *_args, **_kwargs: FailedRemove(),
    )
    with pytest.raises(RuntimeExecutionError, match="confirm container removal"):
        SubprocessDockerRunner().run(spec)


def test_preexisting_task_directory_is_never_claimed_or_deleted(tmp_path: Path) -> None:
    root = tmp_path / "workspaces"
    existing = root / "task-1"
    existing.mkdir(parents=True)
    marker = existing / "keep.txt"
    marker.write_text("existing", encoding="utf-8")
    executor = _executor(tmp_path, FakeRunner())
    with pytest.raises(RuntimeExecutionError, match="already exists"):
        executor.execute(
            _request(
                RuntimeOperation.WRITE_FILE,
                files=[RuntimeFile(relative_path="keep.txt", content="overwrite")],
            )
        )
    assert marker.read_text(encoding="utf-8") == "existing"
    with pytest.raises(RuntimeExecutionError, match="did not create"):
        executor.cleanup("task-1")
    assert marker.is_file()


def test_repair_iteration_reuses_only_its_own_workspace(tmp_path: Path) -> None:
    executor = _executor(tmp_path, FakeRunner())
    for content in ("first", "second"):
        executor.execute(
            _request(
                RuntimeOperation.WRITE_FILE,
                files=[RuntimeFile(relative_path="src/app.py", content=content)],
            )
        )
    assert (tmp_path / "workspaces" / "task-1" / "src" / "app.py").read_text(
        encoding="utf-8"
    ) == "second"


def test_workspace_trace_id_cannot_change_between_operations(tmp_path: Path) -> None:
    runner = FakeRunner()
    executor = _executor(tmp_path, runner)
    executor.execute(
        _request(
            RuntimeOperation.WRITE_FILE,
            files=[RuntimeFile(relative_path="src/app.py", content="safe")],
        )
    )
    other_write = _request(
        RuntimeOperation.WRITE_FILE,
        files=[RuntimeFile(relative_path="src/app.py", content="other")],
    ).model_copy(update={"trace_id": "other-trace"})
    with pytest.raises(RuntimeExecutionError, match="different trace"):
        executor.execute(other_write)
    other_test = _request(
        RuntimeOperation.RUN_TESTS,
        plan=RuntimeTestPlan(commands=["python -m pytest"]),
    ).model_copy(update={"trace_id": "other-trace"})
    with pytest.raises(RuntimeExecutionError, match="different trace"):
        executor.execute(other_test)
    assert (tmp_path / "workspaces" / "task-1" / "src" / "app.py").read_text(
        encoding="utf-8"
    ) == "safe"
    assert runner.specs == []
