import httpx
import pytest

from cloudeq.shared.http_retry import post_json_with_retry


@pytest.mark.parametrize("statuses,expected", [([503, 200], 200), ([503] * 3, 503), ([401], 401)])
def test_temporary_provider_errors_are_bounded(
    statuses: list[int], expected: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[int] = []
    delays: list[float] = []
    monkeypatch.setattr("cloudeq.shared.http_retry.time.sleep", delays.append)

    def respond(request: httpx.Request) -> httpx.Response:
        calls.append(len(calls))
        assert request.headers["x-goog-api-key"] == "private-test-key"
        assert "private-test-key" not in str(request.url)
        return httpx.Response(statuses[len(calls) - 1], json={"result": "fixture"})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        response = post_json_with_retry(
            client,
            "https://provider.example/generate",
            headers={"x-goog-api-key": "private-test-key"},
            body={},
            timeout_seconds=20,
        )
    assert response.status_code == expected
    assert len(calls) == len(statuses)
    assert delays == [1.0, 2.0][: len(statuses) - 1]


def test_retry_does_not_exceed_request_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    def no_sleep(_seconds: float) -> None:
        raise AssertionError("No budget remains for another request")

    monkeypatch.setattr("cloudeq.shared.http_retry.time.sleep", no_sleep)
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(503))) as client:
        assert (
            post_json_with_retry(
                client,
                "https://provider.example/generate",
                headers={},
                body={},
                timeout_seconds=0.1,
            ).status_code
            == 503
        )


def test_crewai_uses_bounded_native_provider_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys
    from types import SimpleNamespace

    from tests.plane2.test_crewai_boundary import _ready, _request

    from cloudeq.plane2_agents.agents.crewai_live import live_kickoff

    seen: dict = {}

    def llm(**kwargs: object) -> object:
        seen.update(kwargs)
        return object()

    fake = SimpleNamespace(
        LLM=llm,
        Agent=lambda **kwargs: kwargs,
        Task=lambda **kwargs: kwargs,
        Process=SimpleNamespace(sequential="sequential"),
        Crew=lambda **kwargs: SimpleNamespace(
            kickoff=lambda: SimpleNamespace(raw='{"summary":"ok"}')
        ),
    )
    monkeypatch.setitem(sys.modules, "crewai", fake)
    assert live_kickoff(_ready(), _request()) == '{"summary":"ok"}'
    options = seen["client_params"]["http_options"]
    assert options.retry_options.attempts == 3
    assert 503 in options.retry_options.http_status_codes
    assert 401 not in options.retry_options.http_status_codes
    assert options.timeout > 0
