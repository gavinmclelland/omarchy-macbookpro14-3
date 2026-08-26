#!/bin/bash
# Fn + ` → Escape. Fn must be a layer, not a 50ms chord.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
pacman -S --noconfirm --needed keyd
install -Dm644 "$ROOT/apple-esc.conf" /etc/keyd/apple-esc.conf
keyd check /etc/keyd/apple-esc.conf
systemctl enable --now keyd.service
systemctl restart keyd.service
echo "Hold Fn, tap \` (left of 1)."
