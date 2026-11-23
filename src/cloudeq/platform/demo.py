"""Scripted end-to-end demonstration (``cloudeq-demo``).

Runs five scenarios through all four planes and prints a readable report:
pass first time, bounded repair, exhausted budget, infeasible routing, and a
rejected prompt; then shows Plane 4 dual retention including a malformed
external event whose raw record survives a failed normalization.
"""

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from cloudeq.plane4_observability.factory import build_observability
from cloudeq.plane4_observability.settings import ObservabilitySettings
from cloudeq.platform.service import Platform
from cloudeq.platform.settings import PlatformSettings, load_dotenv

SCENARIOS: list[dict[str, Any]] = [
    {"title": "Pass on the first iteration", "prompt": "Add a health check endpoint", "f": 0},
    {
        "title": "Bounded repair (2 failing runs, then fix)",
        "prompt": "Validate signup input",
        "f": 2,
    },
    {"title": "Repair budget exhausted", "prompt": "Refactor the billing module", "f": 9},
    {
        "title": "Infeasible: unknown dataset",
        "prompt": "Train on the corpus",
        "f": 0,
        "d": "corpus",
    },
    {"title": "Rejected: blank prompt", "prompt": "   ", "f": 0},
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cloudeq-demo", description=__doc__)
    parser.add_argument(
        "--persist",
        action="store_true",
        help="Write telemetry to the configured store instead of a throwaway database.",
    )
    parser.add_argument("--json", action="store_true", help="Print the full records as JSON.")
    args = parser.parse_args(argv)
    load_dotenv()

    scratch = tempfile.TemporaryDirectory(prefix="forge-span-demo-")
    obs_settings = ObservabilitySettings()
    if not args.persist:
        obs_settings = obs_settings.model_copy(
            update={
                "cloudeq_observability_store": "sqlite",
                "cloudeq_observability_sqlite_path": str(Path(scratch.name) / "demo.sqlite3"),
            }
        )
    stack = build_observability(obs_settings)
    platform = Platform(
        settings=PlatformSettings(),
        observability=stack,
        runs_file=None if args.persist else Path(scratch.name) / "runs.jsonl",
    )
    print(_rule("FORGE SPAN end-to-end demonstration"))
    print(json.dumps(platform.describe(), indent=2))
    records = []
    for number, scenario in enumerate(SCENARIOS, start=1):
        record = platform.run(
            scenario["prompt"], dataset=scenario.get("d"), simulated_failures=scenario["f"]
        )
        records.append(record)
        print(_rule(f"{number}. {scenario['title']}"))
        _print_record(record, stack)

    print(_rule("Plane 4: schema-agnostic ingestion and failure retention"))
    for body in (
        {"agent_id": "qa-agent", "outcome": "failed", "elapsed_ms": 910, "new_field": 1},
        "<<malformed: not JSON>>",
    ):
        envelope = stack.sink.emit_external(body)
        raw = stack.store.get_raw(envelope.event_id)
        assert raw is not None
        print(
            f"  external event {envelope.event_id[:8]}  raw retained=yes  "
            f"normalization={raw.normalization_status.value}"
            + (f"  ({raw.last_error})" if raw.last_error else "")
        )
    metrics = stack.pipeline.metrics()
    print(_rule("Observability summary"))
    print(
        json.dumps(
            {
                k: metrics[k]
                for k in (
                    "totals",
                    "events_by_plane",
                    "normalization",
                    "canonical_status",
                    "run_states",
                )
            },
            indent=2,
        )
    )
    if args.json:
        print(json.dumps(records, indent=2))
    stack.close()
    scratch.cleanup()
    return 0


def _rule(title: str) -> str:
    return f"\n=== {title} " + "=" * max(4, 72 - len(title))


def _print_record(record: dict[str, Any], stack: Any) -> None:
    intake = record["intake"]
    agents = record["agents"]
    print(f"  prompt     : {record['prompt']!r}")
    print(f"  trace_id   : {record['trace_id']}")
    print(f"  Plane 1    : {intake['status']}  {'; '.join(intake['reasons'])}")
    if agents is None:
        print("  Plane 2    : not handed off")
    else:
        stages = " -> ".join(s["stage"] for s in agents["stages"])
        print(f"  Plane 2    : {agents['state']}  engine={agents['engine']}")
        print(f"               stages: {stages}")
        for item in agents["iterations"]:
            verdict = "PASS" if item["passed"] else "FAIL"
            print(f"               iteration {item['iteration']}: {verdict}")
        print(
            f"               DevOps ran: {agents['devops_ran']}  ({agents['termination_reason']})"
        )
        print(
            f"  Plane 3    : backend={record['details'].get('runtime_backend')}  "
            f"host_execution={agents['host_execution']}"
        )
    trace = stack.pipeline.trace(record["trace_id"])
    planes = sorted({e["raw"]["source"] for e in trace["events"]})
    canonical = sum(1 for e in trace["events"] if e["canonical"])
    print(
        f"  Plane 4    : {trace['event_count']} raw / {canonical} canonical events  "
        f"from {', '.join(planes)}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
