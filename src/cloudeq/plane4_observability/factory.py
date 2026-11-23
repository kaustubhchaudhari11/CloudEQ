"""Build the observability stack from settings. Only this module picks concrete adapters."""

from dataclasses import dataclass

from cloudeq.plane4_observability.bus import EventBus, InProcessBus, KafkaBus
from cloudeq.plane4_observability.normalizer import (
    GeminiNormalizer,
    GenerateFn,
    Normalizer,
    OfflineNormalizer,
    gemini_http_generate,
)
from cloudeq.plane4_observability.pipeline import ObservabilityPipeline
from cloudeq.plane4_observability.settings import ObservabilitySettings
from cloudeq.plane4_observability.sink import FederatedTelemetrySink
from cloudeq.plane4_observability.storage import MemoryStore, ObservabilityStore, SQLiteStore


@dataclass
class ObservabilityStack:
    settings: ObservabilitySettings
    store: ObservabilityStore
    bus: EventBus
    pipeline: ObservabilityPipeline
    sink: FederatedTelemetrySink

    def describe(self) -> dict[str, object]:
        raw_days, canonical_days = self.settings.retention_days()
        return {
            "bus": self.bus.name,
            "store": self.store.backend,
            "normalizer": self.pipeline.normalizer.name,
            "normalizer_model": self.pipeline.normalizer.model_id,
            "schema_version": self.pipeline.schema_version,
            "raw_retention_days": raw_days,
            "canonical_retention_days": canonical_days,
            "deletion_enabled": raw_days is not None or canonical_days is not None,
        }

    def close(self) -> None:
        self.bus.close()
        self.store.close()


def build_store(settings: ObservabilitySettings) -> ObservabilityStore:
    if settings.cloudeq_observability_store == "memory":
        return MemoryStore()
    if settings.cloudeq_observability_store == "mongodb":
        from cloudeq.plane4_observability.storage.mongo import MongoStore

        return MongoStore(settings)
    return SQLiteStore(settings.cloudeq_observability_sqlite_path)


def build_normalizer(
    settings: ObservabilitySettings, *, generate: GenerateFn | None = None
) -> Normalizer:
    if settings.gemini_normalizer_ready() is not None:
        return OfflineNormalizer()
    model = settings.gemini_normalizer_model.strip()
    caller = generate or gemini_http_generate(
        api_base=settings.gemini_api_base,
        api_key=settings.gemini_api_key,
        timeout_seconds=settings.cloudeq_gemini_timeout_seconds,
    )
    return GeminiNormalizer(model_id=model, generate=caller)


def build_bus(settings: ObservabilitySettings, *, start_consumer: bool = True) -> EventBus:
    if settings.cloudeq_telemetry_bus == "kafka":
        return KafkaBus(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            topic=settings.kafka_telemetry_topic,
            group_id=settings.kafka_consumer_group,
            max_retries=settings.cloudeq_kafka_max_retries,
            start_consumer=start_consumer,
        )
    return InProcessBus()


def build_observability(
    settings: ObservabilitySettings | None = None,
    *,
    store: ObservabilityStore | None = None,
    bus: EventBus | None = None,
    normalizer: Normalizer | None = None,
    consume: bool = True,
) -> ObservabilityStack:
    chosen = settings or ObservabilitySettings()
    store = store or build_store(chosen)
    bus = bus or build_bus(chosen, start_consumer=consume)
    pipeline = ObservabilityPipeline(
        store,
        normalizer or build_normalizer(chosen),
        schema_version=chosen.cloudeq_canonical_schema_version,
        max_payload_bytes=chosen.cloudeq_telemetry_max_payload_bytes,
        retention_days=chosen.retention_days(),
    )
    if consume:
        bus.subscribe(pipeline.ingest)
    sink = FederatedTelemetrySink(bus, max_payload_bytes=chosen.cloudeq_telemetry_max_payload_bytes)
    return ObservabilityStack(chosen, store, bus, pipeline, sink)
