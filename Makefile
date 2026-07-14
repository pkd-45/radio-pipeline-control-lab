.PHONY: install test lint demo slurm clean

install:
	python -m pip install -e '.[dev]'

test:
	pytest

lint:
	ruff check .

demo:
	radio-pipeline-lab run --config configs/demo.toml

slurm:
	radio-pipeline-lab slurm-plan --config configs/demo.toml --output-dir generated-slurm

clean:
	rm -rf demo-output generated-slurm .pytest_cache .ruff_cache
