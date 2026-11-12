#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
APP_BIN="$BIN_DIR/forgecheck"
ICON_PATH="$ICON_DIR/forgecheck.svg"
DESKTOP_FILE="$APP_DIR/forgecheck.desktop"

mkdir -p "$BIN_DIR" "$APP_DIR" "$ICON_DIR"
install -m 755 "$ROOT_DIR/forgecheck.py" "$APP_BIN"
install -m 644 "$ROOT_DIR/assets/forgecheck.svg" "$ICON_PATH"

# Desktop Exec paths are quoted so home directories containing spaces remain valid.
if command -v konsole >/dev/null 2>&1; then
    TERMINAL="$(command -v konsole)"
    EXEC_LINE="$TERMINAL --fullscreen -e \"$APP_BIN\""
elif command -v x-terminal-emulator >/dev/null 2>&1; then
    TERMINAL="$(command -v x-terminal-emulator)"
    EXEC_LINE="$TERMINAL -e \"$APP_BIN\""
elif command -v xterm >/dev/null 2>&1; then
    TERMINAL="$(command -v xterm)"
    EXEC_LINE="$TERMINAL -e \"$APP_BIN\""
else
    EXEC_LINE="$APP_BIN"
fi

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=ForgeCheck Console
GenericName=Linux System Dashboard
Comment=Open the local read-only ForgeCheck system console
Exec=$EXEC_LINE
Icon=$ICON_PATH
Terminal=false
Categories=System;Utility;
StartupNotify=false
EOF
chmod 644 "$DESKTOP_FILE"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APP_DIR" >/dev/null 2>&1 || true
fi

printf '\nForgeCheck 1.0.0 installed.\n'
printf 'Command: %s\n' "$APP_BIN"
printf 'Launcher: ForgeCheck Console (KDE application menu)\n'
case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) printf '\nAdd this line to ~/.bashrc if the command is not found:\nexport PATH="$BIN_DIR:$PATH"\n' ;;
esac
