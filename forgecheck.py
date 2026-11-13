#!/usr/bin/env python3
"""ForgeCheck 1.2.0 CT — a customizable, local-first Linux system console."""
from __future__ import annotations

import argparse
import curses
import json
import locale
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

VERSION = "1.2.0"
APP_NAME = "ForgeCheck"
REPORT_DIR = Path.home() / "ForgeCheck-Reports"
CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "forgecheck"
CONFIG_PATH = CONFIG_DIR / "config.json"
DEFAULT_CONFIG: dict[str, Any] = {
    "theme": "dark",
    "accent": "teal",
    "density": "comfortable",
    "show_logo": True,
    "brand": "ABDUFORGE",
}
ACCENT_NAMES = ("teal", "blue", "green", "amber", "purple", "red")
THEME_NAMES = ("dark", "light", "mono")
DENSITY_NAMES = ("comfortable", "compact")


def normalize_config(raw: Any) -> dict[str, Any]:
    """Validate user preferences and ignore unknown or malformed values."""
    config = dict(DEFAULT_CONFIG)
    if not isinstance(raw, dict):
        return config
    if raw.get("theme") in THEME_NAMES:
        config["theme"] = raw["theme"]
    if raw.get("accent") in ACCENT_NAMES:
        config["accent"] = raw["accent"]
    if raw.get("density") in DENSITY_NAMES:
        config["density"] = raw["density"]
    if isinstance(raw.get("show_logo"), bool):
        config["show_logo"] = raw["show_logo"]
    brand = raw.get("brand")
    if isinstance(brand, str):
        # Keep branding terminal-safe: printable ASCII, no control sequences.
        brand = re.sub(r"[^A-Za-z0-9 ._-]", "", brand).strip()[:28]
        if brand:
            config["brand"] = brand.upper()
    return config


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    try:
        return normalize_config(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return dict(DEFAULT_CONFIG)


def save_config(config: dict[str, Any], path: Path = CONFIG_PATH) -> None:
    """Atomically save validated preferences with owner-only permissions."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        path.parent.chmod(0o700)
    except OSError:
        pass
    temporary = path.with_name(path.name + ".tmp")
    payload = json.dumps(normalize_config(config), indent=2, ensure_ascii=True) + "\n"
    temporary.write_text(payload, encoding="utf-8")
    try:
        temporary.chmod(0o600)
    except OSError:
        pass
    os.replace(temporary, path)
    try:
        path.chmod(0o600)
    except OSError:
        pass


def reset_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    config = dict(DEFAULT_CONFIG)
    save_config(config, path)
    return config


# Original 5x7 block lettering. Kept compact enough for an 80-column terminal.
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


def read_text(path: Path, default: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return default


def read_os_release(path: Path = Path("/etc/os-release")) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in read_text(path).splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key] = value.strip().strip('"').strip("'")
    return result


def read_meminfo(path: Path = Path("/proc/meminfo")) -> dict[str, int]:
    values: dict[str, int] = {}
    for line in read_text(path).splitlines():
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
    return values


def read_cpu_info(path: Path = Path("/proc/cpuinfo")) -> tuple[str, int]:
    model = "Not reported"
    logical = 0
    for line in read_text(path).splitlines():
        low = line.lower()
        if low.startswith(("model name", "hardware")) and ":" in line and model == "Not reported":
            model = line.split(":", 1)[1].strip()
        elif low.startswith("processor") and ":" in line:
            logical += 1
    return model if model != "Not reported" else (platform.processor() or model), logical or (os.cpu_count() or 0)


def read_cpu_ticks(path: Path = Path("/proc/stat")) -> tuple[int, int] | None:
    for line in read_text(path).splitlines():
        if line.startswith("cpu "):
            try:
                values = [int(item) for item in line.split()[1:]]
            except ValueError:
                return None
            if len(values) < 4:
                return None
            # guest and guest_nice are already included in user and nice.
            values = values[:8]
            total = sum(values)
            idle = values[3] + (values[4] if len(values) > 4 else 0)
            return total, idle
    return None


def cpu_usage(interval: float = 0.12) -> float | None:
    before = read_cpu_ticks()
    if before is None:
        return None
    time.sleep(max(0.02, min(interval, 0.5)))
    after = read_cpu_ticks()
    if after is None:
        return None
    total_delta = after[0] - before[0]
    idle_delta = after[1] - before[1]
    if total_delta <= 0:
        return None
    return round(max(0.0, min(100.0, (1 - idle_delta / total_delta) * 100)), 1)


def read_cpu_frequency_mhz() -> float | None:
    for path in (Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq"),):
        raw = read_text(path).strip()
        try:
            return round(int(raw) / 1000, 0)
        except ValueError:
            pass
    for line in read_text(Path("/proc/cpuinfo")).splitlines():
        if line.lower().startswith("cpu mhz") and ":" in line:
            try:
                return round(float(line.split(":", 1)[1].strip()), 0)
            except ValueError:
                break
    return None


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
    """Run a bounded read-only query. Never invokes a shell."""
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        return proc.returncode, (proc.stdout + "\n" + proc.stderr).strip()
    except (OSError, subprocess.TimeoutExpired):
        return 127, ""


def check_ufw() -> str:
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
    if not shutil.which("dpkg-query"):
        return "Not checked (dpkg-query unavailable)"
    code, output = _run_readonly(["dpkg-query", "-W", "-f=${db:Status-Status}", "openssh-server"])
    return "openssh-server package installed" if code == 0 and output.strip() == "installed" else "openssh-server package not detected"


def parse_ip_output(output: str) -> list[dict[str, str]]:
    interfaces: dict[str, list[str]] = {}
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        name = parts[1].rstrip(":")
        family = parts[2]
        address = parts[3].split("%", 1)[0]
        if name == "lo" or family not in ("inet", "inet6"):
            continue
        if address.startswith("127.") or address == "::1/128":
            continue
        interfaces.setdefault(name, [])
        if address not in interfaces[name]:
            interfaces[name].append(address)
    return [{"name": name, "addresses": ", ".join(addresses)} for name, addresses in sorted(interfaces.items())]


def read_network() -> dict[str, Any]:
    code, output = _run_readonly(["ip", "-o", "addr", "show", "up"])
    interfaces = parse_ip_output(output) if code == 0 else []
    ss_code, ss_output = _run_readonly(["ss", "-H", "-lntu"])
    listeners: list[dict[str, str]] = []
    if ss_code == 0:
        for line in ss_output.splitlines():
            parts = line.split()
            if len(parts) >= 5:
                listeners.append({"protocol": parts[0], "local_address": parts[4]})
    return {
        "interfaces": interfaces,
        "interface_count": len(interfaces),
        "listening_socket_count": len(listeners),
        "listening_sockets": listeners[:20],
        "note": "Local interface and listening-socket inventory only; no packets are sent to other hosts.",
    }


def read_temperature_c() -> float | None:
    readings: list[float] = []
    for hwmon in sorted(Path("/sys/class/hwmon").glob("hwmon*")):
        name = read_text(hwmon / "name").strip().lower()
        if name and not any(token in name for token in ("coretemp", "k10temp", "cpu", "soc")):
            continue
        for path in hwmon.glob("temp*_input"):
            try:
                value = int(read_text(path).strip()) / 1000
            except ValueError:
                continue
            if 0 <= value <= 120:
                readings.append(value)
    if not readings:
        for path in sorted(Path("/sys/class/thermal").glob("thermal_zone*/temp")):
            try:
                value = int(read_text(path).strip()) / 1000
            except ValueError:
                continue
            if 0 <= value <= 120:
                readings.append(value)
    return round(max(readings), 1) if readings else None


def read_battery() -> str:
    for battery in sorted(Path("/sys/class/power_supply").glob("BAT*")):
        try:
            capacity = read_text(battery / "capacity").strip()
            status = read_text(battery / "status").strip().lower()
            if capacity:
                return f"{capacity}% ({status or 'status unknown'})"
        except OSError:
            continue
    return "Not reported"


def read_secure_boot() -> str:
    for path in Path("/sys/firmware/efi/efivars").glob("SecureBoot-*"):
        try:
            raw = path.read_bytes()
        except OSError:
            continue
        if raw:
            if raw[-1] == 1:
                return "Enabled"
            if raw[-1] == 0:
                return "Disabled"
    return "Unknown / UEFI variable unavailable"


def uptime_seconds() -> int | None:
    try:
        return round(float(read_text(Path("/proc/uptime")).split()[0]))
    except (ValueError, IndexError):
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


def disk_snapshot(path: str) -> dict[str, Any]:
    try:
        disk = shutil.disk_usage(path)
        return {
            "path": path,
            "total_bytes": disk.total,
            "used_bytes": disk.used,
            "free_bytes": disk.free,
            "used_percent": round(disk.used / disk.total * 100, 1) if disk.total else None,
        }
    except OSError:
        return {"path": path, "total_bytes": None, "used_bytes": None, "free_bytes": None, "used_percent": None}


def percent(used: int | float | None, total: int | float | None) -> int | None:
    if used is None or total is None or total <= 0:
        return None
    return max(0, min(100, round(used / total * 100)))


def collect_snapshot(sample_cpu: bool = True) -> dict[str, Any]:
    os_info = read_os_release()
    mem = read_meminfo()
    cpu_model, cpu_threads = read_cpu_info()
    total = mem.get("MemTotal")
    available = mem.get("MemAvailable")
    swap_total = mem.get("SwapTotal")
    swap_free = mem.get("SwapFree")
    used_swap = swap_total - swap_free if swap_total is not None and swap_free is not None else None
    used_ram = total - available if total is not None and available is not None else None
    try:
        load = [round(float(x), 2) for x in os.getloadavg()]
    except (AttributeError, OSError):
        load = []
    try:
        swappiness = int(read_text(Path("/proc/sys/vm/swappiness")).strip())
    except ValueError:
        swappiness = None
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
            "cpu_usage_percent": cpu_usage() if sample_cpu else None,
            "cpu_frequency_mhz": read_cpu_frequency_mhz(),
            "python": platform.python_version(),
            "session_type": os.environ.get("XDG_SESSION_TYPE", "Unknown"),
        },
        "memory": {
            "total_bytes": total,
            "available_bytes": available,
            "used_bytes": used_ram,
            "used_percent": percent(used_ram, total),
            "swap_total_bytes": swap_total,
            "swap_used_bytes": used_swap,
            "swap_used_percent": percent(used_swap, swap_total),
            "swappiness": swappiness,
        },
        "disk_root": disk_snapshot("/"),
        "disk_home": disk_snapshot(str(Path.home())),
        "network": read_network(),
        "uptime_seconds": uptime_seconds(),
        "load_average": load,
        "temperature_c": read_temperature_c(),
        "battery": read_battery(),
        "checks": {
            "ufw": check_ufw(),
            "ssh_server": check_ssh_server(),
            "secure_boot": read_secure_boot(),
            "running_as_root": os.geteuid() == 0 if hasattr(os, "geteuid") else False,
        },
        "scope": "Local read-only inventory. No network scanning or configuration changes.",
    }


def render_classic(data: dict[str, Any], color: bool = True) -> str:
    def paint(text: str, code: str) -> str:
        return f"\033[{code}m{text}\033[0m" if color else text

    s, m, d, n, c = data["system"], data["memory"], data["disk_root"], data["network"], data["checks"]
    cpu_text = "Unknown" if s["cpu_usage_percent"] is None else f"{s['cpu_usage_percent']:.1f}%"
    temp_text = "Unknown" if data["temperature_c"] is None else f"{data['temperature_c']:.1f} °C"
    lines = [paint(line, "1;36") for line in logo_lines()]
    lines += [
        paint("  ABDUFORGE / LOCAL-FIRST LINUX SYSTEM CONSOLE", "1;37"),
        paint(f"  VERSION {VERSION}  ·  CT CUSTOM EDITION  ·  READ ONLY", "2"),
        paint("  " + "─" * 59, "2"),
        "",
        paint("  SYSTEM", "1;36"),
        f"  OS           {s['distribution']}",
        f"  Kernel       {s['kernel']} ({s['architecture']})",
        f"  CPU          {s['cpu']} ({s['cpu_threads']} threads)",
        f"  CPU load     {cpu_text}",
        f"  Frequency    {s['cpu_frequency_mhz'] or 'Unknown'} MHz",
        f"  Python       {s['python']}",
        "",
        paint("  RESOURCES", "1;36"),
        f"  RAM          {human_bytes(m['used_bytes'])} / {human_bytes(m['total_bytes'])} ({str(m['used_percent']) + '%' if m['used_percent'] is not None else 'Unknown'})",
        f"  Available    {human_bytes(m['available_bytes'])}",
        f"  Swap         {human_bytes(m['swap_used_bytes'])} / {human_bytes(m['swap_total_bytes'])}",
        f"  Root disk    {human_bytes(d['used_bytes'])} / {human_bytes(d['total_bytes'])} ({str(d['used_percent']) + '%' if d['used_percent'] is not None else 'Unknown'})",
        f"  Temperature  {temp_text}",
        f"  Uptime       {uptime_text(data['uptime_seconds'])}",
        f"  Battery      {data['battery']}",
        "",
        paint("  NETWORK", "1;36"),
        f"  Interfaces   {n['interface_count']}",
        f"  Listeners    {n['listening_socket_count']} local listening sockets",
        "",
        paint("  LOCAL SECURITY INVENTORY", "1;36"),
        f"  Firewall     {c['ufw']}",
        f"  SSH server   {c['ssh_server']}",
        f"  Secure Boot  {c['secure_boot']}",
        paint("  Read-only local inventory · No network scanning · No changes made.", "2"),
        paint(f"  Updated {data['collected_at']}", "2"),
    ]
    return "\n".join(lines)


def render_markdown(data: dict[str, Any]) -> str:
    s, m, d, n, c = data["system"], data["memory"], data["disk_root"], data["network"], data["checks"]
    rows = [
        ("Distribution", s["distribution"]),
        ("Kernel", f"{s['kernel']} ({s['architecture']})"),
        ("CPU", f"{s['cpu']} ({s['cpu_threads']} threads)"),
        ("CPU usage sample", f"{s['cpu_usage_percent']}%" if s["cpu_usage_percent"] is not None else "Unknown"),
        ("CPU frequency", f"{s['cpu_frequency_mhz']} MHz" if s["cpu_frequency_mhz"] is not None else "Unknown"),
        ("Python", s["python"]),
        ("RAM", f"{human_bytes(m['used_bytes'])} used / {human_bytes(m['total_bytes'])} total ({m['used_percent']}%)"),
        ("Available RAM", human_bytes(m["available_bytes"])),
        ("Swap", f"{human_bytes(m['swap_used_bytes'])} used / {human_bytes(m['swap_total_bytes'])} total"),
        ("Swappiness", m["swappiness"] if m["swappiness"] is not None else "Unknown"),
        ("Root disk", f"{human_bytes(d['used_bytes'])} used / {human_bytes(d['total_bytes'])} total"),
        ("Temperature", f"{data['temperature_c']} °C" if data["temperature_c"] is not None else "Unknown"),
        ("Uptime", uptime_text(data["uptime_seconds"])),
        ("Network interfaces", n["interface_count"]),
        ("Local listening sockets", n["listening_socket_count"]),
        ("UFW", c["ufw"]),
        ("OpenSSH server", c["ssh_server"]),
        ("Secure Boot", c["secure_boot"]),
    ]
    table = "\n".join(f"| {name} | {str(value).replace('|', '&#124;')} |" for name, value in rows)
    interfaces = "\n".join(f"- `{item['name']}`: {item['addresses']}" for item in n["interfaces"]) or "- No active non-loopback interface was reported."
    ui = data.get("ui_customization")
    customization = ""
    if isinstance(ui, dict):
        customization = (
            "\n## UI customization\n\n"
            f"- Theme: `{ui.get('theme', 'unknown')}`\n"
            f"- Accent: `{ui.get('accent', 'unknown')}`\n"
            f"- Density: `{ui.get('density', 'unknown')}`\n"
            f"- Brand: `{ui.get('brand', 'unknown')}`\n"
        )
    return (
        f"# ForgeCheck {VERSION} CT report\n\n"
        f"Collected: `{data['collected_at']}`\n\n"
        "| Check | Result |\n|:--|:--|\n"
        f"{table}\n\n## Network interfaces\n\n{interfaces}\n"
        f"{customization}\n"
        "> Local system inventory only. This report is not a security audit. "
        "It may include private LAN IP addresses and listening ports; review before sharing. "
        "No network scanning or system configuration changes are performed.\n"
    )


class Dashboard:
    """Customizable, full-screen terminal dashboard."""
    PAGES = ("OVERVIEW", "RESOURCES", "NETWORK", "SECURITY", "SYSTEM", "CUSTOMIZE", "ABOUT")

    def __init__(self, screen: Any) -> None:
        self.screen = screen
        self.page = 0
        self.data = collect_snapshot()
        self.config = load_config()
        self.message = "Ready. Local read-only mode. Preferences are saved locally."
        self.color = False
        self._setup()

    def _setup(self) -> None:
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        self.screen.keypad(True)
        self.screen.timeout(-1)
        self._apply_colors()

    def _apply_colors(self) -> None:
        """Apply the selected theme and accent using portable curses colors."""
        self.color = False
        if not curses.has_colors() or self.config["theme"] == "mono":
            try:
                self.screen.bkgd(" ")
            except curses.error:
                pass
            return
        try:
            curses.start_color()
            theme = self.config["theme"]
            foreground = curses.COLOR_BLACK if theme == "light" else curses.COLOR_WHITE
            background = curses.COLOR_WHITE if theme == "light" else curses.COLOR_BLACK
            accent_map = {
                "teal": curses.COLOR_CYAN,
                "blue": curses.COLOR_BLUE,
                "green": curses.COLOR_GREEN,
                "amber": curses.COLOR_YELLOW,
                "purple": curses.COLOR_MAGENTA,
                "red": curses.COLOR_RED,
            }
            accent = accent_map.get(self.config["accent"], curses.COLOR_CYAN)
            muted = curses.COLOR_BLUE if theme == "light" else curses.COLOR_CYAN
            pairs = (
                (1, accent, background),
                (2, foreground, background),
                (3, curses.COLOR_GREEN, background),
                (4, curses.COLOR_YELLOW, background),
                (5, muted, background),
                (6, background, accent),
            )
            for pair, fg, bg in pairs:
                curses.init_pair(pair, fg, bg)
            self.screen.bkgd(" ", curses.color_pair(2))
            self.color = True
        except curses.error:
            self.color = False

    def _attr(self, pair: int = 0, bold: bool = False, dim: bool = False) -> int:
        attr = curses.color_pair(pair) if self.color and pair else 0
        if bold:
            attr |= curses.A_BOLD
        if dim:
            attr |= curses.A_DIM
        return attr

    def put(self, y: int, x: int, text: str, attr: int = 0, width: int | None = None) -> None:
        height, columns = self.screen.getmaxyx()
        if y < 0 or y >= height or x < 0 or x >= columns:
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

    def line(self, y: int) -> None:
        _, width = self.screen.getmaxyx()
        self.put(y, 0, "─" * max(0, width - 1), self._attr(5, dim=True))

    def title(self, y: int, x: int, text: str) -> None:
        self.put(y, x, text, self._attr(1, bold=True))

    def kv(self, y: int, x: int, label: str, value: str, width: int) -> None:
        self.put(y, x, f"{label:<13}", self._attr(5, bold=True), 13)
        self.put(y, x + 14, value, self._attr(2), max(1, width - 14))

    def bar(self, y: int, x: int, label: str, used: int | float | None,
            total: int | float | None, width: int) -> None:
        pct = percent(used, total)
        text = "unknown" if pct is None else f"{pct:3d}%"
        bar_width = max(5, min(20, width - 25))
        fill = round((pct or 0) / 100 * bar_width) if pct is not None else 0
        block = "█" * fill + "·" * (bar_width - fill)
        self.put(y, x, f"{label:<9}", self._attr(5, bold=True), 9)
        self.put(y, x + 10, block, self._attr(3 if pct is not None and pct < 85 else 4, bold=True), bar_width)
        self.put(y, x + 12 + bar_width, text, self._attr(2), 6)

    def draw_header(self) -> None:
        height, width = self.screen.getmaxyx()
        logo = logo_lines()
        full_banner = width >= 78 and height >= 25 and self.config["show_logo"] and self.config["density"] == "comfortable"
        if full_banner:
            x = max(1, (width - len(logo[0])) // 2)
            for index, row in enumerate(logo):
                self.put(index, x, row, self._attr(1, bold=True))
            self.put(7, 1, f"{self.config['brand']}  /  LOCAL-FIRST LINUX SYSTEM CONSOLE", self._attr(2, bold=True), width - 2)
            self.put(8, 1, f"VERSION {VERSION}  ·  CT EDITION  ·  READ ONLY  ·  THEME {self.config['theme'].upper()}", self._attr(5, dim=True), width - 2)
            self.line(9)
            nav = "  ".join(f"[{i + 1}] {name}" for i, name in enumerate(self.PAGES))
            self.put(10, 1, nav, self._attr(1, bold=True), width - 2)
            self.line(11)
            self.content_y = 13
        else:
            logo_state = "FORGECHECK" if self.config["show_logo"] else "CONSOLE"
            self.put(0, 1, f"{logo_state}  /  {self.config['brand']}  /  v{VERSION} CT", self._attr(1, bold=True), width - 2)
            self.put(1, 1, f"LOCAL-FIRST LINUX CONSOLE  ·  {self.config['theme'].upper()} / {self.config['accent'].upper()} / {self.config['density'].upper()}", self._attr(5, dim=True), width - 2)
            self.line(2)
            self.put(3, 1, "1 Overview  2 Resources  3 Network  4 Security  5 System  6 Customize  7 About", self._attr(1, bold=True), width - 2)
            self.line(4)
            self.content_y = 6

    def draw_overview(self, y: int, width: int) -> None:
        s, m, d = self.data["system"], self.data["memory"], self.data["disk_root"]
        split = max(39, width // 2)
        left_width, right_width = split - 4, width - split - 3
        self.title(y, 2, "SYSTEM")
        self.kv(y + 2, 2, "OS", s["distribution"], left_width)
        self.kv(y + 3, 2, "Kernel", f"{s['kernel']} / {s['architecture']}", left_width)
        self.kv(y + 4, 2, "CPU", s["cpu"], left_width)
        self.kv(y + 5, 2, "Threads", str(s["cpu_threads"]), left_width)
        self.kv(y + 6, 2, "Python", s["python"], left_width)
        self.kv(y + 7, 2, "Uptime", uptime_text(self.data["uptime_seconds"]), left_width)
        self.title(y, split, "RESOURCES")
        self.bar(y + 2, split, "RAM", m["used_bytes"], m["total_bytes"], right_width)
        self.put(y + 3, split + 10, f"{human_bytes(m['available_bytes'])} available", self._attr(2, dim=True), right_width - 10)
        self.bar(y + 5, split, "SWAP", m["swap_used_bytes"], m["swap_total_bytes"], right_width)
        self.bar(y + 7, split, "ROOT", d["used_bytes"], d["total_bytes"], right_width)

    def draw_resources(self, y: int, width: int) -> None:
        s, m, d = self.data["system"], self.data["memory"], self.data["disk_root"]
        self.title(y, 2, "RESOURCE SUMMARY")
        self.bar(y + 1, 2, "RAM", m["used_bytes"], m["total_bytes"], width - 5)
        self.put(y + 2, 12, f"{human_bytes(m['used_bytes'])} used / {human_bytes(m['total_bytes'])} total / {human_bytes(m['available_bytes'])} available", self._attr(2), width - 14)
        self.bar(y + 3, 2, "SWAP", m["swap_used_bytes"], m["swap_total_bytes"], width - 5)
        self.put(y + 4, 12, f"{human_bytes(m['swap_used_bytes'])} used / {human_bytes(m['swap_total_bytes'])} total / swappiness {m['swappiness']}", self._attr(2), width - 14)
        self.bar(y + 5, 2, "ROOT", d["used_bytes"], d["total_bytes"], width - 5)
        cpu = "Unknown" if s["cpu_usage_percent"] is None else f"{s['cpu_usage_percent']:.1f}%"
        temp = "Unknown" if self.data["temperature_c"] is None else f"{self.data['temperature_c']:.1f} C"
        self.put(y + 6, 12, f"CPU {cpu}  ·  TEMP {temp}  ·  BATTERY {self.data['battery']}", self._attr(2), width - 14)

    def draw_network(self, y: int, width: int) -> None:
        network = self.data["network"]
        self.title(y, 2, "LOCAL NETWORK INVENTORY")
        self.kv(y + 2, 2, "Interfaces", str(network["interface_count"]), width - 5)
        for offset, item in enumerate(network["interfaces"][:3], start=4):
            self.kv(y + offset, 2, item["name"], item["addresses"], width - 5)
        if not network["interfaces"]:
            self.put(y + 4, 2, "No active non-loopback interface reported.", self._attr(4))
        self.kv(y + 7, 2, "Listeners", f"{network['listening_socket_count']} local listening sockets", width - 5)

    def draw_security(self, y: int, width: int) -> None:
        c = self.data["checks"]
        self.title(y, 2, "LOCAL SECURITY INVENTORY")
        self.kv(y + 2, 2, "Firewall", c["ufw"], width - 5)
        self.kv(y + 3, 2, "SSH server", c["ssh_server"], width - 5)
        self.kv(y + 4, 2, "Secure Boot", c["secure_boot"], width - 5)
        self.kv(y + 5, 2, "Privileges", "Root — not recommended" if c["running_as_root"] else "Regular user", width - 5)
        self.put(y + 7, 2, "Inventory only — not an audit. No scanning or settings changed.", self._attr(4, bold=True), width - 5)

    def draw_system(self, y: int, width: int) -> None:
        s = self.data["system"]
        self.title(y, 2, "HARDWARE & RUNTIME")
        cpu = "Unknown" if s["cpu_usage_percent"] is None else f"{s['cpu_usage_percent']:.1f}%"
        freq = f"{s['cpu_frequency_mhz']:.0f} MHz" if s["cpu_frequency_mhz"] is not None else "Unknown"
        temp = f"{self.data['temperature_c']:.1f} °C" if self.data["temperature_c"] is not None else "Not reported"
        self.kv(y + 2, 2, "CPU load", cpu, width - 5)
        self.kv(y + 3, 2, "Frequency", freq, width - 5)
        self.kv(y + 4, 2, "Temperature", temp, width - 5)
        self.kv(y + 5, 2, "Python", s["python"], width - 5)
        self.kv(y + 6, 2, "Session", s["session_type"], width - 5)
        load = ", ".join(str(x) for x in self.data["load_average"]) or "Not reported"
        self.kv(y + 7, 2, "Load average", load, width - 5)

    def draw_customize(self, y: int, width: int) -> None:
        self.title(y, 2, "PERSONALIZE YOUR FORGECHECK CONSOLE")
        rows = [
            ("Theme", f"{self.config['theme'].upper()}  (dark / light / mono)"),
            ("Accent", f"{self.config['accent'].upper()}  ({', '.join(ACCENT_NAMES)})"),
            ("Density", f"{self.config['density'].upper()}  (comfortable / compact)"),
            ("Large logo", "ON" if self.config["show_logo"] else "OFF"),
            ("Brand label", self.config["brand"]),
        ]
        for offset, (label, value) in enumerate(rows, 2):
            self.kv(y + offset, 3, label, value, width - 7)
        controls = "T theme  A accent  D density  L logo  B brand  X reset  S save"
        self.put(y + 8, 3, controls, self._attr(3, bold=True), width - 6)

    def _save_preferences(self) -> None:
        try:
            save_config(self.config)
            self.message = f"Preferences saved to {CONFIG_PATH}"
        except OSError as exc:
            self.message = f"Could not save preferences: {exc}"

    def _edit_brand(self) -> None:
        height, width = self.screen.getmaxyx()
        row = max(0, height - 2)
        prompt = "New brand label (A-Z, 0-9, spaces, . _ -; max 28): "
        try:
            self.screen.move(row, 1)
            self.screen.clrtoeol()
            self.screen.addnstr(row, 1, prompt, max(1, width - 3))
            curses.echo()
            try:
                curses.curs_set(1)
            except curses.error:
                pass
            raw = self.screen.getstr(row, min(width - 2, len(prompt) + 1), 28)
            value = raw.decode("ascii", errors="ignore").strip()
            if not value:
                self.message = "Brand unchanged; empty labels are not allowed."
                return
            safe_value = re.sub(r"[^A-Za-z0-9 ._-]", "", value).strip()[:28]
            if not safe_value:
                self.message = "Brand unchanged; enter at least one supported character."
                return
            normalized = safe_value.upper()
            if normalized != self.config["brand"]:
                self.config["brand"] = normalized
                self._save_preferences()
            else:
                self.message = "Brand unchanged; use at least one valid character."
        except curses.error:
            self.message = "Brand edit cancelled."
        finally:
            curses.noecho()
            try:
                curses.curs_set(0)
            except curses.error:
                pass

    def customize(self, key: int) -> None:
        if key in (ord("t"), ord("T")):
            index = THEME_NAMES.index(self.config["theme"])
            self.config["theme"] = THEME_NAMES[(index + 1) % len(THEME_NAMES)]
            self._apply_colors()
            self._save_preferences()
        elif key in (ord("a"), ord("A")):
            index = ACCENT_NAMES.index(self.config["accent"])
            self.config["accent"] = ACCENT_NAMES[(index + 1) % len(ACCENT_NAMES)]
            self._apply_colors()
            self._save_preferences()
        elif key in (ord("d"), ord("D")):
            self.config["density"] = "compact" if self.config["density"] == "comfortable" else "comfortable"
            self._save_preferences()
        elif key in (ord("l"), ord("L")):
            self.config["show_logo"] = not self.config["show_logo"]
            self._save_preferences()
        elif key in (ord("b"), ord("B")):
            self._edit_brand()
        elif key in (ord("x"), ord("X")):
            self.config = reset_config()
            self._apply_colors()
            self.message = "Default customization restored and saved."
        elif key in (ord("s"), ord("S")):
            self._save_preferences()

    def draw_about(self, y: int, width: int) -> None:
        self.title(y, 2, "ABOUT FORGECHECK CT")
        lines = [
            "A customizable, local-first Linux system console by Abduali / AbduForge.",
            "Personal themes, accent colors, density, logo and brand label.",
            "System, resources, hardware, network and local security inventory.",
            "Python standard library only. No third-party runtime dependencies.",
            "DESIGN:  Local-first  /  Read-only  /  User-customizable",
            "SCOPE:   Not a vulnerability scanner or a security audit.",
            "KEYS:  1-7 pages  |  C customize  |  R refresh  |  J JSON  |  M Markdown  |  Q quit",
            f"CONFIG: {CONFIG_PATH} (local user preferences; excluded from reports)",
        ]
        for offset, line in enumerate(lines, 1):
            strong = line.startswith(("DESIGN:", "SCOPE:", "KEYS:"))
            self.put(y + offset, 2, line, self._attr(1 if strong else 2, bold=strong), width - 5)

    def draw_help(self) -> None:
        self.screen.erase()
        height, width = self.screen.getmaxyx()
        self.put(1, 2, "FORGECHECK CT — KEYBOARD GUIDE", self._attr(1, bold=True))
        self.line(3)
        items = [
            ("1", "Overview", "System identity and compact resource summary."),
            ("2", "Resources", "RAM, swap, root disk, CPU sample and battery."),
            ("3", "Network", "Local interface addresses and listening sockets."),
            ("4", "Security", "UFW, OpenSSH package and Secure Boot inventory."),
            ("5", "System", "CPU frequency, temperature, runtime and load."),
            ("6", "Customize", "Themes, accents, density, logo and brand label."),
            ("7", "About", "Project scope and design principles."),
            ("C", "Customize", "Jump to the customization page."),
            ("T/A/D/L/B", "Style controls", "Change theme, accent, density, logo or brand."),
            ("X / S", "Reset / save", "Restore defaults or save current preferences."),
            ("R", "Refresh", "Collect a fresh local system snapshot."),
            ("J", "Export JSON", "Save a timestamped JSON report."),
            ("M", "Export Markdown", "Save a readable Markdown report."),
            ("Q", "Quit", "Leave the dashboard and return to the shell."),
        ]
        y = 5
        for key, label, description in items:
            self.put(y, 3, f"[{key}]", self._attr(3, bold=True), 5)
            self.put(y, 9, label, self._attr(2, bold=True), 18)
            self.put(y, 29, description, self._attr(2), width - 32)
            y += 1
            if y >= height - 4:
                break
        self.line(height - 3)
        self.put(height - 2, 2, "Press any key to return.", self._attr(4))
        self.screen.refresh()
        self.screen.getch()

    def export(self, kind: str) -> None:
        try:
            REPORT_DIR.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            suffix = "json" if kind == "json" else "md"
            path = REPORT_DIR / f"forgecheck-{stamp}.{suffix}"
            export_data = {**self.data, "ui_customization": dict(self.config)}
            content = json.dumps(export_data, indent=2, ensure_ascii=False) + "\n" if kind == "json" else render_markdown(export_data)
            path.write_text(content, encoding="utf-8")
            self.message = f"Saved {path}"
        except OSError as exc:
            self.message = f"Export failed: {exc}"

    def draw(self) -> None:
        self.screen.erase()
        height, width = self.screen.getmaxyx()
        if height < 20 or width < 60:
            self.put(1, 1, f"FORGECHECK {VERSION} CT", self._attr(1, bold=True))
            self.put(3, 1, "Terminal is too small. Resize to at least 80x24 for the full view.", self._attr(4))
            self.put(5, 1, "Press Q to quit.", self._attr(2))
        else:
            self.draw_header()
            y = self.content_y
            draw_page = (self.draw_overview, self.draw_resources, self.draw_network,
                         self.draw_security, self.draw_system, self.draw_customize, self.draw_about)
            draw_page[self.page](y, width)
            self.line(height - 3)
            self.put(height - 2, 1, "1-7 Pages   C Customize   R Refresh   J JSON   M Markdown   H Help   Q Quit", self._attr(1, bold=True), width - 2)
        self.put(height - 1, 1, self.message, self._attr(2, dim=True), width - 2)
        self.screen.refresh()

    def run(self) -> int:
        while True:
            self.draw()
            key = self.screen.getch()
            if key in (ord("q"), ord("Q"), 27):
                return 0
            if key in (curses.KEY_RESIZE,):
                continue
            if key in (ord("h"), ord("H"), ord("?")):
                self.draw_help()
            elif key in (ord("r"), ord("R")):
                self.data = collect_snapshot()
                self.message = "Snapshot refreshed."
            elif key in (ord("j"), ord("J")):
                self.export("json")
            elif key in (ord("m"), ord("M")):
                self.export("markdown")
            elif ord("1") <= key <= ord("7"):
                self.page = key - ord("1")
                self.message = f"Opened {self.PAGES[self.page].lower()} page."
            elif key in (ord("c"), ord("C")):
                self.page = 5
                self.message = "Opened customization. Preferences are stored locally."
            elif self.page == 5 and key in tuple(map(ord, "tTaAdDlLbBxXsS")):
                self.customize(key)
            elif key in (curses.KEY_LEFT, curses.KEY_RIGHT):
                self.page = (self.page + (1 if key == curses.KEY_RIGHT else -1)) % len(self.PAGES)
                self.message = f"Opened {self.PAGES[self.page].lower()} page."


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="forgecheck",
        description="ForgeCheck 1.2.0 CT — a customizable, local, read-only Linux system console.",
    )
    parser.add_argument("--version", action="version", version=f"ForgeCheck {VERSION} CT")
    parser.add_argument("--classic", action="store_true", help="print a one-shot terminal snapshot")
    parser.add_argument("--dashboard", action="store_true", help="open the full-screen terminal dashboard")
    parser.add_argument("--json", action="store_true", help="print a JSON snapshot")
    parser.add_argument("--report", metavar="FILE", help="write a Markdown report to FILE")
    parser.add_argument("--no-color", action="store_true", help="disable ANSI colors in classic mode")
    parser.add_argument("--config-path", action="store_true", help="print the local customization file path")
    parser.add_argument("--reset-customization", action="store_true", help="restore default UI preferences")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.config_path:
        print(CONFIG_PATH)
        return 0
    if args.reset_customization:
        reset_config()
        print(f"ForgeCheck preferences reset: {CONFIG_PATH}")
        return 0
    if args.dashboard and not (sys.stdin.isatty() and sys.stdout.isatty()):
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
