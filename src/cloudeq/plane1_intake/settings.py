"""Process settings. Secrets stay in the environment and out of logs."""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", env_file=None)

    cloudeq_env: str = "development"
    cloudeq_log_level: str = "INFO"
    cloudeq_api_host: str = "127.0.0.1"
    cloudeq_api_port: int = 8000
    cloudeq_router_mode: Literal["offline", "gemini"] = "offline"
    cloudeq_gemini_live_calls: bool = False
    cloudeq_gemini_timeout_seconds: float = Field(default=30, gt=0)
    gemini_api_key: str = ""
    gemini_router_model: str = ""
    gemini_api_base: str = "https://generativelanguage.googleapis.com"
    cloudeq_github_issues_enabled: bool = False
    cloudeq_jira_enabled: bool = False
    cloudeq_telemetry_max_payload_bytes: int = Field(default=1_048_576, gt=0)

    def gemini_calls_enabled(self) -> bool:
        return (
            self.cloudeq_router_mode == "gemini"
            and self.cloudeq_gemini_live_calls
            and bool(self.gemini_api_key.strip())
            and bool(self.gemini_router_model.strip())
        )


class _DotEnvSettings(Settings):
    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
    )


def load_settings() -> Settings:
    if Path(".env").is_file():
        return _DotEnvSettings()
    return Settings()
