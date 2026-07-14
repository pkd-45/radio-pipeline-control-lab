from __future__ import annotations

from pathlib import Path


def write_config(tmp_path: Path, *, fail_once_stage: str = "", run_id: str = "test-run") -> Path:
    path = tmp_path / f"{run_id}.toml"
    path.write_text(
        f'''[run]
run_id = "{run_id}"
work_dir = "{(tmp_path / run_id).as_posix()}"
seed = 17
image_size = 48
n_antennas = 7
n_visibilities = 2400
calibrator_samples_per_antenna = 24
noise_std = 0.01
rfi_fraction = 0.02
rfi_sigma = 35.0
max_retries = 1
fail_once_stage = "{fail_once_stage}"

[qa]
max_visibility_nrmse = 0.22
max_gain_error = 0.15
min_flag_recall = 0.60
max_flag_false_positive_rate = 0.02
max_image_nrmse = 0.45

[resources.image]
cpus = 4
memory_gb = 8
walltime = "00:20:00"
''',
        encoding="utf-8",
    )
    return path
