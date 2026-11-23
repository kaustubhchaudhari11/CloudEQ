"""Streaming / event-driven layers: move accepted envelopes to the processing layer.

``InProcessBus`` delivers synchronously in the same process (local default).
``KafkaBus`` publishes to a Kafka topic with idempotent, acks=all delivery and a
bounded retry count; a consumer commits offsets only after the store accepted the
raw event, so delivery is at-least-once and duplicates are absorbed by
``event_id`` idempotency in the store.
"""

import json
import logging
import threading
import time
from collections.abc import Callable
from typing import Any, Protocol

logger = logging.getLogger(__name__)

Handler = Callable[[dict[str, Any]], object]


class BusDeliveryError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class EventBus(Protocol):
    name: str

    def publish(self, key: str, message: dict[str, Any]) -> None: ...

    def subscribe(self, handler: Handler) -> None: ...

    def close(self) -> None: ...


class InProcessBus:
    name = "inprocess"

    def __init__(self) -> None:
        self._handlers: list[Handler] = []
        self._lock = threading.RLock()
        self.published = 0

    def publish(self, key: str, message: dict[str, Any]) -> None:
        with self._lock:
            self.published += 1
            handlers = list(self._handlers)
        if not handlers:
            raise BusDeliveryError("No consumer is subscribed to the in-process bus.")
        for handler in handlers:
            handler(message)

    def subscribe(self, handler: Handler) -> None:
        with self._lock:
            self._handlers.append(handler)

    def close(self) -> None:
        return None


class KafkaBus:  # pragma: no cover - exercised only against a live broker
    """Kafka transport. Requires the optional ``kafka`` extra (confluent-kafka)."""

    name = "kafka"

    def __init__(
        self,
        *,
        bootstrap_servers: str,
        topic: str,
        group_id: str,
        max_retries: int = 3,
        start_consumer: bool = True,
    ) -> None:
        try:
            from confluent_kafka import Consumer, Producer
        except ImportError as exc:
            raise RuntimeError(
                "Kafka transport needs confluent-kafka. Run: uv sync --extra kafka"
            ) from exc
        self._topic = topic
        self._max_retries = max_retries
        self._producer = Producer(
            {
                "bootstrap.servers": bootstrap_servers,
                "enable.idempotence": True,
                "acks": "all",
                "message.timeout.ms": 10_000,
            }
        )
        self._consumer_class: Any = Consumer
        self._consumer_config: dict[str, Any] = {
            "bootstrap.servers": bootstrap_servers,
            "group.id": group_id,
            "enable.auto.commit": False,
            "auto.offset.reset": "earliest",
        }
        self._handlers: list[Handler] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._start_consumer = start_consumer
        self.published = 0

    def publish(self, key: str, message: dict[str, Any]) -> None:
        value = json.dumps(message, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        errors: list[str] = []

        def delivered(err: object, _msg: object) -> None:
            if err is not None:
                errors.append(str(err))

        for attempt in range(self._max_retries + 1):
            errors.clear()
            try:
                self._producer.produce(
                    self._topic, key=key.encode("utf-8"), value=value, on_delivery=delivered
                )
                remaining = self._producer.flush(10)
            except BufferError as exc:
                errors.append(str(exc))
                remaining = 1
            if remaining == 0 and not errors:
                self.published += 1
                return
            time.sleep(min(2.0, 0.2 * (2**attempt)))
        raise BusDeliveryError(f"Kafka delivery failed after {self._max_retries} retries.")

    def subscribe(self, handler: Handler) -> None:
        self._handlers.append(handler)
        if self._start_consumer and self._thread is None:
            self._thread = threading.Thread(
                target=self._consume, daemon=True, name="kafka-consumer"
            )
            self._thread.start()

    def consume_forever(self) -> None:
        self._consume()

    def _consume(self) -> None:
        consumer = self._consumer_class(self._consumer_config)
        consumer.subscribe([self._topic])
        try:
            while not self._stop.is_set():
                msg = consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    logger.warning("kafka consumer error: %s", msg.error())
                    continue
                try:
                    message = json.loads(msg.value().decode("utf-8"))
                except ValueError:
                    logger.error(
                        "kafka message was not JSON; offset committed to avoid poison loop"
                    )
                    consumer.commit(message=msg, asynchronous=False)
                    continue
                for handler in self._handlers:
                    handler(message)
                consumer.commit(message=msg, asynchronous=False)
        finally:
            consumer.close()

    def close(self) -> None:
        self._stop.set()
        self._producer.flush(5)
