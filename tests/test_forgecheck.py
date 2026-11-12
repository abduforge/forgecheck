import importlib.util
import tempfile
import unittest
from pathlib import Path

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
            file_path = Path(temp) / "meminfo"
            file_path.write_text("MemTotal:       1024 kB\nSwapFree:        512 kB\n", encoding="utf-8")
            result = forgecheck.read_meminfo(file_path)
        self.assertEqual(result["MemTotal"], 1024 * 1024)
        self.assertEqual(result["SwapFree"], 512 * 1024)

    def test_read_os_release(self):
        with tempfile.TemporaryDirectory() as temp:
            file_path = Path(temp) / "os-release"
            file_path.write_text('NAME="Test Linux"\nID=test\n# comment\n', encoding="utf-8")
            result = forgecheck.read_os_release(file_path)
        self.assertEqual(result["NAME"], "Test Linux")
        self.assertEqual(result["ID"], "test")

    def test_read_cpu_info(self):
        with tempfile.TemporaryDirectory() as temp:
            file_path = Path(temp) / "cpuinfo"
            file_path.write_text(
                "processor : 0\nmodel name : Example CPU\n\nprocessor : 1\nmodel name : Example CPU\n",
                encoding="utf-8",
            )
            model, threads = forgecheck.read_cpu_info(file_path)
        self.assertEqual(model, "Example CPU")
        self.assertEqual(threads, 2)

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

    def test_classic_render_has_brand_and_scope(self):
        data = forgecheck.collect_snapshot()
        output = forgecheck.render_classic(data, color=False)
        self.assertIn("LOCAL-FIRST LINUX SYSTEM CONSOLE", output)
        self.assertIn("Read-only local checks", output)

    def test_markdown_report(self):
        data = forgecheck.collect_snapshot()
        output = forgecheck.render_markdown(data)
        self.assertIn("# ForgeCheck 1.0 report", output)
        self.assertIn("not a security audit", output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
