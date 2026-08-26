#!/bin/bash
# USB-C xHCI fails to reset after suspend without pcie_ports=compat.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
install -Dm644 "$ROOT/macbook-t1.conf" /etc/limine-entry-tool.d/macbook-t1.conf
limine-update
echo "Installed. Reboot for the kernel cmdline to apply."
