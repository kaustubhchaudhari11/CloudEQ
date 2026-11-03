"""Docker CLI runner. Generated code runs only in the restricted container."""

import os
import subprocess
import time
from dataclasses import dataclass
from threading import Thread
from typing import BinaryIO, Protocol

from cloudeq.plane3_runtime.policy import ContainerSpec, container_argv
from cloudeq.shared.ports.errors import RuntimeExecutionError

_CLI_ENV_KEYS = (
    "PATH",
    "PATHEXT",
    "SYSTEMROOT",
    "WINDIR",
    "COMSPEC",
    "HOME",
    "USERPROFILE",
    "DOCKER_HOST",
    "DOCKER_CONTEXT",
)


@dataclass(frozen=True)
class ContainerOutput:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool
    duration_ms: int


class DockerRunner(Protocol):
    def run(self, spec: ContainerSpec) -> ContainerOutput:
        """Start one container and return bounded output."""

    def remove(self, name: str) -> None:
        """Remove a container started by this runner."""


class SubprocessDockerRunner:
    """Drain Docker output continuously, retaining only a bounded prefix."""

    def run(self, spec: ContainerSpec) -> ContainerOutput:
        argv = container_argv(spec)
        if not argv or argv[0] != "docker":
            raise RuntimeExecutionError("Docker command is not available.")
        started = time.perf_counter()
        try:
            proc = subprocess.Popen(
                argv,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                env=_cli_env(),
            )
        except OSError as exc:
            raise RuntimeExecutionError("Docker could not start the container.") from exc
        assert proc.stdout is not None and proc.stderr is not None
        budget = spec.output_limit * 4
        out = bytearray()
        err = bytearray()
        stdout_thread = Thread(target=_drain, args=(proc.stdout, budget, out), daemon=True)
        stderr_thread = Thread(target=_drain, args=(proc.stderr, budget, err), daemon=True)
        stdout_thread.start()
        stderr_thread.start()
        timed_out = False
        try:
            returncode = proc.wait(timeout=spec.timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            proc.kill()
            proc.wait()
            returncode = 124
        finally:
            stdout_thread.join(timeout=5)
            stderr_thread.join(timeout=5)
            proc.stdout.close()
            proc.stderr.close()
        if timed_out:
            self.remove(spec.name)
            return ContainerOutput(
                exit_code=124,
                stdout=_text(out),
                stderr=_text(err),
                timed_out=True,
                duration_ms=_elapsed(started),
            )
        if returncode in {125, 126, 127}:
            raise RuntimeExecutionError("Docker could not start the container.")
        return ContainerOutput(
            exit_code=returncode,
            stdout=_text(out),
            stderr=_text(err),
            timed_out=False,
            duration_ms=_elapsed(started),
        )

    def remove(self, name: str) -> None:
        if not name.startswith("cloudeq-"):
            raise RuntimeExecutionError("Refusing to remove a container this runtime did not name.")
        try:
            completed = subprocess.run(
                ["docker", "rm", "-f", name],
                capture_output=True,
                timeout=20,
                check=False,
                shell=False,
                env=_cli_env(),
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeExecutionError("Docker could not remove the container.") from exc
        if completed.returncode != 0:
            raise RuntimeExecutionError("Docker could not confirm container removal.")


def _drain(stream: BinaryIO, budget: int, retained: bytearray) -> None:
    while chunk := stream.read(4096):
        if len(retained) < budget:
            retained.extend(chunk[: budget - len(retained)])


def _cli_env() -> dict[str, str]:
    return {key: os.environ[key] for key in _CLI_ENV_KEYS if key in os.environ}


def _text(value: bytearray) -> str:
    return bytes(value).decode("utf-8", errors="replace")


def _elapsed(started: float) -> int:
    return max(0, int((time.perf_counter() - started) * 1000))
