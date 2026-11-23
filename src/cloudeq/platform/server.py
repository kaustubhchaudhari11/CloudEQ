"""FORGE SPAN web server: dashboard, run API, Plane 1 contract, and Plane 4 read API.

Start with:  uv run cloudeq-server        (then open http://127.0.0.1:8000)
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib import resources
from typing import Any, Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from cloudeq.plane1_intake.logging import configure_logging
from cloudeq.plane4_observability.api import build_router
from cloudeq.platform.access import AccessSettings, DeploymentAccess
from cloudeq.platform.service import Platform, docker_available
from cloudeq.shared.contracts.models import TaskStatus, TaskSubmission


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(max_length=4000)
    dataset: str | None = None
    simulated_failures: int = Field(default=0, ge=0, le=10)
    run_variant: Literal["configured", "template"] = "configured"


def _dashboard() -> str:
    return resources.files("cloudeq.platform").joinpath("web/index.html").read_text("utf-8")


def create_app(platform: Platform | None = None) -> FastAPI:
    core = platform or Platform()
    configure_logging(core.settings.cloudeq_log_level)

    @asynccontextmanager
    async def lifespan(_app: Any) -> AsyncIterator[None]:
        yield
        core.observability.close()

    app = FastAPI(title="FORGE SPAN", version="0.2.0", lifespan=lifespan)
    access = AccessSettings()
    if access.cloudeq_require_auth:
        app.add_middleware(DeploymentAccess, settings=access)
    app.state.platform = core

    @app.get("/")
    def index() -> HTMLResponse:
        return HTMLResponse(_dashboard())

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "FORGE SPAN",
            "team": "Cloud EQ",
            "planes": ["plane1_intake", "plane2_agents", "plane3_runtime", "plane4_observability"],
            **core.describe(),
            "docker_engine_available": docker_available() if core.mode == "docker" else None,
        }

    @app.get("/api/config")
    def config() -> dict[str, Any]:
        return core.describe()

    @app.post("/api/runs")
    def create_run(body: RunRequest) -> JSONResponse:
        record = core.run(
            body.prompt,
            dataset=body.dataset,
            simulated_failures=body.simulated_failures,
            use_template=body.run_variant == "template",
        )
        code = 422 if record["outcome"] == TaskStatus.REJECTED.value else 200
        return JSONResponse(status_code=code, content=record)

    @app.get("/api/runs")
    def list_runs(limit: int = 50) -> JSONResponse:
        return JSONResponse(core.list_runs(max(1, min(limit, 500))))

    @app.get("/api/runs/{task_id}")
    def read_run(task_id: str) -> JSONResponse:
        found = core.get_run(task_id)
        if found is None:
            return JSONResponse(status_code=404, content={"detail": "run not found"})
        return JSONResponse(found)

    # Plane 1 contract (same body as cloudeq.plane1_intake.api). Here the handoff runs agents.
    @app.post("/tasks")
    def create_task(body: TaskSubmission) -> JSONResponse:
        record = core.run(body.prompt, dataset=(body.external_ref or {}).get("dataset"))
        intake = record["intake"]
        code = 422 if intake["status"] == TaskStatus.REJECTED.value else 200
        return JSONResponse(
            status_code=code, content={**intake, "agent_outcome": record["outcome"]}
        )

    @app.exception_handler(RequestValidationError)
    async def invalid(_request: Request, exc: RequestValidationError) -> JSONResponse:
        reasons = []
        for error in exc.errors():
            where = ".".join(str(p) for p in error.get("loc", ()) if p != "body")
            reasons.append(f"{where}: {error.get('msg')}" if where else str(error.get("msg")))
        return JSONResponse(status_code=422, content={"status": "rejected", "reasons": reasons})

    app.include_router(build_router(core.observability))
    return app


def main(argv: list[str] | None = None) -> int:
    import argparse

    import uvicorn

    from cloudeq.platform.settings import PlatformSettings, load_dotenv

    load_dotenv()
    settings = PlatformSettings()
    parser = argparse.ArgumentParser(prog="cloudeq-server", description="Run the FORGE SPAN UI")
    parser.add_argument("--host", default=settings.cloudeq_api_host)
    parser.add_argument("--port", type=int, default=settings.cloudeq_api_port)
    args = parser.parse_args(argv)
    print(f"FORGE SPAN dashboard: http://{args.host}:{args.port}")
    uvicorn.run(create_app(), host=args.host, port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
