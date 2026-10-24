#!/bin/bash
# Restore Omarchy's built-in lock screen and remove the Vellum visual clone.
set -euo pipefail

clone="$HOME/.config/omarchy/plugins/${USER}.lock"

omarchy plugin enable omarchy.lock >/dev/null 2>&1 || true
omarchy plugin disable "${USER}.lock" >/dev/null 2>&1 || true
rm -rf "$clone"
omarchy restart shell >/dev/null

echo "Built-in Omarchy lock restored."
