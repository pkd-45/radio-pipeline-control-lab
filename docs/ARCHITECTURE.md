# Architecture and data contracts

## Design principle

Science functions do not import Slurm, Kafka, etcd, or Tango. The numerical pipeline, execution engine, control boundary, and infrastructure adapters are separated so each can be tested independently and replaced without rewriting the others.

## Components

### Numerical domain (`domain.py`)

Pure NumPy functions implement sky generation, visibility sampling, interference detection, reference-antenna calibration, gridding, dirty imaging, and quantitative errors. These functions are deterministic for a supplied seed and are tested independently of file I/O.

### Stage layer (`stages.py`)

Stages convert numerical operations into file-producing pipeline steps. Every successful stage returns a product list containing path, byte count, and SHA-256 digest. The QA stage generates the final manifest and enforces configured numerical thresholds.

### Execution layer (`executor.py`)

The executor provides:

- dependency checks;
- persisted attempts;
- retry behaviour;
- verified restart/resume;
- cancellation between stages;
- run and stage events;
- execution-plan materialisation.

A stage is resumable only when its latest state is `SUCCEEDED` and all recorded product hashes still verify.

### State and provenance

SQLite stores attempt history rather than only the latest status, retaining failures and retries for audit. JSON reports are written atomically. Product digests allow the executor to distinguish a completed stage from a stale or corrupted output directory.

### Control boundary (`control.py`)

`PipelineControlService` is framework-independent. It exposes start, abort, and status operations while writing high-level run state through a small coordination interface. A Tango device, REST service, or message consumer can wrap this boundary without entering the numerical code.

### Slurm planning (`slurm.py`)

Each stage receives independent CPU, memory, and wall-time declarations. The generated submission script expresses stage dependencies using Slurm `afterok` job dependencies, allowing resources to be requested only when the relevant stage becomes runnable.

## Data products

| Stage | Main product | Purpose |
|---|---|---|
| simulate | `simulated_observation.npz` | Sky truth, uv coordinates, baselines, gains, noisy visibilities, injected-RFI truth |
| flag | `flags.npy` | Boolean acceptance mask |
| calibrate | `calibrated_visibilities.npz` | Gain estimates and corrected visibilities |
| image | `dirty_image.npz` | Dirty image, PSF, sky truth |
| QA | `qa_metrics.json`, `manifest.json`, `diagnostic.png` | Quality gates, provenance, reviewer-facing diagnostic |

## Failure model

The repository exercises stage exceptions, exhausted retries, dependency failure, cancellation between stages, and product tampering. It does not yet model process pre-emption during an individual numerical kernel or distributed consensus failure.
