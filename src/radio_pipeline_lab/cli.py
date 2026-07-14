from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict
from pathlib import Path

from .config import load_config
from .executor import PipelineExecutor
from .slurm import stage_script, submission_script
from .stages import STAGE_BY_NAME, STAGES


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Synthetic radio-pipeline control laboratory")
    parser.add_argument("--log-level", default="INFO")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("run", "status", "plan", "cancel", "slurm-plan"):
        child = sub.add_parser(command)
        child.add_argument("--config", required=True)
    stage = sub.add_parser("run-stage")
    stage.add_argument("--config", required=True)
    stage.add_argument("--stage", choices=tuple(STAGE_BY_NAME), required=True)
    slurm = sub.choices["slurm-plan"]
    slurm.add_argument("--output-dir", default="generated-slurm")
    slurm.add_argument(
        "--python-executable",
        default=sys.executable,
        help=(
            "Python interpreter embedded in generated stage scripts "
            "(default: current interpreter)"
        ),
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
    )
    config = load_config(args.config)
    executor = PipelineExecutor(config)
    if args.command == "run":
        executor.run(resume=True)
    elif args.command == "run-stage":
        executor.run_stage(args.stage)
    elif args.command == "status":
        records = [asdict(record) for record in executor.store.records(config.run_id)]
        print(json.dumps(records, indent=2, sort_keys=True))
    elif args.command == "plan":
        print(json.dumps(executor.plan(), indent=2, sort_keys=True))
    elif args.command == "cancel":
        print(executor.request_cancel())
    elif args.command == "slurm-plan":
        output = Path(args.output_dir)
        output.mkdir(parents=True, exist_ok=True)
        for stage in STAGES:
            path = output / f"{stage.name}.sbatch"
            path.write_text(
                stage_script(
                    config,
                    stage.name,
                    args.config,
                    python_executable=args.python_executable,
                ),
                encoding="utf-8",
            )
        submit = output / "submit_pipeline.sh"
        submit.write_text(submission_script(config, output), encoding="utf-8")
        submit.chmod(0o755)
        print(submit)


if __name__ == "__main__":
    main()
