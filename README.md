<div align="center">

# FORGECHECK

**A local-first Linux system console.**

`SYSTEM INVENTORY` &nbsp;·&nbsp; `TERMINAL DASHBOARD` &nbsp;·&nbsp; `PYTHON`

*Read the machine. Understand the basics. Change nothing.*

</div>

---

ForgeCheck is a lightweight, keyboard-driven terminal dashboard for viewing a local Linux system snapshot. Version 1.0 introduces a full-screen console, a large original block-letter wordmark, separate information pages, and one-key report exports.

It is designed to be understandable, dependency-free, and gentle on modest hardware.

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
VERSION 1.0.0  ·  READ ONLY

[1] OVERVIEW   [2] RESOURCES   [3] SECURITY   [4] ABOUT

SYSTEM                         RESOURCES
OS       MX Linux              RAM       66%  █████████···
Kernel   Linux 6.x              SWAP      20%  ██··········
CPU      Intel / AMD            ROOT      17%  ██··········
```

*The values above are illustrative. The actual dashboard uses live values from your machine.*

## Features

- Full-screen terminal dashboard with four pages: Overview, Resources, Security, and About.
- Large original `FORGECHECK` block-letter banner inspired by classic system-fetch layouts.
- Live local snapshot of distribution, kernel, CPU, Python, RAM, swap, root filesystem, uptime, load average, and battery when available.
- Basic local inventory for UFW and the Debian `openssh-server` package.
- Keyboard navigation and one-key JSON / Markdown report export.
- Classic one-shot output for scripts and terminals without an interactive TTY.
- Uses Python's standard library only. No `pip install` dependencies.
- Optional KDE launcher opens ForgeCheck in a separate full-screen Konsole window.

## Requirements

- Linux and Python 3.10 or newer.
- A terminal supporting UTF-8 for the block-letter artwork.
- `curses` (normally included with Python on Linux distributions).
- Optional `konsole` for the KDE application-menu launcher.
- Optional `ufw` and `dpkg-query` for the corresponding inventory rows.

## Run from source

```bash
chmod +x forgecheck.py
./forgecheck.py
```

In an interactive terminal, ForgeCheck opens the full-screen dashboard. Press `Q` to return to the shell.

One-shot output:

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

Start the full-screen dashboard explicitly:

```bash
./forgecheck.py --dashboard
```

## Dashboard keys

| Key | Action |
|:--|:--|
| `1` | Overview page |
| `2` | Resources page |
| `3` | Security inventory page |
| `4` | About page |
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

The installer places the command in `~/.local/bin/forgecheck`, installs an icon, and creates a KDE application-menu entry named **ForgeCheck Console**. On KDE systems with Konsole installed, that launcher opens a separate full-screen terminal window.

Make sure `~/.local/bin` is on your `PATH`. The installer prints a reminder if it is not.

Uninstall the user-local command and launcher:

```bash
./uninstall.sh
```

Reports in `~/ForgeCheck-Reports/` are not removed by the uninstaller.

## Safety and scope

ForgeCheck is a **read-only local inventory**, not a vulnerability scanner or penetration-testing framework. It does not send network probes, enumerate remote hosts, exploit services, start or stop services, change firewall rules, or modify system configuration. It does not claim that a machine is secure.

Run it as a regular user. Some optional checks may say that status is unavailable when elevated permission would be required. That is intentional: ForgeCheck does not request `sudo` or prompt for a password.

## Development and tests

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile forgecheck.py
```

The application has no third-party Python runtime dependencies.

## Project

- Version: `1.0.0`
- License: MIT
- Author: Abduali / AbduForge

*Every system tells a story. Learn to read it.*
