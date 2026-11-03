"""Task workspace paths. Symlinks and repository escapes are rejected."""

import re
from pathlib import Path

from cloudeq.shared.contracts.models import MAX_RUNTIME_FILES, normalize_relative_path
from cloudeq.shared.ports.errors import RuntimeExecutionError

_TASK_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def validate_task_id(task_id: str) -> str:
    if _TASK_ID.fullmatch(task_id) is None or ".." in task_id:
        raise RuntimeExecutionError("Task id is not safe for a workspace directory.")
    return task_id


def prepare_workspace_root(root: Path) -> Path:
    """Create the workspace root outside the CloudEQ repository."""

    candidate = root.expanduser()
    if any(_is_link(part) for part in (candidate, *candidate.parents)):
        raise RuntimeExecutionError("Workspace root and its parents must not be links.")
    resolved = candidate.resolve()
    source_root = _source_repository()
    if _inside_repository(resolved) or (
        source_root is not None and source_root.is_relative_to(resolved)
    ):
        raise RuntimeExecutionError(
            "Workspace root must not be inside the CloudEQ source repository."
        )
    resolved.mkdir(parents=True, exist_ok=True)
    if not resolved.is_dir() or _is_link(resolved):
        raise RuntimeExecutionError("Workspace root is not a real directory.")
    return resolved


def task_directory(root: Path, task_id: str, *, create: bool) -> Path:
    validate_task_id(task_id)
    candidate = root / task_id
    if _is_link(candidate):
        raise RuntimeExecutionError("Task workspace must not be a link.")
    if create:
        try:
            candidate.mkdir(parents=False, exist_ok=False)
        except FileExistsError as exc:
            raise RuntimeExecutionError(
                "Task workspace already exists and is not owned by this executor."
            ) from exc
    if not candidate.exists():
        raise RuntimeExecutionError("Task workspace does not exist.")
    if not candidate.is_dir() or _is_link(candidate):
        raise RuntimeExecutionError("Task workspace must be a real directory.")
    resolved = candidate.resolve()
    if not _is_direct_child(resolved, root.resolve()):
        raise RuntimeExecutionError("Task workspace escaped its root.")
    _reject_symlink_parents(candidate, root)
    return candidate


def destination_for(workspace: Path, relative_path: str) -> Path:
    try:
        relative = normalize_relative_path(relative_path)
    except ValueError as exc:
        raise RuntimeExecutionError("Runtime path is not safe.") from exc
    cursor = workspace
    parts = relative.split("/")
    if len(parts) > 16:
        raise RuntimeExecutionError("Runtime path is too deep.")
    for part in parts[:-1]:
        cursor = cursor / part
        if _is_link(cursor):
            raise RuntimeExecutionError("Symlinks are not allowed in the task workspace.")
        if cursor.exists() and not cursor.is_dir():
            raise RuntimeExecutionError("Runtime path is not a directory.")
        cursor.mkdir(exist_ok=True)
        _assert_inside(cursor, workspace)
    target = cursor / parts[-1]
    if _is_link(target):
        raise RuntimeExecutionError("Symlinks are not allowed in the task workspace.")
    return target


def assert_file_budget(count: int) -> None:
    if count < 1 or count > MAX_RUNTIME_FILES:
        raise RuntimeExecutionError("Runtime file count is outside the contract limit.")


def _is_project_root(path: Path) -> bool:
    return (path / "pyproject.toml").is_file() and (path / "src" / "cloudeq").is_dir()


def _inside_repository(path: Path) -> bool:
    return any(_is_project_root(parent) for parent in (path, *path.parents))


def _is_direct_child(path: Path, root: Path) -> bool:
    try:
        return len(path.relative_to(root).parts) == 1
    except ValueError:
        return False


def _assert_inside(path: Path, workspace: Path) -> None:
    try:
        path.resolve().relative_to(workspace.resolve())
    except ValueError as exc:
        raise RuntimeExecutionError("Runtime path escaped the task workspace.") from exc


def _reject_symlink_parents(path: Path, root: Path) -> None:
    current = path
    root_resolved = root.resolve()
    while current.resolve() != root_resolved:
        if _is_link(current):
            raise RuntimeExecutionError("Symlinks are not allowed in the task workspace.")
        if current.parent == current:
            break
        current = current.parent


def _is_link(path: Path) -> bool:
    return path.is_symlink() or path.is_junction()


def _source_repository() -> Path | None:
    for seed in (Path.cwd(), Path(__file__)):
        resolved = seed.resolve()
        for parent in (resolved, *resolved.parents):
            if _is_project_root(parent):
                return parent
    return None
