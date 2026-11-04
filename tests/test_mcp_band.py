"""S21 -3 dB band in data_summary (MCP/api.py _minus_3db_band)."""

import math

import numpy as np
import pytest

pytest.importorskip("PySide6")

from NanoVNASaver.MCP.api import _minus_3db_band
from NanoVNASaver.RFTools import Datapoint


def points(freqs, gains_db):
    out = []
    for f, g in zip(freqs, gains_db, strict=False):
        mag = 10 ** (g / 20)
        out.append(Datapoint(int(f), mag, 0.0))
    return out


def bandpass_truth(f0, q, drop_db=3.0):
    """Exact -3 dB edges of |S21| = a / (1 + x^2), x = Q (f/f0 - f0/f)
    (VirtualVNA filter model)."""
    x = math.sqrt(10 ** (drop_db / 20) - 1)
    k = x / q
    f_lo = f0 * (-k + math.sqrt(k * k + 4)) / 2
    f_hi = f0 * (k + math.sqrt(k * k + 4)) / 2
    return f_lo, f_hi


def bandpass_gain(freqs, f0, q):
    x = q * (freqs / f0 - f0 / freqs)
    return 20 * np.log10(0.95 / (1 + x * x))


def test_two_peaks_band_only_around_main_maximum():
    freqs = np.linspace(100e6, 200e6, 201)
    main = bandpass_gain(freqs, 130e6, 20)
    # second peak 1 dB below the main one, far outside the main band
    side = bandpass_gain(freqs, 180e6, 40) - 1
    gains = np.maximum(main, side)
    band = _minus_3db_band(points(freqs, gains))
    f_lo, f_hi = bandpass_truth(130e6, 20)
    assert band["stop_hz"] < 160e6, band
    assert abs(band["start_hz"] - f_lo) / f_lo < 1e-3
    assert abs(band["stop_hz"] - f_hi) / f_hi < 1e-3
    assert band["open_low"] is False and band["open_high"] is False


def test_interpolated_edges_on_known_curve():
    f0, q = 145e6, 8.0
    freqs = np.linspace(100e6, 200e6, 101)  # 1 MHz step
    band = _minus_3db_band(points(freqs, bandpass_gain(freqs, f0, q)))
    f_lo, f_hi = bandpass_truth(f0, q)
    assert band["edges_interpolated"] is True
    assert abs(band["start_hz"] - f_lo) / f_lo < 1e-3
    assert abs(band["stop_hz"] - f_hi) / f_hi < 1e-3
    bw = f_hi - f_lo
    assert abs(band["bandwidth_hz"] - bw) / bw < 1e-2
    assert band["bandwidth_hz"] == band["stop_hz"] - band["start_hz"]
    assert band["center_hz"] == round(
        math.sqrt(band["start_hz"] * band["stop_hz"]))
    # f1 * f2 = f0^2 for this model: geometric centre is f0
    assert abs(band["center_hz"] - f0) / f0 < 1e-3


def test_linear_slope_exact_interpolation():
    # gain falls linearly 1 dB / 10 Hz on both sides: edges at +-30 Hz
    freqs = list(range(1000, 1101, 10))
    gains = [-abs(f - 1050) / 10 for f in freqs]
    band = _minus_3db_band(points(freqs, gains))
    assert band["start_hz"] == 1020
    assert band["stop_hz"] == 1080
    assert band["bandwidth_hz"] == 60


def test_open_edges_are_not_reported_as_measured():
    freqs = np.linspace(140e6, 150e6, 51)  # whole sweep inside the band
    band = _minus_3db_band(points(freqs, bandpass_gain(freqs, 145e6, 8)))
    assert band["open_low"] is True and band["open_high"] is True
    assert band["start_hz"] is None and band["stop_hz"] is None
    assert band["bandwidth_hz"] is None and band["center_hz"] is None


def test_open_high_only():
    freqs = np.linspace(100e6, 150e6, 101)
    band = _minus_3db_band(points(freqs, bandpass_gain(freqs, 145e6, 8)))
    f_lo, _ = bandpass_truth(145e6, 8)
    assert band["open_low"] is False and band["open_high"] is True
    assert abs(band["start_hz"] - f_lo) / f_lo < 1e-3
    assert band["stop_hz"] is None and band["bandwidth_hz"] is None
