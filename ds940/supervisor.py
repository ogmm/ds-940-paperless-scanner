"""Restart a worker when the vendor library exits or stops responding."""

import argparse
import fcntl
import json
import logging
import os
from pathlib import Path
import signal
import subprocess
import sys
from threading import Event
import time

from .config import Settings
from .spool import atomic_json


LOG = logging.getLogger(__name__)


def read_status(path):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(value, dict) and isinstance(value.get("updated"), (int, float)):
            return value
    except (OSError, ValueError):
        pass
    return {}


class WorkerGuard:
    def __init__(self, started, timeout=180, error_limit=3):
        self.started = self.progress = started
        self.last_update = 0
        self.errors = 0
        self.timeout = timeout
        self.error_limit = error_limit

    def reason(self, status, now):
        updated = status.get("updated", 0)
        if self.started <= updated <= now + 5 and updated > self.last_update:
            self.last_update = updated
            self.progress = min(updated, now)
            self.errors = self.errors + 1 if status.get("state") == "retry_after_error" else 0
        if self.errors >= self.error_limit:
            return "three consecutive scanner errors"
        if now - self.progress > self.timeout:
            return f"no worker progress for {self.timeout} seconds"
        return None


def stop_worker(child):
    if child.poll() is not None:
        return
    child.terminate()
    try:
        child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        LOG.warning("Worker did not exit, stopping PID %s", child.pid)
        child.kill()
        child.wait(timeout=5)


def supervise(work, stop):
    def record(state, child=None, reason=None):
        atomic_json(
            work / "supervisor-status.json",
            {"updated": time.time(), "state": state, "worker_pid": child.pid if child else None, "reason": reason},
        )

    child = None
    try:
        while not stop.is_set():
            guard = WorkerGuard(time.time())
            child = subprocess.Popen([sys.executable, "-m", "ds940.worker"])
            LOG.info("Started worker PID %s", child.pid)
            reason = None
            while child.poll() is None and not stop.is_set():
                reason = guard.reason(read_status(work / "auto-status.json"), time.time())
                if reason:
                    break
                record("running", child)
                stop.wait(2)
            if stop.is_set():
                break
            reason = reason or f"worker exited with status {child.returncode}"
            LOG.warning("Restarting worker: %s", reason)
            stop_worker(child)
            record("recovering", reason=reason)
            stop.wait(15)
    finally:
        if child:
            stop_worker(child)
        record("stopped")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("serve", "healthcheck"), default="serve", nargs="?")
    args = parser.parse_args()
    if args.command == "healthcheck":
        work = Path(os.environ.get("WORK_DIR", "/work"))
        status = read_status(work / "supervisor-status.json")
        age = time.time() - status.get("updated", 0)
        return 0 if status.get("state") in ("running", "recovering") and -5 <= age < 35 else 1

    os.umask(0o007)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = Settings.from_environment()
    settings.work.mkdir(parents=True, exist_ok=True)
    stop = Event()
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_: stop.set())
    with (settings.work / "supervisor.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise SystemExit("A scanner supervisor already owns this work directory") from error
        supervise(settings.work, stop)
    return 0


if __name__ == "__main__":
    sys.exit(main())
