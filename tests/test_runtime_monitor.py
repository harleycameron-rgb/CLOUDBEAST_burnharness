import hashlib
import unittest
from unittest.mock import patch

import runtime_monitor


class RuntimeMonitorTests(unittest.TestCase):
    def test_health_check_uses_live_validation(self):
        for ready in (True, False):
            with self.subTest(ready=ready):
                with patch.object(runtime_monitor, "system_heartbeat", return_value=ready) as heartbeat:
                    self.assertIs(runtime_monitor.system_health_check(), ready)
                heartbeat.assert_called_once_with()

    def test_hash_is_sha512_of_utf8_text(self):
        text = "sphere_intérieur"
        self.assertEqual(
            runtime_monitor.generate_integrity_hash(text),
            hashlib.sha512(text.encode("utf-8")).hexdigest(),
        )

    def test_monitor_reports_each_check_and_sleeps(self):
        with patch.object(runtime_monitor, "system_health_check", side_effect=[True, False]) as check:
            with patch.object(runtime_monitor.time, "strftime", return_value="12:34:56"):
                with patch.object(runtime_monitor.time, "sleep", side_effect=[None, StopIteration]) as sleep:
                    with patch("builtins.print") as output:
                        with self.assertRaises(StopIteration):
                            runtime_monitor.monitor_system(interval=30)

        self.assertEqual(check.call_count, 2)
        self.assertEqual([call.args for call in sleep.call_args_list], [(30,), (30,)])
        prefix = runtime_monitor.generate_integrity_hash("sphere_interior")[:16]
        self.assertEqual(
            [call.args[0] for call in output.call_args_list],
            [
                "Starting runtime monitor...",
                f"[12:34:56] System ready: True | Hash: {prefix}...",
                f"[12:34:56] System ready: False | Hash: {prefix}...",
            ],
        )


if __name__ == "__main__":
    unittest.main()
