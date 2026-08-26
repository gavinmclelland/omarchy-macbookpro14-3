#!/bin/bash
# Fn + ` → Escape. Fn must be a layer, not a 50ms chord.
# Also install the Touch Bar Fn watcher: keyd grab hides KEY_FN from apple_ib_tb.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
pacman -S --noconfirm --needed keyd
install -Dm644 "$ROOT/apple-esc.conf" /etc/keyd/apple-esc.conf
keyd check /etc/keyd/apple-esc.conf
install -Dm755 "$ROOT/touchbar-fn-watch.sh" /usr/local/sbin/touchbar-fn-watch.sh
install -Dm644 "$ROOT/touchbar-fn.service" /etc/systemd/system/touchbar-fn.service
systemctl daemon-reload
systemctl enable --now keyd.service
systemctl restart keyd.service
systemctl enable --now touchbar-fn.service
systemctl restart touchbar-fn.service
echo "Hold Fn, tap \` (left of 1) for Esc. Hold Fn to switch the Touch Bar to F1–F12."
