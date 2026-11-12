#!/usr/bin/env python3
"""ForgeCheck: a small, read-only Linux system snapshot CLI."""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

VERSION = "0.1.0"


def read_os_release(path: Path = Path("/etc/os-release")) -> dict[str, str]:
    result: dict[str, str] = {}
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "=" not in line or line.startswith("#"):
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
            if parts:
                try:
                    values[key] = int(parts[0]) * (1024 if len(parts) > 1 and parts[1] == "kB" else 1)
                except ValueError:
                    continue
    except OSError:
        pass
    return values


def read_cpu_model(path: Path = Path("/proc/cpuinfo")) -> str:
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.lower().startswith(("model name", "hardware")) and ":" in line:
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "Not reported"


def human_bytes(value: int | None) -> str:
    if value is None:
        return "Unknown"
    amount = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if amount < 1024 or unit == "TiB":
            return f"{amount:.1f} {unit}" if unit != "B" else f"{int(amount)} B"
        amount /= 1024
    return f"{amount:.1f} TiB"


def check_ufw() -> str:
    """Read UFW status if the command exists; do not change firewall rules."""
    if not shutil.which("ufw"):
        return "UFW not detected (other firewall tools may be in use)"
    try:
        proc = subprocess.run(
            ["ufw", "status"], capture_output=True, text=True, timeout=4, check=False
        )
        output = (proc.stdout + "\n" + proc.stderr).strip()
        for line in output.splitlines():
            if line.strip().lower() == "status: active":
                return "UFW reports active"
            if line.strip().lower() == "status: inactive":
                return "UFW reports inactive"
        if "permission denied" in output.lower() or "must be run as root" in output.lower():
            return "UFW installed; status requires elevated permission"
        return "UFW installed; status could not be determined"
    except (OSError, subprocess.TimeoutExpired):
        return "UFW installed; status check failed"


def check_ssh_server() -> str:
    """Check whether the OpenSSH server package is installed on Debian-like systems."""
    if not shutil.which("dpkg-query"):
        return "Not checked (dpkg-query unavailable)"
    try:
        proc = subprocess.run(
            ["dpkg-query", "-W", "-f=${db:Status-Status}", "openssh-server"],
            capture_output=True, text=True, timeout=4, check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip() == "installed":
            return "openssh-server package installed"
        return "openssh-server package not detected"
    except (OSError, subprocess.TimeoutExpired):
        return "Not checked"


def collect_snapshot() -> dict[str, Any]:
    os_info = read_os_release()
    mem = read_meminfo()
    total = mem.get("MemTotal")
    available = mem.get("MemAvailable")
    swap_total = mem.get("SwapTotal")
    swap_free = mem.get("SwapFree")

    try:
        disk = shutil.disk_usage("/")
        disk_data = {
            "total_bytes": disk.total,
            "used_bytes": disk.used,
            "free_bytes": disk.free,
            "used_percent": round((disk.used / disk.total) * 100, 1) if disk.total else None,
        }
    except OSError:
        disk_data = {"total_bytes": None, "used_bytes": None, "free_bytes": None, "used_percent": None}

    try:
        uptime_seconds = float(Path("/proc/uptime").read_text().split()[0])
    except (OSError, ValueError, IndexError):
        uptime_seconds = None

    used_swap = (swap_total - swap_free) if swap_total is not None and swap_free is not None else None
    used_ram = (total - available) if total is not None and available is not None else None

    return {
        "tool": "ForgeCheck",
        "version": VERSION,
        "collected_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "system": {
            "distribution": os_info.get("PRETTY_NAME", os_info.get("NAME", "Unknown")),
            "kernel": platform.release(),
            "architecture": platform.machine(),
            "cpu": read_cpu_model(),
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
        "uptime_seconds": round(uptime_seconds) if uptime_seconds is not None else None,
        "checks": {
            "ufw": check_ufw(),
            "ssh_server": check_ssh_server(),
            "running_as_root": os.geteuid() == 0 if hasattr(os, "geteuid") else False,
        },
        "scope": "Local read-only inventory. No network scanning or configuration changes.",
    }


class Style:
    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def paint(self, text: str, code: str) -> str:
        return f"\033[{code}m{text}\033[0m" if self.enabled else text


def uptime_text(seconds: int | None) -> str:
    if seconds is None:
        return "Unknown"
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes = remainder // 60
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


def render_terminal(data: dict[str, Any], style: Style) -> str:
    sysinfo = data["system"]
    mem = data["memory"]
    disk = data["disk_root"]
    checks = data["checks"]
    lines = [
        style.paint("╭──────────────────────────────────────────────╮", "2;36"),
        style.paint("│  FORGECHECK  ·  LOCAL SYSTEM SNAPSHOT         │", "1;36"),
        style.paint("╰──────────────────────────────────────────────╯", "2;36"),
        f"  {style.paint('SYSTEM', '1;37')}",
        f"  OS           {sysinfo['distribution']}",
        f"  Kernel       {sysinfo['kernel']} ({sysinfo['architecture']})",
        f"  CPU          {sysinfo['cpu']}",
        f"  Python       {sysinfo['python']}",
        "",
        f"  {style.paint('RESOURCES', '1;37')}",
        f"  RAM          {human_bytes(mem['used_bytes'])} used / {human_bytes(mem['total_bytes'])} total",
        f"  Available    {human_bytes(mem['available_bytes'])}",
        f"  Swap         {human_bytes(mem['swap_used_bytes'])} used / {human_bytes(mem['swap_total_bytes'])} total",
        f"  Root disk    {human_bytes(disk['used_bytes'])} used / {human_bytes(disk['total_bytes'])} total ({disk['used_percent']}%)" if disk['used_percent'] is not None else "  Root disk    Unknown",
        f"  Uptime       {uptime_text(data['uptime_seconds'])}",
        "",
        f"  {style.paint('SECURITY POSTURE (BASIC INVENTORY)', '1;37')}",
        f"  Firewall     {checks['ufw']}",
        f"  SSH server   {checks['ssh_server']}",
        f"  Privileges   {'Running as root — not recommended' if checks['running_as_root'] else 'Regular user'}",
        "",
        style.paint("  Read-only local checks. No packets sent. No settings changed.", "2"),
        style.paint(f"  ForgeCheck v{data['version']}  ·  {data['collected_at']}", "2"),
    ]
    return "\n".join(lines)


def render_markdown(data: dict[str, Any]) -> str:
    s, m, d, c = data["system"], data["memory"], data["disk_root"], data["checks"]
    rows = [
        ("Distribution", s["distribution"]),
        ("Kernel", f"{s['kernel']} ({s['architecture']})"),
        ("CPU", s["cpu"]),
        ("Python", s["python"]),
        ("RAM", f"{human_bytes(m['used_bytes'])} used / {human_bytes(m['total_bytes'])} total"),
        ("Available RAM", human_bytes(m["available_bytes"])),
        ("Swap", f"{human_bytes(m['swap_used_bytes'])} used / {human_bytes(m['swap_total_bytes'])} total"),
        ("Root disk", f"{human_bytes(d['used_bytes'])} used / {human_bytes(d['total_bytes'])} total"),
        ("Uptime", uptime_text(data["uptime_seconds"])),
        ("UFW", c["ufw"]),
        ("OpenSSH server", c["ssh_server"]),
    ]
    table = "\n".join(f"| {name} | {value} |" for name, value in rows)
    return (
        "# ForgeCheck report\n\n"
        f"Collected: `{data['collected_at']}`\n\n"
        "| Check | Result |\n|:--|:--|\n"
        f"{table}\n\n"
        "> This is a basic local inventory, not a security audit. "
        "It does not scan networks, test vulnerabilities, or change system settings.\n"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="forgecheck",
        description="A small, read-only Linux system snapshot tool.",
    )
    parser.add_argument("--version", action="version", version=f"ForgeCheck {VERSION}")
    parser.add_argument("--json", action="store_true", help="print the snapshot as JSON")
    parser.add_argument("--report", metavar="FILE", help="write a Markdown report to FILE")
    parser.add_argument("--no-color", action="store_true", help="disable terminal colors")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    data = collect_snapshot()
    if args.report:
        try:
            Path(args.report).expanduser().write_text(render_markdown(data), encoding="utf-8")
        except OSError as exc:
            print(f"forgecheck: could not write report: {exc}", file=sys.stderr)
            return 2
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        color = sys.stdout.isatty() and not args.no_color and "NO_COLOR" not in os.environ
        print(render_terminal(data, Style(color)))
        if args.report:
            print(f"\n  Markdown report saved to: {Path(args.report).expanduser()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
