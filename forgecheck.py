#!/usr/bin/env python3
"""ForgeCheck 1.0 — a local, read-only Linux system console."""
from __future__ import annotations

import argparse
import curses
import json
import locale
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

VERSION = "1.0.0"
APP_NAME = "ForgeCheck"
REPORT_DIR = Path.home() / "ForgeCheck-Reports"

# A small 5x7 block font. This is original project artwork, not generated at runtime.
FONT: dict[str, tuple[str, ...]] = {
    "A": ("█████", "█   █", "█   █", "█████", "█   █", "█   █", "█   █"),
    "C": ("█████", "█    ", "█    ", "█    ", "█    ", "█    ", "█████"),
    "E": ("█████", "█    ", "█    ", "████ ", "█    ", "█    ", "█████"),
    "F": ("█████", "█    ", "█    ", "████ ", "█    ", "█    ", "█    "),
    "G": ("█████", "█    ", "█    ", "█ ███", "█   █", "█   █", "█████"),
    "H": ("█   █", "█   █", "█   █", "█████", "█   █", "█   █", "█   █"),
    "K": ("█   █", "█  █ ", "█ █  ", "██   ", "█ █  ", "█  █ ", "█   █"),
    "O": ("█████", "█   █", "█   █", "█   █", "█   █", "█   █", "█████"),
    "R": ("████ ", "█   █", "█   █", "████ ", "█ █  ", "█  █ ", "█   █"),
}


def logo_lines(word: str = "FORGECHECK") -> list[str]:
    glyphs = [FONT[ch] for ch in word if ch in FONT]
    return [" ".join(glyph[row] for glyph in glyphs) for row in range(7)]


def read_os_release(path: Path = Path("/etc/os-release")) -> dict[str, str]:
    result: dict[str, str] = {}
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            result[key] = value.strip().strip('"').strip("'")
    except OSError:
        pass
    return result


def read_meminfo(path: Path = Path("/proc/meminfo")) -> dict[str, int]:
    values: dict[str, int] = {}
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if ":" not in line:
                continue
            key, raw = line.split(":", 1)
            parts = raw.strip().split()
            if not parts:
                continue
            try:
                values[key] = int(parts[0]) * (1024 if len(parts) > 1 and parts[1] == "kB" else 1)
            except ValueError:
                continue
    except OSError:
        pass
    return values


def read_cpu_info(path: Path = Path("/proc/cpuinfo")) -> tuple[str, int]:
    model = "Not reported"
    logical = 0
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            low = line.lower()
            if low.startswith(("model name", "hardware")) and ":" in line and model == "Not reported":
                model = line.split(":", 1)[1].strip()
            elif low.startswith("processor") and ":" in line:
                logical += 1
    except OSError:
        pass
    return model if model != "Not reported" else (platform.processor() or model), logical or (os.cpu_count() or 0)


def human_bytes(value: int | float | None) -> str:
    if value is None:
        return "Unknown"
    amount = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if amount < 1024 or unit == "TiB":
            return f"{int(amount)} B" if unit == "B" else f"{amount:.1f} {unit}"
        amount /= 1024
    return f"{amount:.1f} TiB"


def _run_readonly(command: list[str], timeout: float = 3.0) -> tuple[int, str]:
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        return proc.returncode, (proc.stdout + "\n" + proc.stderr).strip()
    except (OSError, subprocess.TimeoutExpired):
        return 127, ""


def check_ufw() -> str:
    """Read UFW status only; this function never changes firewall settings."""
    if not shutil.which("ufw"):
        return "UFW not detected (another firewall may be used)"
    code, output = _run_readonly(["ufw", "status"])
    lower = output.lower()
    if "status: active" in lower:
        return "UFW reports active"
    if "status: inactive" in lower:
        return "UFW reports inactive"
    if "must be run as root" in lower or "permission denied" in lower:
        return "Installed; status needs elevated permission"
    return "Installed; status could not be determined" if code else "Status unavailable"


def check_ssh_server() -> str:
    """Check Debian package state; does not start or stop SSH."""
    if not shutil.which("dpkg-query"):
        return "Not checked (dpkg-query unavailable)"
    code, output = _run_readonly(["dpkg-query", "-W", "-f=${db:Status-Status}", "openssh-server"])
    return "openssh-server package installed" if code == 0 and output.strip() == "installed" else "openssh-server package not detected"


def read_battery() -> str:
    for battery in sorted(Path("/sys/class/power_supply").glob("BAT*")):
        try:
            capacity = (battery / "capacity").read_text().strip()
            status = (battery / "status").read_text().strip().lower()
            return f"{capacity}% ({status})"
        except OSError:
            continue
    return "Not reported"


def uptime_seconds() -> int | None:
    try:
        return round(float(Path("/proc/uptime").read_text().split()[0]))
    except (OSError, ValueError, IndexError):
        return None


def uptime_text(seconds: int | None) -> str:
    if seconds is None:
        return "Unknown"
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes = remainder // 60
    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


def collect_snapshot() -> dict[str, Any]:
    os_info = read_os_release()
    mem = read_meminfo()
    cpu_model, cpu_threads = read_cpu_info()
    total = mem.get("MemTotal")
    available = mem.get("MemAvailable")
    swap_total = mem.get("SwapTotal")
    swap_free = mem.get("SwapFree")
    try:
        disk = shutil.disk_usage("/")
        disk_data: dict[str, Any] = {
            "total_bytes": disk.total,
            "used_bytes": disk.used,
            "free_bytes": disk.free,
            "used_percent": round(disk.used / disk.total * 100, 1) if disk.total else None,
        }
    except OSError:
        disk_data = {"total_bytes": None, "used_bytes": None, "free_bytes": None, "used_percent": None}
    used_swap = swap_total - swap_free if swap_total is not None and swap_free is not None else None
    used_ram = total - available if total is not None and available is not None else None
    try:
        load = [round(float(x), 2) for x in os.getloadavg()]
    except (AttributeError, OSError):
        load = []
    return {
        "tool": APP_NAME,
        "version": VERSION,
        "collected_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "system": {
            "distribution": os_info.get("PRETTY_NAME", os_info.get("NAME", "Unknown")),
            "kernel": platform.release(),
            "architecture": platform.machine(),
            "cpu": cpu_model,
            "cpu_threads": cpu_threads,
            "python": platform.python_version(),
        },
        "memory": {
            "total_bytes": total,
            "available_bytes": available,
            "used_bytes": used_ram,
            "swap_total_bytes": swap_total,
            "swap_used_bytes": used_swap,
        },
        "disk_root": disk_data,
        "uptime_seconds": uptime_seconds(),
        "load_average": load,
        "battery": read_battery(),
        "checks": {
            "ufw": check_ufw(),
            "ssh_server": check_ssh_server(),
            "running_as_root": os.geteuid() == 0 if hasattr(os, "geteuid") else False,
        },
        "scope": "Local read-only inventory. No network scanning or configuration changes.",
    }


def percent(used: int | None, total: int | None) -> int | None:
    if used is None or total is None or total <= 0:
        return None
    return max(0, min(100, round(used / total * 100)))


def render_classic(data: dict[str, Any], color: bool = True) -> str:
    def paint(text: str, code: str) -> str:
        return f"\033[{code}m{text}\033[0m" if color else text

    s, m, d, c = data["system"], data["memory"], data["disk_root"], data["checks"]
    lines = [paint(line, "1;36") for line in logo_lines()]
    lines += [
        paint("  LOCAL-FIRST LINUX SYSTEM CONSOLE  /  v" + data["version"], "1;37"),
        paint("  ─────────────────────────────────────────────────────────────", "2"),
        "",
        paint("  SYSTEM", "1;36"),
        f"  OS           {s['distribution']}",
        f"  Kernel       {s['kernel']} ({s['architecture']})",
        f"  CPU          {s['cpu']} ({s['cpu_threads']} threads)",
        f"  Python       {s['python']}",
        "",
        paint("  RESOURCES", "1;36"),
        f"  RAM          {human_bytes(m['used_bytes'])} used / {human_bytes(m['total_bytes'])} total",
        f"  Available    {human_bytes(m['available_bytes'])}",
        f"  Swap         {human_bytes(m['swap_used_bytes'])} used / {human_bytes(m['swap_total_bytes'])} total",
        f"  Root disk    {human_bytes(d['used_bytes'])} used / {human_bytes(d['total_bytes'])} total ({d['used_percent']}%)",
        f"  Uptime       {uptime_text(data['uptime_seconds'])}",
        f"  Battery      {data['battery']}",
        "",
        paint("  SECURITY INVENTORY", "1;36"),
        f"  Firewall     {c['ufw']}",
        f"  SSH server   {c['ssh_server']}",
        f"  Privileges   {'Root (not recommended)' if c['running_as_root'] else 'Regular user'}",
        "",
        paint("  Read-only local checks. No network scanning. No settings changed.", "2"),
        paint(f"  Updated {data['collected_at']}", "2"),
    ]
    return "\n".join(lines)


def render_markdown(data: dict[str, Any]) -> str:
    s, m, d, c = data["system"], data["memory"], data["disk_root"], data["checks"]
    rows = [
        ("Distribution", s["distribution"]),
        ("Kernel", f"{s['kernel']} ({s['architecture']})"),
        ("CPU", f"{s['cpu']} ({s['cpu_threads']} threads)"),
        ("Python", s["python"]),
        ("RAM", f"{human_bytes(m['used_bytes'])} used / {human_bytes(m['total_bytes'])} total"),
        ("Available RAM", human_bytes(m["available_bytes"])),
        ("Swap", f"{human_bytes(m['swap_used_bytes'])} used / {human_bytes(m['swap_total_bytes'])} total"),
        ("Root disk", f"{human_bytes(d['used_bytes'])} used / {human_bytes(d['total_bytes'])} total"),
        ("Uptime", uptime_text(data["uptime_seconds"])),
        ("Battery", data["battery"]),
        ("UFW", c["ufw"]),
        ("OpenSSH server", c["ssh_server"]),
    ]
    escaped_rows = [(name, str(value).replace("|", "&#124;")) for name, value in rows]
    table = "\n".join(f"| {name} | {value} |" for name, value in escaped_rows)
    return (
        "# ForgeCheck 1.0 report\n\n"
        f"Collected: `{data['collected_at']}`\n\n"
        "| Check | Result |\n|:--|:--|\n"
        f"{table}\n\n"
        "> Local system inventory only. This report is not a security audit. "
        "No network scanning or system configuration changes are performed.\n"
    )


class Dashboard:
    """Full-screen, keyboard-driven terminal dashboard."""
    PAGES = ("OVERVIEW", "RESOURCES", "SECURITY", "ABOUT")

    def __init__(self, screen: Any) -> None:
        self.screen = screen
        self.page = 0
        self.data = collect_snapshot()
        self.message = "Ready. Local read-only mode."
        self.color = False
        self._setup()

    def _setup(self) -> None:
        curses.curs_set(0)
        self.screen.keypad(True)
        self.screen.timeout(-1)
        if curses.has_colors():
            curses.start_color()
            try:
                curses.use_default_colors()
            except curses.error:
                pass
            curses.init_pair(1, curses.COLOR_CYAN, -1)
            curses.init_pair(2, curses.COLOR_WHITE, -1)
            curses.init_pair(3, curses.COLOR_GREEN, -1)
            curses.init_pair(4, curses.COLOR_YELLOW, -1)
            curses.init_pair(5, curses.COLOR_BLUE, -1)
            curses.init_pair(6, curses.COLOR_MAGENTA, -1)
            self.color = True

    def _attr(self, pair: int = 0, bold: bool = False, dim: bool = False) -> int:
        attr = curses.color_pair(pair) if self.color and pair else 0
        if bold:
            attr |= curses.A_BOLD
        if dim:
            attr |= curses.A_DIM
        return attr

    def put(self, y: int, x: int, text: str, attr: int = 0, width: int | None = None) -> None:
        height, columns = self.screen.getmaxyx()
        if y < 0 or y >= height or x >= columns or x < 0:
            return
        room = columns - x - 1
        if width is not None:
            room = min(room, width)
        if room <= 0:
            return
        try:
            self.screen.addnstr(y, x, str(text), room, attr)
        except curses.error:
            pass

    def line(self, y: int, char: str = "─") -> None:
        _, width = self.screen.getmaxyx()
        self.put(y, 0, char * max(0, width - 1), self._attr(5, dim=True))

    def title(self, y: int, x: int, text: str) -> None:
        self.put(y, x, text, self._attr(1, bold=True))

    def kv(self, y: int, x: int, label: str, value: str, width: int) -> None:
        self.put(y, x, f"{label:<13}", self._attr(5, bold=True), 13)
        self.put(y, x + 14, value, self._attr(2), max(1, width - 14))

    def bar(self, y: int, x: int, label: str, used: int | None, total: int | None, width: int) -> None:
        pct = percent(used, total)
        text = "unknown" if pct is None else f"{pct:3d}%"
        bar_width = max(5, min(18, width - 25))
        fill = round((pct or 0) / 100 * bar_width) if pct is not None else 0
        block = "█" * fill + "·" * (bar_width - fill)
        self.put(y, x, f"{label:<9}", self._attr(5, bold=True), 9)
        self.put(y, x + 10, block, self._attr(3 if pct is not None and pct < 85 else 4, bold=True), bar_width)
        self.put(y, x + 12 + bar_width, text, self._attr(2), 6)

    def draw_header(self) -> None:
        height, width = self.screen.getmaxyx()
        logo = logo_lines()
        if width >= 67 and height >= 22:
            x = max(1, (width - len(logo[0])) // 2)
            for index, row in enumerate(logo):
                self.put(index, x, row, self._attr(1, bold=True))
            self.put(7, 0, "ABDUFORGE  /  LOCAL-FIRST LINUX SYSTEM CONSOLE", self._attr(2, bold=True), width - 1)
            self.put(8, 0, f"VERSION {VERSION}    ·    READ ONLY    ·    {self.data['collected_at']}", self._attr(5, dim=True), width - 1)
            self.line(9)
            nav = "   ".join(f"[{i + 1}] {name}" for i, name in enumerate(self.PAGES))
            self.put(10, 1, nav, self._attr(1, bold=True), width - 2)
            self.line(11)
            self.content_y = 13
        else:
            self.put(0, 1, "FORGECHECK 1.0  /  ABDUFORGE", self._attr(1, bold=True))
            self.put(1, 1, "Terminal is small; enlarge to 80x24 for the full banner.", self._attr(4))
            self.line(2)
            nav = "  ".join(f"[{i + 1}] {name}" for i, name in enumerate(self.PAGES))
            self.put(3, 1, nav, self._attr(1, bold=True), width - 2)
            self.line(4)
            self.content_y = 6

    def draw_overview(self, y: int, width: int) -> None:
        s, m, d = self.data["system"], self.data["memory"], self.data["disk_root"]
        left = 2
        split = max(39, width // 2)
        left_width = split - left - 2
        right_width = width - split - 3
        self.title(y, left, "SYSTEM")
        self.kv(y + 2, left, "OS", s["distribution"], left_width)
        self.kv(y + 3, left, "Kernel", f"{s['kernel']} / {s['architecture']}", left_width)
        self.kv(y + 4, left, "CPU", s["cpu"], left_width)
        self.kv(y + 5, left, "Threads", str(s["cpu_threads"]), left_width)
        self.kv(y + 6, left, "Python", s["python"], left_width)
        self.kv(y + 7, left, "Uptime", uptime_text(self.data["uptime_seconds"]), left_width)
        self.title(y, split, "RESOURCES")
        self.bar(y + 2, split, "RAM", m["used_bytes"], m["total_bytes"], right_width)
        self.put(y + 3, split + 10, f"{human_bytes(m['available_bytes'])} available", self._attr(2, dim=True), right_width - 10)
        self.bar(y + 5, split, "SWAP", m["swap_used_bytes"], m["swap_total_bytes"], right_width)
        self.bar(y + 7, split, "ROOT", d["used_bytes"], d["total_bytes"], right_width)

    def draw_resources(self, y: int, width: int) -> None:
        s, m, d = self.data["system"], self.data["memory"], self.data["disk_root"]
        self.title(y, 2, "RESOURCE SUMMARY")
        self.bar(y + 1, 2, "RAM", m["used_bytes"], m["total_bytes"], width - 5)
        self.put(y + 2, 12, f"{human_bytes(m['used_bytes'])} used  /  {human_bytes(m['total_bytes'])} total  /  {human_bytes(m['available_bytes'])} available", self._attr(2), width - 14)
        self.bar(y + 3, 2, "SWAP", m["swap_used_bytes"], m["swap_total_bytes"], width - 5)
        self.put(y + 4, 12, f"{human_bytes(m['swap_used_bytes'])} used  /  {human_bytes(m['swap_total_bytes'])} total", self._attr(2), width - 14)
        self.bar(y + 5, 2, "ROOT", d["used_bytes"], d["total_bytes"], width - 5)
        load = ", ".join(str(x) for x in self.data["load_average"]) or "Not reported"
        self.put(y + 6, 12, f"{human_bytes(d['free_bytes'])} free  ·  LOAD {load}  ·  BATTERY {self.data['battery']}", self._attr(2), width - 14)

    def draw_security(self, y: int, width: int) -> None:
        c = self.data["checks"]
        self.title(y, 2, "LOCAL SECURITY INVENTORY")
        self.kv(y + 2, 2, "Firewall", c["ufw"], width - 5)
        self.kv(y + 3, 2, "SSH server", c["ssh_server"], width - 5)
        self.kv(y + 4, 2, "Privileges", "Root — not recommended" if c["running_as_root"] else "Regular user", width - 5)
        self.put(y + 6, 2, "Inventory only — not a security audit.", self._attr(4, bold=True))
        self.put(y + 7, 2, "No network scanning. No services or settings changed.", self._attr(2, dim=True))

    def draw_about(self, y: int, width: int) -> None:
        self.title(y, 2, "ABOUT FORGECHECK")
        lines = [
            "A local-first Linux system console by Abduali / AbduForge.",
            "Reads OS, CPU, memory, storage, uptime and basic package state.",
            "Built with Python's standard library. No pip dependencies.",
            "",
            "DESIGN:  Local-first  /  Read-only  /  Understandable",
            "",
            "KEYS:  1-4 pages  |  R refresh  |  J JSON  |  M Markdown  |  H help  |  Q quit",
        ]
        for offset, line in enumerate(lines, 1):
            self.put(y + offset, 2, line, self._attr(1 if line.startswith(("DESIGN:", "KEYS:")) else 2, bold=line.startswith(("DESIGN:", "KEYS:"))), width - 5)

    def draw_help(self) -> None:
        self.screen.erase()
        height, width = self.screen.getmaxyx()
        self.put(1, 2, "FORGECHECK — KEYBOARD GUIDE", self._attr(1, bold=True))
        self.line(3)
        items = [
            ("1", "Overview", "System identity and a compact resource summary."),
            ("2", "Resources", "RAM, swap, root filesystem, load average and battery."),
            ("3", "Security", "Basic local inventory for UFW and OpenSSH package."),
            ("4", "About", "Project scope, design principles and shortcuts."),
            ("R", "Refresh", "Collect a new local system snapshot."),
            ("J", "Export JSON", "Save a timestamped machine-readable report."),
            ("M", "Export Markdown", "Save a report suitable for GitHub or notes."),
            ("Q", "Quit", "Leave the dashboard and return to the shell."),
        ]
        y = 5
        for key, label, description in items:
            self.put(y, 3, f"[{key}]", self._attr(3, bold=True), 5)
            self.put(y, 9, label, self._attr(2, bold=True), 18)
            self.put(y, 29, description, self._attr(2), width - 32)
            y += 2
        self.line(height - 3)
        self.put(height - 2, 2, "Press any key to return.", self._attr(4))
        self.screen.refresh()
        self.screen.getch()

    def export(self, kind: str) -> None:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = REPORT_DIR / f"forgecheck-{stamp}.{ 'json' if kind == 'json' else 'md' }"
        content = json.dumps(self.data, indent=2, ensure_ascii=False) + "\n" if kind == "json" else render_markdown(self.data)
        try:
            path.write_text(content, encoding="utf-8")
            self.message = f"Saved {path}"
        except OSError as exc:
            self.message = f"Export failed: {exc}"

    def draw(self) -> None:
        self.screen.erase()
        height, width = self.screen.getmaxyx()
        if height < 22 or width < 67:
            self.put(1, 1, "FORGECHECK 1.0", self._attr(1, bold=True))
            self.put(3, 1, "Please enlarge this terminal to at least 67x22.", self._attr(4))
            self.put(5, 1, "Press Q to quit.", self._attr(2))
        else:
            self.draw_header()
            y = self.content_y
            if self.page == 0:
                self.draw_overview(y, width)
            elif self.page == 1:
                self.draw_resources(y, width)
            elif self.page == 2:
                self.draw_security(y, width)
            else:
                self.draw_about(y, width)
            self.line(height - 3)
            self.put(height - 2, 1, "1-4 Pages   R Refresh   J JSON   M Markdown   H Help   Q Quit", self._attr(1, bold=True), width - 2)
        height, width = self.screen.getmaxyx()
        self.put(height - 1, 1, self.message, self._attr(2, dim=True), width - 2)
        self.screen.refresh()

    def run(self) -> int:
        while True:
            self.draw()
            key = self.screen.getch()
            if key in (ord("q"), ord("Q"), 27):
                return 0
            if key in (ord("h"), ord("H"), ord("?")):
                self.draw_help()
            elif key in (ord("r"), ord("R")):
                self.data = collect_snapshot()
                self.message = "Snapshot refreshed."
            elif key in (ord("j"), ord("J")):
                self.export("json")
            elif key in (ord("m"), ord("M")):
                self.export("markdown")
            elif ord("1") <= key <= ord("4"):
                self.page = key - ord("1")
                self.message = f"Opened {self.PAGES[self.page].lower()} page."
            elif key in (curses.KEY_LEFT, curses.KEY_RIGHT):
                self.page = (self.page + (1 if key == curses.KEY_RIGHT else -1)) % len(self.PAGES)
                self.message = f"Opened {self.PAGES[self.page].lower()} page."


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="forgecheck",
        description="ForgeCheck 1.0 — a local, read-only Linux system console.",
    )
    parser.add_argument("--version", action="version", version=f"ForgeCheck {VERSION}")
    parser.add_argument("--classic", action="store_true", help="print a one-shot terminal snapshot")
    parser.add_argument("--dashboard", action="store_true", help="open the full-screen terminal dashboard")
    parser.add_argument("--json", action="store_true", help="print a JSON snapshot")
    parser.add_argument("--report", metavar="FILE", help="write a Markdown report to FILE")
    parser.add_argument("--no-color", action="store_true", help="disable ANSI colors in classic mode")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.dashboard and not sys.stdin.isatty():
        print("forgecheck: --dashboard needs an interactive terminal", file=sys.stderr)
        return 2
    if args.dashboard or (sys.stdin.isatty() and sys.stdout.isatty() and not args.classic and not args.json and not args.report):
        try:
            locale.setlocale(locale.LC_ALL, "")
            return curses.wrapper(lambda screen: Dashboard(screen).run())
        except curses.error as exc:
            print(f"forgecheck: could not start dashboard: {exc}. Try --classic.", file=sys.stderr)
            return 2
    data = collect_snapshot()
    if args.report:
        try:
            report_path = Path(args.report).expanduser()
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(render_markdown(data), encoding="utf-8")
        except OSError as exc:
            print(f"forgecheck: could not write report: {exc}", file=sys.stderr)
            return 2
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        use_color = sys.stdout.isatty() and not args.no_color and "NO_COLOR" not in os.environ
        print(render_classic(data, use_color))
        if args.report:
            print(f"\nMarkdown report saved to: {Path(args.report).expanduser()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
