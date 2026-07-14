# Learning roadmap and production limitations

## Kafka

Implemented here: deterministic JSON event publication through an injectable producer interface.

Next production topics:

- Avro/Protobuf or JSON-schema contracts and compatibility policy;
- idempotent producers and delivery guarantees;
- partition-key design and ordering requirements;
- consumer groups, offset management, retries, and dead-letter handling;
- back-pressure, lag monitoring, authentication, and TLS.

## etcd

Implemented here: simple put/get run-state operations through the v3 JSON gateway.

Next production topics:

- leases and expiry for liveness state;
- watch streams for reactive control;
- compare-and-swap transactions and leader election;
- authentication, TLS, compaction, quorum behaviour, and recovery testing.

## Tango

Implemented here: optional attributes and commands around a framework-independent control service.

Next production topics:

- device properties and configuration;
- event subscriptions and asynchronous long-running commands;
- Tango database deployment and device lifecycle;
- state/status conventions, alarms, logging, and integration testing with real devices.

## Distributed execution

Implemented here: local synchronous executor plus Slurm stage/DAG generation.

Next production topics:

- job submission and polling backend;
- pre-emption and node-failure recovery;
- distributed locks and duplicate-execution protection;
- storage locality and data-transfer accounting;
- scalable metrics, tracing, dashboards, alerting, and SLOs;
- Kubernetes or other runtime backends where appropriate.

## Scientific pipeline realism

Implemented here: a transparent synthetic calibration and dirty-imaging chain.

Next production topics:

- Measurement Set or visibility-domain standard formats;
- channel/time-dependent gains and bandpass calibration;
- multiple weighting and gridding kernels;
- deconvolution and source-finding stages;
- real data, instrument metadata, and regression datasets;
- numerical benchmarking against established radio software.
