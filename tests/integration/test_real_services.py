"""Integration tests requiring real Kafka and etcd services."""

from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from radio_pipeline_lab.adapters.etcd import EtcdV3CoordinationStore
from radio_pipeline_lab.adapters.kafka import KafkaEventPublisher
from radio_pipeline_lab.events import PipelineEvent

pytestmark = pytest.mark.integration

if os.getenv("RUN_SERVICE_INTEGRATION") != "1":
    pytest.skip(
        "Set RUN_SERVICE_INTEGRATION=1 to run service-backed tests",
        allow_module_level=True,
    )

KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "127.0.0.1:19092",
)
KAFKA_TOPIC = os.getenv(
    "KAFKA_TOPIC",
    "radio-pipeline-events",
)
ETCD_ENDPOINT = os.getenv(
    "ETCD_ENDPOINT",
    "http://127.0.0.1:2379",
)


def consume_event(
    run_id: str,
    timeout_s: float = 20.0,
) -> dict[str, object]:
    """Consume the event belonging to the supplied unique run ID."""

    from confluent_kafka import Consumer

    consumer = Consumer(
        {
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
            "group.id": f"radio-pipeline-integration-{uuid4()}",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )
    consumer.subscribe([KAFKA_TOPIC])

    deadline = time.monotonic() + timeout_s

    try:
        while time.monotonic() < deadline:
            message = consumer.poll(1.0)

            if message is None:
                continue

            if message.error():
                raise RuntimeError(f"Kafka consumer error: {message.error()}")

            value = message.value()

            if not isinstance(value, bytes):
                continue

            decoded = json.loads(value.decode("utf-8"))

            if isinstance(decoded, dict) and decoded.get("run_id") == run_id:
                return decoded
    finally:
        consumer.close()

    raise TimeoutError(f"Did not receive Kafka event for run_id={run_id}")


def test_real_kafka_and_etcd_services() -> None:
    """Publish a Kafka event and persist matching run state in etcd."""

    run_id = f"integration-test-{uuid4()}"

    event = PipelineEvent(
        timestamp=datetime.now(UTC).isoformat(),
        run_id=run_id,
        event="real_services_verified",
        stage="integration",
        payload={
            "kafka": "redpanda",
            "etcd": "v3-json-gateway",
        },
    )

    publisher = KafkaEventPublisher(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        topic=KAFKA_TOPIC,
    )
    publisher.publish(event)
    publisher.close()

    received = consume_event(run_id)

    assert received["run_id"] == run_id
    assert received["event"] == "real_services_verified"
    assert received["stage"] == "integration"

    store = EtcdV3CoordinationStore(ETCD_ENDPOINT)
    key = f"/radio-pipeline-lab/integration/{run_id}/state"

    store.put(key, "SUCCEEDED")

    assert store.get(key) == "SUCCEEDED"
