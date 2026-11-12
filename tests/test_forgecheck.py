import importlib.util
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
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            file_path = Path(temp) / "meminfo"
            file_path.write_text("MemTotal:       1024 kB\nSwapFree:        512 kB\n", encoding="utf-8")
            result = forgecheck.read_meminfo(file_path)
        self.assertEqual(result["MemTotal"], 1024 * 1024)
        self.assertEqual(result["SwapFree"], 512 * 1024)

    def test_uptime_format(self):
        self.assertEqual(forgecheck.uptime_text(90061), "1d 1h 1m")
        self.assertEqual(forgecheck.uptime_text(None), "Unknown")


if __name__ == "__main__":
    unittest.main()
