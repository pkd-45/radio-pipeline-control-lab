from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
ComplexArray = NDArray[np.complex128]
IntArray = NDArray[np.int64]
BoolArray = NDArray[np.bool_]


@dataclass(frozen=True)
class SimulationData:
    sky: FloatArray
    uv: IntArray
    ant1: IntArray
    ant2: IntArray
    observed_vis: ComplexArray
    true_vis: ComplexArray
    calibrator_antennas: IntArray
    calibrator_vis: ComplexArray
    true_gains: ComplexArray
    rfi_mask: BoolArray


def gaussian_2d(size: int, x0: float, y0: float, sx: float, sy: float, theta: float) -> FloatArray:
    y, x = np.mgrid[0:size, 0:size]
    cos_t = np.cos(theta)
    sin_t = np.sin(theta)
    xr = cos_t * (x - x0) + sin_t * (y - y0)
    yr = -sin_t * (x - x0) + cos_t * (y - y0)
    result = np.exp(-0.5 * ((xr / sx) ** 2 + (yr / sy) ** 2))
    return np.asarray(result, dtype=np.float64)


def make_sky_model(size: int, rng: np.random.Generator) -> FloatArray:
    sky = 0.8 * gaussian_2d(size, 0.50 * size, 0.51 * size, 7.0, 3.2, 0.55)
    sky += 0.35 * gaussian_2d(size, 0.34 * size, 0.64 * size, 2.2, 2.2, 0.0)
    sky += 0.22 * gaussian_2d(size, 0.69 * size, 0.38 * size, 1.7, 1.7, 0.0)
    for _ in range(2):
        sky += rng.uniform(0.08, 0.16) * gaussian_2d(
            size,
            rng.uniform(0.25, 0.75) * size,
            rng.uniform(0.25, 0.75) * size,
            rng.uniform(1.0, 2.0),
            rng.uniform(1.0, 2.0),
            rng.uniform(0, np.pi),
        )
    return (sky / np.max(sky)).astype(np.float64)


def sample_uv_coordinates(size: int, count: int, rng: np.random.Generator) -> IntArray:
    max_radius = size // 2 - 2
    radius = np.sqrt(rng.uniform(0.0, 1.0, count)) * max_radius
    angle = rng.uniform(0.0, 2.0 * np.pi, count)
    u = np.rint(radius * np.cos(angle)).astype(np.int64)
    v = np.rint(radius * np.sin(angle)).astype(np.int64)
    return np.column_stack((u, v))


def sky_visibilities(sky: FloatArray, uv: IntArray) -> ComplexArray:
    spectrum = np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(sky)))
    centre = sky.shape[0] // 2
    sampled = spectrum[centre + uv[:, 1], centre + uv[:, 0]]
    return np.asarray(sampled, dtype=np.complex128)


def simulate_observation(
    *,
    size: int,
    n_antennas: int,
    n_visibilities: int,
    calibrator_samples_per_antenna: int,
    noise_std: float,
    rfi_fraction: float,
    rfi_sigma: float,
    seed: int,
) -> SimulationData:
    rng = np.random.default_rng(seed)
    sky = make_sky_model(size, rng)
    uv = sample_uv_coordinates(size, n_visibilities, rng)
    true_vis = sky_visibilities(sky, uv)

    ant1 = rng.integers(0, n_antennas, n_visibilities, dtype=np.int64)
    ant2 = rng.integers(0, n_antennas - 1, n_visibilities, dtype=np.int64)
    ant2 = np.where(ant2 >= ant1, ant2 + 1, ant2)

    amplitudes = rng.normal(1.0, 0.05, n_antennas)
    phases = rng.normal(0.0, 0.12, n_antennas)
    true_gains = amplitudes * np.exp(1j * phases)
    true_gains[0] = 1.0 + 0.0j

    scale = max(float(np.median(np.abs(true_vis))), 1e-6)
    thermal = noise_std * scale * (
        rng.normal(size=n_visibilities) + 1j * rng.normal(size=n_visibilities)
    )
    observed = true_gains[ant1] * np.conj(true_gains[ant2]) * true_vis + thermal

    rfi_count = max(1, int(round(rfi_fraction * n_visibilities)))
    rfi_indices = rng.choice(n_visibilities, size=rfi_count, replace=False)
    rfi_mask = np.zeros(n_visibilities, dtype=bool)
    rfi_mask[rfi_indices] = True
    observed[rfi_indices] += rfi_sigma * scale * (
        rng.normal(size=rfi_count) + 1j * rng.normal(size=rfi_count)
    )

    cal_antennas = np.repeat(np.arange(1, n_antennas), calibrator_samples_per_antenna)
    cal_noise = noise_std * (
        rng.normal(size=cal_antennas.size) + 1j * rng.normal(size=cal_antennas.size)
    )
    calibrator_vis = true_gains[cal_antennas] + cal_noise

    return SimulationData(
        sky=sky,
        uv=uv,
        ant1=ant1,
        ant2=ant2,
        observed_vis=observed,
        true_vis=true_vis,
        calibrator_antennas=cal_antennas.astype(np.int64),
        calibrator_vis=calibrator_vis.astype(np.complex128),
        true_gains=true_gains.astype(np.complex128),
        rfi_mask=rfi_mask,
    )


def robust_radial_flags(
    uv: IntArray, vis: ComplexArray, sigma_threshold: float = 10.0
) -> BoolArray:
    radius = np.sqrt(np.sum(uv.astype(np.float64) ** 2, axis=1))
    amplitude = np.abs(vis)
    good = np.ones(vis.size, dtype=bool)
    edges = np.linspace(0.0, float(np.max(radius)) + 1e-9, 10)
    for lower, upper in zip(edges[:-1], edges[1:], strict=True):
        members = (radius >= lower) & (radius < upper)
        if np.count_nonzero(members) < 8:
            continue
        values = amplitude[members]
        median = np.median(values)
        mad = 1.4826 * np.median(np.abs(values - median))
        threshold = median + sigma_threshold * max(float(mad), 1e-12)
        good[members] = values <= threshold
    return good


def solve_reference_gains(
    n_antennas: int, calibrator_antennas: IntArray, calibrator_vis: ComplexArray
) -> ComplexArray:
    gains = np.ones(n_antennas, dtype=np.complex128)
    for antenna in range(1, n_antennas):
        values = calibrator_vis[calibrator_antennas == antenna]
        if values.size == 0:
            raise ValueError(f"No calibrator samples for antenna {antenna}")
        gains[antenna] = np.median(values.real) + 1j * np.median(values.imag)
    return gains


def apply_calibration(
    vis: ComplexArray, ant1: IntArray, ant2: IntArray, gains: ComplexArray
) -> ComplexArray:
    denominator = gains[ant1] * np.conj(gains[ant2])
    if np.any(np.abs(denominator) < 1e-12):
        raise ValueError("Calibration contains a near-zero antenna gain")
    return np.asarray(vis / denominator, dtype=np.complex128)


def grid_visibilities(
    size: int, uv: IntArray, vis: ComplexArray, good: BoolArray
) -> tuple[ComplexArray, FloatArray]:
    grid = np.zeros((size, size), dtype=np.complex128)
    weights = np.zeros((size, size), dtype=np.float64)
    centre = size // 2
    for (u, v), value, accepted in zip(uv, vis, good, strict=True):
        if not accepted:
            continue
        y = centre + int(v)
        x = centre + int(u)
        yc = centre - int(v)
        xc = centre - int(u)
        if 0 <= x < size and 0 <= y < size:
            grid[y, x] += value
            weights[y, x] += 1.0
        if 0 <= xc < size and 0 <= yc < size:
            grid[yc, xc] += np.conj(value)
            weights[yc, xc] += 1.0
    populated = weights > 0
    grid[populated] /= weights[populated]
    return grid, weights


def dirty_image(
    size: int, uv: IntArray, vis: ComplexArray, good: BoolArray
) -> tuple[FloatArray, FloatArray]:
    grid, weights = grid_visibilities(size, uv, vis, good)
    sampling = (weights > 0).astype(np.complex128)
    image = np.fft.fftshift(np.fft.ifft2(np.fft.ifftshift(grid))).real
    psf = np.fft.fftshift(np.fft.ifft2(np.fft.ifftshift(sampling))).real
    peak = float(np.max(np.abs(psf)))
    if peak <= 0:
        raise ValueError("No valid visibility samples were available for imaging")
    return (image / peak).astype(np.float64), (psf / peak).astype(np.float64)


def normalised_rmse(estimate: ComplexArray | FloatArray, truth: ComplexArray | FloatArray) -> float:
    numerator = np.linalg.norm(estimate - truth)
    denominator = max(float(np.linalg.norm(truth)), 1e-12)
    return float(numerator / denominator)
