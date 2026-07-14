# Testing and validation strategy

## Numerical tests

- Calibration must reduce visibility error on accepted samples.
- Recovered gains must remain close to injected gains.
- The flagger must meet both recall and false-positive limits.
- Imaging must return finite arrays with the configured dimensions and a normalised PSF.

## Pipeline tests

- End-to-end execution must pass the science-quality gate and create a complete manifest.
- A second run must resume without creating new attempts when products still verify.
- An intentionally transient failure must create `FAILED` and `SUCCEEDED` attempts.
- A tampered product must invalidate resume and trigger recomputation.
- Generated Slurm scripts must contain configured resources and correct job dependencies.

## Control and adapter tests

- The control service must update coordination state and report completed-stage progress.
- Kafka event serialisation is checked deterministically through an injected producer.
- The etcd adapter is exercised over a real local HTTP boundary using a small protocol stub.

## Continuous integration

GitHub Actions runs linting and the full test suite on Python 3.11, 3.12, and 3.13.

## Why QA is separate from execution success

A pipeline can complete computationally while producing scientifically unusable products. The final QA stage therefore enforces numerical limits on calibration error, visibility error, flagging recall and contamination, image error, and finite output fraction. A failed quality gate fails the run.

## Cross-platform validation

The deterministic metrics have been reproduced on macOS and on a Linux Slurm cluster. See [the validation record](VALIDATION.md).
