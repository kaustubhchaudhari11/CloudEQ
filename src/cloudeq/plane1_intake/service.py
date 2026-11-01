"""Intake decisions shared by the API and the CLI."""

import logging
from datetime import UTC, datetime
from uuid import uuid4

from cloudeq.plane1_intake.adapters import InMemoryTaskHandoff, InMemoryTelemetrySink
from cloudeq.plane1_intake.router.gemini import apply_dataset_catalog_rule, build_router
from cloudeq.plane1_intake.settings import Settings
from cloudeq.shared.contracts.models import (
    DatasetCheck,
    FeasibilityResult,
    FeasibilityStatus,
    HandoffRequest,
    PlaneName,
    RouterKind,
    RoutingRequest,
    SubmissionSource,
    TaskResult,
    TaskStatus,
    TaskSubmission,
    TelemetryEnvelope,
)
from cloudeq.shared.ports.protocols import (
    FeasibilityRouter,
    GeminiTransport,
    TaskHandoff,
    TelemetrySink,
)

logger = logging.getLogger(__name__)


class IntakeService:
    def __init__(
        self,
        *,
        settings: Settings,
        router: FeasibilityRouter,
        sink: TelemetrySink,
        handoff: TaskHandoff,
    ) -> None:
        self.settings = settings
        self.router = router
        self.telemetry = sink
        self.handoff = handoff
        self._tasks: dict[str, TaskResult] = {}

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        transport: GeminiTransport | None = None,
        handoff: TaskHandoff | None = None,
        sink: TelemetrySink | None = None,
    ) -> "IntakeService":
        return cls(
            settings=settings,
            router=build_router(settings, transport),
            sink=sink or InMemoryTelemetrySink(settings.cloudeq_telemetry_max_payload_bytes),
            handoff=handoff or InMemoryTaskHandoff(),
        )

    def submit(
        self,
        submission: TaskSubmission,
        *,
        expected_source: SubmissionSource | None = None,
    ) -> TaskResult:
        trace_id = str(uuid4())
        reasons = self._validation_errors(submission, expected_source=expected_source)
        if reasons:
            result = TaskResult(
                status=TaskStatus.REJECTED,
                trace_id=trace_id,
                reasons=reasons,
                execution_started=False,
            )
            self._emit("intake.submission_rejected", trace_id, None, {"reasons": reasons})
            self._log("submission rejected", result)
            return result

        task_id = str(uuid4())
        prompt = submission.prompt.strip()
        self._emit(
            "intake.submission_accepted",
            trace_id,
            task_id,
            {"source": submission.source.value},
        )
        feasibility = self._route(
            RoutingRequest(
                task_id=task_id,
                trace_id=trace_id,
                prompt=prompt,
                external_ref=submission.external_ref,
            )
        )
        feasibility = apply_dataset_catalog_rule(feasibility, submission.external_ref)
        self._emit(
            "intake.feasibility_routed",
            trace_id,
            task_id,
            {
                "status": feasibility.status.value,
                "dataset_check": feasibility.dataset_check.value,
                "router": feasibility.router.value,
                "model_id": feasibility.model_id,
            },
        )
        if feasibility.status is not FeasibilityStatus.FEASIBLE:
            result = self._store(
                TaskResult(
                    status=TaskStatus.ROUTED,
                    trace_id=trace_id,
                    task_id=task_id,
                    source=submission.source,
                    prompt=prompt,
                    reasons=list(feasibility.reasons),
                    feasibility=feasibility,
                    handoff_accepted=False,
                    execution_started=False,
                )
            )
            self._log("submission routed", result)
            return result

        acknowledgement = self.handoff.submit(
            HandoffRequest(
                task_id=task_id,
                trace_id=trace_id,
                prompt=prompt,
                feasibility=feasibility,
            )
        )
        if (
            not acknowledgement.accepted
            or acknowledgement.execution_started
            or acknowledgement.task_id != task_id
            or acknowledgement.trace_id != trace_id
        ):
            if acknowledgement.execution_started:
                handoff_reason = "Handoff reported execution, which Plane 1 cannot claim."
            elif acknowledgement.task_id != task_id or acknowledgement.trace_id != trace_id:
                handoff_reason = (
                    "Handoff acknowledgement did not match the task and trace identifiers."
                )
            else:
                handoff_reason = "Plane 2 did not accept the handoff. Execution did not start."
            result = self._store(
                TaskResult(
                    status=TaskStatus.ROUTED,
                    trace_id=trace_id,
                    task_id=task_id,
                    source=submission.source,
                    prompt=prompt,
                    reasons=[*feasibility.reasons, handoff_reason],
                    feasibility=feasibility,
                    handoff_accepted=False,
                    execution_started=False,
                )
            )
            self._log("handoff refused", result)
            return result

        self._emit("intake.task_handed_off", trace_id, task_id, {"execution_started": False})
        result = self._store(
            TaskResult(
                status=TaskStatus.HANDED_OFF,
                trace_id=trace_id,
                task_id=task_id,
                source=submission.source,
                prompt=prompt,
                reasons=list(feasibility.reasons),
                feasibility=feasibility,
                handoff_accepted=True,
                execution_started=False,
            )
        )
        self._log("task handed off", result)
        return result

    def reject_invalid(self, reasons: list[str]) -> TaskResult:
        trace_id = str(uuid4())
        cleaned = reasons or ["invalid request"]
        result = TaskResult(
            status=TaskStatus.REJECTED,
            trace_id=trace_id,
            reasons=cleaned,
            execution_started=False,
        )
        self._emit("intake.submission_rejected", trace_id, None, {"reasons": cleaned})
        self._log("submission rejected", result)
        return result

    def get(self, task_id: str) -> TaskResult | None:
        return self._tasks.get(task_id)

    def _route(self, request: RoutingRequest) -> FeasibilityResult:
        try:
            return self.router.evaluate(request)
        except Exception:
            logger.exception(
                "feasibility router failed",
                extra={"trace_id": request.trace_id, "task_id": request.task_id},
            )
            kind = (
                RouterKind.GEMINI
                if self.settings.cloudeq_router_mode == "gemini"
                else RouterKind.OFFLINE
            )
            return FeasibilityResult(
                status=FeasibilityStatus.ERROR,
                dataset_check=DatasetCheck.NOT_APPLICABLE,
                reasons=["Feasibility router failed before returning a decision."],
                router=kind,
                model_id=self.settings.gemini_router_model.strip(),
            )

    def _validation_errors(
        self,
        submission: TaskSubmission,
        *,
        expected_source: SubmissionSource | None,
    ) -> list[str]:
        reasons: list[str] = []
        if expected_source is not None and submission.source is not expected_source:
            reasons.append(f"source must be {expected_source.value}")
        if submission.prompt.strip() == "":
            reasons.append("prompt must not be empty")
        if (
            submission.source is SubmissionSource.GITHUB_ISSUES
            and not self.settings.cloudeq_github_issues_enabled
        ):
            reasons.append("GitHub Issues intake is disabled")
        if submission.source is SubmissionSource.JIRA and not self.settings.cloudeq_jira_enabled:
            reasons.append("Jira intake is disabled")
        return reasons

    def _store(self, result: TaskResult) -> TaskResult:
        if result.task_id is not None:
            self._tasks[result.task_id] = result
        return result

    def _emit(
        self,
        event_name: str,
        trace_id: str,
        task_id: str | None,
        payload: dict[str, object],
    ) -> None:
        envelope = TelemetryEnvelope(
            event_id=str(uuid4()),
            trace_id=trace_id,
            source=PlaneName.PLANE1_INTAKE,
            event_name=event_name,
            occurred_at=datetime.now(UTC),
            payload=payload,
            task_id=task_id,
        )
        self.telemetry.emit(envelope)

    def _log(self, message: str, result: TaskResult) -> None:
        logger.info(
            message,
            extra={
                "trace_id": result.trace_id,
                "task_id": result.task_id or "-",
                "status": result.status.value,
            },
        )
