import os
import subprocess
import unittest
from unittest.mock import Mock, call, patch

from ds940.config import Settings
from ds940.sane import FIXED_SCALE, NO_DOCS, SaneDevice
from ds940.supervisor import WorkerGuard, stop_worker


class SettingsTests(unittest.TestCase):
    def test_requires_scanner_address(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "LAN IPv4"):
                Settings.from_environment()

    def test_a4_is_the_default(self):
        with patch.dict(os.environ, {"SCANNER_IP": "192.0.2.42"}, clear=True):
            self.assertEqual(Settings.from_environment().paper_size, "a4")

    def test_unknown_size_is_rejected(self):
        with patch.dict(os.environ, {"SCANNER_IP": "192.0.2.42", "SCAN_PAPER_SIZE": "long"}, clear=True):
            with self.assertRaisesRegex(ValueError, "must be a4, auto, or legal"):
                Settings.from_environment()


class DriverTests(unittest.TestCase):
    def test_empty_start_is_cancelled_exactly_once_before_close(self):
        device = object.__new__(SaneDevice)
        device.lib = Mock()
        device.handle = None
        device.initialized = device.opened = True
        device.active = False
        device.lib.sane_start.return_value = NO_DOCS
        self.assertEqual(device.start(), NO_DOCS)
        device.close()
        device.close()
        self.assertEqual(device.lib.mock_calls, [
            call.sane_start(None), call.sane_cancel(None), call.sane_close(None), call.sane_exit(),
        ])

    def test_legal_accepts_driver_rounding_within_one_pixel(self):
        device = object.__new__(SaneDevice)
        device.set_option = Mock()
        device.read_word = Mock(side_effect=[0, round(215.88 * FIXED_SCALE), round(355.57 * FIXED_SCALE)])
        self.assertEqual(device.configure_size("legal"), "Legal (215.88 x 355.57 mm)")
        self.assertEqual(device.set_option.call_args_list, [
            call("AutoDocumentSize", 0), call("br-x", 215.9), call("br-y", 355.6),
        ])

    def test_legal_rejects_readback_clamped_to_a4(self):
        device = object.__new__(SaneDevice)
        device.set_option = Mock()
        device.read_word = Mock(side_effect=[0, 210 * FIXED_SCALE, 297 * FIXED_SCALE])
        with self.assertRaisesRegex(RuntimeError, "210.00 x 297.00 mm"):
            device.configure_size("legal")


class SupervisorTests(unittest.TestCase):
    def test_repeated_read_of_same_error_does_not_count_as_new_error(self):
        guard = WorkerGuard(started=100)
        error = {"updated": 101, "state": "retry_after_error"}
        for _ in range(5):
            self.assertIsNone(guard.reason(error, now=102))
        self.assertIsNone(guard.reason({**error, "updated": 103}, now=103))
        self.assertIn("three consecutive", guard.reason({**error, "updated": 105}, now=105))

    def test_old_worker_status_cannot_mask_stall(self):
        guard = WorkerGuard(started=100)
        self.assertIn("no worker progress", guard.reason({"updated": 99}, now=281))

    def test_offline_busy_and_jam_are_recoverable_waiting_states(self):
        guard = WorkerGuard(started=100)
        for index, state in enumerate(("scanner_offline", "scanner_busy", "paper_blocked") * 3, start=1):
            self.assertIsNone(guard.reason({"updated": 100 + index, "state": state}, now=100 + index))

    def test_stop_escalates_if_vendor_call_never_returns(self):
        child = Mock()
        child.poll.return_value = None
        child.wait.side_effect = [subprocess.TimeoutExpired("worker", 5), 0]
        stop_worker(child)
        child.terminate.assert_called_once()
        child.kill.assert_called_once()
