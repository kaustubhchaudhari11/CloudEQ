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


def test_live_stage_prompts_describe_the_supported_runtime() -> None:
    from tests.plane2.test_crewai_boundary import _request

    from cloudeq.plane2_agents.agents.crewai_live import _description
    from cloudeq.plane2_agents.models import StageName

    for stage in StageName:
        prompt = _description(_request(stage))
        assert "only supported test command is exactly python -m pytest" in prompt
        if stage is StageName.TESTING:
            assert 'test_commands=["python -m pytest"]' in prompt
        elif stage is StageName.DEVELOPMENT:
            assert "implementation AND test_*.py" in prompt
            assert "Python 3.11, pytest, and Flask 3.1.3" in prompt
        else:
            assert "files=[] and test_commands=[]" in prompt


@pytest.mark.parametrize("code", [429, 503, 403])
def test_provider_error_reports_status_without_secret_text(code: int) -> None:
    from cloudeq.plane2_agents.agents.crewai_live import _provider_failure_message

    class ProviderFailure(Exception):
        def __init__(self) -> None:
            super().__init__("private-api-key-and-request-body")
            self.code = code

    outer = RuntimeError("wrapper")
    outer.__cause__ = ProviderFailure()
    message = _provider_failure_message(outer)
    assert str(code) in message
    assert "private-api-key" not in message
