# ForgeCheck Roadmap

## 2.0.0 GLOBAL

- Rust CLI rewrite
- Local, read-only checks
- Text, JSON, and Markdown reports
- Clear severity levels and plain-language recommendations
- English and Russian documentation

## 2.1.0 — Reliability

- Expand distro-aware parsing with fixtures from supported distributions
- Improve effective SSH configuration analysis without executing service changes
- Add structured check metadata and more parser tests
- Improve report filtering and stable JSON schema documentation

## 2.2.0 — Baselines

- Optional user-defined local policy profiles
- Compare current settings with a selected baseline
- Export machine-readable baseline differences

## 3.0.0 — Extensible checks

- Documented check interface
- Signed, reviewable rule packs
- Optional offline configuration-file audits

All future features should remain defensive, transparent, opt-in, and read-only by default. No exploit automation, credential collection, stealth, or unauthorized remote scanning is planned.
