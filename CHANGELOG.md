# Changelog

## [2.0.0] - 2026-11-15

### Added
- Rebuilt ForgeCheck as a Rust CLI focused on fast, local Linux security reviews.
- Added checks for account-file permissions and additional UID 0 accounts.
- Added best-effort SSH configuration and local TCP/22 listener checks.
- Added read-only firewall status detection for UFW, firewalld, nftables, and iptables.
- Added IPv4 redirect, forwarding, and sensitive system-directory permission checks.
- Added human-readable terminal, JSON, and Markdown reports.
- Added `doctor`, `checks`, `--help`, and `--version` commands.
- Added a user-local installer and uninstaller.
- Added CI and tagged-release workflows.
- Added English and Russian README files and check/privacy documentation.

### Design
- No third-party Rust dependencies.
- Read-only scan behavior; no remote scanning, exploitation, or automatic remediation.
- Reports avoid including hostnames, login names, IP addresses, and account names.
