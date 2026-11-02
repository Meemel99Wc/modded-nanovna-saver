"""Frequency limit of the H4 driver: our LiteVNA64 firmware reaches 6.3 GHz."""

from unittest import mock

from NanoVNASaver.Hardware import NanoVNA_H4 as h4_mod
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


def test_real_nanovna_h4_stays_at_1_5_ghz():
    vna = make("NanoVNA-H 4\nVersion: 1.2.3")
    assert vna.sweep_max_freq_hz == 1500e6
