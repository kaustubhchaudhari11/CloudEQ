from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from cloudeq.plane3_runtime.policy import spec_from_settings
from cloudeq.plane3_runtime.render_runner import RenderRuntimeSettings, RenderSandboxRunner
from cloudeq.plane3_runtime.settings import RuntimeSettings
from cloudeq.shared.ports.errors import RuntimeExecutionError


class FakeSandboxes:
    def __init__(self, code: int = 0, *, broken: str = "") -> None:
        self.sandboxes = self
        self.code = code
        self.broken = broken
        self.created: dict[str, Any] = {}
        self.uploads: list[tuple[str, str]] = []
        self.commands: list[str] = []
        self.terminated: list[str] = []

    async def create(self, **kwargs: Any) -> SimpleNamespace:
        self.created = kwargs
        return SimpleNamespace(id="sbx-owned-test")

    async def wait_until_running(self, *args: Any, **kwargs: Any) -> None:
        if self.broken == "timeout":
            raise TimeoutError

    async def copy_to(self, sid: str, source: str, target: str) -> None:
        self.uploads.append((source, target))

    async def exec(self, sid: str, command: str) -> Any:
        self.commands.append(command)
        if "forge-harness" in command:
            if self.broken == "network":
                raise OSError("secret-should-not-leak")
            yield SimpleNamespace(stream="stdout", data="passed\n" * 10000)
            if self.broken == "no-exit":
                return
            yield SimpleNamespace(exit_code=self.code)
        else:
            yield SimpleNamespace(exit_code=0)

    async def terminate(self, sid: str) -> None:
        self.terminated.append(sid)
        if self.broken == "cleanup":
            raise OSError("private-api-token")


def setup_runner(tmp_path: Path, fake: FakeSandboxes) -> tuple[Any, Any]:
    workspace = tmp_path / "task"
    workspace.mkdir()
    (workspace / "test_example.py").write_text("def test_ok(): assert 1 == 1\n")
    wheels = tmp_path / "wheels"
    wheels.mkdir()
    (wheels / "pytest-9.2.0-py3-none-any.whl").write_bytes(b"fixture")
    (wheels / "flask-3.1.3-py3-none-any.whl").write_bytes(b"fixture")
    settings = RenderRuntimeSettings(
        render_api_key="local-test-key",
        render_workspace_id="tea-test",
        cloudeq_render_wheels_dir=str(wheels),
    )
    runner = RenderSandboxRunner(settings, client_factory=lambda: fake)
    spec = spec_from_settings(
        RuntimeSettings(),
        name="cloudeq-test",
        workspace_host=str(workspace),
        command=("python", "-m", "pytest"),
    )
    return runner, spec


@pytest.mark.parametrize("code", [0, 1, 5, 124])
def test_remote_exit_status_is_authoritative_and_cleanup_runs(tmp_path: Path, code: int) -> None:
    fake = FakeSandboxes(code)
    runner, spec = setup_runner(tmp_path, fake)
    result = runner.run(spec)
    assert result.exit_code == code
    assert result.timed_out is (code == 124)
    assert len(result.stdout) <= spec.output_limit
    assert runner.is_live is False
    assert fake.created["network_policy"] == "deny-all"
    assert fake.created["timeout_seconds"] == 270
    assert fake.created["env"] == {"PYTHONDONTWRITEBYTECODE": "1"}
    assert fake.created["plan"] == "1c-2g"
    assert fake.terminated == ["sbx-owned-test"]
    assert fake.uploads[-1][1] == "/tmp/forge-task"
    assert "--no-index" in fake.commands[0]
    assert "Flask==3.1.3" in fake.commands[0]


@pytest.mark.parametrize("broken", ["network", "no-exit", "cleanup"])
def test_remote_failures_cannot_become_a_pass(tmp_path: Path, broken: str) -> None:
    fake = FakeSandboxes(broken=broken)
    runner, spec = setup_runner(tmp_path, fake)
    with pytest.raises(RuntimeExecutionError) as failure:
        runner.run(spec)
    assert "private-api-token" not in str(failure.value)
    assert "secret-should-not-leak" not in str(failure.value)
    assert fake.terminated == ["sbx-owned-test"]


def test_setup_timeout_cleans_up_created_sandbox(tmp_path: Path) -> None:
    fake = FakeSandboxes(broken="timeout")
    runner, spec = setup_runner(tmp_path, fake)
    assert runner.run(spec).timed_out
    assert fake.terminated == ["sbx-owned-test"]


def test_missing_bundle_never_provisions_compute(tmp_path: Path) -> None:
    fake = FakeSandboxes()
    runner, spec = setup_runner(tmp_path, fake)
    runner.settings.cloudeq_render_wheels_dir = str(tmp_path / "missing")
    with pytest.raises(RuntimeExecutionError, match="bundle"):
        runner.run(spec)
    assert not fake.created


def test_linked_upload_is_rejected(tmp_path: Path) -> None:
    fake = FakeSandboxes()
    runner, spec = setup_runner(tmp_path, fake)
    link = Path(spec.workspace_host) / "linked.py"
    try:
        link.symlink_to(tmp_path / "outside.py")
    except OSError:
        pytest.skip("Symlink creation is unavailable on this machine.")
    with pytest.raises(RuntimeExecutionError, match="Linked"):
        runner.run(spec)
    assert not fake.created
