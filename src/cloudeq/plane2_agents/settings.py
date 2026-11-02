"""Plane 2 settings. This module does not import Plane 1."""

import re
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_MODEL_ID = re.compile(r"[A-Za-z0-9._-]{1,128}")


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    cloudeq_repair_max_iterations: int = 3
    cloudeq_agent_engine: Literal["offline", "crewai"] = "offline"
    cloudeq_agents_config: str = ""
    cloudeq_gemini_live_calls: bool = False
    cloudeq_gemini_timeout_seconds: float = Field(default=30, gt=0)
    gemini_api_key: str = ""
    gemini_agent_model: str = ""

    def live_gemini_ready(self) -> str | None:
        """Return a configuration error, or None when a live stage call is allowed."""

        if not self.cloudeq_gemini_live_calls:
            return (
                "Gemini live calls are disabled. Set CLOUDEQ_GEMINI_LIVE_CALLS=true, "
                "GEMINI_API_KEY, and GEMINI_AGENT_MODEL. No model id was guessed."
            )
        if not self.gemini_api_key.strip():
            return "GEMINI_API_KEY is missing. Live CrewAI was not called."
        model_id = self.gemini_agent_model.strip()
        if not model_id:
            return "GEMINI_AGENT_MODEL is missing. No model id was guessed."
        if _MODEL_ID.fullmatch(model_id) is None:
            return "GEMINI_AGENT_MODEL is not a valid model id."
        return None
