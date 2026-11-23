"""Plane 4 settings. Defaults are local and offline: in-process bus, SQLite, offline normalizer."""

import re
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_MODEL_ID = re.compile(r"[A-Za-z0-9._-]{1,128}")


class ObservabilitySettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    # Transport between producers and the processing layer.
    cloudeq_telemetry_bus: Literal["inprocess", "kafka"] = "inprocess"
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_telemetry_topic: str = "cloudeq.telemetry.raw"
    kafka_consumer_group: str = "cloudeq.observability"
    cloudeq_kafka_max_retries: int = Field(default=3, ge=0, le=10)

    # Dual-retention storage. SQLite is the zero-install local default.
    cloudeq_observability_store: Literal["sqlite", "memory", "mongodb"] = "sqlite"
    cloudeq_observability_sqlite_path: str = "~/.cloudeq/observability.sqlite3"
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "cloudeq"
    mongodb_raw_collection: str = "raw_events"
    mongodb_canonical_collection: str = "canonical_events"
    mongodb_normalization_collection: str = "normalization_attempts"

    # Processing layer.
    cloudeq_normalizer_mode: Literal["offline", "gemini"] = "offline"
    cloudeq_gemini_live_calls: bool = False
    cloudeq_gemini_timeout_seconds: float = Field(default=30, gt=0)
    gemini_api_key: str = ""
    gemini_normalizer_model: str = ""
    gemini_api_base: str = "https://generativelanguage.googleapis.com"

    cloudeq_telemetry_max_payload_bytes: int = Field(default=1_048_576, gt=0)
    cloudeq_canonical_schema_version: str = "1"

    # Empty means unresolved: nothing is ever deleted.
    foap_raw_retention_days: str = ""
    foap_canonical_retention_days: str = ""

    def gemini_normalizer_ready(self) -> str | None:
        """Return why live normalization is unavailable, or None when it is allowed."""

        if self.cloudeq_normalizer_mode != "gemini":
            return "CLOUDEQ_NORMALIZER_MODE is offline."
        if not self.cloudeq_gemini_live_calls:
            return "CLOUDEQ_GEMINI_LIVE_CALLS is false."
        if not self.gemini_api_key.strip():
            return "GEMINI_API_KEY is missing."
        model = self.gemini_normalizer_model.strip()
        if not model:
            return "GEMINI_NORMALIZER_MODEL is missing. No model id was guessed."
        if _MODEL_ID.fullmatch(model) is None:
            return "GEMINI_NORMALIZER_MODEL is not a valid model id."
        return None

    def retention_days(self) -> tuple[int | None, int | None]:
        return _days(self.foap_raw_retention_days), _days(self.foap_canonical_retention_days)


def _days(value: str) -> int | None:
    text = value.strip()
    if not text:
        return None
    days = int(text)
    if days < 1:
        raise ValueError("Retention days must be a positive integer or empty.")
    return days
