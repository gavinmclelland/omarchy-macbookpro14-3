#!/bin/bash
# USB-C after suspend, NVMe d3cold, Apple Option-key EFI Boot.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)

install -Dm644 "$ROOT/macbook-t1.conf" /etc/limine-entry-tool.d/macbook-t1.conf
limine-update

install -Dm644 "$ROOT/nvme-d3cold.service" /etc/systemd/system/omarchy-nvme-suspend-fix.service
systemctl daemon-reload
systemctl enable --now omarchy-nvme-suspend-fix.service

# Apple's Option picker only lists EFI Boot if \EFI\BOOT\BOOTX64.EFI exists.
# Do not place limine.conf next to it — Limine would prefer that copy.
if [ -f /boot/EFI/limine/limine_x64.efi ]; then
  mkdir -p /boot/EFI/BOOT
  cp -f /boot/EFI/limine/limine_x64.efi /boot/EFI/BOOT/BOOTX64.EFI
  echo "BOOTX64.EFI installed for Option-key picker"
else
  echo "limine_x64.efi not found; skip BOOTX64" >&2
fi

echo "pcie_ports=compat needs a reboot if it was just added."
echo "NVMe d3cold_allowed=$(cat /sys/bus/pci/devices/0000:02:00.0/d3cold_allowed)"
