"""Platform-level settings and ``.env`` loading."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from cloudeq.shared.dotenv import load_dotenv

__all__ = ["PlatformSettings", "load_dotenv"]


class PlatformSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    # simulation: offline agent engine + offline runtime simulation (runs anywhere).
    # docker: template (or live Gemini) stage client + real Docker sandbox.
    cloudeq_execution_mode: Literal["simulation", "docker", "render"] = "simulation"
    cloudeq_runs_file: str = "~/.cloudeq/runs.jsonl"
    cloudeq_repair_max_iterations: int = Field(default=3, ge=1, le=10)
    cloudeq_api_host: str = "127.0.0.1"
    cloudeq_api_port: int = 8000
    cloudeq_log_level: str = "INFO"
