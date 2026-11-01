"""Plane 2 implementation of the shared task-handoff port.

Accepting a handoff stores the supervised run. It does not tell Plane 1 that
live agents or generated code executed.
"""

from cloudeq.plane2_agents.models import AgentRunResult, RepairState
from cloudeq.plane2_agents.supervisor import Supervisor
from cloudeq.shared.contracts.models import HandoffAcknowledgement, HandoffRequest


class SupervisingHandoff:
    def __init__(self, supervisor: Supervisor) -> None:
        self.supervisor = supervisor
        self.results: dict[str, AgentRunResult] = {}

    def submit(self, handoff: HandoffRequest) -> HandoffAcknowledgement:
        result = self.supervisor.run(handoff)
        self.results[handoff.task_id] = result
        refused = result.state is RepairState.ERROR and not result.stages and not result.iterations
        return HandoffAcknowledgement(
            task_id=handoff.task_id,
            trace_id=handoff.trace_id,
            accepted=not refused,
            execution_started=False,
        )
