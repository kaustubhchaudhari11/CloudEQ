"""Plane 2 settings. This module does not import Plane 1."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    cloudeq_repair_max_iterations: int = 3
    cloudeq_agent_engine: Literal["offline", "crewai"] = "offline"
    cloudeq_agents_config: str = ""
