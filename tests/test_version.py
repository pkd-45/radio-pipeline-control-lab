from importlib.metadata import version

import radio_pipeline_lab


def test_package_version_matches_metadata() -> None:
    assert radio_pipeline_lab.__version__ == version(
        "radio-pipeline-control-lab"
    )
