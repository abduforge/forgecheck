# Privacy and data handling

ForgeCheck is designed to run locally.

## Network behavior

The ForgeCheck executable does not make network requests. It does not upload reports, telemetry, or scan results. It does not scan remote hosts.

## Local information read

Depending on the checks available on a Linux system, ForgeCheck may read:

- `/etc/os-release`
- `/etc/passwd` (to count UID 0 entries; account names are not included in reports)
- metadata for `/etc/passwd`, `/etc/shadow`, `/etc`, and `/etc/ssh`
- selected SSH server configuration files
- selected `/proc/sys` kernel settings
- local socket and firewall status through fixed read-only system utilities

## Report content

Reports include the Linux distribution name, kernel release, architecture, check identifiers, findings, and recommendations. They are designed not to include hostnames, login names, IP addresses, full firewall rules, or names of additional UID 0 accounts.

Reports are written only when the user explicitly supplies an output path. Review a report before sharing it because configuration details can still reveal information about a system.
