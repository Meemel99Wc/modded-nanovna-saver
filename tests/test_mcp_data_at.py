"""data_at interpolation (MCP/api.py _interp_point)."""

import math

import numpy as np
import pytest

pytest.importorskip("PySide6")

from NanoVNASaver.MCP.api import ActionError, _interp_point
from NanoVNASaver.RFTools import Datapoint

F0, Q = 145e6, 8


def bandpass_gain(freqs, f0, q):
    """dB gain of |S21| = a / (1 + x^2), x = Q (f/f0 - f0/f): the VirtualVNA filter model."""
    x = q * (freqs / f0 - f0 / freqs)
    return 20 * np.log10(0.95 / (1 + x * x))


def points(freqs, gains_db):
    return [Datapoint(int(f), 10 ** (g / 20), 0.0) for f, g in zip(freqs, gains_db, strict=False)]


def grid():
    freqs = np.linspace(100e6, 300e6, 101)          # 2 MHz step, as a wide sweep of the eval task
    return freqs, points(freqs, bandpass_gain(freqs, F0, Q))


def truth_db(f):
    return float(bandpass_gain(np.array([f]), F0, Q)[0])


def db_of(dp):
    return 20 * math.log10(math.hypot(dp.re, dp.im))


def test_off_grid_value_is_much_closer_than_nearest_point():
    freqs, data = grid()
    f = 173e6                                        # between the 172 and 174 MHz points, steep part of the edge
    dp, step, interpolated = _interp_point(data, f)
    nearest = min(data, key=lambda d: abs(d.freq - f))
    assert interpolated and step == pytest.approx(2e6)
    assert abs(db_of(dp) - truth_db(f)) < 0.15
    # the old behaviour (nearest point) was far outside the 0.2 dB the eval task asks for
    assert abs(db_of(nearest) - truth_db(f)) > 0.3


def test_point_on_the_grid_is_returned_as_measured():
    freqs, data = grid()
    dp, step, interpolated = _interp_point(data, float(freqs[40]))
    assert not interpolated and dp == data[40] and step == pytest.approx(2e6)
    dp, _, interpolated = _interp_point(data, float(freqs[0]))
    assert not interpolated and dp == data[0]
    dp, _, interpolated = _interp_point(data, float(freqs[-1]))
    assert not interpolated and dp == data[-1]


def test_outside_the_sweep_is_an_error_not_the_edge_point():
    freqs, data = grid()
    with pytest.raises(ActionError, match="ulkopuolella"):
        _interp_point(data, 50e6)
    with pytest.raises(ActionError, match="ulkopuolella"):
        _interp_point(data, 301e6)


def test_phase_is_interpolated_the_short_way_round():
    # +170 deg and -170 deg: halfway is 180 deg, not 0 deg
    a = Datapoint(100, math.cos(math.radians(170)), math.sin(math.radians(170)))
    b = Datapoint(200, math.cos(math.radians(-170)), math.sin(math.radians(-170)))
    dp, _, interpolated = _interp_point([a, b], 150)
    assert interpolated
    assert abs(math.degrees(math.atan2(dp.im, dp.re))) == pytest.approx(180, abs=0.5)
    assert math.hypot(dp.re, dp.im) == pytest.approx(1.0, abs=1e-6)


def test_unsorted_input_and_zero_magnitude_do_not_break():
    a = Datapoint(200, 0.0, 0.0)
    b = Datapoint(100, 1.0, 0.0)
    dp, _, interpolated = _interp_point([a, b], 150)        # plain complex interpolation when a magnitude is 0
    assert interpolated and dp.re == pytest.approx(0.5)
