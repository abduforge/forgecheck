# Built-in checks in ForgeCheck 2.0.0

ForgeCheck intentionally checks a limited set of local configuration signals. It does not claim to detect every security problem.

| Check ID | What is inspected | Important limitation |
|---|---|---|
| `SHADOW_FILE_PERMISSIONS` | Owner and selected permission bits on `/etc/shadow` | Does not inspect password hashes or account contents |
| `PASSWD_FILE_PERMISSIONS` | Group/other write permissions on `/etc/passwd` | Does not audit LDAP, SSSD, or other remote identity providers |
| `UID_ZERO_ACCOUNTS` | UID 0 entries in `/etc/passwd` | Does not list account names in the report |
| `SSH_EMPTY_PASSWORDS` | Explicit `PermitEmptyPasswords yes` directives | Static inspection; does not calculate the full effective configuration |
| `SSH_ROOT_LOGIN` | Explicit `PermitRootLogin yes` directives | Included files and Match blocks can affect effective behavior |
| `SSH_PASSWORD_AUTH` | Explicit `PasswordAuthentication yes` directives | Password authentication is context-dependent, not automatically a vulnerability |
| `SSH_LISTENER` | Local TCP listener on port 22 via `ss` | Does not test remote reachability |
| `FIREWALL_STATUS` | Read-only status from supported firewall tools | Does not evaluate every rule or prove internet exposure |
| `IPV4_REDIRECTS` | Selected IPv4 redirect sysctl values | Does not cover every network namespace or IPv6 setting |
| `IPV4_FORWARDING` | `/proc/sys/net/ipv4/ip_forward` | Forwarding may be intentional for routers, VPN gateways, or containers |
| `SYSTEM_DIRECTORY_PERMISSIONS` | World-write bit on `/etc` and `/etc/ssh` | Does not audit every file, ACL, or mount option |

## Severity meanings

- **PASS:** the inspected setting matched this check's expected condition.
- **INFO:** informational context or a check that could not be completed.
- **LOW:** a minor configuration concern.
- **MEDIUM:** a setting worth reviewing in context.
- **HIGH:** a potentially important configuration weakness.
- **CRITICAL:** a high-impact setting that should be reviewed promptly.

A PASS is limited to the specific check. It is not a certification that the host is secure.
