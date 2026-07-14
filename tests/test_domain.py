from __future__ import annotations

import numpy as np

from radio_pipeline_lab.domain import (
    apply_calibration,
    dirty_image,
    normalised_rmse,
    robust_radial_flags,
    simulate_observation,
    solve_reference_gains,
)


def test_calibration_improves_clean_visibility_error() -> None:
    data = simulate_observation(
        size=48,
        n_antennas=7,
        n_visibilities=3000,
        calibrator_samples_per_antenna=32,
        noise_std=0.008,
        rfi_fraction=0.01,
        rfi_sigma=30.0,
        seed=3,
    )
    good = robust_radial_flags(data.uv, data.observed_vis)
    gains = solve_reference_gains(7, data.calibrator_antennas, data.calibrator_vis)
    corrected = apply_calibration(data.observed_vis, data.ant1, data.ant2, gains)
    before = normalised_rmse(data.observed_vis[good], data.true_vis[good])
    after = normalised_rmse(corrected[good], data.true_vis[good])
    assert after < before
    assert normalised_rmse(gains, data.true_gains) < 0.08


def test_flagger_recovers_most_injected_outliers() -> None:
    data = simulate_observation(
        size=48,
        n_antennas=7,
        n_visibilities=3000,
        calibrator_samples_per_antenna=16,
        noise_std=0.01,
        rfi_fraction=0.02,
        rfi_sigma=40.0,
        seed=9,
    )
    good = robust_radial_flags(data.uv, data.observed_vis)
    recall = np.count_nonzero((~good) & data.rfi_mask) / np.count_nonzero(data.rfi_mask)
    false_positive_rate = (
        np.count_nonzero((~good) & (~data.rfi_mask)) / np.count_nonzero(~data.rfi_mask)
    )
    assert recall >= 0.6
    assert false_positive_rate <= 0.02


def test_dirty_image_is_finite_and_has_expected_shape() -> None:
    data = simulate_observation(
        size=32,
        n_antennas=6,
        n_visibilities=1200,
        calibrator_samples_per_antenna=12,
        noise_std=0.0,
        rfi_fraction=0.001,
        rfi_sigma=0.0,
        seed=4,
    )
    image, psf = dirty_image(32, data.uv, data.true_vis, np.ones(data.true_vis.size, dtype=bool))
    assert image.shape == (32, 32)
    assert psf.shape == (32, 32)
    assert np.isfinite(image).all()
    assert np.max(np.abs(psf)) == 1.0
