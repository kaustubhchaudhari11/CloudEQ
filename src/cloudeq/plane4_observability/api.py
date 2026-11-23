"""Analysis layer: HTTP read API. Grafana reads it through the Infinity data source.

Grafana never receives the MongoDB URI; it only sees these JSON endpoints.
"""

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from cloudeq.plane4_observability.factory import ObservabilityStack
from cloudeq.plane4_observability.normalizer import OfflineNormalizer
from cloudeq.plane4_observability.records import NormalizationStatus


def build_router(stack: ObservabilityStack) -> APIRouter:
    router = APIRouter()
    pipeline = stack.pipeline
    store = stack.store

    @router.get("/observability/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "plane": "plane4_observability",
            **stack.describe(),
            "sink_delivered": stack.sink.delivered,
            "sink_undelivered": len(stack.sink.undelivered),
            "pipeline_counters": dict(pipeline.counters),
        }

    @router.get("/observability/metrics")
    def metrics() -> dict[str, Any]:
        return pipeline.metrics()

    @router.get("/observability/events/raw")
    def raw_events(
        trace_id: str | None = None, status: str | None = None, limit: int = 200
    ) -> JSONResponse:
        wanted = NormalizationStatus(status) if status else None
        rows = store.list_raw(trace_id=trace_id, status=wanted, limit=_limit(limit))
        return JSONResponse([r.model_dump(mode="json") for r in rows])

    @router.get("/observability/events/canonical")
    def canonical_events(trace_id: str | None = None, limit: int = 200) -> JSONResponse:
        rows = store.list_canonical(trace_id=trace_id, limit=_limit(limit))
        return JSONResponse([c.model_dump(mode="json", by_alias=True) for c in rows])

    @router.get("/observability/traces/{trace_id}")
    def trace(trace_id: str) -> dict[str, Any]:
        return pipeline.trace(trace_id)

    @router.get("/observability/attempts")
    def attempts(event_id: str | None = None, limit: int = 200) -> JSONResponse:
        rows = store.list_attempts(event_id=event_id, limit=_limit(limit))
        return JSONResponse([a.model_dump(mode="json") for a in rows])

    @router.post("/observability/ingest")
    async def ingest(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except ValueError:
            body = (await request.body()).decode("utf-8", errors="replace")
        envelope = stack.sink.emit_external(body)
        raw = store.get_raw(envelope.event_id)
        return JSONResponse(
            status_code=202,
            content={
                "event_id": envelope.event_id,
                "trace_id": envelope.trace_id,
                "raw_retained": raw is not None,
                "normalization_status": raw.normalization_status.value if raw else "queued",
                "last_error": raw.last_error if raw else None,
            },
        )

    @router.post("/observability/retry")
    def retry(normalizer: str = "configured", limit: int = 100) -> dict[str, int]:
        chosen = OfflineNormalizer() if normalizer == "offline" else None
        return pipeline.retry_failed(limit=_limit(limit), normalizer=chosen)

    # Flat tables for Grafana Infinity (no root selector needed).
    @router.get("/observability/grafana/events-per-minute")
    def g_events_per_minute() -> JSONResponse:
        return JSONResponse(pipeline.metrics()["events_per_minute"])

    @router.get("/observability/grafana/events-by-plane")
    def g_by_plane() -> JSONResponse:
        data = pipeline.metrics()["events_by_plane"]
        return JSONResponse([{"plane": k, "events": v} for k, v in data.items()])

    @router.get("/observability/grafana/status")
    def g_status() -> JSONResponse:
        m = pipeline.metrics()
        rows = [
            {"group": "canonical", "status": k, "count": v}
            for k, v in m["canonical_status"].items()
        ]
        rows += [
            {"group": "normalization", "status": k, "count": v}
            for k, v in m["normalization"].items()
            if k != "success_rate"
        ]
        return JSONResponse(rows)

    @router.get("/observability/grafana/repairs")
    def g_repairs() -> JSONResponse:
        data = pipeline.metrics()["repair_iterations_by_trace"]
        return JSONResponse([{"trace_id": k, "iterations": v} for k, v in data.items()])

    @router.get("/observability/grafana/canonical")
    def g_canonical(limit: int = 500) -> JSONResponse:
        rows = store.list_canonical(limit=_limit(limit))
        return JSONResponse(
            [
                {
                    "timestamp": c.timestamp,
                    "trace_id": c.trace_id,
                    "task_id": c.task_id,
                    "plane": c.source_plane,
                    "job": c.job,
                    "status": c.status,
                    "latency_ms": c.latency_ms,
                    "message": c.message,
                }
                for c in rows
            ]
        )

    return router


def _limit(value: int) -> int:
    return max(1, min(int(value), 5000))
