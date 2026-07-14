from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Protocol

from .events import PipelineEvent, make_event
from .executor import PipelineExecutor


class CoordinationStore(Protocol):
    def put(self, key: str, value: str) -> None: ...
    def get(self, key: str) -> str | None: ...


class ControlEventPublisher(Protocol):
    def publish(self, event: PipelineEvent) -> None: ...


@dataclass(frozen=True)
class ControlStatus:
    run_id: str
    state: str
    completed_stages: int
    total_stages: int
    last_error: str = ""


class InMemoryCoordinationStore:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def put(self, key: str, value: str) -> None:
        self.values[key] = value

    def get(self, key: str) -> str | None:
        return self.values.get(key)


class PipelineControlService:
    """Framework-independent observatory-facing control boundary.

    A real deployment could expose this service through a Tango device, REST/gRPC API,
    or message-driven command consumer without coupling those frameworks to science code.
    """

    def __init__(
        self,
        executor: PipelineExecutor,
        coordination: CoordinationStore,
        publisher: ControlEventPublisher,
    ) -> None:
        self.executor = executor
        self.coordination = coordination
        self.publisher = publisher
        self._last_error = ""

    @property
    def key(self) -> str:
        return f"/radio-pipeline/runs/{self.executor.config.run_id}/state"

    def start(self, resume: bool = True) -> ControlStatus:
        self._set_state("RUNNING")
        self.publisher.publish(make_event(self.executor.config.run_id, "control_start_requested"))
        try:
            self.executor.run(resume=resume)
        except Exception as exc:
            self._last_error = str(exc)
            self._set_state("FAILED")
            self.publisher.publish(
                make_event(self.executor.config.run_id, "control_run_failed", error=str(exc))
            )
            raise
        self._set_state("SUCCEEDED")
        self.publisher.publish(make_event(self.executor.config.run_id, "control_run_succeeded"))
        return self.status()

    def abort(self) -> ControlStatus:
        self.executor.request_cancel()
        self._set_state("CANCEL_REQUESTED")
        self.publisher.publish(make_event(self.executor.config.run_id, "control_abort_requested"))
        return self.status()

    def status(self) -> ControlStatus:
        records = self.executor.store.records(self.executor.config.run_id)
        succeeded = {record.stage for record in records if record.status == "SUCCEEDED"}
        return ControlStatus(
            run_id=self.executor.config.run_id,
            state=self.coordination.get(self.key) or "IDLE",
            completed_stages=len(succeeded),
            total_stages=len(self.executor.plan()),
            last_error=self._last_error,
        )

    def status_dict(self) -> dict[str, object]:
        return asdict(self.status())

    def _set_state(self, state: str) -> None:
        self.coordination.put(self.key, state)
