# Changelog

## 1.1.0 — SUPER — 2026-11-13

- Expanded the dashboard from four to six pages: Overview, Resources, Network, Security, System, and About.
- Added local network interface and listening-socket inventory using `ip` and `ss` when available.
- Added CPU usage sampling, CPU frequency, and hardware temperature readings when exposed by the kernel.
- Added Secure Boot state detection when the UEFI variable is readable.
- Added swappiness, separate root/home filesystem details, and fuller RAM/swap percentages.
- Expanded JSON and Markdown reports with network, hardware, and security inventory; documented that reports may contain private LAN addresses.
- Improved terminal resizing, small-screen handling, keyboard help, and KDE launcher naming.
- Expanded automated tests and clarified the read-only local scope.
- Kept the application dependency-free and compatible with modest Linux systems.

## 1.0.0 — 2026-11-12

- Rebuilt the one-shot snapshot tool as a full-screen, keyboard-driven terminal dashboard.
- Added an original large block-letter FORGECHECK wordmark.
- Added Overview, Resources, Security, and About pages.
- Added one-key refresh and timestamped JSON / Markdown exports.
- Added CPU thread count, load average, and battery status when available.
- Added a user-local installer and uninstaller, plus a KDE Konsole application launcher.
- Kept the app read-only, dependency-free, and limited to local system inventory.

## 0.1.0 — 2026-11-12

- First public version.
- Added local Linux system snapshot for OS, kernel, CPU, memory, swap, disk, and uptime.
- Added basic UFW and Debian OpenSSH package inventory checks.
- Added JSON output and Markdown report export.
- Kept the tool dependency-free and read-only.
