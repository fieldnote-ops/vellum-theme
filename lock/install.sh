#!/bin/bash
# Install the Vellum lock-screen visual over Omarchy's built-in lock service.
# The clone supplies Service.qml (PAM, session lock) untouched from Omarchy;
# only LockView.qml comes from this theme.
set -euo pipefail

root=$(cd "$(dirname "$0")/.." && pwd)
clone="$HOME/.config/omarchy/plugins/${USER}.lock"

if [[ ! -d $clone ]]; then
  omarchy plugin clone omarchy.lock
fi

cp "$root/lock/LockView.qml" "$clone/LockView.qml"
omarchy plugin validate "$clone"
omarchy plugin enable "${USER}.lock" >/dev/null 2>&1 || true
omarchy restart shell >/dev/null

echo "Animated Vellum lock installed."
echo "Preview: omarchy-shell lock preview"
echo "Close:   omarchy-shell lock hidePreview"
