"""Records kept by the observability plane.

``CanonicalEvent`` follows the canonical event schema in the FOAP paper (Table 4)
and adds linkage fields (``event_id``, ``trace_id``) plus schema version and
normalization provenance so a canonical row can always be traced to its raw row.
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NormalizationStatus(StrEnum):
    PENDING = "pending"
    NORMALIZED = "normalized"
    FAILED = "failed"


class EntityRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_type: str
    entity_id: str


class RawRecord(BaseModel):
    """An accepted event, stored before normalization is attempted."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    trace_id: str
    task_id: str | None = None
    source: str
    event_name: str
    occurred_at: str
    ingested_at: str
    envelope: dict[str, Any]
    raw: str
    redactions: int = 0
    normalization_status: NormalizationStatus = NormalizationStatus.PENDING
    normalization_attempts: int = 0
    last_error: str | None = None


class CanonicalEvent(BaseModel):
    """FOAP Table 4 canonical fields plus FORGE SPAN linkage and provenance."""

    model_config = ConfigDict(extra="forbid")

    # Linkage and provenance
    event_id: str
    trace_id: str
    schema_version: str
    normalizer: str
    normalizer_model: str = ""
    source_plane: str = ""

    # Entity
    actor_entity: EntityRef | None = None
    target_entity: EntityRef | None = None
    data_entity: EntityRef | None = None
    destination_entity: EntityRef | None = None
    human_id: str | None = None

    # Classification
    event_type: str
    action: str
    job: str

    # Traceability
    task_id: str | None = None
    tool_name: str | None = None
    tool_invocation_id: str | None = None
    span_id: str | None = None
    parent_span_id: str | None = None

    # Operational
    status: str = Field(pattern="^(SUCCESS|FAILED|ERROR)$")
    message: str = ""
    timestamp: str = Field(serialization_alias="Timestamp")
    ingest_timestamp: str = Field(serialization_alias="ingestTimestamp")
    latency_ms: float | None = None
    data_size_kb: float | None = None

    # Control
    success: bool
    error_code: str | None = None
    parse_error: bool = Field(default=False, serialization_alias="parseError")
    raw: str


class NormalizationAttempt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attempt_id: str
    event_id: str
    trace_id: str
    attempt: int
    normalizer: str
    status: NormalizationStatus
    error: str | None = None
    at: str
