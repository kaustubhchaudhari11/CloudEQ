"""Plane 1 handoff reaches the supervisor without claiming live execution."""

from tests.plane1.support import settings

from cloudeq.plane1_intake.service import IntakeService
from cloudeq.plane2_agents.handoff import SupervisingHandoff
from cloudeq.plane2_agents.models import RepairState
from cloudeq.plane2_agents.runtime_sim import OfflineRuntimeSimulation
from cloudeq.plane2_agents.supervisor import Supervisor
from cloudeq.plane2_agents.telemetry import MemoryTelemetrySink
from cloudeq.shared.contracts.models import SubmissionSource, TaskStatus, TaskSubmission


def test_intake_handoff_runs_the_offline_supervisor() -> None:
    sink = MemoryTelemetrySink()
    supervisor = Supervisor(runtime=OfflineRuntimeSimulation(test_outcomes=[True]), sink=sink)
    port = SupervisingHandoff(supervisor)
    intake = IntakeService.from_settings(settings(), handoff=port, sink=sink)
    result = intake.submit(
        TaskSubmission(source=SubmissionSource.API, prompt="Add a health check"),
        expected_source=SubmissionSource.API,
    )
    assert result.status is TaskStatus.HANDED_OFF
    assert result.execution_started is False
    assert result.task_id is not None
    run = port.results[result.task_id]
    assert run.state is RepairState.PASSED
    assert run.trace_id == result.trace_id
    assert run.live_crewai is False
    assert run.simulation is True
    assert run.devops_ran is True
    assert {event.trace_id for event in sink.events} == {result.trace_id}
