# Changelog

## 0.4.0 — 2026-07-14

- Added a containerised Redpanda and etcd integration environment.
- Added an opt-in test that publishes and consumes a real Kafka event.
- Added real etcd state persistence through the v3 JSON gateway.
- Added an idempotent Kafka topic initialisation container.
- Added a dedicated GitHub Actions job for service-backed integration tests.
- Kept Kafka optional and verified that the ordinary package works without it.
- Updated GitHub Actions to Node.js 24-based action releases.

## 0.3.0 — 2026-07-14

- Recorded independent Linux/Slurm validation and reproduced QA metrics.
- Added a dedicated `configs/slurm.toml` so interactive and scheduler runs keep separate state histories.
- Routed operational logs to standard output, leaving Slurm `.err` files for uncaught process errors.
- Added a regression test for the logging-stream convention.
- Added validation documentation and committed cluster QA metrics.

## 0.2.0 — 2026-07-14

- Made generated Slurm scripts portable by capturing absolute interpreter, configuration, and script paths.
- Added explicit task and environment-export directives.
- Added cluster execution documentation and MyPy validation.

## 0.1.0 — 2026-07-14

- Initial synthetic interferometry pipeline, execution controller, QA gates, provenance, tests, Slurm planner, and optional learning adapters.
