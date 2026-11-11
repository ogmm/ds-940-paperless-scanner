"""Wait for a sheet, capture both sides, and publish one complete PDF."""

import fcntl
import logging
import os
import signal
import socket
from threading import Event
import time

from PIL import Image

from .config import DPI, Settings
from .sane import COVER_OPEN, DEVICE_BUSY, EOF, JAMMED, NO_DOCS, SaneDevice, SaneFailure
from .spool import ScanSpool, atomic_json, build_pdf


LOG = logging.getLogger(__name__)
MAX_FRAME_BYTES = 64 * 1024 * 1024
FRAME_READ_SECONDS = 60
SCAN_PORT = 54921


def frame_layout(params):
    width, height, stride = params.pixels_per_line, params.lines, params.bytes_per_line
    if params.format != 1 or params.depth != 8:
        raise RuntimeError("Expected an 8-bit RGB image")
    if not (0 < width <= 10000 and 0 < height <= 10000 and width * 3 <= stride <= width * 3 + 4096):
        raise RuntimeError("Invalid scanner frame dimensions")
    expected = stride * height
    if expected > MAX_FRAME_BYTES:
        raise RuntimeError("Scanner frame exceeds the memory limit")
    return width, height, stride, expected


def read_side(device, folder, page):
    width, height, stride, expected = frame_layout(device.parameters())
    raw = folder / f"page-{page}.rgb.part"
    received = 0
    deadline = time.monotonic() + FRAME_READ_SECONDS
    with raw.open("xb") as stream:
        while True:
            if time.monotonic() >= deadline:
                raise RuntimeError("Scanner frame read timed out")
            status, data = device.read()
            if status not in (0, EOF):
                raise SaneFailure(f"read side {page}", status)
            if received + len(data) > expected:
                raise RuntimeError("Scanner sent too much image data")
            stream.write(data)
            received += len(data)
            if status == EOF:
                break
            if not data:
                time.sleep(0.02)
        stream.flush()
        os.fsync(stream.fileno())
    if received != expected:
        raise RuntimeError(f"Incomplete frame: received {received} of {expected} bytes")

    target = folder / f"page-{page}.tif"
    with Image.frombytes("RGB", (width, height), raw.read_bytes(), "raw", "RGB", stride, 1) as image:
        image.save(target, format="TIFF", dpi=(DPI, DPI))
    raw.unlink()
    return target


def capture_if_ready(device, spool, paper_size, on_scan):
    status = device.start()
    if status == NO_DOCS:
        return None
    if status:
        raise SaneFailure("start front side", status)

    folder = spool.new_scan()
    manifest_path = folder / "manifest.json"
    manifest = {"id": folder.name, "phase": "scanning", "dpi": DPI, "duplex": True, "paper_size": paper_size}
    atomic_json(manifest_path, manifest, durable=True)
    try:
        on_scan()
        front = read_side(device, folder, 1)
        status = device.start()
        if status:
            raise SaneFailure("start back side", status)
        back = read_side(device, folder, 2)
        build_pdf([front, back], folder / "document.pdf")
        manifest.update(phase="ready", pages=2)
        atomic_json(manifest_path, manifest, durable=True)
        spool.publish(folder)
    except Exception as error:
        if manifest["phase"] != "ready":
            manifest.update(phase="error", error=str(error))
            atomic_json(manifest_path, manifest, durable=True)
        raise
    return folder.name


def scanner_greeting(ip):
    with socket.create_connection((ip, SCAN_PORT), timeout=2) as client:
        client.settimeout(2)
        try:
            return client.recv(64)
        except TimeoutError:
            return b""


def retry_state(error, scanner_ip):
    if isinstance(error, SaneFailure):
        if error.status in (JAMMED, COVER_OPEN):
            return "paper_blocked", 20
        if error.status == DEVICE_BUSY:
            return "scanner_busy", 90
        if error.action == "open":
            try:
                greeting = scanner_greeting(scanner_ip)
            except OSError:
                return "scanner_offline", 30
            if greeting.startswith(b"-NG 401"):
                return "scanner_busy", 90
    return "retry_after_error", 15


def serve(settings, stop):
    def status(state, **details):
        atomic_json(
            settings.work / "auto-status.json",
            {"updated": time.time(), "state": state, "paper_size": settings.paper_size, **details},
        )

    settings.configure_driver()
    spool = ScanSpool(settings.work, settings.output)
    status("connecting")
    previous_state = None
    next_recovery = 0.0
    try:
        while not stop.is_set():
            if time.monotonic() >= next_recovery:
                spool.recover()
                next_recovery = time.monotonic() + 30
            try:
                with SaneDevice(settings.paper_size) as device:
                    geometry = device.geometry
                    capture_if_ready(device, spool, settings.paper_size, lambda: status("scanning"))
                if previous_state != "waiting_for_paper":
                    LOG.info("Ready for paper, %s, duplex, %d dpi", geometry, DPI)
                previous_state = "waiting_for_paper"
                status(previous_state, geometry=geometry)
                stop.wait(3)
            except (OSError, RuntimeError, ValueError, KeyError) as error:
                state, delay = retry_state(error, settings.scanner_ip)
                if state != previous_state or state == "retry_after_error":
                    LOG.warning("%s. Retrying in %d seconds (%s).", error, delay, state)
                previous_state = state
                status(state, retry_seconds=delay)
                if state == "retry_after_error":
                    # The supervisor counts failed attempts, not repeated heartbeats.
                    stop.wait(delay)
                    continue
                deadline = time.monotonic() + delay
                while not stop.is_set() and (remaining := deadline - time.monotonic()) > 0:
                    if stop.wait(min(5, remaining)):
                        break
                    status(state)
    finally:
        status("stopped")


def main():
    os.umask(0o007)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = Settings.from_environment()
    stop = Event()
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_: stop.set())
    with (settings.work / "worker.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise SystemExit("A worker already owns this work directory") from error
        serve(settings, stop)


if __name__ == "__main__":
    main()
