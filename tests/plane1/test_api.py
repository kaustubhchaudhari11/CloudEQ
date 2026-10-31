"""API validation, routing, and trace behavior."""

import ast
from pathlib import Path

from tests.plane1.support import client_for, service_for, settings

from cloudeq.plane1_intake.adapters import InMemoryTaskHandoff
from cloudeq.shared.contracts.models import HandoffAcknowledgement, HandoffRequest


def test_health_reports_offline_intake_without_execution() -> None:
    intake, _sink, _handoff = service_for()
    response = client_for(intake).get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["plane"] == "plane1_intake"
    assert body["router_mode"] == "offline"
    assert body["live_gemini_calls"] is False
    assert body["execution_available"] is False


def test_valid_prompt_is_handed_off_and_not_executed() -> None:
    intake, sink, handoff = service_for()
    response = client_for(intake).post(
        "/tasks",
        json={"source": "api", "prompt": "  Add a health check  "},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "handed_off"
    assert body["execution_started"] is False
    assert body["handoff_accepted"] is True
    assert body["feasibility"]["status"] == "feasible"
    assert body["feasibility"]["router"] == "offline"
    assert body["feasibility"]["model_id"] == ""
    assert body["prompt"] == "Add a health check"
    assert body["task_id"]
    assert body["trace_id"]
    stored = client_for(intake).get(f"/tasks/{body['task_id']}")
    assert stored.status_code == 200
    assert stored.json()["trace_id"] == body["trace_id"]
    assert len(handoff.requests) == 1
    assert handoff.requests[0].trace_id == body["trace_id"]
    names = [event.event_name for event in sink.events]
    assert names == [
        "intake.submission_accepted",
        "intake.feasibility_routed",
        "intake.task_handed_off",
    ]
    assert {event.trace_id for event in sink.events} == {body["trace_id"]}
    assert {event.task_id for event in sink.events} == {body["task_id"]}


def test_empty_and_whitespace_prompts_are_rejected_without_handoff() -> None:
    intake, sink, handoff = service_for()
    client = client_for(intake)
    for prompt in ("", "   "):
        response = client.post("/tasks", json={"source": "api", "prompt": prompt})
        assert response.status_code == 422
        body = response.json()
        assert body["status"] == "rejected"
        assert body["task_id"] is None
        assert body["execution_started"] is False
        assert "prompt must not be empty" in body["reasons"]
        assert body["trace_id"]
    assert handoff.requests == []
    assert all(event.event_name == "intake.submission_rejected" for event in sink.events)
    assert all(event.task_id is None for event in sink.events)


def test_caller_supplied_task_id_is_rejected() -> None:
    intake, _sink, handoff = service_for()
    response = client_for(intake).post(
        "/tasks",
        json={"source": "api", "prompt": "Build a parser", "task_id": "caller-chosen"},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["status"] == "rejected"
    assert body["trace_id"]
    assert any("task_id" in reason for reason in body["reasons"])
    assert handoff.requests == []


def test_cli_source_on_the_api_is_rejected() -> None:
    intake, _sink, handoff = service_for()
    response = client_for(intake).post(
        "/tasks",
        json={"source": "cli", "prompt": "Build a parser"},
    )
    assert response.status_code == 422
    assert response.json()["status"] == "rejected"
    assert "source must be api" in response.json()["reasons"]
    assert handoff.requests == []


def test_ticket_sources_stay_disabled() -> None:
    intake, _sink, handoff = service_for()
    client = client_for(intake)
    for source in ("github_issues", "jira"):
        response = client.post("/tasks", json={"source": source, "prompt": "Fix the bug"})
        assert response.status_code == 422
        assert response.json()["status"] == "rejected"
        assert response.json()["execution_started"] is False
    assert handoff.requests == []


def test_named_dataset_is_infeasible_and_not_handed_off() -> None:
    intake, sink, handoff = service_for()
    response = client_for(intake).post(
        "/tasks",
        json={
            "source": "api",
            "prompt": "Train on the support corpus",
            "external_ref": {"dataset": "support-corpus"},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "routed"
    assert body["handoff_accepted"] is False
    assert body["execution_started"] is False
    assert body["feasibility"]["status"] == "infeasible"
    assert body["feasibility"]["dataset_check"] == "failed"
    assert "No dataset catalog is configured." in body["reasons"]
    assert handoff.requests == []
    assert [event.event_name for event in sink.events] == [
        "intake.submission_accepted",
        "intake.feasibility_routed",
    ]
    assert len({event.trace_id for event in sink.events}) == 1


def test_refusing_handoff_stays_routed() -> None:
    intake, _sink, handoff = service_for(handoff=InMemoryTaskHandoff(accept=False))
    response = client_for(intake).post(
        "/tasks",
        json={"source": "api", "prompt": "Add a parser"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "routed"
    assert body["handoff_accepted"] is False
    assert body["execution_started"] is False
    assert body["feasibility"]["status"] == "feasible"
    assert len(handoff.requests) == 1


def test_missing_task_is_not_found() -> None:
    intake, _sink, _handoff = service_for()
    response = client_for(intake).get("/tasks/missing")
    assert response.status_code == 404


def test_plane1_modules_do_not_import_other_planes() -> None:
    root = Path("src/cloudeq/plane1_intake")
    forbidden = ("cloudeq.plane2_agents", "cloudeq.plane3_runtime", "cloudeq.plane4_observability")
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


class _ExecutingHandoff:
    def submit(self, handoff: HandoffRequest) -> HandoffAcknowledgement:
        return HandoffAcknowledgement(
            task_id=handoff.task_id,
            trace_id=handoff.trace_id,
            accepted=True,
            execution_started=True,
        )


def test_plane1_does_not_report_execution_when_handoff_claims_it() -> None:
    configured = settings()
    from cloudeq.plane1_intake.service import IntakeService

    intake = IntakeService.from_settings(configured, handoff=_ExecutingHandoff())
    response = client_for(intake).post("/tasks", json={"source": "api", "prompt": "Ship it"})
    body = response.json()
    assert body["status"] == "routed"
    assert body["execution_started"] is False
    assert "cannot claim" in " ".join(body["reasons"])


class _MismatchedHandoff:
    def __init__(self, mismatch: str) -> None:
        self.mismatch = mismatch

    def submit(self, handoff: HandoffRequest) -> HandoffAcknowledgement:
        return HandoffAcknowledgement(
            task_id="other-task" if self.mismatch == "task" else handoff.task_id,
            trace_id="other-trace" if self.mismatch == "trace" else handoff.trace_id,
            accepted=True,
            execution_started=False,
        )


def test_mismatched_handoff_ids_are_not_reported_as_accepted() -> None:
    from cloudeq.plane1_intake.service import IntakeService

    for mismatch in ("task", "trace"):
        intake = IntakeService.from_settings(settings(), handoff=_MismatchedHandoff(mismatch))
        response = client_for(intake).post(
            "/tasks", json={"source": "api", "prompt": "Build a parser"}
        )
        body = response.json()
        assert body["status"] == "routed"
        assert body["handoff_accepted"] is False
        assert body["execution_started"] is False
        assert "did not match" in " ".join(body["reasons"])
