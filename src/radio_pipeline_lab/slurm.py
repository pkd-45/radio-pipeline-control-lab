from __future__ import annotations

import shlex
import sys
from pathlib import Path

from .config import PipelineConfig
from .stages import STAGE_BY_NAME, STAGES


def stage_script(
    config: PipelineConfig,
    stage_name: str,
    config_path: str | Path,
    *,
    python_executable: str | Path | None = None,
) -> str:
    """Render a self-contained Slurm script for one pipeline stage.

    The generated script captures absolute paths for the configuration, log directory,
    and Python interpreter. Generate it on the host where it will run, after activating
    the intended environment.
    """
    if stage_name not in STAGE_BY_NAME:
        raise ValueError(f"Unknown stage: {stage_name}")

    resource = config.resources[stage_name]
    logs = config.work_dir / "logs"
    interpreter = Path(python_executable or sys.executable).expanduser()
    if not interpreter.is_absolute():
        interpreter = (Path.cwd() / interpreter).absolute()
    resolved_config = Path(config_path).expanduser().resolve()
    command = (
        shlex.quote(str(interpreter))
        + " -m radio_pipeline_lab.cli run-stage --config "
        + shlex.quote(str(resolved_config))
        + " --stage "
        + shlex.quote(stage_name)
    )

    return f"""#!/usr/bin/env bash
#SBATCH --job-name=radio-{stage_name}
#SBATCH --ntasks=1
#SBATCH --cpus-per-task={resource.cpus}
#SBATCH --mem={resource.memory_gb}G
#SBATCH --time={resource.walltime}
#SBATCH --export=ALL
#SBATCH --output={logs}/{stage_name}-%j.out
#SBATCH --error={logs}/{stage_name}-%j.err

set -euo pipefail
mkdir -p {shlex.quote(str(logs))}
echo "stage={stage_name} host=$(hostname) job_id=${{SLURM_JOB_ID:-local}}"
echo "started=$(date --iso-8601=seconds)"
echo "python={interpreter}"
{command}
echo "stage={stage_name} finished=$(date --iso-8601=seconds)"
"""


def submission_script(config: PipelineConfig, scripts_dir: str | Path) -> str:
    """Render a submission script with absolute stage-script paths and DAG dependencies."""
    del config  # Reserved for future scheduler-level configuration.
    directory = Path(scripts_dir).expanduser().resolve()
    lines = ["#!/usr/bin/env bash", "set -euo pipefail", ""]
    job_vars: dict[str, str] = {}
    for stage in STAGES:
        variable = f"JOB_{stage.name.upper()}"
        dependency = ""
        if stage.dependencies:
            parents = ":".join(f"${job_vars[parent]}" for parent in stage.dependencies)
            dependency = f"--dependency=afterok:{parents} "
        script_path = directory / f"{stage.name}.sbatch"
        lines.append(
            f'{variable}=$(sbatch --parsable {dependency}{shlex.quote(str(script_path))})'
        )
        lines.append(f'echo "submitted {stage.name}: ${variable}"')
        job_vars[stage.name] = variable
    lines.append("")
    return "\n".join(lines)
