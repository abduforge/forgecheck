# ForgeCheck 2.0.0 GLOBAL

A complete Rust rewrite focused on one goal: make useful Linux security checks fast and understandable.

## Highlights

- One-command local review: `forgecheck`
- Clear PASS / INFO / LOW / MEDIUM / HIGH / CRITICAL findings
- Readable explanations and recommendations
- JSON and Markdown report export
- Checks for account-file permissions, UID 0 accounts, SSH configuration, local SSH listener, firewall status, IPv4 redirect/forwarding settings, and sensitive system-directory permissions
- `doctor` and `checks` helper commands
- User-local installation without `sudo`
- No third-party Rust dependencies

## Safety and scope

ForgeCheck 2.0.0 is read-only. It does not exploit vulnerabilities, modify system settings, scan remote devices, or upload reports. Firewall and SSH checks are best-effort and distribution-dependent.

This release has not undergone an independent security audit. Findings are configuration signals, not a guarantee that a host is secure.

## Install

Download the Linux archive matching your architecture, extract it, and run:

```bash
./install.sh
```

Then run:

```bash
forgecheck
```
