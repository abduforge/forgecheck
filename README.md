<div align="center">

# FORGECHECK

**SUPER · A local-first Linux system console**

`SYSTEM INVENTORY` &nbsp;·&nbsp; `TERMINAL DASHBOARD` &nbsp;·&nbsp; `PYTHON`

*Read the machine. Understand the basics. Change nothing.*

**Version 1.1.0**

</div>

---

ForgeCheck is a lightweight, keyboard-driven terminal dashboard for viewing a local Linux system snapshot. The SUPER release expands the dashboard with local network inventory, listening-socket visibility, CPU sampling, hardware telemetry, Secure Boot state, and more complete reports.

It is designed to be understandable, dependency-free, read-only, and gentle on modest hardware.

## Preview

```text
█████ █████ ████  █████ █████ █████ █   █ █████ █████ █   █
█     █   █ █   █ █     █     █     █   █ █     █     █  █
█     █   █ █   █ █     █     █     █   █ █     █     █ █
████  █   █ ████  █ ███ ████  █     █████ ████  █     ██
█     █   █ █ █   █   █ █     █     █   █ █     █     █ █
█     █   █ █  █  █   █ █     █     █   █ █     █     █  █
█     █████ █   █ █████ █████ █████ █   █ █████ █████ █   █

ABDUFORGE / LOCAL-FIRST LINUX SYSTEM CONSOLE
VERSION 1.1.0 · SUPER EDITION · READ ONLY

[1] OVERVIEW [2] RESOURCES [3] NETWORK
[4] SECURITY [5] SYSTEM [6] ABOUT
```

*The screenshot-style text above is illustrative. Actual values are collected locally from the machine running ForgeCheck.*

## What's new in 1.1.0 SUPER

- Six-page full-screen terminal dashboard: Overview, Resources, Network, Security, System, About.
- CPU usage sampling and current frequency when the kernel exposes it.
- Hardware temperature reading from supported `hwmon` / thermal sysfs sensors.
- Local network interface addresses and listening-socket inventory using `ip` and `ss` when available.
- Secure Boot state when the UEFI variable is readable.
- RAM, swap, swappiness, root and home filesystem details.
- Timestamped JSON and Markdown report exports.
- Responsive terminal layout, keyboard navigation and resize handling.
- Updated KDE launcher, installer, uninstaller, tests and documentation.

## Features

- Large original `FORGECHECK` block-letter wordmark.
- Live local snapshot of distribution, kernel, architecture, CPU, Python, RAM, swap, filesystems, uptime, load average, battery, CPU temperature and frequency when available.
- Basic local inventory for UFW, the Debian `openssh-server` package and Secure Boot state when readable.
- Local-only network inventory. It lists this machine's interface addresses and listening sockets; it does not probe remote machines.
- Classic one-shot output for scripts and non-interactive terminals.
- JSON output and Markdown report export.
- Optional KDE launcher opens a dedicated full-screen Konsole window.
- Python standard library only. No `pip install` runtime dependencies.

## Requirements

- Linux and Python 3.10 or newer.
- A UTF-8 terminal for the block-letter artwork.
- `curses` (normally included with Python on Linux distributions).
- Optional `ip` and `ss` commands from `iproute2` for network inventory.
- Optional `ufw`, `dpkg-query`, and UEFI efivars for their respective inventory rows.
- Optional `konsole` for the KDE application-menu launcher.

## Run from source

```bash
chmod +x forgecheck.py
./forgecheck.py
```

In an interactive terminal, ForgeCheck opens the full-screen dashboard. Press `Q` or `Esc` to return to the shell.

Classic one-shot output:

```bash
./forgecheck.py --classic
```

JSON output:

```bash
./forgecheck.py --json
```

Write a Markdown report:

```bash
./forgecheck.py --report ~/forgecheck-report.md
```

Start the dashboard explicitly:

```bash
./forgecheck.py --dashboard
```

## Dashboard keys

| Key | Action |
|:--|:--|
| `1`–`6` | Open Overview, Resources, Network, Security, System or About |
| `←` / `→` | Previous / next page |
| `R` | Refresh the snapshot |
| `J` | Export JSON to `~/ForgeCheck-Reports/` |
| `M` | Export Markdown to `~/ForgeCheck-Reports/` |
| `H` or `?` | Keyboard help |
| `Q` or `Esc` | Quit dashboard |

## Install for the current user

No administrator privileges are required. From the project directory:

```bash
./install.sh
```

The installer places the command in `~/.local/bin/forgecheck`, installs the icon, and creates a KDE application-menu entry named **ForgeCheck SUPER Console**. On KDE systems with Konsole installed, that launcher opens a separate full-screen terminal window.

Make sure `~/.local/bin` is on your `PATH` if the command is not found.

Uninstall the user-local command and launcher:

```bash
./uninstall.sh
```

Reports in `~/ForgeCheck-Reports/` are not removed by the uninstaller.

## Safety and scope

ForgeCheck is a **read-only local inventory**, not a vulnerability scanner or penetration-testing framework. Network information is limited to local interface addresses and local listening sockets. It does not send network probes, enumerate remote hosts, exploit services, start or stop services, change firewall rules, or modify system configuration. It does not claim that a machine is secure.

Run it as a regular user. Some optional checks may say that status is unavailable when elevated permission would be required. That is intentional: ForgeCheck does not request `sudo` or prompt for a password.

**Privacy note:** JSON and Markdown reports can contain local LAN IP addresses and listening-port details. Review exported reports before posting them publicly.

## Development and tests

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile forgecheck.py
```

The test suite uses only Python's standard library.

## Project

- Version: `1.1.0`
- Codename: `SUPER`
- License: MIT
- Author: Abduali / AbduForge

*Every system tells a story. Learn to read it.*
