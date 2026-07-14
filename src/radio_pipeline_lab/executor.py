from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from .config import PipelineConfig
from .events import EventPublisher, JsonlEventPublisher, make_event
from .provenance import atomic_json, verify_products
from .stages import STAGE_BY_NAME, STAGES
from .state import RunStore

LOGGER = logging.getLogger("radio_pipeline_lab")


class PipelineCancelled(RuntimeError):
    """Raised when a cancellation marker is detected between stages."""


class PipelineExecutor:
    def __init__(self, config: PipelineConfig, publisher: EventPublisher | None = None):
        self.config = config
        self.store = RunStore(config.work_dir / "state" / "runs.sqlite3")
        self.publisher = publisher or JsonlEventPublisher(
            config.work_dir / "events" / "events.jsonl"
        )

    def plan(self) -> list[dict[str, Any]]:
        return [
            {
                "stage": stage.name,
                "dependencies": list(stage.dependencies),
                "resources": self.config.resources[stage.name].__dict__,
            }
            for stage in STAGES
        ]

    def run(self, resume: bool = True) -> None:
        self.config.work_dir.mkdir(parents=True, exist_ok=True)
        atomic_json(
            self.config.work_dir / "reports" / "execution_plan.json",
            {"stages": self.plan()},
        )
        self.publisher.publish(make_event(self.config.run_id, "run_started", resume=resume))
        try:
            for stage in STAGES:
                self._check_cancelled()
                latest = self.store.latest(self.config.run_id, stage.name)
                if resume and self._can_resume(latest):
                    LOGGER.info("stage=%s status=SKIPPED reason=verified_products", stage.name)
                    self.publisher.publish(
                        make_event(self.config.run_id, "stage_skipped", stage=stage.name)
                    )
                    continue
                self.run_stage(stage.name)
        except Exception as exc:
            self.publisher.publish(make_event(self.config.run_id, "run_failed", error=str(exc)))
            raise
        self.publisher.publish(make_event(self.config.run_id, "run_succeeded"))

    def run_stage(self, stage_name: str) -> None:
        if stage_name not in STAGE_BY_NAME:
            raise ValueError(f"Unknown stage: {stage_name}")
        stage = STAGE_BY_NAME[stage_name]
        self._assert_dependencies(stage.dependencies)
        prior = self.store.latest(self.config.run_id, stage_name)
        first_attempt = 1 if prior is None else prior.attempt + 1
        for offset in range(self.config.max_retries + 1):
            attempt = first_attempt + offset
            self.store.start(self.config.run_id, stage_name, attempt)
            self.publisher.publish(
                make_event(self.config.run_id, "stage_started", stage=stage_name, attempt=attempt)
            )
            started = time.perf_counter()
            try:
                result = stage.function(self.config)
            except Exception as exc:
                elapsed = time.perf_counter() - started
                detail = {"error": str(exc), "elapsed_s": elapsed}
                self.store.finish(self.config.run_id, stage_name, attempt, "FAILED", detail)
                self.publisher.publish(
                    make_event(
                        self.config.run_id,
                        "stage_failed",
                        stage=stage_name,
                        attempt=attempt,
                        **detail,
                    )
                )
                LOGGER.exception("stage=%s attempt=%d failed", stage_name, attempt)
                if offset >= self.config.max_retries:
                    raise
                continue
            elapsed = time.perf_counter() - started
            detail = {**result, "elapsed_s": elapsed}
            self.store.finish(self.config.run_id, stage_name, attempt, "SUCCEEDED", detail)
            self.publisher.publish(
                make_event(
                    self.config.run_id,
                    "stage_succeeded",
                    stage=stage_name,
                    attempt=attempt,
                    elapsed_s=elapsed,
                )
            )
            LOGGER.info("stage=%s status=SUCCEEDED elapsed_s=%.3f", stage_name, elapsed)
            return

    def request_cancel(self) -> Path:
        marker = self.config.work_dir / "state" / "CANCEL"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("cancel requested\n", encoding="utf-8")
        return marker

    def _check_cancelled(self) -> None:
        marker = self.config.work_dir / "state" / "CANCEL"
        if marker.exists():
            self.publisher.publish(make_event(self.config.run_id, "run_cancelled"))
            raise PipelineCancelled(f"Cancellation requested via {marker}")

    def _assert_dependencies(self, dependencies: tuple[str, ...]) -> None:
        for dependency in dependencies:
            latest = self.store.latest(self.config.run_id, dependency)
            if not self._can_resume(latest):
                raise RuntimeError(
                    f"Stage dependency '{dependency}' has not completed with verified products"
                )

    @staticmethod
    def _can_resume(record: Any) -> bool:
        return bool(
            record
            and record.status == "SUCCEEDED"
            and isinstance(record.detail.get("products"), list)
            and verify_products(record.detail["products"])
        )
