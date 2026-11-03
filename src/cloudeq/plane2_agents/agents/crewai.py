"""Injectable CrewAI boundary for one SDLC stage.

Live kickoff is implemented and stays behind explicit Gemini configuration
plus the container runtime. This module does not execute generated code.
"""

from collections.abc import Callable

from cloudeq.plane2_agents.agents.stage_client import (
    CrewConfigurationError,
    CrewProviderError,
    CrewStageTimeout,
    MalformedStageOutput,
    StageDraft,
    StageRunRequest,
    parse_stage_text,
    require_live_gemini,
)
from cloudeq.plane2_agents.settings import AgentSettings


class CrewAIGeminiStageClient:
    """Call one configured role. An injected kickoff never counts as live."""

    def __init__(
        self,
        settings: AgentSettings,
        *,
        kickoff: Callable[[StageRunRequest], str] | None = None,
    ) -> None:
        self._settings = settings
        self._kickoff = kickoff
        self.uses_live_provider = kickoff is None
        self.live_crewai = False
        self.live_gemini = False

    def run_stage(self, request: StageRunRequest) -> StageDraft:
        require_live_gemini(self._settings)
        raw = self._raw_output(request)
        return parse_stage_text(raw, request)

    def _raw_output(self, request: StageRunRequest) -> str:
        if self._kickoff is not None:
            try:
                return self._kickoff(request)
            except TimeoutError as exc:
                raise CrewStageTimeout("The injected stage call timed out.") from exc
            except (
                MalformedStageOutput,
                CrewStageTimeout,
                CrewProviderError,
                CrewConfigurationError,
            ):
                raise
            except Exception as exc:
                raise CrewProviderError("The stage provider failed.") from exc
        from cloudeq.plane2_agents.agents.crewai_live import live_kickoff

        raw = live_kickoff(self._settings, request)
        self.live_crewai = True
        self.live_gemini = True
        return raw
