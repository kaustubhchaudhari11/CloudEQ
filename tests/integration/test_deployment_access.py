from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cloudeq.plane4_observability.factory import build_observability
from cloudeq.plane4_observability.settings import ObservabilitySettings
from cloudeq.platform.server import create_app
from cloudeq.platform.service import Platform


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("CLOUDEQ_REQUIRE_AUTH", "true")
    monkeypatch.setenv("CLOUDEQ_WEB_PASSWORD", "test-password-long-enough")
    stack = build_observability(ObservabilitySettings(cloudeq_observability_store="memory"))
    return TestClient(create_app(Platform(observability=stack, runs_file=tmp_path / "runs.jsonl")))


@pytest.mark.parametrize(
    "path", ["/", "/api/config", "/api/runs", "/observability/metrics", "/docs"]
)
def test_public_endpoints_require_login(client: TestClient, path: str) -> None:
    assert client.get(path).status_code == 401
    assert client.get(path, auth=("forge", "wrong")).status_code == 401
    assert client.get(path, auth=("forge", "test-password-long-enough")).status_code == 200


def test_health_is_public_but_does_not_leak_configuration(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok", "service": "FORGE SPAN"}


def test_anonymous_post_cannot_spend_model_allowance(client: TestClient) -> None:
    assert client.post("/api/runs", json={"prompt": "Build something"}).status_code == 401


def test_cross_origin_submission_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/runs",
        json={"prompt": "Hello"},
        auth=("forge", "test-password-long-enough"),
        headers={"Origin": "https://unrelated.example"},
    )
    assert response.status_code == 403
