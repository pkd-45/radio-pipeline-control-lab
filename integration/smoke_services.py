"""Exercise the Kafka and etcd adapters against real local services."""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from uuid import uuid4

from confluent_kafka import Consumer

from radio_pipeline_lab.adapters.etcd import EtcdV3CoordinationStore
from radio_pipeline_lab.adapters.kafka import KafkaEventPublisher
from radio_pipeline_lab.events import PipelineEvent

KAFKA_BOOTSTRAP_SERVERS = "127.0.0.1:19092"
KAFKA_TOPIC = "radio-pipeline-events"
ETCD_ENDPOINT = "http://127.0.0.1:2379"


def consume_event(run_id: str, timeout_s: float = 20.0) -> dict[str, object]:
    consumer = Consumer(
        {
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
            "group.id": f"radio-pipeline-smoke-{uuid4()}",
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
                raise RuntimeError("Kafka message value was not bytes")

            decoded = json.loads(value.decode("utf-8"))

            if decoded.get("run_id") == run_id:
                return decoded
    finally:
        consumer.close()

    raise TimeoutError(f"Did not receive Kafka event for run_id={run_id}")


def main() -> None:
    run_id = f"integration-smoke-{uuid4()}"

    event = PipelineEvent(
        timestamp=datetime.now(UTC).isoformat(),
        run_id=run_id,
        event="integration_services_checked",
        stage=None,
        payload={
            "kafka": "real-service",
            "etcd": "real-service",
        },
    )

    publisher = KafkaEventPublisher(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        topic=KAFKA_TOPIC,
    )
    publisher.publish(event)
    publisher.close()

    received = consume_event(run_id)

    if received["event"] != event.event:
        raise AssertionError(
            f"Unexpected event: {received['event']!r}"
        )

    coordination = EtcdV3CoordinationStore(ETCD_ENDPOINT)
    key = f"/radio-pipeline-lab/smoke/{run_id}/state"

    coordination.put(key, "SUCCEEDED")
    stored_state = coordination.get(key)

    if stored_state != "SUCCEEDED":
        raise AssertionError(
            f"Unexpected etcd value: {stored_state!r}"
        )

    result = {
        "run_id": run_id,
        "kafka_event_received": True,
        "kafka_event": received["event"],
        "etcd_key": key,
        "etcd_value": stored_state,
    }

    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
