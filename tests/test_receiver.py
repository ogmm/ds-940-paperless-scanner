from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from pypdf import PdfReader

from ds940.sane import EOF, JAMMED, NO_DOCS, FrameParameters, SaneFailure
from ds940.spool import ScanSpool
from ds940.worker import capture_if_ready, retry_state


class Feeder:
    def __init__(self, *, height=300, starts=(0, 0), complete=True):
        self.height = height
        self.starts = iter(starts)
        frame = bytes([160]) * 300 * height
        if not complete:
            frame = frame[:-300]
        chunks = [(0, frame[i:i + 65536]) for i in range(0, len(frame), 65536)]
        self.chunks = iter((chunks + [(EOF, b"")]) * 2)

    def start(self):
        return next(self.starts)

    def parameters(self):
        return FrameParameters(format=1, bytes_per_line=300, pixels_per_line=100, lines=self.height, depth=8)

    def read(self):
        return next(self.chunks)


class ReceiverTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        work = root / "work"
        work.mkdir()
        self.consume = root / "consume"
        self.consume.mkdir()
        self.spool = ScanSpool(work, self.consume)
        self.on_scan = Mock()

    def manifests(self):
        return list(self.spool.jobs.glob("*/manifest.json"))

    def test_empty_feeder_creates_no_work(self):
        result = capture_if_ready(Feeder(starts=(NO_DOCS,)), self.spool, "a4", self.on_scan)
        self.assertIsNone(result)
        self.assertEqual(self.manifests(), [])
        self.on_scan.assert_not_called()

    def test_jammed_front_creates_no_pdf(self):
        with self.assertRaisesRegex(SaneFailure, "status 6"):
            capture_if_ready(Feeder(starts=(JAMMED,)), self.spool, "legal", self.on_scan)
        self.assertEqual(self.manifests(), [])
        self.assertEqual(list(self.consume.iterdir()), [])

    def test_duplex_pdf_preserves_legal_height(self):
        scan_id = capture_if_ready(Feeder(height=4200), self.spool, "legal", self.on_scan)
        files = list(self.consume.iterdir())
        self.assertEqual(files, [self.consume / f"{scan_id}.pdf"])
        pages = PdfReader(BytesIO(files[0].read_bytes())).pages
        self.assertEqual(len(pages), 2)
        for page in pages:
            self.assertAlmostEqual(float(page.mediabox.height), 1008)
            self.assertAlmostEqual(float(page.mediabox.width), 24)
        manifest = json.loads(self.manifests()[0].read_text(encoding="utf-8"))
        self.assertEqual(manifest["phase"], "forwarded")
        self.assertEqual(manifest["paper_size"], "legal")
        self.on_scan.assert_called_once()

    def test_incomplete_frame_is_retained_without_publishing(self):
        with self.assertRaisesRegex(RuntimeError, "Incomplete frame"):
            capture_if_ready(Feeder(complete=False), self.spool, "a4", self.on_scan)
        manifest = self.manifests()[0]
        self.assertTrue((manifest.parent / "page-1.rgb.part").exists())
        self.assertEqual(json.loads(manifest.read_bytes())["phase"], "error")
        self.spool.recover()
        self.assertEqual(list(self.consume.iterdir()), [])

    def test_back_failure_keeps_the_front_for_diagnosis(self):
        with self.assertRaisesRegex(SaneFailure, "start back side"):
            capture_if_ready(Feeder(starts=(0, JAMMED)), self.spool, "a4", self.on_scan)
        self.assertTrue((self.manifests()[0].parent / "page-1.tif").exists())
        self.assertEqual(list(self.consume.iterdir()), [])

    def test_recovery_retries_a_finished_pdf_after_output_failure(self):
        with patch.object(self.spool, "publish", side_effect=OSError("output unavailable")):
            with self.assertRaisesRegex(OSError, "output unavailable"):
                capture_if_ready(Feeder(), self.spool, "a4", self.on_scan)
        manifest = self.manifests()[0]
        self.assertEqual(json.loads(manifest.read_bytes())["phase"], "ready")
        self.assertEqual(list(self.consume.iterdir()), [])
        self.spool.recover()
        self.spool.recover()
        self.assertEqual(json.loads(manifest.read_bytes())["phase"], "forwarded")
        self.assertEqual(len(list(self.consume.glob("*.pdf"))), 1)

    def test_output_collision_leaves_a_ready_scan_in_the_spool(self):
        with patch.object(self.spool, "publish", return_value=False):
            scan_id = capture_if_ready(Feeder(), self.spool, "a4", self.on_scan)
        existing = self.consume / f"{scan_id}.pdf"
        existing.write_bytes(b"keep this file")
        with self.assertRaises(FileExistsError):
            self.spool.publish(self.manifests()[0].parent)
        self.assertEqual(existing.read_bytes(), b"keep this file")
        self.assertEqual(json.loads(self.manifests()[0].read_bytes())["phase"], "ready")

    def test_dimensions_limit_is_checked_before_reading(self):
        feeder = Feeder()
        feeder.parameters = Mock(return_value=FrameParameters(
            format=1, bytes_per_line=30000, pixels_per_line=10000, lines=10000, depth=8
        ))
        feeder.read = Mock()
        with self.assertRaisesRegex(RuntimeError, "memory limit"):
            capture_if_ready(feeder, self.spool, "a4", self.on_scan)
        feeder.read.assert_not_called()


class ConnectionTests(unittest.TestCase):
    def test_firmware_busy_greeting_gets_quiet_backoff(self):
        with patch("ds940.worker.scanner_greeting", return_value=b"-NG 401\r\n"):
            self.assertEqual(retry_state(SaneFailure("open", 4), "192.0.2.42"), ("scanner_busy", 90))

    def test_unreachable_scanner_is_treated_as_offline(self):
        with patch("ds940.worker.scanner_greeting", side_effect=TimeoutError):
            self.assertEqual(retry_state(SaneFailure("open", 4), "192.0.2.42"), ("scanner_offline", 30))

    def test_jam_waits_for_user_without_probe(self):
        with patch("ds940.worker.scanner_greeting") as probe:
            self.assertEqual(retry_state(SaneFailure("start front side", JAMMED), "192.0.2.42"), ("paper_blocked", 20))
        probe.assert_not_called()
