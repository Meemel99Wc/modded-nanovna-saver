"""Frequency limit of the H4 driver: our LiteVNA64 firmware reaches 6.3 GHz."""

from unittest import mock

from NanoVNASaver.Hardware import NanoVNA_H4 as h4_mod
from NanoVNASaver.Hardware import VNA as vna_module
from NanoVNASaver.Hardware.NanoVNA_H import NanoVNA_H


def make(info: str):
    with mock.patch.object(NanoVNA_H, "__init__", lambda self, iface: None):
        vna = h4_mod.NanoVNA_H4.__new__(h4_mod.NanoVNA_H4)
        vna.features = set()
        vna.exec_command = lambda cmd, wait=0: iter(info.splitlines())
        h4_mod.NanoVNA_H4.__init__(vna, None)
    return vna


def test_litevna64_firmware_gets_6_3_ghz():
    vna = make("Board: ZN406-VNA (NanoVNA-H 4 compatible, LiteVNA64 hardware)")
    assert vna.sweep_max_freq_hz == 6300e6
    assert vna.sweep_points_max == 401


def test_real_nanovna_h4_stays_at_1_5_ghz():
    vna = make("NanoVNA-H 4\nVersion: 1.2.3")
    assert vna.sweep_max_freq_hz == 1500e6
    assert vna.sweep_points_max != 401


def test_litevna64_firmware_waits_longer_for_slow_answers():
    vna = make("Board: ZN406-VNA (NanoVNA-H 4 compatible, LiteVNA64 hardware)")
    assert vna.slow_firmware_retries == vna_module.SLOW_FIRMWARE_RETRIES
    assert vna_module._max_retries(1000, 101, vna.slow_firmware_retries) * 0.1 >= 5


def test_real_nanovna_h4_keeps_the_original_retry_budget():
    vna = make("NanoVNA-H 4\nVersion: 1.2.3")
    assert vna.slow_firmware_retries == 0
    assert vna_module._max_retries(1000, 101, vna.slow_firmware_retries) == 41

