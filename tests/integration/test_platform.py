"""End-to-end: Plane 1 -> 2 -> 3 -> 4 through the platform and its HTTP server."""

import subprocess
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cloudeq.plane3_runtime.policy import ContainerSpec
from cloudeq.plane3_runtime.runner import ContainerOutput
from cloudeq.plane3_runtime.settings import RuntimeSettings
from cloudeq.plane4_observability.factory import build_observability
from cloudeq.plane4_observability.settings import ObservabilitySettings
from cloudeq.platform.server import create_app
from cloudeq.platform.service import Platform
from cloudeq.platform.settings import PlatformSettings


def _platform(tmp_path: Path, **settings: object) -> Platform:
    stack = build_observability(ObservabilitySettings(cloudeq_observability_store="memory"))
    return Platform(
        settings=PlatformSettings(**settings),  # type: ignore[arg-type]
        observability=stack,
        runs_file=tmp_path / "runs.jsonl",
    )


def test_simulation_run_passes_and_correlates_all_planes(tmp_path: Path) -> None:
    platform = _platform(tmp_path)
    record = platform.run("Add a health check", simulated_failures=1)
    assert record["intake"]["status"] == "handed_off"
    assert record["intake"]["execution_started"] is False
    agents = record["agents"]
    assert agents["state"] == "passed" and agents["devops_ran"] is True
    assert [i["passed"] for i in agents["iterations"]] == [False, True]
    assert agents["simulation"] is True and agents["host_execution"] is False
    trace = platform.observability.pipeline.trace(record["trace_id"])
    planes = {e["raw"]["source"] for e in trace["events"]}
    assert planes == {"plane1_intake", "plane2_agents", "plane3_runtime"}
    assert all(e["canonical"] for e in trace["events"])
    assert {e["raw"]["task_id"] for e in trace["events"]} == {record["task_id"]}


def test_budget_exhaustion_skips_devops(tmp_path: Path) -> None:
    record = _platform(tmp_path).run("Refactor billing", simulated_failures=9)
    assert record["agents"]["state"] == "failed_budget_exhausted"
    assert record["agents"]["devops_ran"] is False
    assert len(record["agents"]["iterations"]) == 3


def test_infeasible_and_rejected_do_not_reach_agents(tmp_path: Path) -> None:
    platform = _platform(tmp_path)
    infeasible = platform.run("Use the corpus", dataset="corpus-v1")
    assert infeasible["outcome"] == "routed" and infeasible["agents"] is None
    rejected = platform.run("   ")
    assert rejected["outcome"] == "rejected" and rejected["task_id"] is None


def test_runs_persist_to_the_runs_file(tmp_path: Path) -> None:
    first = _platform(tmp_path)
    record = first.run("Add a health check")
    second = _platform(tmp_path)
    assert second.get_run(record["task_id"]) is not None
    assert second.list_runs()[0]["task_id"] == record["task_id"]


class LocalPytestRunner:
    """Test double for the Docker CLI: runs the generated tests in the task workspace."""

    def run(self, spec: ContainerSpec) -> ContainerOutput:
        started = time.perf_counter()
        done = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
            cwd=spec.workspace_host,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        return ContainerOutput(
            done.returncode,
            done.stdout[-2000:],
            done.stderr[-500:],
            False,
            int((time.perf_counter() - started) * 1000),
        )

    def remove(self, name: str) -> None:
        return None


def test_docker_mode_repairs_generated_code_with_real_test_feedback(tmp_path: Path) -> None:
    stack = build_observability(ObservabilitySettings(cloudeq_observability_store="memory"))
    platform = Platform(
        settings=PlatformSettings(cloudeq_execution_mode="docker"),
        observability=stack,
        runtime_settings=RuntimeSettings(cloudeq_runtime_workspace_root=str(tmp_path / "ws")),
        docker_runner=LocalPytestRunner(),
        runs_file=tmp_path / "runs.jsonl",
    )
    record = platform.run("Add a health check", simulated_failures=1)
    agents = record["agents"]
    assert [i["passed"] for i in agents["iterations"]] == [False, True]
    assert "1 failed" in agents["iterations"][0]["tester_feedback"]
    assert agents["state"] == "passed" and agents["devops_ran"] is True
    # An injected runner is never reported as a real container run.
    assert record["details"]["runtime_backend"] == "container-mock"
    assert agents["simulation"] is True and agents["live_gemini"] is False
    paths = {f["path"] for f in record["details"]["generated_files"]}
    assert paths == {"forge_feature.py", "test_forge_feature.py"}


def test_docker_mode_reports_unavailable_engine_honestly(tmp_path: Path) -> None:
    class DeadRunner(LocalPytestRunner):
        def run(self, spec: ContainerSpec) -> ContainerOutput:
            from cloudeq.shared.ports.errors import RuntimeExecutionError

            raise RuntimeExecutionError("Docker could not start the container.")

    stack = build_observability(ObservabilitySettings(cloudeq_observability_store="memory"))
    platform = Platform(
        settings=PlatformSettings(cloudeq_execution_mode="docker"),
        observability=stack,
        runtime_settings=RuntimeSettings(cloudeq_runtime_workspace_root=str(tmp_path / "ws")),
        docker_runner=DeadRunner(),
        runs_file=tmp_path / "runs.jsonl",
    )
    record = platform.run("Add a health check")
    assert record["agents"]["state"] == "error"
    assert record["agents"]["devops_ran"] is False


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(_platform(tmp_path)))


def test_server_dashboard_and_run_api(client: TestClient) -> None:
    page = client.get("/")
    assert page.status_code == 200 and "FORGE" in page.text
    assert client.get("/health").json()["status"] == "ok"
    made = client.post("/api/runs", json={"prompt": "Add a health check", "simulated_failures": 2})
    assert made.status_code == 200
    body = made.json()
    assert body["outcome"] == "passed"
    listed = client.get("/api/runs").json()
    assert listed[0]["task_id"] == body["task_id"] and listed[0]["iterations"] == 3
    assert client.get(f"/api/runs/{body['task_id']}").status_code == 200
    assert client.get("/api/runs/missing").status_code == 404
    trace = client.get(f"/observability/traces/{body['trace_id']}").json()
    assert trace["event_count"] > 10
    metrics = client.get("/observability/metrics").json()
    assert metrics["totals"]["agent_runs"] == 1
    assert client.get("/observability/grafana/events-by-plane").status_code == 200
    assert client.get("/observability/grafana/repairs").json()[0]["iterations"] == 3


def test_server_rejects_bad_input(client: TestClient) -> None:
    blank = client.post("/api/runs", json={"prompt": " "})
    assert blank.status_code == 422 and blank.json()["outcome"] == "rejected"
    invalid = client.post("/api/runs", json={"prompt": "x", "simulated_failures": 99})
    assert invalid.status_code == 422 and invalid.json()["status"] == "rejected"


def test_plane1_contract_endpoint_still_works(client: TestClient) -> None:
    done = client.post("/tasks", json={"source": "api", "prompt": "Add a health check"})
    assert done.status_code == 200
    assert done.json()["status"] == "handed_off" and done.json()["execution_started"] is False
    assert done.json()["agent_outcome"] == "passed"


def test_external_ingest_and_retry_endpoints(client: TestClient) -> None:
    good = client.post("/observability/ingest", json={"agent_id": "a", "status": "ok"})
    assert good.status_code == 202 and good.json()["normalization_status"] == "normalized"
    bad = client.post(
        "/observability/ingest", content=b"<<garbage>>", headers={"content-type": "text/plain"}
    )
    assert bad.json()["raw_retained"] is True
    assert bad.json()["normalization_status"] == "failed"
    failed = client.get("/observability/events/raw?status=failed").json()
    assert len(failed) == 1
    retry = client.post("/observability/retry?normalizer=offline").json()
    assert retry["retried"] == 1
    assert client.get("/observability/health").json()["store"] == "memory"
