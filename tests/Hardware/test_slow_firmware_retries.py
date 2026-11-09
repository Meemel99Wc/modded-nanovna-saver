"""Retry budget: slow text-shell firmware (LiteVNA64, ~5 s per sweep) gets extra
retries, every other device keeps the original budget (review of PR #7)."""

from NanoVNASaver.Hardware import VNA as vna_module


def test_default_budget_is_the_original_one():
    # 20 + 20 * 1 + 1 ** 1.3 * 1 = 41 retries: the value before the slow-firmware change
    assert vna_module._max_retries(1000, 101) == 41
    assert vna_module.VNA.slow_firmware_retries == 0


def test_slow_budget_covers_a_5_second_answer():
    extra = vna_module.SLOW_FIRMWARE_RETRIES
    # ~0.1 s per retry: a 5 s answer must fit
    assert vna_module._max_retries(1000, 101, extra) * 0.1 >= 5


def test_extra_budget_scales():
    extra = vna_module.SLOW_FIRMWARE_RETRIES
    assert vna_module._max_retries(1000, 101, extra * 8) > vna_module._max_retries(
        1000, 101, extra
    )
