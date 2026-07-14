#!/usr/bin/env bash
set -euo pipefail

JOB_SIMULATE=$(sbatch --parsable generated-slurm/simulate.sbatch)
echo "submitted simulate: $JOB_SIMULATE"
JOB_FLAG=$(sbatch --parsable --dependency=afterok:$JOB_SIMULATE generated-slurm/flag.sbatch)
echo "submitted flag: $JOB_FLAG"
JOB_CALIBRATE=$(sbatch --parsable --dependency=afterok:$JOB_SIMULATE:$JOB_FLAG generated-slurm/calibrate.sbatch)
echo "submitted calibrate: $JOB_CALIBRATE"
JOB_IMAGE=$(sbatch --parsable --dependency=afterok:$JOB_CALIBRATE generated-slurm/image.sbatch)
echo "submitted image: $JOB_IMAGE"
JOB_QA=$(sbatch --parsable --dependency=afterok:$JOB_IMAGE generated-slurm/qa.sbatch)
echo "submitted qa: $JOB_QA"
