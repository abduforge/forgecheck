# Contributing

Thanks for helping improve ForgeCheck.

## Before opening an issue

- Use a current ForgeCheck version.
- Include your Linux distribution and ForgeCheck version.
- Remove hostnames, usernames, IP addresses, and other private data from logs.
- Explain what you expected and what happened.

## Development

Requirements: Rust 1.85+.

```bash
cargo fmt --all
cargo fmt --all -- --check
cargo test --all-targets --locked
cargo clippy --all-targets --locked -- -D warnings
cargo build --release --locked
```

## Pull requests

- Keep checks read-only by default.
- Explain false-positive and distribution-specific behavior.
- Add parser fixtures or tests for new checks.
- Do not add remote scanning, exploit execution, credential collection, or automatic configuration changes.
- Avoid unnecessary dependencies; document any new dependency and its purpose.
