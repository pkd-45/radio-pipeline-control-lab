from __future__ import annotations

import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from conftest import write_config

from radio_pipeline_lab.adapters.etcd import EtcdV3CoordinationStore
from radio_pipeline_lab.adapters.kafka import KafkaEventPublisher
from radio_pipeline_lab.config import load_config
from radio_pipeline_lab.control import InMemoryCoordinationStore, PipelineControlService
from radio_pipeline_lab.events import PipelineEvent
from radio_pipeline_lab.executor import PipelineExecutor


class CapturingPublisher:
    def __init__(self) -> None:
        self.events: list[PipelineEvent] = []

    def publish(self, event: PipelineEvent) -> None:
        self.events.append(event)


def test_control_service_updates_state_and_reports_progress(tmp_path: Path) -> None:
    config = load_config(write_config(tmp_path))
    publisher = CapturingPublisher()
    coordination = InMemoryCoordinationStore()
    service = PipelineControlService(PipelineExecutor(config), coordination, publisher)
    status = service.start()
    assert status.state == "SUCCEEDED"
    assert status.completed_stages == status.total_stages == 5
    assert publisher.events[0].event == "control_start_requested"
    assert publisher.events[-1].event == "control_run_succeeded"


class FakeProducer:
    def __init__(self) -> None:
        self.records: list[tuple[str, str, str]] = []
        self.flushed = False

    def produce(self, topic: str, *, key: str, value: str) -> None:
        self.records.append((topic, key, value))

    def poll(self, timeout: float) -> int:
        return 0

    def flush(self, timeout: float) -> int:
        self.flushed = True
        return 0


def test_kafka_adapter_serialises_event_deterministically() -> None:
    fake = FakeProducer()
    adapter = KafkaEventPublisher(topic="telemetry", producer=fake)
    event = PipelineEvent("2026-01-01T00:00:00+00:00", "run-1", "started", None, {"b": 2, "a": 1})
    adapter.publish(event)
    adapter.close()
    assert fake.records[0][0:2] == ("telemetry", "run-1")
    decoded = json.loads(fake.records[0][2])
    assert decoded == {
        "event": "started",
        "payload": {"a": 1, "b": 2},
        "run_id": "run-1",
        "stage": None,
        "timestamp": "2026-01-01T00:00:00+00:00",
    }
    assert fake.flushed is True


class EtcdHandler(BaseHTTPRequestHandler):
    values: dict[str, str] = {}

    def do_POST(self) -> None:  # noqa: N802
        size = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(size).decode("utf-8"))
        key = base64.b64decode(payload["key"]).decode("utf-8")
        if self.path == "/v3/kv/put":
            self.values[key] = payload["value"]
            response = {"header": {"revision": "1"}}
        elif self.path == "/v3/kv/range":
            value = self.values.get(key)
            response = {"kvs": [] if value is None else [{"value": value}]}
        else:
            self.send_error(404)
            return
        encoded = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: Any) -> None:
        return


def test_etcd_adapter_uses_real_http_boundary() -> None:
    EtcdHandler.values = {}
    server = ThreadingHTTPServer(("127.0.0.1", 0), EtcdHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        store = EtcdV3CoordinationStore(f"http://127.0.0.1:{server.server_port}")
        assert store.get("/missing") is None
        store.put("/runs/one/state", "RUNNING")
        assert store.get("/runs/one/state") == "RUNNING"
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()
