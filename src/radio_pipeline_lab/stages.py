from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .config import PipelineConfig
from .domain import (
    apply_calibration,
    dirty_image,
    normalised_rmse,
    robust_radial_flags,
    simulate_observation,
    solve_reference_gains,
)
from .provenance import atomic_json, product_record

StageFunction = Callable[[PipelineConfig], dict[str, Any]]


@dataclass(frozen=True)
class StageDefinition:
    name: str
    dependencies: tuple[str, ...]
    function: StageFunction


def _products(config: PipelineConfig) -> Path:
    path = config.work_dir / "products"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _reports(config: PipelineConfig) -> Path:
    path = config.work_dir / "reports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _maybe_fail_once(config: PipelineConfig, stage: str) -> None:
    if config.fail_once_stage != stage:
        return
    marker = config.work_dir / "state" / f".{stage}.failed_once"
    if not marker.exists():
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("intentional one-time failure\n", encoding="utf-8")
        raise RuntimeError(f"Intentional one-time failure in stage '{stage}'")


def simulate(config: PipelineConfig) -> dict[str, Any]:
    _maybe_fail_once(config, "simulate")
    data = simulate_observation(
        size=config.image_size,
        n_antennas=config.n_antennas,
        n_visibilities=config.n_visibilities,
        calibrator_samples_per_antenna=config.calibrator_samples_per_antenna,
        noise_std=config.noise_std,
        rfi_fraction=config.rfi_fraction,
        rfi_sigma=config.rfi_sigma,
        seed=config.seed,
    )
    output = _products(config) / "simulated_observation.npz"
    np.savez_compressed(
        output,
        sky=data.sky,
        uv=data.uv,
        ant1=data.ant1,
        ant2=data.ant2,
        observed_vis=data.observed_vis,
        true_vis=data.true_vis,
        calibrator_antennas=data.calibrator_antennas,
        calibrator_vis=data.calibrator_vis,
        true_gains=data.true_gains,
        rfi_mask=data.rfi_mask,
    )
    return {
        "products": [product_record(output)],
        "image_size": config.image_size,
        "n_visibilities": config.n_visibilities,
        "n_antennas": config.n_antennas,
        "injected_rfi": int(np.count_nonzero(data.rfi_mask)),
    }


def flag(config: PipelineConfig) -> dict[str, Any]:
    _maybe_fail_once(config, "flag")
    source = np.load(_products(config) / "simulated_observation.npz")
    good = robust_radial_flags(source["uv"], source["observed_vis"])
    output = _products(config) / "flags.npy"
    np.save(output, good)
    return {
        "products": [product_record(output)],
        "accepted": int(np.count_nonzero(good)),
        "flagged": int(np.count_nonzero(~good)),
        "accepted_fraction": float(np.mean(good)),
    }


def calibrate(config: PipelineConfig) -> dict[str, Any]:
    _maybe_fail_once(config, "calibrate")
    source = np.load(_products(config) / "simulated_observation.npz")
    good = np.load(_products(config) / "flags.npy")
    gains = solve_reference_gains(
        config.n_antennas, source["calibrator_antennas"], source["calibrator_vis"]
    )
    corrected = apply_calibration(source["observed_vis"], source["ant1"], source["ant2"], gains)
    output = _products(config) / "calibrated_visibilities.npz"
    np.savez_compressed(
        output,
        uv=source["uv"],
        ant1=source["ant1"],
        ant2=source["ant2"],
        calibrated_vis=corrected,
        true_vis=source["true_vis"],
        good=good,
        estimated_gains=gains,
        true_gains=source["true_gains"],
        rfi_mask=source["rfi_mask"],
        sky=source["sky"],
    )
    gain_error = normalised_rmse(gains, source["true_gains"])
    visibility_error = normalised_rmse(corrected[good], source["true_vis"][good])
    return {
        "products": [product_record(output)],
        "gain_nrmse": gain_error,
        "visibility_nrmse": visibility_error,
    }



def _psf_sidelobe(psf: np.ndarray) -> float:
    centre = tuple(index // 2 for index in psf.shape)
    masked = np.abs(psf).copy()
    y, x = centre
    masked[max(0, y - 1) : y + 2, max(0, x - 1) : x + 2] = 0.0
    return float(np.max(masked))


def image(config: PipelineConfig) -> dict[str, Any]:
    _maybe_fail_once(config, "image")
    source = np.load(_products(config) / "calibrated_visibilities.npz")
    dirty, psf = dirty_image(
        config.image_size, source["uv"], source["calibrated_vis"], source["good"]
    )
    output = _products(config) / "dirty_image.npz"
    np.savez_compressed(output, dirty=dirty, psf=psf, sky=source["sky"])
    return {
        "products": [product_record(output)],
        "dirty_peak": float(np.max(dirty)),
        "psf_sidelobe": _psf_sidelobe(psf),
    }


def _save_diagnostic_plot(path: Path, sky: np.ndarray, dirty: np.ndarray, psf: np.ndarray) -> None:
    scale = float(np.vdot(dirty, sky).real / max(np.vdot(dirty, dirty).real, 1e-12))
    residual = sky - scale * dirty
    figure, axes = plt.subplots(1, 4, figsize=(12, 3))
    for axis, image_data, title in zip(
        axes,
        (sky, dirty, residual, psf),
        ("Truth", "Dirty image", "Scaled residual", "PSF"),
        strict=True,
    ):
        rendered = axis.imshow(image_data, origin="lower")
        axis.set_title(title)
        axis.set_xticks([])
        axis.set_yticks([])
        figure.colorbar(rendered, ax=axis, fraction=0.046, pad=0.04)
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)


def qa(config: PipelineConfig) -> dict[str, Any]:
    _maybe_fail_once(config, "qa")
    calibrated = np.load(_products(config) / "calibrated_visibilities.npz")
    images = np.load(_products(config) / "dirty_image.npz")
    good = calibrated["good"].astype(bool)
    rfi = calibrated["rfi_mask"].astype(bool)
    estimated_gains = calibrated["estimated_gains"]
    true_gains = calibrated["true_gains"]
    corrected = calibrated["calibrated_vis"]
    true_vis = calibrated["true_vis"]

    gain_error = normalised_rmse(estimated_gains, true_gains)
    visibility_error = normalised_rmse(corrected[good], true_vis[good])
    injected = max(int(np.count_nonzero(rfi)), 1)
    flag_recall = float(np.count_nonzero((~good) & rfi) / injected)
    false_positives = int(np.count_nonzero((~good) & (~rfi)))
    non_rfi = max(int(np.count_nonzero(~rfi)), 1)
    false_positive_rate = float(false_positives / non_rfi)

    dirty = images["dirty"]
    sky = images["sky"]
    scale = float(np.vdot(dirty, sky).real / max(np.vdot(dirty, dirty).real, 1e-12))
    image_error = normalised_rmse(scale * dirty, sky)
    finite_fraction = float(np.mean(np.isfinite(dirty)))

    passed = (
        finite_fraction == 1.0
        and visibility_error <= config.qa_max_visibility_nrmse
        and gain_error <= config.qa_max_gain_error
        and flag_recall >= config.qa_min_flag_recall
        and false_positive_rate <= config.qa_max_flag_false_positive_rate
        and image_error <= config.qa_max_image_nrmse
    )
    metrics = {
        "qa_passed": passed,
        "gain_nrmse": gain_error,
        "visibility_nrmse": visibility_error,
        "image_nrmse": image_error,
        "flag_recall": flag_recall,
        "flag_false_positive_rate": false_positive_rate,
        "finite_fraction": finite_fraction,
        "thresholds": {
            "max_visibility_nrmse": config.qa_max_visibility_nrmse,
            "max_gain_error": config.qa_max_gain_error,
            "min_flag_recall": config.qa_min_flag_recall,
            "max_flag_false_positive_rate": config.qa_max_flag_false_positive_rate,
            "max_image_nrmse": config.qa_max_image_nrmse,
        },
    }
    metrics_path = _reports(config) / "qa_metrics.json"
    plot_path = _reports(config) / "diagnostic.png"
    atomic_json(metrics_path, metrics)
    _save_diagnostic_plot(plot_path, sky, dirty, images["psf"])

    product_paths = [
        _products(config) / "simulated_observation.npz",
        _products(config) / "flags.npy",
        _products(config) / "calibrated_visibilities.npz",
        _products(config) / "dirty_image.npz",
        metrics_path,
        plot_path,
    ]
    manifest = {
        "run_id": config.run_id,
        "pipeline": ["simulate", "flag", "calibrate", "image", "qa"],
        "qa": metrics,
        "products": [product_record(path) for path in product_paths],
    }
    manifest_path = _reports(config) / "manifest.json"
    atomic_json(manifest_path, manifest)
    result = {
        "products": [
            product_record(metrics_path),
            product_record(plot_path),
            product_record(manifest_path),
        ],
        **metrics,
    }
    if not passed:
        raise RuntimeError("Science quality gate failed: " + json.dumps(metrics, sort_keys=True))
    return result


STAGES: tuple[StageDefinition, ...] = (
    StageDefinition("simulate", (), simulate),
    StageDefinition("flag", ("simulate",), flag),
    StageDefinition("calibrate", ("simulate", "flag"), calibrate),
    StageDefinition("image", ("calibrate",), image),
    StageDefinition("qa", ("image",), qa),
)
STAGE_BY_NAME = {stage.name: stage for stage in STAGES}
