"""Docker argument lists. Nothing here is passed through a shell."""

from dataclasses import dataclass

from cloudeq.plane3_runtime.settings import RuntimeSettings
from cloudeq.shared.contracts.models import TEST_COMMAND_ALLOWLIST


@dataclass(frozen=True)
class ContainerSpec:
    name: str
    image: str
    command: tuple[str, ...]
    workspace_host: str
    network: str
    memory: str
    cpus: str
    pids_limit: int
    user: str
    timeout_seconds: float
    output_limit: int = 8192


def allowlisted_argv(command: str) -> tuple[str, ...]:
    if command not in TEST_COMMAND_ALLOWLIST:
        raise ValueError("Command is not allowlisted.")
    if command == "python -m pytest":
        return ("python", "-m", "pytest")
    raise ValueError("Command is not allowlisted.")


def container_argv(spec: ContainerSpec) -> list[str]:
    if spec.command != ("python", "-m", "pytest"):
        raise ValueError("Container command must be the allowlisted test plan.")
    if spec.network != "none":
        raise ValueError("Container network must stay disabled.")
    if spec.user.startswith("0:"):
        raise ValueError("Container user must not be root.")
    mount = f"{spec.workspace_host}:/workspace:ro"
    if "docker.sock" in mount.lower():
        raise ValueError("The Docker socket must not be mounted.")
    return [
        "docker",
        "run",
        "--rm",
        "--pull",
        "never",
        "--name",
        spec.name,
        "--network",
        spec.network,
        "--memory",
        spec.memory,
        "--cpus",
        spec.cpus,
        "--pids-limit",
        str(spec.pids_limit),
        "--user",
        spec.user,
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=64m",
        "-e",
        "PYTHONDONTWRITEBYTECODE=1",
        "-e",
        "HOME=/tmp",
        "-e",
        "PYTEST_ADDOPTS=-p no:cacheprovider",
        "-w",
        "/workspace",
        "-v",
        mount,
        spec.image,
        *spec.command,
    ]


def spec_from_settings(
    settings: RuntimeSettings,
    *,
    name: str,
    workspace_host: str,
    command: tuple[str, ...],
) -> ContainerSpec:
    settings.validate_policy()
    return ContainerSpec(
        name=name,
        image=settings.cloudeq_runtime_image,
        command=command,
        workspace_host=workspace_host,
        network=settings.cloudeq_runtime_network,
        memory=settings.cloudeq_runtime_memory,
        cpus=settings.cloudeq_runtime_cpus,
        pids_limit=settings.cloudeq_runtime_pids_limit,
        user=settings.cloudeq_runtime_user,
        timeout_seconds=settings.cloudeq_runtime_timeout_seconds,
        output_limit=settings.cloudeq_runtime_output_limit,
    )
