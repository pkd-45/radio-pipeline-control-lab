from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ResourceSpec:
    cpus: int = 1
    memory_gb: int = 2
    walltime: str = "00:10:00"


@dataclass(frozen=True)
class PipelineConfig:
    run_id: str
    work_dir: Path
    seed: int = 42
    image_size: int = 64
    n_antennas: int = 8
    n_visibilities: int = 4000
    calibrator_samples_per_antenna: int = 24
    noise_std: float = 0.015
    rfi_fraction: float = 0.015
    rfi_sigma: float = 25.0
    max_retries: int = 1
    fail_once_stage: str = ""
    qa_max_visibility_nrmse: float = 0.20
    qa_max_gain_error: float = 0.15
    qa_min_flag_recall: float = 0.65
    qa_max_flag_false_positive_rate: float = 0.02
    qa_max_image_nrmse: float = 0.45
    resources: dict[str, ResourceSpec] = field(default_factory=dict)


DEFAULT_RESOURCES = {
    "simulate": ResourceSpec(cpus=1, memory_gb=2, walltime="00:05:00"),
    "flag": ResourceSpec(cpus=1, memory_gb=2, walltime="00:05:00"),
    "calibrate": ResourceSpec(cpus=2, memory_gb=4, walltime="00:10:00"),
    "image": ResourceSpec(cpus=4, memory_gb=8, walltime="00:20:00"),
    "qa": ResourceSpec(cpus=1, memory_gb=4, walltime="00:10:00"),
}


def load_config(path: str | Path) -> PipelineConfig:
    config_path = Path(path)
    raw = tomllib.loads(config_path.read_text(encoding="utf-8"))
    run = raw.get("run", {})
    qa = raw.get("qa", {})
    resource_raw = raw.get("resources", {})
    resources = dict(DEFAULT_RESOURCES)
    for stage, values in resource_raw.items():
        base = resources.get(stage, ResourceSpec())
        resources[stage] = ResourceSpec(
            cpus=int(values.get("cpus", base.cpus)),
            memory_gb=int(values.get("memory_gb", base.memory_gb)),
            walltime=str(values.get("walltime", base.walltime)),
        )
    work_dir = Path(run.get("work_dir", "run-output"))
    if not work_dir.is_absolute():
        work_dir = (config_path.parent / work_dir).resolve()
    return PipelineConfig(
        run_id=str(run.get("run_id", "demo-run")),
        work_dir=work_dir,
        seed=int(run.get("seed", 42)),
        image_size=int(run.get("image_size", 64)),
        n_antennas=int(run.get("n_antennas", 8)),
        n_visibilities=int(run.get("n_visibilities", 4000)),
        calibrator_samples_per_antenna=int(run.get("calibrator_samples_per_antenna", 24)),
        noise_std=float(run.get("noise_std", 0.015)),
        rfi_fraction=float(run.get("rfi_fraction", 0.015)),
        rfi_sigma=float(run.get("rfi_sigma", 25.0)),
        max_retries=int(run.get("max_retries", 1)),
        fail_once_stage=str(run.get("fail_once_stage", "")),
        qa_max_visibility_nrmse=float(qa.get("max_visibility_nrmse", 0.20)),
        qa_max_gain_error=float(qa.get("max_gain_error", 0.15)),
        qa_min_flag_recall=float(qa.get("min_flag_recall", 0.65)),
        qa_max_flag_false_positive_rate=float(
            qa.get("max_flag_false_positive_rate", 0.02)
        ),
        qa_max_image_nrmse=float(qa.get("max_image_nrmse", 0.45)),
        resources=resources,
    )
