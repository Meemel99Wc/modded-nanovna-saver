"""Device state from USB and following the device across resets
(litevna-openvna#190).

The USB side is faked: a sysfs tree in tmp_path for the scanner, and a
scan function for the watcher, which then drives Saver's virtual device as
if it were a LiteVNA on USB port path "1-1".
"""

import asyncio
import threading
import time
from types import SimpleNamespace

import pytest

from NanoVNASaver.Hardware import usb_state
from NanoVNASaver.Hardware.usb_state import (
    APP,
    GONE,
    ROM_DFU,
    STORAGE,
    VENDOR_BL,
    UsbDevice,
)

# --- scanner -------------------------------------------------------------


def _dev(root, name, vid, pid, product="", ifaces=(), serial="ZN406001"):
    d = root / name
    d.mkdir()
    (d / "idVendor").write_text(f"{vid:04x}\n")
    (d / "idProduct").write_text(f"{pid:04x}\n")
    (d / "product").write_text(product + "\n")
    (d / "serial").write_text(serial + "\n")
    for num, (cls, tty) in enumerate(ifaces):
        i = root / f"{name}:1.{num}"
        i.mkdir()
        (i / "bInterfaceClass").write_text(f"{cls:02x}\n")
        if tty:
            (i / "tty" / tty).mkdir(parents=True)


def test_scan_sysfs_states(tmp_path):
    _dev(tmp_path, "1-1", 0x04B4, 0x0008, "ZN406-VNA",
         [(0x02, "ttyACM0"), (0x0A, None)])
    _dev(tmp_path, "1-2", 0x04B4, 0x0008, "ZN406-VNA", [(0x08, None)],
         serial="ZN406001B")
    _dev(tmp_path, "1-3", 0x04B4, 0x0008, "CDC-ACM Demo",
         [(0x02, "ttyACM1"), (0x0A, None)])
    _dev(tmp_path, "1-4", 0x2E3C, 0xDF11, "AT32 DFU", [(0xFE, None)])
    _dev(tmp_path, "1-5", 0x046D, 0xC077, "mouse", [(0x03, None)])
    (tmp_path / "usb1").mkdir()  # root hub
    found = {d.location: d for d in usb_state.scan_sysfs(tmp_path)}
    assert set(found) == {"1-1", "1-2", "1-3", "1-4"}
    assert found["1-1"].state == APP
    assert found["1-1"].port == "/dev/ttyACM0"
    assert found["1-2"].state == STORAGE and found["1-2"].port is None
    assert found["1-3"].state == VENDOR_BL
    assert found["1-4"].state == ROM_DFU
    assert usb_state.by_port(found.values(), "/dev/ttyACM1").location == "1-3"


def test_scan_serial_uses_device_path_as_identity():
    ports = [
        SimpleNamespace(device="/dev/ttyACM3", vid=0x04B4, pid=0x0008,
                        product="ZN406-VNA", location="3-2:1.0",
                        serial_number="ZN406001"),
        SimpleNamespace(device="COM7", vid=0x04B4, pid=0x0008,
                        product="CDC-ACM Demo", location=None,
                        serial_number=None),
        SimpleNamespace(device="/dev/ttyUSB0", vid=None, pid=None),
    ]
    found = usb_state.scan_serial(lambda: ports)
    assert [(d.location, d.state, d.port) for d in found] == [
        ("3-2", APP, "/dev/ttyACM3"),
        ("COM7", VENDOR_BL, "COM7"),
    ]


# --- watcher with Saver's virtual device ----------------------------------

mcp = pytest.importorskip("mcp")

from PySide6 import QtWidgets  # noqa: E402

from NanoVNASaver.Hardware import VirtualVNA  # noqa: E402
from NanoVNASaver.MCP import MCPOptions  # noqa: E402
from NanoVNASaver.MCP import device_watch  # noqa: E402



class FakeUsb:
    """The virtual device seen as a LiteVNA on USB port path 1-1."""

    def __init__(self) -> None:
        self.state = APP

    def __call__(self) -> list[UsbDevice]:
        if self.state == GONE:
            return []
        port = "virtual" if self.state == APP else None
        return [UsbDevice("1-1", 0x04B4, 0x0008, self.state, port)]


@pytest.fixture()
def saver(tmp_path, monkeypatch):
    monkeypatch.setattr(device_watch, "RETRY_S", 0.0)
    # reconnecting rescans ports: never probe a real VNA that is plugged in
    import serial.tools.list_ports as list_ports

    monkeypatch.setattr(list_ports, "comports", lambda *a, **k: [])
    VirtualVNA.enable()
    qapp = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from NanoVNASaver.NanoVNASaver import NanoVNASaver

    window = NanoVNASaver(MCPOptions(headless=True, workspace=tmp_path))
    svc = window.mcp.build_service()
    window.mcp.control.allow(True)
    usb = FakeUsb()
    svc.api.watch._scan = usb
    yield qapp, window, svc, usb
    window.mcp.control.allow(False)
    if window.worker.isRunning():
        window.worker.quit()
        window.worker.wait(5000)
    if window.vna.connected():
        window.serial_control.disconnect_device()


def pump(qapp, until, timeout=30.0):
    deadline = time.monotonic() + timeout
    while not until():
        qapp.processEvents()
        time.sleep(0.005)
        assert time.monotonic() < deadline, "timeout"


def connect_virtual(qapp, window, svc):
    result = svc.api.device_connect("virtual")
    fut = getattr(result, "future", None)
    if fut is not None:
        pump(qapp, fut.done)
    pump(qapp, lambda: not window.worker.isRunning())
    assert window.vna.connected()
    assert svc.api.watch.location == "1-1"


def wait(qapp, svc, state, timeout_s=10.0):
    fut = svc.api.device_wait(state, timeout_s).future
    pump(qapp, fut.done, timeout_s + 10)
    return fut.result()


def test_storage_and_back_reconnects_by_itself(saver):
    qapp, window, svc, usb = saver
    connect_virtual(qapp, window, svc)

    usb.state = STORAGE  # e.g. usb mode storage on the device
    seen = wait(qapp, svc, STORAGE)
    assert seen["state"] == STORAGE and not seen.get("timeout")
    assert seen["lost"] and not seen["connected"]
    assert not window.vna.connected()
    assert "storage" in svc.api.device_info()["usb"]["reason"]

    usb.state = APP
    seen = wait(qapp, svc, APP)
    assert not seen.get("timeout"), seen
    assert seen["connected"] and not seen["lost"]
    assert seen["reconnects"] == 1
    assert window.vna.connected()

    fut = svc.api.sweep_run().future  # measuring works again
    pump(qapp, fut.done)
    assert fut.exception() is None


def test_reset_through_gone_10_times(saver):
    qapp, window, svc, usb = saver
    connect_virtual(qapp, window, svc)
    for n in range(10):
        usb.state = GONE
        assert wait(qapp, svc, GONE)["state"] == GONE
        usb.state = APP
        seen = wait(qapp, svc, APP)
        assert seen["connected"] and seen["reconnects"] == n + 1, seen


def test_lost_during_sweep_fails_the_sweep(saver):
    qapp, window, svc, usb = saver
    connect_virtual(qapp, window, svc)
    fut = svc.api._start_sweep()
    assert window.worker.isRunning() or fut.done()
    usb.state = VENDOR_BL
    svc.api.watch.poll()
    pump(qapp, fut.done)
    if window.worker.isRunning() is False and fut.exception() is None:
        pytest.skip("virtual sweep finished before the device was lost")
    assert "vendor_bl" in str(fut.exception())


def test_wait_times_out_with_seen_state(saver):
    qapp, window, svc, usb = saver
    connect_virtual(qapp, window, svc)
    seen = wait(qapp, svc, ROM_DFU, timeout_s=0.6)
    assert seen["timeout"] and seen["wanted"] == ROM_DFU
    assert seen["state"] == APP


def test_user_disconnect_stops_following(saver):
    qapp, window, svc, usb = saver
    connect_virtual(qapp, window, svc)
    svc.api.device_disconnect()
    assert svc.api.watch.location is None
    usb.state = APP
    svc.api.watch.poll()
    assert not window.vna.connected()  # no reconnect behind the user's back


def test_unknown_state_is_refused(saver):
    _, _, svc, _ = saver
    with pytest.raises(ValueError):
        svc.api.device_wait("sleeping", 1)


class RecordingSession:
    def __init__(self) -> None:
        self.sent: list[tuple[str, object]] = []

    async def send_resource_updated(self, uri) -> None:
        self.sent.append(("updated", str(uri)))

    async def send_log_message(self, level, data, logger=None) -> None:
        self.sent.append((level, data))


def test_known_sessions_are_told_when_the_device_goes(saver):
    qapp, window, svc, usb = saver
    connect_virtual(qapp, window, svc)
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    session = RecordingSession()
    svc._sessions[id(session)] = (session, loop)
    try:
        usb.state = STORAGE
        svc.api.watch.poll()
        pump(qapp, lambda: len(session.sent) >= 2, 10)
    finally:
        loop.call_soon_threadsafe(loop.stop)
        thread.join(5)
        loop.close()
    assert session.sent[0] == ("updated", "saver://device")
    level, data = session.sent[1]
    assert level == "warning"
    assert data["event"] == "lost" and data["state"] == STORAGE
