# Kafka and etcd integration lab

This directory contains optional service-backed integrations for the Radio
Pipeline Control Lab.

The core scientific pipeline remains runnable without Kafka or etcd.

## Intended demonstration

- Publish structured pipeline events to a Kafka-compatible broker.
- Consume and inspect pipeline stage transitions.
- Store pipeline coordination state in etcd.
- Use an etcd lease to prevent duplicate execution.
- Preserve JSONL and SQLite as local fallbacks.
- Run integration tests against containerised services.

These integrations demonstrate structured learning and prototype-level
integration. They are not claimed as production observatory infrastructure.

## Services

The integration environment runs:

- Redpanda as a Kafka-compatible event broker.
- etcd as a coordination and state service.
- A one-shot topic initialisation container.

## Running the real-service tests

Start the services:

```bash
docker compose \
  -f integration/docker-compose.yml \
  up -d --wait redpanda etcd
```

Create or verify the Kafka topic:

```bash
docker compose \
  -f integration/docker-compose.yml \
  run --rm topic-init
```

Run the service-backed test:

```bash
RUN_SERVICE_INTEGRATION=1 \
KAFKA_BOOTSTRAP_SERVERS=127.0.0.1:19092 \
KAFKA_TOPIC=radio-pipeline-events \
ETCD_ENDPOINT=http://127.0.0.1:2379 \
pytest tests/integration
```

Stop and remove the disposable environment:

```bash
docker compose \
  -f integration/docker-compose.yml \
  down -v
```

The ordinary test suite skips service-backed integration tests unless
`RUN_SERVICE_INTEGRATION=1` is explicitly set.
