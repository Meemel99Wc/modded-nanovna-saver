"""Allowlist of the device_shell tools (MCP/shell_allowlist.py)."""

import pytest

from NanoVNASaver.MCP.registry import Risk
from NanoVNASaver.MCP.shell_allowlist import (
    ShellRefused,
    allowed_commands,
    check,
    classify,
)

READ = ["version", "info", "sweep-stats", "sd stats", "cal why",
        "msc log", "usb status", "sweep", "ref show", "power", "  version  "]
ACT = ["input key 4f 00 down", "input ptr 100 -20 move", "input wheel -3",
       "sweep 50000000 1500000000 201", "sweep 1000000 2000000",
       "sweep-avg 16", "ref on", "power lo 2", "cal off", "recall 1"]
PERSIST = ["save 2", "meas save", "meas note Antenna 3 test"]
NEVER = ["reset", "config-reset", "usb mode storage force", "usb reset",
         "sd read 0", "sd cs PB 9", "pin mode PA 6 1", "rf set 1 1 1 1 1",
         "i2c probe", "clk-set 0", "clk-drive 1", "test-mode on",
         "fs", "bootloader", "dfu", "flash", "capture", "cal open",
         "save 5", "sweep-avg 17", "save"]


@pytest.mark.parametrize("risk,commands",
                         [(Risk.READ, READ), (Risk.ACT, ACT),
                          (Risk.PERSIST, PERSIST)])
def test_listed_commands_have_their_class(risk, commands):
    for cmd in commands:
        assert check(cmd, risk) == " ".join(cmd.split())


@pytest.mark.parametrize("cmd", NEVER)
def test_unlisted_commands_refused(cmd):
    with pytest.raises(ShellRefused):
        classify(cmd)


@pytest.mark.parametrize("cmd", [
    "version; reset", "version && reset", "version | cat", "info\nreset",
    "info\rreset", "version `reset`", "ver$(sion)", "info > x",
    "", "   ", "version " + "a" * 200, "versiön",
])
def test_injection_and_junk_refused(cmd):
    with pytest.raises(ShellRefused):
        classify(cmd)


def test_wrong_class_names_the_right_tool():
    with pytest.raises(ShellRefused, match="device_shell_act"):
        check("sweep-avg 4", Risk.READ)
    with pytest.raises(ShellRefused, match="device_shell_persist"):
        check("save 1", Risk.ACT)
    with pytest.raises(ShellRefused, match="device_shell"):
        check("version", Risk.PERSIST)


def test_every_rule_has_a_reason_and_class_lists_exist():
    from NanoVNASaver.MCP.shell_allowlist import RULES

    assert all(r.reason for r in RULES)
    for risk in (Risk.READ, Risk.ACT, Risk.PERSIST):
        assert allowed_commands(risk)
