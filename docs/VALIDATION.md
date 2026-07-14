# Validation record

## Automated validation

The project is checked with:

- Ruff linting;
- MyPy static type checking;
- Pytest unit and integration tests;
- GitHub Actions on Python 3.11, 3.12, and 3.13.

## Independent local execution

The deterministic demonstration was installed from a clean archive and executed on macOS with Python 3.14. The full pipeline passed all quality gates.

## Slurm-cluster execution

On 14 July 2026, the package was installed in a clean Python 3.11.15 Conda environment on a Linux research cluster. The following checks passed:

- Ruff: passed;
- MyPy: passed for all 16 source files;
- Pytest: 10/10 tests passed;
- interactive end-to-end execution: passed;
- generated five-stage Slurm dependency chain: passed;
- Slurm execution across more than one compute node: passed;
- final science-quality gate: passed.

The Slurm chain executed:

```text
simulate -> flag -> calibrate -> image -> qa
```

with `afterok` dependencies, per-stage CPU/memory/wall-time requests, an absolute Python interpreter path, and persisted provenance. The independently reproduced metrics are committed in `examples/slurm_cluster_qa_metrics.json`.

| Metric | Slurm result |
|---|---:|
| Antenna-gain NRMSE | 0.0035818 |
| Calibrated-visibility NRMSE | 0.0106526 |
| Injected-interference recall | 0.76 |
| Flag false-positive rate | 0.0099492 |
| Dirty-image NRMSE | 0.0365892 |
| Finite output fraction | 1.0 |
| Overall QA | passed |

These values are deterministic synthetic regression results, not measurements of telescope or SKAO performance.

## Logging convention

Operational `INFO` and `WARNING` records are written to standard output. Unhandled Python exceptions remain visible on standard error. This keeps successful Slurm `.err` files empty and avoids treating normal telemetry as an error condition.
