"""Retry budget for slow text-shell firmware (LiteVNA64, ~5 s per sweep)."""

from NanoVNASaver.Hardware import VNA as vna_module


def test_budget_covers_slow_sweep_and_scales(monkeypatch):
    base = vna_module._max_retries(1000, 101)
    # ~0.1 s per retry: a 5 s answer must fit
    assert base * 0.1 >= 5
    monkeypatch.setattr(vna_module, "SLOW_FIRMWARE_RETRIES",
                        vna_module.SLOW_FIRMWARE_RETRIES * 8)
    assert vna_module._max_retries(1000, 101) > base
