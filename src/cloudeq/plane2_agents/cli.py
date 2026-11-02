"""Run the offline agent engine from the command line."""

import argparse
import json
from pathlib import Path
from uuid import uuid4

from cloudeq.plane2_agents.models import RepairState
from cloudeq.plane2_agents.runtime_sim import OfflineRuntimeSimulation
from cloudeq.plane2_agents.settings import AgentSettings
from cloudeq.plane2_agents.supervisor import Supervisor
from cloudeq.plane2_agents.telemetry import MemoryTelemetrySink
from cloudeq.shared.contracts.models import (
    DatasetCheck,
    FeasibilityResult,
    FeasibilityStatus,
    HandoffRequest,
    RouterKind,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cloudeq-agents",
        description=(
            "Run the FORGE SPAN agent supervisor. "
            "The default engine is an offline simulation, not live CrewAI or Gemini."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run", help="Supervise one accepted prompt")
    run.add_argument("--prompt", required=True)
    run.add_argument("--engine", choices=["offline", "crewai"], default=None)
    args = parser.parse_args(argv)
    if args.command != "run":
        return 1
    settings = AgentSettings()
    config_value = settings.cloudeq_agents_config.strip()
    config_path = Path(config_value) if config_value else None
    engine = str(args.engine or settings.cloudeq_agent_engine)
    supervisor = Supervisor(
        config_path=config_path,
        runtime=OfflineRuntimeSimulation(),
        sink=MemoryTelemetrySink(),
        max_iterations=settings.cloudeq_repair_max_iterations,
        engine=engine,
    )
    result = supervisor.run(
        HandoffRequest(
            task_id=str(uuid4()),
            trace_id=str(uuid4()),
            prompt=str(args.prompt),
            feasibility=FeasibilityResult(
                status=FeasibilityStatus.FEASIBLE,
                dataset_check=DatasetCheck.NOT_APPLICABLE,
                reasons=["CLI constructed a feasible handoff for the offline engine."],
                router=RouterKind.OFFLINE,
                model_id="",
            ),
        )
    )
    print(json.dumps(result.model_dump(mode="json"), indent=2))
    if result.state is RepairState.PASSED:
        return 0
    if result.state is RepairState.FAILED_BUDGET_EXHAUSTED:
        return 2
    if result.state is RepairState.CANCELLED:
        return 3
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
