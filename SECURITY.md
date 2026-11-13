# Security and privacy

ForgeCheck is a read-only local inventory utility. It is not a vulnerability scanner, penetration-testing framework, or security audit tool.

- It does not probe remote hosts or send network scans.
- It does not modify firewall rules, services, packages, or system configuration.
- It does not request administrator privileges.
- Network output is limited to local interface addresses and local listening sockets.
- Exported reports may contain private LAN IP addresses and local listening-port details. Review them before sharing publicly.
- UI preferences are saved locally under the user's configuration directory. The config file is written with owner-only permissions and is not uploaded by ForgeCheck.

For bugs, open a GitHub issue without including passwords, access tokens, private keys, or unredacted sensitive system information.
