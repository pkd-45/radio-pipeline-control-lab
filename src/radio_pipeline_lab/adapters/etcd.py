from __future__ import annotations

import base64
import json
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

JsonObject = dict[str, Any]


class EtcdV3CoordinationStore:
    """Minimal etcd v3 JSON-gateway client for run-state coordination.

    This is a learning adapter, not a high-availability production client. Production work
    would add TLS, authentication, leases, compare-and-swap transactions, retries, and watch.
    """

    def __init__(self, endpoint: str = "http://127.0.0.1:2379", timeout_s: float = 3.0):
        self.endpoint = endpoint.rstrip("/")
        self.timeout_s = timeout_s

    def put(self, key: str, value: str) -> None:
        payload = {
            "key": self._encode(key),
            "value": self._encode(value),
        }
        self._post("/v3/kv/put", payload)

    def get(self, key: str) -> str | None:
        response = self._post("/v3/kv/range", {"key": self._encode(key)})
        values = response.get("kvs", [])
        if not isinstance(values, list) or not values:
            return None
        first = values[0]
        if not isinstance(first, dict):
            raise RuntimeError("Invalid etcd response: kv entry is not an object")
        encoded_value = first.get("value")
        if not isinstance(encoded_value, str):
            raise RuntimeError("Invalid etcd response: value is missing or not a string")
        return self._decode(encoded_value)

    def _post(self, path: str, payload: dict[str, str]) -> JsonObject:
        request = Request(
            self.endpoint + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_s) as response:
                parsed = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError) as exc:
            raise RuntimeError(f"etcd request failed for {path}: {exc}") from exc
        if not isinstance(parsed, dict):
            raise RuntimeError("Invalid etcd response: expected a JSON object")
        return cast(JsonObject, parsed)

    @staticmethod
    def _encode(value: str) -> str:
        return base64.b64encode(value.encode("utf-8")).decode("ascii")

    @staticmethod
    def _decode(value: str) -> str:
        return base64.b64decode(value).decode("utf-8")
