<div align="center">

# ForgeCheck

**A small, local-first Linux system snapshot tool.**

Read the machine. Understand the basics. Change nothing.

`LINUX` &nbsp;·&nbsp; `PYTHON` &nbsp;·&nbsp; `SYSTEM INVENTORY`

</div>

---

ForgeCheck is a lightweight command-line utility that prints a clear snapshot of a Linux machine: distribution, kernel, CPU, memory, swap, root-disk usage, uptime, and a couple of basic security-related inventory checks.

It is designed as a small, understandable Python project — useful for learning how a CLI works and for keeping a simple record of a machine's state.

## Preview

```text
╭──────────────────────────────────────────────╮
│  FORGECHECK  ·  LOCAL SYSTEM SNAPSHOT         │
╰──────────────────────────────────────────────╯
  SYSTEM
  OS           Debian GNU/Linux 13 (trixie)
  Kernel       6.x.x (x86_64)
  CPU          Intel / AMD processor
  Python       3.x.x

  RESOURCES
  RAM          ... used / ... total
  Available    ...
  Swap         ... used / ... total
  Root disk    ... used / ... total
  Uptime       ...

  SECURITY POSTURE (BASIC INVENTORY)
  Firewall     UFW status or not detected
  SSH server   Package status
  Privileges   Regular user

  Read-only local checks. No packets sent. No settings changed.
```

*The values above are illustrative; your output will reflect your own computer.*

## Features

- Shows Linux distribution, kernel, architecture, CPU, and Python version.
- Summarizes RAM, swap, root-disk usage, and uptime.
- Reports whether UFW is available and what its status command reports.
- Checks whether the Debian `openssh-server` package is installed.
- Supports JSON output and Markdown reports.
- Uses only the Python standard library; no pip dependencies.

## Requirements

- Linux
- Python 3.10 or newer
- `dpkg-query` for the optional OpenSSH package check on Debian-based systems
- `ufw` for the optional UFW status check

## Run

Clone the repository, then:

```bash
chmod +x forgecheck.py
./forgecheck.py
```

JSON output:

```bash
./forgecheck.py --json
```

Save a Markdown report:

```bash
./forgecheck.py --report forgecheck-report.md
```

Disable terminal colors:

```bash
./forgecheck.py --no-color
```

## Optional user-local command

Install the script for the current user (no `sudo` required):

```bash
mkdir -p "$HOME/.local/bin"
install -m 755 forgecheck.py "$HOME/.local/bin/forgecheck"
```

Make sure `~/.local/bin` is on your `PATH`. For Bash, add it if needed:

```bash
grep -q 'HOME/.local/bin' "$HOME/.bashrc" || \
  printf '\nexport PATH="$HOME/.local/bin:$PATH"\n' >> "$HOME/.bashrc"
source "$HOME/.bashrc"
```

Then run `forgecheck` from any directory.

## Safety and scope

ForgeCheck is a **read-only local inventory**, not a vulnerability scanner or penetration-testing tool. It does not send network packets, enumerate remote hosts, exploit services, or modify system configuration. It does not claim that a machine is secure. Firewall status may be unknown when a different firewall manager is used or elevated permissions are required.

Run it as a regular user. Some checks may return `unknown` rather than asking for administrator privileges.

## Project status

Early development — `0.1.0`. Contributions, bug reports, and suggestions are welcome.

## License

MIT. See [LICENSE](LICENSE).

---

<div align="center">

**Built by Abduali · AbduForge**

*Every system tells a story. Learn to read it.*

</div>
