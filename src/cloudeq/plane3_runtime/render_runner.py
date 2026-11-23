"""Run the allowlisted test in a short-lived Render sandbox, never on the API host."""

import asyncio
import math
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from cloudeq.plane3_runtime.policy import ContainerSpec, container_argv
from cloudeq.plane3_runtime.runner import ContainerOutput
from cloudeq.shared.contracts.models import MAX_RUNTIME_FILE_CHARS, MAX_RUNTIME_FILES
from cloudeq.shared.ports.errors import RuntimeExecutionError


class RenderRuntimeSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    render_api_key: SecretStr = SecretStr("")
    render_workspace_id: str = ""
    render_sandbox_group_id: str = ""
    cloudeq_render_wheels_dir: str = "/opt/forge-wheels"
    cloudeq_render_setup_timeout: int = Field(default=120, ge=30, le=180)

    def validate_credentials(self) -> None:
        if not self.render_api_key.get_secret_value() or not self.render_workspace_id:
            raise RuntimeExecutionError("Render API key and workspace ID are required.")


class RenderSandboxRunner:
    """A new sandbox for every test attempt; all outbound traffic is denied.

    Package wheels and the fixed harness are trusted deployment assets. They are
    installed before uploading task files. No application credentials are sent.
    A supplied client factory is always labeled as a mock by the executor.
    """

    def __init__(
        self,
        settings: RenderRuntimeSettings,
        *,
        client_factory: Callable[[], Any] | None = None,
    ) -> None:
        settings.validate_credentials()
        self.settings = settings
        self.is_live = client_factory is None
        self._client_factory = client_factory

    def run(self, spec: ContainerSpec) -> ContainerOutput:
        container_argv(spec)  # Enforce the same command/network/user policy.
        workspace = Path(spec.workspace_host)
        self._validate_workspace(workspace)
        wheels = Path(self.settings.cloudeq_render_wheels_dir)
        if not wheels.is_dir() or not list(wheels.glob("pytest-9.2.0-*.whl")):
            raise RuntimeExecutionError("The trusted pytest wheel bundle is missing.")
        return asyncio.run(self._run(spec, workspace, wheels))

    @staticmethod
    def _validate_workspace(workspace: Path) -> None:
        if not workspace.is_dir() or workspace.is_symlink() or workspace.is_junction():
            raise RuntimeExecutionError("Invalid sandbox upload directory.")
        count = 0
        for entry in workspace.rglob("*"):
            if entry.is_symlink() or entry.is_junction():
                raise RuntimeExecutionError("Linked files cannot be uploaded to Render.")
            if entry.is_dir():
                continue
            if not entry.is_file() or entry.stat().st_size > MAX_RUNTIME_FILE_CHARS * 4:
                raise RuntimeExecutionError("Sandbox upload violates the file policy.")
            count += 1
        if not 1 <= count <= MAX_RUNTIME_FILES:
            raise RuntimeExecutionError("Sandbox upload violates the file-count policy.")

    async def _run(self, spec: ContainerSpec, workspace: Path, wheels: Path) -> ContainerOutput:
        if self._client_factory is None:
            from render import RenderAsync

            sdk = RenderAsync(
                token=self.settings.render_api_key.get_secret_value(),
                owner_id=self.settings.render_workspace_id,
            )
        else:
            sdk = self._client_factory()
        client = sdk.sandboxes
        sandbox_id: str | None = None
        started = time.perf_counter()
        setup = self.settings.cloudeq_render_setup_timeout
        lifetime = math.ceil(spec.timeout_seconds + setup + 30)
        try:
            async with asyncio.timeout(lifetime):
                sandbox = await client.create(
                    name=spec.name,
                    plan="1c-2g",
                    timeout_seconds=lifetime,
                    idle_timeout_seconds=300,
                    network_policy="deny-all",
                    env={"PYTHONDONTWRITEBYTECODE": "1"},
                    sandbox_group_id=self.settings.render_sandbox_group_id or None,
                    wait=False,
                )
                sandbox_id = sandbox.id
                async with asyncio.timeout(setup):
                    await client.wait_until_running(sandbox_id, timeout_seconds=60)
                    await client.copy_to(sandbox_id, str(wheels), "/tmp/forge-wheels")
                    prepared = await self._exec(
                        client,
                        sandbox_id,
                        "python3 -m venv /tmp/forge-venv && "
                        "/tmp/forge-venv/bin/python -m pip install --no-index "
                        "--find-links=/tmp/forge-wheels pytest==9.2.0",
                        spec.output_limit,
                    )
                    if prepared.exit_code != 0:
                        raise RuntimeExecutionError("Render test-environment preparation failed.")
                    await client.copy_to(
                        sandbox_id,
                        str(Path(__file__).with_name("sandbox_harness.py")),
                        "/tmp/forge-harness.py",
                    )
                    await client.copy_to(sandbox_id, str(workspace), "/tmp/forge-task")
                # Only validated numeric parameters enter this fixed shell command.
                seconds = max(1, math.ceil(spec.timeout_seconds))
                async with asyncio.timeout(seconds + 10):
                    result = await self._exec(
                        client,
                        sandbox_id,
                        f"/tmp/forge-venv/bin/python /tmp/forge-harness.py {seconds} "
                        f"{int(spec.pids_limit)} {_memory_bytes(spec.memory)}",
                        spec.output_limit,
                    )
                return ContainerOutput(
                    result.exit_code,
                    result.stdout,
                    result.stderr,
                    result.exit_code == 124,
                    int((time.perf_counter() - started) * 1000),
                )
        except TimeoutError:
            return ContainerOutput(
                124,
                "",
                "Remote runtime timed out.",
                True,
                int((time.perf_counter() - started) * 1000),
            )
        except RuntimeExecutionError:
            raise
        except Exception as exc:
            # SDK exceptions can include request details. Do not expose credentials.
            raise RuntimeExecutionError(
                "Render sandbox execution failed; check service status."
            ) from exc
        finally:
            if sandbox_id is not None:
                try:
                    async with asyncio.timeout(20):
                        await client.terminate(sandbox_id)
                except Exception as exc:
                    raise RuntimeExecutionError(
                        "Sandbox cleanup could not be confirmed. "
                        "Its runtime deadline remains active."
                    ) from exc
            if self.is_live:
                await sdk.sandboxes.client.get_async_httpx_client().aclose()

    @staticmethod
    async def _exec(client: Any, sandbox_id: str, command: str, limit: int) -> ContainerOutput:
        stdout = ""
        stderr = ""
        exit_code: int | None = None
        async for event in client.exec(sandbox_id, command):
            if hasattr(event, "exit_code"):
                exit_code = int(event.exit_code)
            elif event.stream == "stdout":
                stdout = (stdout + str(event.data))[:limit]
            elif event.stream == "stderr":
                stderr = (stderr + str(event.data))[:limit]
        if exit_code is None:
            raise RuntimeExecutionError("Remote test stream ended without an exit status.")
        return ContainerOutput(exit_code, stdout, stderr, exit_code == 124, 0)

    def remove(self, name: str) -> None:
        raise RuntimeExecutionError("Render sandboxes are cleaned up by their owning run.")


def _memory_bytes(value: str) -> int:
    suffix = value[-1].lower()
    if suffix.isdigit():
        return int(value)
    return int(value[:-1]) * {"b": 1, "k": 1024, "m": 1024**2, "g": 1024**3}[suffix]
