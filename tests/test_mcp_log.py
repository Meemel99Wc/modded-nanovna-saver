"""AI log lines (MCP/control.py): Finnish display, outcome unchanged."""

import json
import re

from NanoVNASaver.MCP.control import OUTCOME_TEXT, AIControl, LogEntry

ENGLISH = re.compile(
    r"not allowed|another action|declined|pressed|revoked|timeout\b|"
    r"\b(denied|error|stopped)\b"
)


def test_outcome_values_unchanged_and_shown_in_finnish():
    assert set(OUTCOME_TEXT) == {"ok", "denied", "error", "timeout",
                                 "stopped"}
    shown = {k: LogEntry(0, "t", "act", {}, k).line().split("-> ")[1]
             for k in OUTCOME_TEXT}
    assert shown == {"ok": "ok", "denied": "estetty", "error": "virhe",
                     "timeout": "aikakatkaisu", "stopped": "pysäytetty"}


def test_stop_line_finnish_json_log_machine_readable(tmp_path):
    log_file = tmp_path / "ai.jsonl"
    control = AIControl(log_file)
    control.allow(True)
    control.stop()
    entry = control.entries[-1]
    assert entry.outcome == "stopped"
    assert not ENGLISH.search(entry.line()), entry.line()
    row = json.loads(log_file.read_text(encoding="utf-8").splitlines()[-1])
    assert row["outcome"] == "stopped"


def test_server_log_details_are_finnish():
    from pathlib import Path

    from NanoVNASaver.MCP import server

    src = Path(server.__file__).read_text(encoding="utf-8")
    details = re.findall(r'\blog\("(\w+)", f?"([^"]*)"', src)
    assert {o for o, _ in details} <= set(OUTCOME_TEXT)
    assert len(details) >= 5
    for _, detail in details:
        shown = re.sub(r"\{[^}]*\}", "", detail)  # f-string fields
        assert not ENGLISH.search(shown), detail
