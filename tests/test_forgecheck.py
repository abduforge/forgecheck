import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parents[1] / "forgecheck.py"
spec = importlib.util.spec_from_file_location("forgecheck", MODULE_PATH)
forgecheck = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(forgecheck)


class ForgeCheckTests(unittest.TestCase):
    def test_human_bytes(self):
        self.assertEqual(forgecheck.human_bytes(0), "0 B")
        self.assertEqual(forgecheck.human_bytes(1024), "1.0 KiB")
        self.assertEqual(forgecheck.human_bytes(None), "Unknown")

    def test_read_meminfo(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "meminfo"
            path.write_text("MemTotal:       1024 kB\nSwapFree:        512 kB\n", encoding="utf-8")
            data = forgecheck.read_meminfo(path)
        self.assertEqual(data["MemTotal"], 1024 * 1024)
        self.assertEqual(data["SwapFree"], 512 * 1024)

    def test_read_os_release(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "os-release"
            path.write_text('NAME="Test Linux"\nID=test\n# comment\n', encoding="utf-8")
            data = forgecheck.read_os_release(path)
        self.assertEqual(data["NAME"], "Test Linux")
        self.assertEqual(data["ID"], "test")

    def test_read_cpu_info(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "cpuinfo"
            path.write_text(
                "processor : 0\nmodel name : Example CPU\n\nprocessor : 1\nmodel name : Example CPU\n",
                encoding="utf-8",
            )
            model, threads = forgecheck.read_cpu_info(path)
        self.assertEqual(model, "Example CPU")
        self.assertEqual(threads, 2)

    def test_read_cpu_ticks(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "stat"
            path.write_text("cpu  10 2 3 40 5 0 0 0 0 0\n", encoding="utf-8")
            self.assertEqual(forgecheck.read_cpu_ticks(path), (60, 45))

    def test_uptime_format(self):
        self.assertEqual(forgecheck.uptime_text(90061), "1d 1h 1m")
        self.assertEqual(forgecheck.uptime_text(None), "Unknown")

    def test_percent(self):
        self.assertEqual(forgecheck.percent(50, 100), 50)
        self.assertEqual(forgecheck.percent(120, 100), 100)
        self.assertIsNone(forgecheck.percent(None, 100))
        self.assertIsNone(forgecheck.percent(1, 0))

    def test_logo_is_large_and_consistent(self):
        lines = forgecheck.logo_lines()
        self.assertEqual(len(lines), 7)
        self.assertTrue(all(len(line) == len(lines[0]) for line in lines))
        self.assertGreaterEqual(len(lines[0]), 50)

    def test_parse_ip_output(self):
        sample = (
            "1: lo    inet 127.0.0.1/8 scope host lo\\n"
            "2: wlan0    inet 192.168.0.108/24 brd 192.168.0.255 scope global wlan0\\n"
            "2: wlan0    inet6 fe80::abcd/64 scope link wlan0\\n"
        ).replace("\\n", "\n")
        result = forgecheck.parse_ip_output(sample)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "wlan0")
        self.assertIn("192.168.0.108/24", result[0]["addresses"])

    def test_network_summary_is_local_and_read_only(self):
        with patch.object(forgecheck, "_run_readonly", side_effect=[
            (0, "2: wlan0 inet 192.168.1.3/24 scope global wlan0"),
            (0, "tcp LISTEN 0 128 127.0.0.1:631 0.0.0.0:*"),
        ]):
            data = forgecheck.read_network()
        self.assertEqual(data["interface_count"], 1)
        self.assertEqual(data["listening_socket_count"], 1)
        self.assertIn("no packets are sent", data["note"].lower())

    def test_cpu_usage_clamped(self):
        with patch.object(forgecheck, "read_cpu_ticks", side_effect=[(100, 50), (200, 80)]), patch.object(forgecheck.time, "sleep"):
            self.assertEqual(forgecheck.cpu_usage(), 70.0)

    def test_classic_render_has_brand_and_scope(self):
        data = forgecheck.collect_snapshot(sample_cpu=False)
        output = forgecheck.render_classic(data, color=False)
        self.assertIn("LOCAL-FIRST LINUX SYSTEM CONSOLE", output)
        self.assertIn("SUPER EDITION", output)
        self.assertIn("No network scanning", output)

    def test_markdown_report_includes_network_and_secure_boot(self):
        data = forgecheck.collect_snapshot(sample_cpu=False)
        output = forgecheck.render_markdown(data)
        self.assertIn("# ForgeCheck 1.1.0 SUPER report", output)
        self.assertIn("Network interfaces", output)
        self.assertIn("Secure Boot", output)
        self.assertIn("not a security audit", output)

    def test_snapshot_schema(self):
        data = forgecheck.collect_snapshot(sample_cpu=False)
        self.assertEqual(data["version"], "1.1.0")
        self.assertIn("network", data)
        self.assertIn("temperature_c", data)
        self.assertIn("secure_boot", data["checks"])

    def test_report_roundtrip_json(self):
        import json
        data = forgecheck.collect_snapshot(sample_cpu=False)
        restored = json.loads(json.dumps(data))
        self.assertEqual(restored["tool"], "ForgeCheck")
        self.assertEqual(restored["version"], "1.1.0")


if __name__ == "__main__":
    unittest.main(verbosity=2)
