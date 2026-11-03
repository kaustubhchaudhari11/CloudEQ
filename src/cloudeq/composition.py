"""Composition root. Planes stay decoupled; this module is the only place that wires them."""

from pathlib import Path

from cloudeq.plane2_agents.agents.stage_client import CrewStageClient
from cloudeq.plane2_agents.settings import AgentSettings
from cloudeq.plane2_agents.supervisor import Supervisor
from cloudeq.plane2_agents.telemetry import MemoryTelemetrySink
from cloudeq.plane3_runtime.executor import DockerRuntimeExecutor
from cloudeq.plane3_runtime.runner import DockerRunner
from cloudeq.plane3_runtime.settings import RuntimeSettings
from cloudeq.shared.ports.protocols import RuntimeExecutor, TelemetrySink


def container_executor(
    runner: DockerRunner,
    *,
    settings: RuntimeSettings | None = None,
    sink: TelemetrySink | None = None,
    workspace_root: Path | None = None,
) -> DockerRuntimeExecutor:
    return DockerRuntimeExecutor(
        settings or RuntimeSettings(),
        runner,
        sink or MemoryTelemetrySink(),
        workspace_root=workspace_root,
    )


def supervising_runtime(
    runtime: RuntimeExecutor,
    *,
    sink: TelemetrySink | None = None,
    engine: str = "offline",
    crew_client: CrewStageClient | None = None,
    agent_settings: AgentSettings | None = None,
    max_iterations: int = 3,
) -> Supervisor:
    """Connect a runtime port to the supervisor. The default engine stays offline."""

    return Supervisor(
        runtime=runtime,
        sink=sink or MemoryTelemetrySink(),
        engine=engine,
        crew_client=crew_client,
        settings=agent_settings,
        max_iterations=max_iterations,
    )
