use forgecheck::{check_ids, run_scan, AuditReport, Severity, VERSION};
use std::env;
use std::fs;
use std::io::{self, IsTerminal};
use std::path::Path;
use std::process::ExitCode;

#[derive(Clone, Copy, Eq, PartialEq)]
enum OutputFormat {
    Text,
    Json,
    Markdown,
}

struct Options {
    format: OutputFormat,
    output: Option<String>,
    no_color: bool,
}

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("ForgeCheck: {message}");
            ExitCode::from(2)
        }
    }
}

fn run() -> Result<(), String> {
    let mut args: Vec<String> = env::args().skip(1).collect();
    if args.is_empty() {
        args.push("scan".to_string());
    }

    match args[0].as_str() {
        "--version" | "-V" | "version" => {
            println!("ForgeCheck {VERSION}");
            return Ok(());
        }
        "--help" | "-h" | "help" => {
            print_help();
            return Ok(());
        }
        "doctor" => {
            run_doctor();
            return Ok(());
        }
        "checks" | "list-checks" => {
            print_checks();
            return Ok(());
        }
        "scan" => {
            args.remove(0);
        }
        first if first.starts_with('-') => {}
        other => {
            return Err(format!(
                "unknown command '{other}'. Run 'forgecheck --help'."
            ))
        }
    }

    let options = parse_options(&args)?;
    let report = run_scan();
    let use_color = options.output.is_none() && !options.no_color && io::stdout().is_terminal();
    let rendered = match options.format {
        OutputFormat::Text => render_text(&report, use_color),
        OutputFormat::Json => report.to_json(),
        OutputFormat::Markdown => report.to_markdown(),
    };

    if let Some(path) = options.output {
        fs::write(&path, rendered)
            .map_err(|error| format!("cannot write report to '{path}': {error}"))?;
        println!("Report saved to {}", Path::new(&path).display());
    } else {
        print!("{rendered}");
    }
    Ok(())
}

fn parse_options(args: &[String]) -> Result<Options, String> {
    let mut options = Options {
        format: OutputFormat::Text,
        output: None,
        no_color: false,
    };
    let mut index = 0;
    while index < args.len() {
        match args[index].as_str() {
            "--json" => options.format = OutputFormat::Json,
            "--markdown" => options.format = OutputFormat::Markdown,
            "--no-color" => options.no_color = true,
            "--format" => {
                index += 1;
                let value = args
                    .get(index)
                    .ok_or("--format requires text, json, or markdown")?;
                options.format = match value.as_str() {
                    "text" => OutputFormat::Text,
                    "json" => OutputFormat::Json,
                    "markdown" | "md" => OutputFormat::Markdown,
                    _ => {
                        return Err(format!(
                            "unsupported format '{value}'. Use text, json, or markdown."
                        ))
                    }
                };
            }
            "--output" | "-o" => {
                index += 1;
                let value = args.get(index).ok_or("--output requires a file path")?;
                options.output = Some(value.clone());
            }
            "--help" | "-h" => {
                print_help();
                std::process::exit(0);
            }
            other => {
                return Err(format!(
                    "unknown option '{other}'. Run 'forgecheck --help'."
                ))
            }
        }
        index += 1;
    }
    Ok(options)
}

fn render_text(report: &AuditReport, color: bool) -> String {
    let summary = report.summary();
    let mut output = String::new();
    output.push_str("  ______                      ____ _               _\n");
    output.push_str(" |  ____|                    / ___| |__   ___  ___| | __\n");
    output.push_str(" | |__ ___  _ __ __ _  ___  | |   | '_ \\ / _ \\/ __| |/ /\n");
    output.push_str(" |  __/ _ \\| '__/ _` |/ _ \\ | |___| | | |  __/ (__|   <\n");
    output.push_str(" |_| | (_) | | | (_| |  __/  \\____|_| |_|\\___|\\___|_|\\_\\\n\n");
    output.push_str(&format!(" ForgeCheck {VERSION} GLOBAL\n"));
    output.push_str(" Local Linux security overview · read-only · no network scanning\n\n");
    output.push_str(&format!(
        " OS: {}\n Kernel: {}\n Architecture: {}\n\n",
        report.host.os, report.host.kernel, report.host.architecture
    ));
    output.push_str(&format!(
        " Summary: {} checks | {} pass | {} info | {} low | {} medium | {} high | {} critical\n\n",
        summary.checks,
        summary.pass,
        summary.info,
        summary.low,
        summary.medium,
        summary.high,
        summary.critical
    ));

    for finding in &report.findings {
        let label = finding.severity.as_str();
        let decorated = if color {
            let code = match finding.severity {
                Severity::Pass => "32",
                Severity::Info => "36",
                Severity::Low => "34",
                Severity::Medium => "33",
                Severity::High => "31",
                Severity::Critical => "1;31",
            };
            format!("\x1b[{code}m[{label}]\x1b[0m")
        } else {
            format!("[{label}]")
        };
        output.push_str(&format!("{decorated} {} — {}\n", finding.id, finding.title));
        output.push_str(&format!("  {}\n", finding.details));
        output.push_str(&format!("  Recommendation: {}\n\n", finding.recommendation));
    }
    output.push_str("Note: findings are configuration signals, not proof of compromise or a guarantee of security. Review recommendations before changing your system.\n");
    output
}

fn print_checks() {
    println!("ForgeCheck {VERSION} — built-in local checks\n");
    for id in check_ids() {
        println!("  {id}");
    }
    println!("\nAll checks are local and read-only. No remote hosts are scanned.");
}

fn run_doctor() {
    println!("ForgeCheck {VERSION} — environment doctor\n");
    check_path("/proc", "Linux procfs", true);
    check_path("/etc/os-release", "Distribution information", false);
    check_program("ss", "Optional socket inspection (iproute2)");
    check_program("ufw", "Optional firewall status (UFW)");
    check_program("firewall-cmd", "Optional firewall status (firewalld)");
    check_program("nft", "Optional firewall status (nftables)");
    check_program("iptables", "Optional firewall status (iptables)");
    println!("\nForgeCheck does not need root privileges for its standard scan. Some checks may be unavailable to an unprivileged user.");
}

fn check_path(path: &str, label: &str, required: bool) {
    let exists = Path::new(path).exists();
    let status = if exists {
        "OK"
    } else if required {
        "MISSING"
    } else {
        "OPTIONAL"
    };
    println!("  [{status}] {label}: {path}");
}

fn check_program(program: &str, label: &str) {
    let found = env::var_os("PATH")
        .map(|paths| env::split_paths(&paths).any(|directory| directory.join(program).is_file()))
        .unwrap_or(false);
    println!(
        "  [{}] {label}: {program}",
        if found { "FOUND" } else { "OPTIONAL" }
    );
}

fn print_help() {
    println!(
        "ForgeCheck {VERSION} — fast, read-only Linux security checks\n\n\
USAGE:\n  forgecheck [COMMAND] [OPTIONS]\n\n\
COMMANDS:\n  scan              Run the local security review (default)\n  checks            List all built-in checks\n  doctor            Check the local environment and optional tools\n  help              Show this help\n  version           Show version\n\n\
OPTIONS (scan):\n  --format FORMAT   text, json, or markdown\n  --json            Shortcut for --format json\n  --markdown        Shortcut for --format markdown\n  -o, --output FILE Save the report to a file\n  --no-color        Disable terminal colors\n  -h, --help        Show this help\n\n\
EXAMPLES:\n  forgecheck\n  forgecheck scan --json\n  forgecheck scan --format markdown --output audit.md\n  forgecheck checks\n  forgecheck doctor\n\n\
SAFETY:\n  ForgeCheck reads local system configuration and runs limited, read-only\n  status commands. It does not exploit, modify, or scan remote systems."
    );
}
