#!/usr/bin/env bash
set -euo pipefail
TARGET="${HOME}/.local/bin/forgecheck"
if [[ -e "${TARGET}" ]]; then
  rm -- "${TARGET}"
  echo "Removed ${TARGET}"
else
  echo "ForgeCheck is not installed at ${TARGET}"
fi
