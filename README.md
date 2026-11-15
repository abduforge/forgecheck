# ForgeCheck

Русская версия: [README на русском](README_RU.md).

**A simple, fast, read-only security check for Linux.** Run one command, understand the findings, and decide what to fix. No cloud account, no remote scanning, and no automatic system changes.

<p align="center">
  <a href="https://github.com/abduforge/forgecheck/releases/latest"><strong>⬇ DOWNLOAD FOR LINUX — LATEST RELEASE</strong></a>
</p>

New here? Open the download page above, choose the Linux archive for your computer, extract it, and run `./install.sh`. Then open a terminal and type `forgecheck`.

```bash
forgecheck
```

[Quick start](#quick-start) · [Features](#what-it-checks) · [Example output](#example) · [Full documentation](#documentation) · [Security](SECURITY.md)

---

## What is ForgeCheck?

ForgeCheck is a lightweight Linux security and configuration auditor written in Rust. It checks selected local settings, explains why a result matters, and gives a practical recommendation in plain language.

**The goal:** useful security visibility without a complicated interface.

### At a glance

- **One-command workflow:** run `forgecheck` to start a local review.
- **Readable findings:** PASS, INFO, LOW, MEDIUM, HIGH, and CRITICAL labels.
- **Useful reports:** terminal, JSON, and Markdown formats.
- **Read-only by design:** ForgeCheck does not change settings or install packages.
- **Local-first:** it does not upload reports or scan remote systems.
- **Fast and lightweight:** Rust, standard library only, no third-party Rust dependencies.

## Quick start

### Option A — Download a ready-to-run Linux build

1. Open **[ForgeCheck Releases](https://github.com/abduforge/forgecheck/releases/latest)**.
2. Download the archive matching your Linux computer (`x86_64` for most Intel/AMD PCs).
3. Extract the archive.
4. In the extracted folder, run:

   ```bash
   ./install.sh
   ```

5. Open a new terminal and run:

   ```bash
   forgecheck
   ```

The installer places the program in `~/.local/bin` and does not require root privileges. If that directory is not in your `PATH`, add this line to `~/.profile` and reopen your terminal:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

### Option B — Build from source

Requirements: Linux and Rust 1.85 or newer.

```bash
git clone https://github.com/abduforge/forgecheck.git
cd forgecheck
cargo test --all-targets
cargo build --release
./target/release/forgecheck
```

To install the built program into your user account:

```bash
./install.sh
```

## What it checks

ForgeCheck 2.0.0 currently focuses on a small set of useful local Linux checks:

| Area | What ForgeCheck looks for |
|---|---|
| Account files | Risky permissions on `/etc/passwd` and `/etc/shadow` |
| Privileged accounts | Unexpected additional accounts with UID 0 |
| SSH configuration | Explicit settings for root login, empty passwords, and password authentication |
| SSH listener | A local TCP listener on port 22, when `ss` is available |
| Firewall | Read-only status from UFW, firewalld, nftables, or iptables when available |
| Kernel networking | IPv4 redirect settings and IP forwarding |
| System directories | World-writable `/etc` or `/etc/ssh` directories |

ForgeCheck reports what it can actually observe. Missing tools or inaccessible settings are marked as unavailable or informational; they are not silently treated as secure.

## Commands

| Command | What it does |
|---|---|
| `forgecheck` | Run the default local review |
| `forgecheck scan` | Same as the default review |
| `forgecheck scan --json` | Print a JSON report |
| `forgecheck scan --markdown` | Print a Markdown report |
| `forgecheck scan -o report.md --markdown` | Save a Markdown report |
| `forgecheck checks` | List the checks included in this version |
| `forgecheck doctor` | Check Linux files and optional local tools |
| `forgecheck --version` | Print the installed version |
| `forgecheck --help` | Show help |

### Save a report

Markdown:

```bash
forgecheck scan --markdown --output forgecheck-report.md
```

JSON:

```bash
forgecheck scan --json --output forgecheck-report.json
```

Reports do not include the computer's hostname, the current username, IP addresses, or account names for additional UID 0 entries. Review any report before sharing it anyway.

## Example

A result looks like this:

```text
ForgeCheck 2.0.0 GLOBAL
Local Linux security overview · read-only · no network scanning

OS: Debian GNU/Linux
Kernel: 6.x
Architecture: x86_64

Summary: 11 checks | 7 pass | 2 info | 1 medium | 1 high | 0 critical

[PASS] PASSWD_FILE_PERMISSIONS — /etc/passwd is not group- or world-writable
[MEDIUM] FIREWALL_STATUS — No active supported firewall could be confirmed
  Recommendation: Check your firewall using the tool that manages it...
```

The numbers above are illustrative, not a real scan result.

## How ForgeCheck works

1. It reads selected local Linux configuration files and kernel settings.
2. It may run a few fixed, read-only status commands if the relevant utility is installed.
3. It converts observations into findings with a severity, explanation, and recommendation.
4. It displays the report locally or writes it to a file you choose.

ForgeCheck does not need `sudo` for its normal scan. Some checks may be unavailable to an unprivileged user. Do not run it as root just to make every check appear complete.

## What ForgeCheck is not

- It is **not** a penetration-testing framework.
- It does **not** exploit vulnerabilities or attempt to gain access.
- It does **not** scan public IP addresses, other devices, or networks.
- It is **not** an antivirus or malware-removal tool.
- It does **not** automatically edit firewall, SSH, kernel, or account settings.
- A PASS result is not a guarantee that a system is secure.

## Supported systems

ForgeCheck is Linux-first and is intended for modern Linux distributions, including MX Linux, Debian, Ubuntu, Fedora, and Arch-based systems. Some checks depend on distribution tools and configuration paths, so results can differ between distributions.

## Project status

**Version:** 2.0.0 GLOBAL  
**Language:** Rust  
**License:** MIT  
**Maintainer:** [AbduForge](https://github.com/abduforge)

ForgeCheck 2.0.0 is an initial global redesign. It is useful for local configuration review, but it has not undergone an independent security audit. See [SECURITY.md](SECURITY.md).

## Documentation

- [Checks explained](docs/CHECKS.md)
- [Privacy and data handling](docs/PRIVACY.md)
- [Security policy](SECURITY.md)
- [Changelog](CHANGELOG.md)
- [Release notes](RELEASE_NOTES.md)
- [Project plan](PROJECT_PLAN.md)

## Contributing

Bug reports, documentation improvements, and defensive Linux-check ideas are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

---

**ForgeCheck — powerful checks, straightforward results.**
