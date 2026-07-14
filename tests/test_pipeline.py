from __future__ import annotations

import json
import sys
from pathlib import Path

from conftest import write_config

from radio_pipeline_lab.config import load_config
from radio_pipeline_lab.executor import PipelineExecutor
from radio_pipeline_lab.slurm import stage_script, submission_script


def test_end_to_end_resume_and_manifest(tmp_path: Path) -> None:
    config = load_config(write_config(tmp_path))
    executor = PipelineExecutor(config)
    executor.run()
    metrics = json.loads((config.work_dir / "reports" / "qa_metrics.json").read_text())
    manifest = json.loads((config.work_dir / "reports" / "manifest.json").read_text())
    assert metrics["qa_passed"] is True
    assert len(manifest["products"]) == 6
    before = len(executor.store.records(config.run_id))
    executor.run(resume=True)
    assert len(executor.store.records(config.run_id)) == before


def test_retry_records_failed_then_successful_attempt(tmp_path: Path) -> None:
    config = load_config(write_config(tmp_path, fail_once_stage="calibrate"))
    executor = PipelineExecutor(config)
    executor.run()
    records = [
        record
        for record in executor.store.records(config.run_id)
        if record.stage == "calibrate"
    ]
    assert [record.status for record in records] == ["FAILED", "SUCCEEDED"]


def test_tampered_product_is_recomputed(tmp_path: Path) -> None:
    config = load_config(write_config(tmp_path))
    executor = PipelineExecutor(config)
    executor.run()
    flags = config.work_dir / "products" / "flags.npy"
    flags.write_bytes(b"tampered")
    executor.run(resume=True)
    records = [record for record in executor.store.records(config.run_id) if record.stage == "flag"]
    assert len(records) == 2
    assert records[-1].status == "SUCCEEDED"


def test_slurm_plan_encodes_resources_and_dependencies(tmp_path: Path) -> None:
    config_path = write_config(tmp_path)
    config = load_config(config_path)
    image = stage_script(config, "image", config_path)
    submit = submission_script(config, tmp_path / "slurm")
    assert "#SBATCH --ntasks=1" in image
    assert "#SBATCH --export=ALL" in image
    assert f"python={Path(sys.executable).absolute()}" in image
    assert "#SBATCH --cpus-per-task=4" in image
    assert "#SBATCH --mem=8G" in image
    assert str((tmp_path / "slurm" / "simulate.sbatch").resolve()) in submit
    assert "--dependency=afterok:$JOB_CALIBRATE" in submit
    assert "--dependency=afterok:$JOB_SIMULATE:$JOB_FLAG" in submit


def test_cli_configures_operational_logs_on_stdout(monkeypatch, tmp_path: Path) -> None:
    import logging

    from radio_pipeline_lab import cli

    config_path = write_config(tmp_path, run_id="logging-test")
    captured: dict[str, object] = {}

    def fake_basic_config(**kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(logging, "basicConfig", fake_basic_config)
    monkeypatch.setattr(
        sys,
        "argv",
        ["radio-pipeline-lab", "plan", "--config", str(config_path)],
    )
    cli.main()
    assert captured["stream"] is sys.stdout
