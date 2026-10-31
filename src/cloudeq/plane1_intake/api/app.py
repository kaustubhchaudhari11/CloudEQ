"""FastAPI intake. Status values describe routing, not code execution."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from cloudeq.plane1_intake.logging import configure_logging
from cloudeq.plane1_intake.service import IntakeService
from cloudeq.plane1_intake.settings import load_settings
from cloudeq.shared.contracts.models import SubmissionSource, TaskResult, TaskStatus, TaskSubmission


def create_app(service: IntakeService | None = None) -> FastAPI:
    intake = service or IntakeService.from_settings(load_settings())
    configure_logging(intake.settings.cloudeq_log_level)
    app = FastAPI(title="FORGE SPAN", version="0.1.0")
    app.state.intake = intake

    @app.get("/health")
    def health() -> dict[str, object]:
        return {
            "status": "ok",
            "service": "FORGE SPAN",
            "team": "Cloud EQ",
            "plane": "plane1_intake",
            "router_mode": intake.settings.cloudeq_router_mode,
            "live_gemini_calls": intake.settings.cloudeq_gemini_live_calls,
            "execution_available": False,
        }

    @app.post("/tasks")
    def create_task(body: TaskSubmission) -> JSONResponse:
        return _json(intake.submit(body, expected_source=SubmissionSource.API))

    @app.get("/tasks/{task_id}")
    def read_task(task_id: str) -> JSONResponse:
        found = intake.get(task_id)
        if found is None:
            return JSONResponse(status_code=404, content={"detail": "task not found"})
        return JSONResponse(status_code=200, content=found.model_dump(mode="json"))

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return _json(intake.reject_invalid(_validation_reasons(exc)))

    return app


def _json(result: TaskResult) -> JSONResponse:
    status_code = 422 if result.status is TaskStatus.REJECTED else 200
    return JSONResponse(status_code=status_code, content=result.model_dump(mode="json"))


def _validation_reasons(exc: RequestValidationError) -> list[str]:
    reasons: list[str] = []
    for error in exc.errors():
        location = [str(part) for part in error.get("loc", ()) if part != "body"]
        message = str(error.get("msg", "invalid request"))
        prefix = ".".join(location)
        reasons.append(f"{prefix}: {message}" if prefix else message)
    return reasons or ["invalid request"]


app = create_app()
