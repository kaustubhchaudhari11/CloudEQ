"""Plane 3 policy and workspace checks. These tests do not start Docker."""

import ast
from pathlib import Path

import pytest

from cloudeq.plane3_runtime.policy import ContainerSpec, container_argv
from cloudeq.plane3_runtime.settings import RuntimeSettings
from cloudeq.plane3_runtime.workspace import (
    destination_for,
    prepare_workspace_root,
    task_directory,
    validate_task_id,
)
from cloudeq.shared.contracts.models import RuntimeFile
from cloudeq.shared.ports.errors import RuntimeExecutionError


def test_task_ids_and_workspace_root_stay_inside_bounds(tmp_path: Path) -> None:
    with pytest.raises(RuntimeExecutionError):
        validate_task_id("../task")
    with pytest.raises(RuntimeExecutionError):
        validate_task_id("")
    root = prepare_workspace_root(tmp_path / "workspaces")
    created = task_directory(root, "task-1", create=True)
    assert created == root / "task-1"
    with pytest.raises(RuntimeExecutionError, match="already exists"):
        task_directory(root, "task-1", create=True)
    assert destination_for(created, "src/app.py") == created / "src" / "app.py"
    with pytest.raises(RuntimeExecutionError):
        prepare_workspace_root(Path(".").resolve())
    with pytest.raises(RuntimeExecutionError):
        prepare_workspace_root(Path("src"))


def test_symlink_workspace_and_nested_escape_are_rejected(tmp_path: Path) -> None:
    root = prepare_workspace_root(tmp_path / "workspaces")
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (root / "task-1").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("This process cannot create symlinks.")
    with pytest.raises(RuntimeExecutionError):
        task_directory(root, "task-1", create=False)
    (root / "task-1").unlink()
    workspace = task_directory(root, "task-1", create=True)
    try:
        (workspace / "escape").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("This process cannot create symlinks.")
    with pytest.raises(RuntimeExecutionError):
        destination_for(workspace, "escape/pwned.txt")


def test_file_model_rejects_parent_and_absolute_paths() -> None:
    with pytest.raises(ValueError):
        RuntimeFile(relative_path="../secret.txt", content="nope")
    with pytest.raises(ValueError):
        RuntimeFile(relative_path="/etc/passwd", content="nope")
    for path in ("src/name:stream.py", "CON.txt", "src/aux.py", "src/file.", "src/a?.py"):
        with pytest.raises(ValueError):
            RuntimeFile(relative_path=path, content="nope")


def test_container_arguments_disable_network_and_the_docker_socket() -> None:
    settings = RuntimeSettings()
    settings.validate_policy()
    spec = ContainerSpec(
        name="cloudeq-abc",
        image=settings.cloudeq_runtime_image,
        command=("python", "-m", "pytest"),
        workspace_host="C:/work/task-1",
        network="none",
        memory="512m",
        cpus="1",
        pids_limit=64,
        user="65534:65534",
        timeout_seconds=120,
    )
    argv = container_argv(spec)
    assert isinstance(argv, list)
    assert argv[0] == "docker"
    assert "--network" in argv and argv[argv.index("--network") + 1] == "none"
    assert "--user" in argv and argv[argv.index("--user") + 1] == "65534:65534"
    assert "--pids-limit" in argv
    assert "docker.sock" not in " ".join(argv)
    assert argv[-3:] == ["python", "-m", "pytest"]
    assert argv[argv.index("--pull") + 1] == "never"
    assert ":/workspace:ro" in argv[argv.index("-v") + 1]
    assert "PYTEST_ADDOPTS=-p no:cacheprovider" in argv
    unsafe = ContainerSpec(
        name="cloudeq-abc",
        image=spec.image,
        command=spec.command,
        workspace_host="/var/run/docker.sock",
        network="none",
        memory="512m",
        cpus="1",
        pids_limit=64,
        user="65534:65534",
        timeout_seconds=120,
    )
    with pytest.raises(ValueError):
        container_argv(unsafe)
    unsafe_command = ContainerSpec(
        name=spec.name,
        image=spec.image,
        command=("python", "-c", "print(1)"),
        workspace_host=spec.workspace_host,
        network="none",
        memory="512m",
        cpus="1",
        pids_limit=64,
        user="65534:65534",
        timeout_seconds=120,
    )
    with pytest.raises(ValueError):
        container_argv(unsafe_command)


def test_host_execution_and_git_push_settings_are_rejected() -> None:
    with pytest.raises(ValueError):
        RuntimeSettings(cloudeq_runtime_allow_host_execution=True).validate_policy()
    with pytest.raises(ValueError):
        RuntimeSettings(cloudeq_runtime_allow_git_push=True).validate_policy()


def test_plane3_does_not_import_other_planes() -> None:
    root = Path("src/cloudeq/plane3_runtime")
    forbidden = ("cloudeq.plane1_intake", "cloudeq.plane2_agents", "cloudeq.plane4_observability")
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


def test_workspace_root_cannot_contain_source_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "cloudeq.plane3_runtime.workspace._source_repository",
        lambda: tmp_path / "CloudEQ",
    )
    with pytest.raises(RuntimeExecutionError, match="source repository"):
        prepare_workspace_root(tmp_path)
