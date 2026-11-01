"""CrewAI boundary. This module does not import CrewAI and does not call it.

The default engine is the offline simulation. Selecting this adapter records
that a live crew was not started.
"""

from cloudeq.plane2_agents.models import AgentTeam


class CrewAINotExecuted(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class CrewAIAdapter:
    """Prepares role names from agents.yaml and refuses to call kickoff."""

    live_crewai = False
    live_gemini = False

    def prepare_roles(self, team: AgentTeam) -> list[str]:
        return [role.name.value for role in team.roles]

    def execute(self, team: AgentTeam) -> None:
        prepared = ", ".join(self.prepare_roles(team))
        raise CrewAINotExecuted(
            "Live CrewAI kickoff was not run. "
            f"Prepared roles: {prepared}. "
            "Install CrewAI and an explicit model in a later session before claiming "
            "a live crew. This result is not an offline simulation of success."
        )
