from __future__ import annotations

import json
from dataclasses import asdict
from typing import Protocol

from ..events import PipelineEvent


class ProducerLike(Protocol):
    def produce(self, topic: str, *, key: str, value: str) -> object: ...

    def poll(self, timeout: float) -> object: ...

    def flush(self, timeout: float) -> int: ...


class KafkaEventPublisher:
    """Publish pipeline events using a supplied or confluent-kafka Producer."""

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        topic: str = "radio-pipeline.telemetry",
        *,
        producer: ProducerLike | None = None,
    ) -> None:
        if producer is None:
            try:
                from confluent_kafka import Producer
            except ImportError as exc:
                raise RuntimeError("Install the 'kafka' optional dependency") from exc
            producer = Producer({"bootstrap.servers": bootstrap_servers})
        self.producer = producer
        self.topic = topic

    def publish(self, event: PipelineEvent) -> None:
        payload = json.dumps(asdict(event), separators=(",", ":"), sort_keys=True)
        self.producer.produce(self.topic, key=event.run_id, value=payload)
        self.producer.poll(0)

    def close(self) -> None:
        remaining = self.producer.flush(10)
        if remaining:
            raise RuntimeError(f"Kafka producer still has {remaining} undelivered message(s)")
