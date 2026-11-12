#!/usr/bin/env bash
set -euo pipefail
rm -f "$HOME/.local/bin/forgecheck"
rm -f "$HOME/.local/share/applications/forgecheck.desktop"
rm -f "$HOME/.local/share/icons/hicolor/scalable/apps/forgecheck.svg"
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true
fi
printf 'ForgeCheck command, icon, and launcher removed.\n'
printf 'Saved reports in ~/ForgeCheck-Reports were left untouched.\n'
