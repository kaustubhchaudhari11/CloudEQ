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
    return TestClient(
        create_app(Platform(observability=stack, runs_file=tmp_path / "runs.jsonl")),
        base_url="https://testserver",
    )


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


def test_browser_sign_in_session_and_logout(client: TestClient) -> None:
    page = client.get("/", headers={"Accept": "text/html"})
    assert page.status_code == 200
    assert page.url.path == "/login"
    assert 'type="password"' in page.text
    wrong = client.post("/login", data={"username": "forge", "password": "wrong"})
    assert wrong.status_code == 401
    assert "forge_session" not in client.cookies
    login = client.post(
        "/login",
        data={"username": "forge", "password": "test-password-long-enough"},
        follow_redirects=False,
    )
    assert login.status_code == 303
    cookie = login.headers["set-cookie"]
    assert "Secure" in cookie and "HttpOnly" in cookie and "SameSite=strict" in cookie
    assert "test-password-long-enough" not in cookie
    assert client.get("/api/config").status_code == 200
    assert client.post("/logout", follow_redirects=False).status_code == 303
    assert client.get("/api/config").status_code == 401


def test_tampered_and_expired_session_denied(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from itsdangerous import TimestampSigner

    with monkeypatch.context() as patch:
        patch.setattr(TimestampSigner, "get_timestamp", lambda self: 1)
        client.post("/login", data={"username": "forge", "password": "test-password-long-enough"})
    assert client.get("/api/config").status_code == 401
    client.cookies.clear()
    client.cookies.set("forge_session", "forged-cookie")
    assert client.get("/api/config").status_code == 401


def test_login_rejects_cross_origin_and_large_requests(client: TestClient) -> None:
    assert (
        client.post(
            "/login",
            data={"username": "forge", "password": "test-password-long-enough"},
            headers={"Origin": "https://unrelated.example"},
        ).status_code
        == 403
    )
    assert client.post("/login", content=b"x" * 4097).status_code == 413
