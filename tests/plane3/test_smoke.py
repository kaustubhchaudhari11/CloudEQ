"""One real container check. Skipped when the Docker engine is not running."""

import shutil
import subprocess
from pathlib import Path

import pytest

from cloudeq.plane3_runtime.executor import DockerRuntimeExecutor
from cloudeq.plane3_runtime.runner import SubprocessDockerRunner
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

IMAGE = "cloudeq-runtime:py3.12-pytest9.2.0"
FIXTURE = "def test_health():\n    assert True\n"


class ListSink:
    def emit(self, envelope: TelemetryEnvelope) -> str:
        return envelope.event_id


def _engine_ready() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        info = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=30,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return info.returncode == 0


def test_real_container_runs_fixed_pytest_fixture(tmp_path: Path) -> None:
    if not _engine_ready():
        pytest.skip("Docker engine is unavailable; the live smoke test was not run.")
    build = subprocess.run(
        ["docker", "build", "-t", IMAGE, "infra/runtime"],
        capture_output=True,
        timeout=300,
        check=False,
        shell=False,
    )
    assert build.returncode == 0, build.stderr.decode("utf-8", errors="replace")[-500:]
    settings = RuntimeSettings(
        cloudeq_runtime_image=IMAGE,
        cloudeq_runtime_timeout_seconds=120,
    )
    executor = DockerRuntimeExecutor(
        settings,
        SubprocessDockerRunner(),
        ListSink(),
        workspace_root=tmp_path / "workspaces",
    )
    request = ExecutionRequest(
        task_id="smoke1",
        trace_id="trace-smoke",
        operation=RuntimeOperation.WRITE_FILE,
        iteration=1,
        files=[RuntimeFile(relative_path="tests/test_health.py", content=FIXTURE)],
    )
    written = executor.execute(request)
    try:
        result = executor.execute(
            ExecutionRequest(
                task_id="smoke1",
                trace_id="trace-smoke",
                operation=RuntimeOperation.RUN_TESTS,
                iteration=1,
                test_plan=RuntimeTestPlan(commands=["python -m pytest"]),
            )
        )
        assert written.simulation is False
        assert written.host_execution is False
        assert result.task_id == "smoke1"
        assert result.trace_id == "trace-smoke"
        assert result.operation is RuntimeOperation.RUN_TESTS
        assert result.passed is True
        assert result.exit_code == 0
        assert result.timed_out is False
        assert result.simulation is False
        assert result.host_execution is False
    finally:
        executor.cleanup("smoke1")
