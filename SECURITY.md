# Security Policy

## Scope

ForgeCheck is a local, read-only Linux configuration auditor. It is not a penetration-testing framework, vulnerability exploit, malware scanner, or remote network scanner.

## Reporting a security issue

Please do not publish credentials, private reports, or an unpatched vulnerability in a public issue. Use GitHub's **Report a vulnerability** feature on the repository's Security tab when available. If private reporting is unavailable, open a minimal issue asking for a private contact route without including sensitive details.

## Security design

- No network requests are made by the ForgeCheck executable.
- No system settings or files are changed by scan commands.
- External commands are fixed, read-only status commands (`ss`, `ufw status`, `firewall-cmd --state`, `nft list ruleset`, and `iptables -S`) and are only attempted if present.
- Reports omit the hostname, login name, IP addresses, full firewall rules, and names of additional UID 0 accounts.
- A report is still local system information. Review it before sharing.
- ForgeCheck does not require root privileges for its normal scan.

## Limitations

Checks are best-effort and distribution-dependent. Static SSH configuration inspection does not fully evaluate every `Include`, `Match`, command-line override, or effective runtime setting. Firewall-manager detection does not prove internet reachability or evaluate every rule. A PASS finding is not a guarantee of security.

ForgeCheck 2.0.0 has not undergone an independent security audit. Do not treat it as the only control protecting a critical system.
