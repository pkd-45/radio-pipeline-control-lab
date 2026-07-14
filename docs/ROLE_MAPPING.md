# Mapping to the Data Processing Software Engineer role

## Immediate contribution supported by existing experience and this repository

| Role requirement | Evidence |
|---|---|
| Solid Python engineering | Installable package, typed interfaces, CLI, configuration model, tests, linting, CI, documentation |
| Systematic unit and integration testing | Numerical unit tests; end-to-end QA test; retry, resume, corruption, Slurm, control, Kafka, and etcd boundary tests |
| Execute and monitor large-data processing | Persisted execution state, structured events, status reporting, retries, cancellation, and per-stage timing |
| Allocate compute and storage at the right time | Per-stage resource model and Slurm DAG generation with `afterok` dependencies |
| Automated scientific pipeline integration | Configuration-driven simulate → flag → calibrate → image → QA workflow with data contracts and quality gates |
| Scientific and computational performance monitoring | Numerical QA thresholds, timing events, finite-data checks, product sizes, hashes, and diagnostic outputs |
| Radio data-product awareness | Synthetic visibilities, antenna gains, RFI-like corruption, calibration, uv gridding, dirty image, and PSF |
| Reliability and traceability | Attempt history, atomic reports, checksum-verified resume, provenance manifest, explicit failure propagation |

## Skills demonstrated primarily through prior work

The portfolio project is most credible when read alongside established work in scientific Python pipelines, IFU data products, machine learning, MCMC modelling, Slurm workflows, simulation analysis, and interferometric reconstruction. The repository does not replace that record; it makes the transferable engineering practices inspectable.

## Technologies being learned rather than claimed as production experience

- Tango device and control-system conventions.
- Kafka delivery guarantees, partitions, consumer groups, schema evolution, and back-pressure.
- etcd leases, watches, transactions, authentication, and high-availability deployment.

The optional adapters demonstrate interface understanding and testable isolation. They are intentionally not presented as evidence of operating those technologies at observatory scale.
