# Running on a Slurm cluster

Generate the Slurm files **on the execution host**, after activating the Python environment
that will run the jobs. The generator intentionally captures absolute paths for the selected
Python interpreter and configuration file so that batch jobs do not depend on an interactive
shell setup.

```bash
cd /path/to/radio-pipeline-control-lab
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'

ruff check .
mypy src
pytest

rm -rf generated-slurm
radio-pipeline-lab slurm-plan \
  --config configs/slurm.toml \
  --output-dir generated-slurm

head -30 generated-slurm/simulate.sbatch
bash generated-slurm/submit_pipeline.sh
```

The generated stage scripts include:

- an absolute Python interpreter path;
- an absolute configuration path;
- absolute log locations;
- explicit task, CPU, memory, wall-time, and environment-export directives;
- a dependency-aware submission DAG using `afterok`.

Monitor the run with the scheduler tools available on the target system, then inspect:

```bash
radio-pipeline-lab status --config configs/slurm.toml
cat demo-output/reports/qa_metrics.json
```

Do not generate the scripts on one machine and copy them to another, because the absolute
paths are deliberately host-specific.

The repository intentionally provides separate `demo.toml` and `slurm.toml` files. This prevents an interactive validation run and a scheduler-backed run from sharing the same run ID or SQLite attempt history.

Successful stage telemetry is written to standard output; `.err` files are reserved for uncaught process errors.
