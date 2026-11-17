"""Offline checks for the opt-in housekeeping loop."""
import unittest
from staging_housekeeper import run_forever, INTERVAL_SECONDS

class HousekeeperTests(unittest.TestCase):
    def test_runs_once_then_waits_one_day(self):
        calls = []
        def stop_after_sleep(seconds):
            calls.append(("sleep", seconds))
            raise StopIteration
        with self.assertRaises(StopIteration):
            run_forever(sleep=stop_after_sleep, cleanup=lambda: calls.append(("cleanup",)))
        self.assertEqual(calls, [("cleanup",), ("sleep", INTERVAL_SECONDS)])

    def test_failed_cleanup_does_not_crash_worker(self):
        from moonraker_upload import UploadError
        calls = []
        def failing_cleanup():
            calls.append("cleanup")
            raise UploadError("safe failure")
        def stop_after_sleep(seconds):
            calls.append("sleep")
            raise StopIteration
        with self.assertRaises(StopIteration):
            run_forever(sleep=stop_after_sleep, cleanup=failing_cleanup)
        self.assertEqual(calls, ["cleanup", "sleep"])

if __name__ == "__main__":
    unittest.main()
