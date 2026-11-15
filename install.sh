#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEST_DIR="${HOME}/.local/bin"
SOURCE_BIN=""

if [[ -x "${ROOT_DIR}/forgecheck" ]]; then
  SOURCE_BIN="${ROOT_DIR}/forgecheck"
elif [[ -x "${ROOT_DIR}/bin/forgecheck" ]]; then
  SOURCE_BIN="${ROOT_DIR}/bin/forgecheck"
elif [[ -f "${ROOT_DIR}/Cargo.toml" ]]; then
  if ! command -v cargo >/dev/null 2>&1; then
    echo "Cargo is required to build from source. Install Rust from https://rustup.rs/" >&2
    exit 1
  fi
  echo "Building ForgeCheck in release mode..."
  (cd "${ROOT_DIR}" && cargo build --locked --release)
  SOURCE_BIN="${ROOT_DIR}/target/release/forgecheck"
else
  echo "Could not find a ForgeCheck binary or Cargo.toml in ${ROOT_DIR}" >&2
  exit 1
fi

install -d "${DEST_DIR}"
install -m 0755 "${SOURCE_BIN}" "${DEST_DIR}/forgecheck"
echo "ForgeCheck installed to ${DEST_DIR}/forgecheck"
case ":${PATH}:" in
  *":${DEST_DIR}:"*) echo "Run: forgecheck" ;;
  *) echo "Add this to ~/.profile if forgecheck is not found:"; echo "  export PATH=\"\$HOME/.local/bin:\$PATH\"" ;;
esac
