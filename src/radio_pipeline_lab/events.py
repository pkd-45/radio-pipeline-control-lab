from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class PipelineEvent:
    timestamp: str
    run_id: str
    event: str
    stage: str | None
    payload: dict[str, Any]


class EventPublisher(Protocol):
    def publish(self, event: PipelineEvent) -> None: ...


class JsonlEventPublisher:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def publish(self, event: PipelineEvent) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(event), sort_keys=True) + "\n")


def make_event(
    run_id: str, event: str, *, stage: str | None = None, **payload: Any
) -> PipelineEvent:
    return PipelineEvent(
        timestamp=datetime.now(UTC).isoformat(),
        run_id=run_id,
        event=event,
        stage=stage,
        payload=payload,
    )
