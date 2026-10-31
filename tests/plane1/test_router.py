"""Gemini adapter failures stay offline from the network and do not hand off."""

import json

import httpx
from tests.plane1.support import SpyTransport, client_for, service_for, settings

from cloudeq.plane1_intake.router.gemini import GeminiCallError, GeminiTimeout, HttpxGeminiTransport
from cloudeq.plane1_intake.settings import Settings
from cloudeq.shared.contracts.models import SubmissionSource, TaskSubmission


def _gemini_settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "cloudeq_router_mode": "gemini",
        "cloudeq_gemini_live_calls": True,
        "gemini_api_key": "test-key",
        "gemini_router_model": "example-model",
        "cloudeq_gemini_timeout_seconds": 5,
    }
    base.update(overrides)
    return settings(**base)


def _payload(status: str = "feasible") -> str:
    return json.dumps(
        {
            "status": status,
            "dataset_check": "not_applicable",
            "reasons": ["model said " + status],
        }
    )


def test_disabled_gemini_does_not_call_transport() -> None:
    spy = SpyTransport(_payload())
    configured = settings(
        cloudeq_router_mode="gemini",
        cloudeq_gemini_live_calls=False,
        gemini_api_key="test-key",
        gemini_router_model="example-model",
    )
    intake, _sink, handoff = service_for(configured=configured, transport=spy)
    response = client_for(intake).post("/tasks", json={"source": "api", "prompt": "Add a parser"})
    body = response.json()
    assert body["status"] == "routed"
    assert body["feasibility"]["status"] == "error"
    assert body["feasibility"]["model_id"] == "example-model"
    assert "No model id was guessed" in " ".join(body["reasons"])
    assert spy.calls == []
    assert handoff.requests == []


def test_missing_model_id_does_not_guess_or_call() -> None:
    spy = SpyTransport(_payload())
    configured = settings(
        cloudeq_router_mode="gemini",
        cloudeq_gemini_live_calls=True,
        gemini_api_key="test-key",
        gemini_router_model="",
    )
    intake, _sink, handoff = service_for(configured=configured, transport=spy)
    response = client_for(intake).post("/tasks", json={"source": "api", "prompt": "Add a parser"})
    assert response.json()["feasibility"]["status"] == "error"
    assert response.json()["feasibility"]["model_id"] == ""
    assert spy.calls == []
    assert handoff.requests == []


def test_timeout_and_malformed_output_do_not_hand_off() -> None:
    timeout = SpyTransport(error=GeminiTimeout("slow"))
    intake, _sink, handoff = service_for(
        configured=_gemini_settings(),
        transport=timeout,
    )
    timed = client_for(intake).post("/tasks", json={"source": "api", "prompt": "Add a parser"})
    assert timed.json()["status"] == "routed"
    assert timed.json()["feasibility"]["status"] == "error"
    assert "timed out" in " ".join(timed.json()["reasons"])
    assert timeout.calls
    assert handoff.requests == []

    broken = SpyTransport("this is not json")
    intake, _sink, handoff = service_for(
        configured=_gemini_settings(),
        transport=broken,
    )
    malformed = client_for(intake).post("/tasks", json={"source": "api", "prompt": "Add a parser"})
    assert malformed.json()["feasibility"]["status"] == "error"
    assert "malformed" in " ".join(malformed.json()["reasons"])
    assert handoff.requests == []


def test_valid_model_json_hands_off_with_the_configured_model_id() -> None:
    spy = SpyTransport(_payload())
    intake, sink, handoff = service_for(
        configured=_gemini_settings(),
        transport=spy,
    )
    response = client_for(intake).post("/tasks", json={"source": "api", "prompt": "Add a parser"})
    body = response.json()
    assert body["status"] == "handed_off"
    assert body["execution_started"] is False
    assert body["feasibility"]["router"] == "gemini"
    assert body["feasibility"]["model_id"] == "example-model"
    assert spy.calls[0][0] == "example-model"
    assert "test-key" not in json.dumps(sink.events[0].model_dump(mode="json"))
    assert len(handoff.requests) == 1


def test_model_cannot_pass_a_named_dataset() -> None:
    spy = SpyTransport(
        json.dumps({"status": "feasible", "dataset_check": "passed", "reasons": ["looks fine"]})
    )
    intake, _sink, handoff = service_for(
        configured=_gemini_settings(),
        transport=spy,
    )
    response = client_for(intake).post(
        "/tasks",
        json={
            "source": "api",
            "prompt": "Use the corpus",
            "external_ref": {"dataset_id": "corpus-v1"},
        },
    )
    body = response.json()
    assert body["status"] == "routed"
    assert body["feasibility"]["status"] == "infeasible"
    assert body["feasibility"]["dataset_check"] == "failed"
    assert handoff.requests == []


def test_http_transport_sends_the_key_as_a_header_and_maps_errors() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["key"] = request.headers["x-goog-api-key"]
        payload = json.loads(request.content.decode())
        assert payload["generationConfig"]["responseMimeType"] == "application/json"
        text = json.dumps(
            {"status": "infeasible", "dataset_check": "not_applicable", "reasons": ["too broad"]}
        )
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": text}]}}]},
        )

    transport = HttpxGeminiTransport(
        base_url="https://gemini.example",
        timeout_seconds=2,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    raw = transport.generate(model="example-model", api_key="test-key", user_text="prompt")
    assert "infeasible" in raw
    assert seen["key"] == "test-key"
    assert "test-key" not in seen["url"]
    assert seen["url"].endswith("/v1beta/models/example-model:generateContent")

    def fail(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "unavailable"})

    failing = HttpxGeminiTransport(
        base_url="https://gemini.example",
        timeout_seconds=2,
        client=httpx.Client(transport=httpx.MockTransport(fail)),
    )
    try:
        failing.generate(model="example-model", api_key="test-key", user_text="prompt")
    except GeminiCallError as exc:
        assert exc.status_code == 503
        assert "test-key" not in str(exc)
    else:
        raise AssertionError("expected GeminiCallError")


def test_provider_error_is_a_routed_error() -> None:
    spy = SpyTransport(error=GeminiCallError(503, "Gemini request failed"))
    intake, _sink, handoff = service_for(
        configured=_gemini_settings(),
        transport=spy,
    )
    response = client_for(intake).post("/tasks", json={"source": "api", "prompt": "Add a parser"})
    body = response.json()
    assert body["feasibility"]["status"] == "error"
    assert "503" in " ".join(body["reasons"])
    assert "test-key" not in json.dumps(body)
    assert handoff.requests == []


def test_submission_model_is_used_by_the_service_path() -> None:
    intake, _sink, _handoff = service_for()
    result = intake.submit(
        TaskSubmission(source=SubmissionSource.API, prompt="Direct call"),
        expected_source=SubmissionSource.API,
    )
    assert result.status.value == "handed_off"
