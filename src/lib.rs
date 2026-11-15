//! ForgeCheck: a fast, read-only Linux security and configuration auditor.
//!
//! ForgeCheck does not scan remote hosts, exploit vulnerabilities, change
//! system settings, or transmit collected information.

use std::fs;
use std::path::Path;
use std::process::{Command, Output};

pub const VERSION: &str = env!("CARGO_PKG_VERSION");

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Severity {
    Pass,
    Info,
    Low,
    Medium,
    High,
    Critical,
}

impl Severity {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Pass => "PASS",
            Self::Info => "INFO",
            Self::Low => "LOW",
            Self::Medium => "MEDIUM",
            Self::High => "HIGH",
            Self::Critical => "CRITICAL",
        }
    }
}

#[derive(Clone, Debug)]
pub struct Finding {
    pub id: &'static str,
    pub severity: Severity,
    pub title: String,
    pub details: String,
    pub recommendation: String,
}

#[derive(Clone, Debug)]
pub struct HostInfo {
    pub os: String,
    pub kernel: String,
    pub architecture: String,
}

#[derive(Clone, Debug)]
pub struct Summary {
    pub checks: usize,
    pub pass: usize,
    pub info: usize,
    pub low: usize,
    pub medium: usize,
    pub high: usize,
    pub critical: usize,
}

#[derive(Clone, Debug)]
pub struct AuditReport {
    pub tool: &'static str,
    pub version: &'static str,
    pub host: HostInfo,
    pub findings: Vec<Finding>,
}

impl AuditReport {
    pub fn summary(&self) -> Summary {
        let mut summary = Summary {
            checks: self.findings.len(),
            pass: 0,
            info: 0,
            low: 0,
            medium: 0,
            high: 0,
            critical: 0,
        };
        for finding in &self.findings {
            match finding.severity {
                Severity::Pass => summary.pass += 1,
                Severity::Info => summary.info += 1,
                Severity::Low => summary.low += 1,
                Severity::Medium => summary.medium += 1,
                Severity::High => summary.high += 1,
                Severity::Critical => summary.critical += 1,
            }
        }
        summary
    }

    pub fn to_json(&self) -> String {
        let summary = self.summary();
        let mut output = String::new();
        output.push_str("{\n  \"tool\": \"");
        output.push_str(self.tool);
        output.push_str("\",\n  \"version\": \"");
        output.push_str(self.version);
        output.push_str("\",\n  \"host\": {\n    \"os\": \"");
        output.push_str(&json_escape(&self.host.os));
        output.push_str("\",\n    \"kernel\": \"");
        output.push_str(&json_escape(&self.host.kernel));
        output.push_str("\",\n    \"architecture\": \"");
        output.push_str(&json_escape(&self.host.architecture));
        output.push_str("\"\n  },\n  \"summary\": {\n");
        output.push_str(&format!(
            "    \"checks\": {},\n    \"pass\": {},\n    \"info\": {},\n    \"low\": {},\n    \"medium\": {},\n    \"high\": {},\n    \"critical\": {}\n  }},\n  \"findings\": [\n",
            summary.checks,
            summary.pass,
            summary.info,
            summary.low,
            summary.medium,
            summary.high,
            summary.critical
        ));
        for (index, finding) in self.findings.iter().enumerate() {
            output.push_str("    {\n      \"id\": \"");
            output.push_str(finding.id);
            output.push_str("\",\n      \"severity\": \"");
            output.push_str(finding.severity.as_str());
            output.push_str("\",\n      \"title\": \"");
            output.push_str(&json_escape(&finding.title));
            output.push_str("\",\n      \"details\": \"");
            output.push_str(&json_escape(&finding.details));
            output.push_str("\",\n      \"recommendation\": \"");
            output.push_str(&json_escape(&finding.recommendation));
            output.push_str("\"\n    }");
            if index + 1 != self.findings.len() {
                output.push(',');
            }
            output.push('\n');
        }
        output.push_str("  ]\n}\n");
        output
    }

    pub fn to_markdown(&self) -> String {
        let summary = self.summary();
        let mut output = format!(
            "# ForgeCheck {} report\n\n- **Operating system:** {}\n- **Kernel:** {}\n- **Architecture:** {}\n\n## Summary\n\n| Checks | Pass | Info | Low | Medium | High | Critical |\n|---:|---:|---:|---:|---:|---:|---:|\n| {} | {} | {} | {} | {} | {} | {} |\n\n## Findings\n",
            self.version,
            markdown_escape(&self.host.os),
            markdown_escape(&self.host.kernel),
            markdown_escape(&self.host.architecture),
            summary.checks,
            summary.pass,
            summary.info,
            summary.low,
            summary.medium,
            summary.high,
            summary.critical
        );
        for finding in &self.findings {
            output.push_str(&format!(
                "\n### [{}] {} — {}\n\n{}\n\n**Recommended action:** {}\n",
                finding.severity.as_str(),
                finding.id,
                markdown_escape(&finding.title),
                markdown_escape(&finding.details),
                markdown_escape(&finding.recommendation)
            ));
        }
        output.push_str(
            "\n---\nGenerated locally by ForgeCheck. This report is a point-in-time configuration review, not a guarantee that the system is secure.\n",
        );
        output
    }
}

pub fn run_scan() -> AuditReport {
    let mut report = AuditReport {
        tool: "ForgeCheck",
        version: VERSION,
        host: collect_host_info(),
        findings: Vec::new(),
    };

    check_shadow_permissions(&mut report);
    check_passwd_permissions(&mut report);
    check_extra_uid_zero_accounts(&mut report);
    check_ssh_configuration(&mut report);
    check_ssh_listener(&mut report);
    check_firewall(&mut report);
    check_ipv4_redirects(&mut report);
    check_ipv4_forwarding(&mut report);
    check_world_writable_system_paths(&mut report);

    report
}

fn collect_host_info() -> HostInfo {
    let os_release = fs::read_to_string("/etc/os-release").unwrap_or_default();
    let os = parse_os_release(&os_release)
        .unwrap_or_else(|| "Linux (distribution not identified)".to_string());
    let kernel = fs::read_to_string("/proc/sys/kernel/osrelease")
        .map(|value| value.trim().to_string())
        .unwrap_or_else(|_| "Unavailable".to_string());
    HostInfo {
        os,
        kernel,
        architecture: std::env::consts::ARCH.to_string(),
    }
}

fn parse_os_release(input: &str) -> Option<String> {
    for line in input.lines() {
        let line = line.trim();
        if let Some(value) = line.strip_prefix("PRETTY_NAME=") {
            let value = value.trim();
            let unquoted = value
                .strip_prefix('"')
                .and_then(|part| part.strip_suffix('"'))
                .or_else(|| {
                    value
                        .strip_prefix('\'')
                        .and_then(|part| part.strip_suffix('\''))
                })
                .unwrap_or(value);
            if !unquoted.is_empty() {
                return Some(unquoted.to_string());
            }
        }
    }
    None
}

fn add(
    report: &mut AuditReport,
    id: &'static str,
    severity: Severity,
    title: impl Into<String>,
    details: impl Into<String>,
    recommendation: impl Into<String>,
) {
    report.findings.push(Finding {
        id,
        severity,
        title: title.into(),
        details: details.into(),
        recommendation: recommendation.into(),
    });
}

fn check_shadow_permissions(report: &mut AuditReport) {
    let path = Path::new("/etc/shadow");
    match fs::metadata(path) {
        Ok(metadata) => {
            #[cfg(unix)]
            {
                use std::os::unix::fs::MetadataExt;
                let mode = metadata.mode();
                let owner = metadata.uid();
                if owner != 0 || mode & 0o007 != 0 || mode & 0o020 != 0 {
                    add(
                        report,
                        "SHADOW_FILE_PERMISSIONS",
                        Severity::High,
                        "/etc/shadow permissions need review",
                        format!("Observed owner UID {} and permission mode {:o}.", owner, mode & 0o777),
                        "Ensure /etc/shadow is owned by root and is not readable or writable by other users. Review your distribution's expected shadow group permissions before changing it.",
                    );
                } else {
                    add(
                        report,
                        "SHADOW_FILE_PERMISSIONS",
                        Severity::Pass,
                        "/etc/shadow is not exposed to other users",
                        format!("Observed owner UID {} and permission mode {:o}.", owner, mode & 0o777),
                        "No action suggested. Keep the file permissions aligned with your distribution defaults.",
                    );
                }
            }
            #[cfg(not(unix))]
            add(report, "SHADOW_FILE_PERMISSIONS", Severity::Info, "Permission check unavailable", "Unix file metadata is unavailable on this platform.", "Run ForgeCheck on Linux.");
        }
        Err(_) => add(
            report,
            "SHADOW_FILE_PERMISSIONS",
            Severity::Info,
            "/etc/shadow could not be inspected",
            "The file is missing or its metadata is not accessible.",
            "Run ForgeCheck on a standard Linux installation. Elevated privileges are not required for most checks.",
        ),
    }
}

fn check_passwd_permissions(report: &mut AuditReport) {
    match fs::metadata("/etc/passwd") {
        Ok(metadata) => {
            #[cfg(unix)]
            {
                use std::os::unix::fs::MetadataExt;
                let mode = metadata.mode();
                if mode & 0o022 != 0 {
                    add(
                        report,
                        "PASSWD_FILE_PERMISSIONS",
                        Severity::High,
                        "/etc/passwd is group- or world-writable",
                        format!("Observed permission mode {:o}.", mode & 0o777),
                        "Review ownership and permissions. On many Linux distributions /etc/passwd is root-owned and not writable by group or other users.",
                    );
                } else {
                    add(
                        report,
                        "PASSWD_FILE_PERMISSIONS",
                        Severity::Pass,
                        "/etc/passwd is not group- or world-writable",
                        format!("Observed permission mode {:o}.", mode & 0o777),
                        "No action suggested.",
                    );
                }
            }
            #[cfg(not(unix))]
            add(
                report,
                "PASSWD_FILE_PERMISSIONS",
                Severity::Info,
                "Permission check unavailable",
                "Unix file metadata is unavailable.",
                "Run ForgeCheck on Linux.",
            );
        }
        Err(_) => add(
            report,
            "PASSWD_FILE_PERMISSIONS",
            Severity::Info,
            "/etc/passwd could not be inspected",
            "The file is missing or its metadata is not accessible.",
            "Check that this is a Linux system with a standard local account database.",
        ),
    }
}

fn check_extra_uid_zero_accounts(report: &mut AuditReport) {
    let content = match fs::read_to_string("/etc/passwd") {
        Ok(content) => content,
        Err(_) => {
            add(
                report,
                "UID_ZERO_ACCOUNTS",
                Severity::Info,
                "Local account list could not be inspected",
                "Unable to read /etc/passwd.",
                "Review local accounts manually.",
            );
            return;
        }
    };
    let extra = content
        .lines()
        .filter_map(|line| {
            let fields: Vec<&str> = line.split(':').collect();
            if fields.len() > 2 && fields[2] == "0" && fields[0] != "root" {
                Some(fields[0])
            } else {
                None
            }
        })
        .count();
    if extra == 0 {
        add(
            report,
            "UID_ZERO_ACCOUNTS",
            Severity::Pass,
            "No additional UID 0 accounts found",
            "Only the standard root account has UID 0 in /etc/passwd.",
            "No action suggested. Review privileged accounts periodically.",
        );
    } else {
        add(report, "UID_ZERO_ACCOUNTS", Severity::High, "Additional UID 0 account(s) found", format!("Found {} account(s) other than root with UID 0; account names are intentionally not included in this report.", extra), "Verify that every additional UID 0 account is explicitly required and authorized. Remove or correct unexpected entries using your distribution's account-management tools.");
    }
}

fn check_ssh_configuration(report: &mut AuditReport) {
    let mut paths = vec!["/etc/ssh/sshd_config".to_string()];
    let drop_in_dir = Path::new("/etc/ssh/sshd_config.d");
    if let Ok(entries) = fs::read_dir(drop_in_dir) {
        let mut extra: Vec<String> = entries
            .filter_map(Result::ok)
            .map(|entry| entry.path())
            .filter(|path| {
                path.extension()
                    .is_some_and(|extension| extension.to_string_lossy() == "conf")
            })
            .map(|path| path.to_string_lossy().into_owned())
            .collect();
        extra.sort();
        paths.extend(extra);
    }

    let mut found_config = false;
    let mut root_login_yes = false;
    let mut empty_passwords_yes = false;
    let mut password_auth_yes = false;
    for path in paths {
        if let Ok(contents) = fs::read_to_string(path) {
            found_config = true;
            for line in contents.lines() {
                if let Some((key, value)) = parse_sshd_directive(line) {
                    if key.eq_ignore_ascii_case("PermitRootLogin")
                        && value.eq_ignore_ascii_case("yes")
                    {
                        root_login_yes = true;
                    }
                    if key.eq_ignore_ascii_case("PermitEmptyPasswords")
                        && value.eq_ignore_ascii_case("yes")
                    {
                        empty_passwords_yes = true;
                    }
                    if key.eq_ignore_ascii_case("PasswordAuthentication")
                        && value.eq_ignore_ascii_case("yes")
                    {
                        password_auth_yes = true;
                    }
                }
            }
        }
    }

    if !found_config {
        add(report, "SSH_CONFIG", Severity::Info, "SSH server configuration not found", "No readable sshd_config or supported drop-in configuration was found.", "If an SSH server is installed, review its effective configuration with the tools provided by your distribution.");
        return;
    }
    if empty_passwords_yes {
        add(report, "SSH_EMPTY_PASSWORDS", Severity::Critical, "SSH permits empty passwords in configuration", "PermitEmptyPasswords is explicitly set to yes in a read configuration file.", "Change this setting to no and validate the effective SSH configuration before reloading the SSH service.");
    } else {
        add(
            report,
            "SSH_EMPTY_PASSWORDS",
            Severity::Pass,
            "No explicit SSH empty-password allowance found",
            "No active PermitEmptyPasswords yes directive was found in the inspected files.",
            "Keep empty-password authentication disabled.",
        );
    }
    if root_login_yes {
        add(report, "SSH_ROOT_LOGIN", Severity::High, "SSH root login is explicitly enabled", "PermitRootLogin is set to yes in an inspected configuration file.", "Prefer a named administrative account with least privilege. Review effective SSH configuration before changing this setting.");
    } else {
        add(
            report,
            "SSH_ROOT_LOGIN",
            Severity::Pass,
            "No explicit SSH root-login yes directive found",
            "No active PermitRootLogin yes directive was found in the inspected files.",
            "Keep direct root login disabled unless a documented operational need exists.",
        );
    }
    if password_auth_yes {
        add(report, "SSH_PASSWORD_AUTH", Severity::Medium, "SSH password authentication is enabled", "PasswordAuthentication is explicitly set to yes. This is not automatically a vulnerability, but it increases the importance of strong account controls and rate limiting.", "Consider key-based authentication where practical. Confirm that users have working alternative access before changing SSH settings.");
    } else {
        add(
            report,
            "SSH_PASSWORD_AUTH",
            Severity::Pass,
            "No explicit SSH password-authentication yes directive found",
            "No active PasswordAuthentication yes directive was found in inspected files.",
            "Keep SSH authentication aligned with your access requirements.",
        );
    }
}

fn parse_sshd_directive(line: &str) -> Option<(&str, &str)> {
    let active = line.split('#').next()?.trim();
    let mut parts = active.split_whitespace();
    Some((parts.next()?, parts.next()?))
}

fn check_ssh_listener(report: &mut AuditReport) {
    match command_output("ss", &["-lntH"]) {
        Some(output) if output.status.success() => {
            let text = String::from_utf8_lossy(&output.stdout);
            if text.lines().any(is_ssh_listener_line) {
                add(report, "SSH_LISTENER", Severity::Info, "A TCP listener on port 22 was detected", "A local listening socket uses TCP port 22. This check does not determine whether the port is reachable from the internet.", "Confirm that remote access is intentional and restricted by your host and network firewall.");
            } else {
                add(report, "SSH_LISTENER", Severity::Pass, "No TCP listener on port 22 detected", "The local socket listing did not show a listener on TCP port 22.", "No action suggested.");
            }
        }
        _ => add(report, "SSH_LISTENER", Severity::Info, "SSH listener check unavailable", "The ss utility is missing or could not read the local socket table.", "Install iproute2 if you want this optional local socket check. No network scan was performed."),
    }
}

fn is_ssh_listener_line(line: &str) -> bool {
    let fields: Vec<&str> = line.split_whitespace().collect();
    fields.len() >= 4
        && fields[0].eq_ignore_ascii_case("LISTEN")
        && fields[3].rsplit(':').next() == Some("22")
}

fn check_firewall(report: &mut AuditReport) {
    let mut ufw_inactive = false;
    if let Some(output) = command_output("ufw", &["status"]) {
        let text = String::from_utf8_lossy(&output.stdout).to_ascii_lowercase();
        if text.contains("status: active") {
            add(
                report,
                "FIREWALL_STATUS",
                Severity::Pass,
                "UFW reports an active firewall",
                "The ufw status command reports Status: active.",
                "Keep firewall rules reviewed and limited to required services.",
            );
            return;
        }
        ufw_inactive = text.contains("status: inactive");
    }
    if let Some(output) = command_output("firewall-cmd", &["--state"]) {
        if output.status.success() && String::from_utf8_lossy(&output.stdout).trim() == "running" {
            add(
                report,
                "FIREWALL_STATUS",
                Severity::Pass,
                "firewalld reports running",
                "The firewall-cmd state command reports running.",
                "Keep active firewall zones and services limited to what you need.",
            );
            return;
        }
    }
    if let Some(output) = command_output("nft", &["list", "ruleset"]) {
        let text = String::from_utf8_lossy(&output.stdout);
        if output.status.success()
            && text
                .lines()
                .any(|line| line.trim_start().starts_with("table "))
        {
            add(
                report,
                "FIREWALL_STATUS",
                Severity::Pass,
                "An nftables ruleset was detected",
                "The local nft command returned a ruleset containing at least one table.",
                "Review the ruleset to confirm it matches your intended access policy.",
            );
            return;
        }
    }
    if let Some(output) = command_output("iptables", &["-S"]) {
        let text = String::from_utf8_lossy(&output.stdout);
        if output.status.success() && text.lines().any(|line| line.starts_with("-A ")) {
            add(report, "FIREWALL_STATUS", Severity::Info, "iptables rules were detected", "The local iptables listing contains explicit rules. ForgeCheck does not evaluate the full rule logic.", "Review the rules with your system administrator or distribution documentation.");
            return;
        }
    }
    let details = if ufw_inactive {
        "UFW reports inactive, and ForgeCheck could not confirm an active firewalld, nftables, or iptables ruleset. Custom firewall setups may not be detected."
    } else {
        "ForgeCheck could not confirm an active UFW, firewalld, nftables, or iptables ruleset. Custom firewall setups may not be detected."
    };
    add(report, "FIREWALL_STATUS", Severity::Medium, "No active supported firewall could be confirmed", details, "Check your firewall using the tool that manages it on this distribution. This result is not proof that the host has no firewall.");
}

fn check_ipv4_redirects(report: &mut AuditReport) {
    let paths = [
        "/proc/sys/net/ipv4/conf/all/accept_redirects",
        "/proc/sys/net/ipv4/conf/default/accept_redirects",
        "/proc/sys/net/ipv4/conf/all/send_redirects",
        "/proc/sys/net/ipv4/conf/default/send_redirects",
    ];
    let mut enabled = Vec::new();
    let mut readable = 0;
    for path in paths {
        if let Ok(value) = fs::read_to_string(path) {
            readable += 1;
            if value.trim() == "1" {
                enabled.push(
                    path.rsplit('/')
                        .take(2)
                        .collect::<Vec<_>>()
                        .into_iter()
                        .rev()
                        .collect::<Vec<_>>()
                        .join("/"),
                );
            }
        }
    }
    if !enabled.is_empty() {
        add(report, "IPV4_REDIRECTS", Severity::Medium, "IPv4 redirect settings are enabled", format!("Enabled settings detected: {}.", enabled.join(", ")), "Review whether ICMP redirects are required in your network. Disable them only after checking routing requirements.");
    } else if readable > 0 {
        add(report, "IPV4_REDIRECTS", Severity::Pass, "No inspected IPv4 redirect setting is enabled", "The inspected all/default accept_redirects and send_redirects values are not set to 1.", "No action suggested.");
    } else {
        add(report, "IPV4_REDIRECTS", Severity::Info, "IPv4 redirect settings unavailable", "The relevant procfs settings could not be read.", "Review the kernel network settings manually if this check is important to your environment.");
    }
}

fn check_ipv4_forwarding(report: &mut AuditReport) {
    match fs::read_to_string("/proc/sys/net/ipv4/ip_forward") {
        Ok(value) if value.trim() == "1" => add(report, "IPV4_FORWARDING", Severity::Info, "IPv4 forwarding is enabled", "This host is configured to forward IPv4 packets. This may be intentional for routers, VPN gateways, containers, or labs.", "Confirm that forwarding is intentional and that firewall rules control which traffic may pass through the host."),
        Ok(_) => add(report, "IPV4_FORWARDING", Severity::Pass, "IPv4 forwarding is disabled", "The kernel IPv4 forwarding setting is not enabled.", "No action suggested unless this host is intended to route traffic."),
        Err(_) => add(report, "IPV4_FORWARDING", Severity::Info, "IPv4 forwarding setting unavailable", "The procfs setting could not be read.", "Review the setting manually if this host is intended to route traffic."),
    }
}

fn check_world_writable_system_paths(report: &mut AuditReport) {
    let paths = ["/etc", "/etc/ssh"];
    let mut writable = Vec::new();
    let mut checked = 0;
    for path in paths {
        if let Ok(metadata) = fs::metadata(path) {
            checked += 1;
            #[cfg(unix)]
            {
                use std::os::unix::fs::MetadataExt;
                if metadata.mode() & 0o002 != 0 {
                    writable.push(path);
                }
            }
        }
    }
    if !writable.is_empty() {
        add(report, "SYSTEM_DIRECTORY_PERMISSIONS", Severity::High, "A sensitive system directory is world-writable", format!("World-writable directories detected: {}.", writable.join(", ")), "Review directory ownership, ACLs, and permissions. Do not change permissions blindly because package managers and services may depend on distribution defaults.");
    } else if checked > 0 {
        add(
            report,
            "SYSTEM_DIRECTORY_PERMISSIONS",
            Severity::Pass,
            "Inspected system directories are not world-writable",
            "The /etc and /etc/ssh directories inspected by ForgeCheck are not world-writable.",
            "No action suggested.",
        );
    } else {
        add(
            report,
            "SYSTEM_DIRECTORY_PERMISSIONS",
            Severity::Info,
            "System directory permissions unavailable",
            "Could not inspect /etc or /etc/ssh metadata.",
            "Review sensitive system directory permissions manually.",
        );
    }
}

fn command_output(program: &str, args: &[&str]) -> Option<Output> {
    Command::new(program).args(args).output().ok()
}

fn json_escape(input: &str) -> String {
    let mut output = String::with_capacity(input.len());
    for character in input.chars() {
        match character {
            '"' => output.push_str("\\\""),
            '\\' => output.push_str("\\\\"),
            '\n' => output.push_str("\\n"),
            '\r' => output.push_str("\\r"),
            '\t' => output.push_str("\\t"),
            character if character.is_control() => {
                output.push_str(&format!("\\u{:04x}", character as u32))
            }
            character => output.push(character),
        }
    }
    output
}

fn markdown_escape(input: &str) -> String {
    input.replace('|', "\\|").replace('\n', " ")
}

pub fn check_ids() -> &'static [&'static str] {
    &[
        "SHADOW_FILE_PERMISSIONS",
        "PASSWD_FILE_PERMISSIONS",
        "UID_ZERO_ACCOUNTS",
        "SSH_EMPTY_PASSWORDS",
        "SSH_ROOT_LOGIN",
        "SSH_PASSWORD_AUTH",
        "SSH_LISTENER",
        "FIREWALL_STATUS",
        "IPV4_REDIRECTS",
        "IPV4_FORWARDING",
        "SYSTEM_DIRECTORY_PERMISSIONS",
    ]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_quoted_os_release_name() {
        assert_eq!(
            parse_os_release("NAME=Debian\nPRETTY_NAME=\"Debian GNU/Linux 13 (trixie)\"\n"),
            Some("Debian GNU/Linux 13 (trixie)".to_string())
        );
    }

    #[test]
    fn parses_single_quoted_os_release_name() {
        assert_eq!(
            parse_os_release("PRETTY_NAME='Example Linux'"),
            Some("Example Linux".to_string())
        );
    }

    #[test]
    fn ignores_os_release_without_pretty_name() {
        assert_eq!(parse_os_release("NAME=Linux"), None);
    }

    #[test]
    fn parses_active_sshd_directive() {
        assert_eq!(
            parse_sshd_directive("  PermitRootLogin yes # comment"),
            Some(("PermitRootLogin", "yes"))
        );
    }

    #[test]
    fn ignores_commented_sshd_directive() {
        assert_eq!(parse_sshd_directive("#PermitRootLogin yes"), None);
    }

    #[test]
    fn detects_ipv4_and_ipv6_style_port_22_listener() {
        assert!(is_ssh_listener_line("LISTEN 0 128 0.0.0.0:22 0.0.0.0:*"));
        assert!(is_ssh_listener_line("LISTEN 0 128 [::]:22 [::]:*"));
    }

    #[test]
    fn does_not_treat_port_2222_as_ssh_port_22() {
        assert!(!is_ssh_listener_line("LISTEN 0 128 0.0.0.0:2222 0.0.0.0:*"));
    }

    #[test]
    fn escapes_json_control_characters() {
        assert_eq!(
            json_escape("quote \" slash \\ newline\n"),
            "quote \\\" slash \\\\ newline\\n"
        );
    }

    #[test]
    fn summary_counts_each_severity() {
        let report = AuditReport {
            tool: "ForgeCheck",
            version: "2.0.0",
            host: HostInfo {
                os: "Test".into(),
                kernel: "1".into(),
                architecture: "x86_64".into(),
            },
            findings: vec![
                Finding {
                    id: "a",
                    severity: Severity::Pass,
                    title: "a".into(),
                    details: "".into(),
                    recommendation: "".into(),
                },
                Finding {
                    id: "b",
                    severity: Severity::High,
                    title: "b".into(),
                    details: "".into(),
                    recommendation: "".into(),
                },
                Finding {
                    id: "c",
                    severity: Severity::Info,
                    title: "c".into(),
                    details: "".into(),
                    recommendation: "".into(),
                },
            ],
        };
        let summary = report.summary();
        assert_eq!(summary.checks, 3);
        assert_eq!(summary.pass, 1);
        assert_eq!(summary.high, 1);
        assert_eq!(summary.info, 1);
    }

    #[test]
    fn json_output_contains_version_and_findings() {
        let report = AuditReport {
            tool: "ForgeCheck",
            version: "2.0.0",
            host: HostInfo {
                os: "Test OS".into(),
                kernel: "1.2".into(),
                architecture: "x86_64".into(),
            },
            findings: vec![],
        };
        let json = report.to_json();
        assert!(json.contains("\"version\": \"2.0.0\""));
        assert!(json.contains("\"findings\": ["));
    }

    #[test]
    fn markdown_output_has_summary_table() {
        let report = AuditReport {
            tool: "ForgeCheck",
            version: "2.0.0",
            host: HostInfo {
                os: "Test|OS".into(),
                kernel: "1".into(),
                architecture: "x86_64".into(),
            },
            findings: vec![],
        };
        let markdown = report.to_markdown();
        assert!(markdown.contains("## Summary"));
        assert!(markdown.contains("Test\\|OS"));
    }
}
