#!/bin/bash
# BCM43602 NVRAM into firmware/updates so pacman cannot clobber it.
# Reboot after this. Do not rmmod brcmfmac live — a bad NVRAM can wedge the chip.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
install -d /usr/lib/firmware/updates/brcm
install -m644 "$ROOT/brcmfmac43602-pcie.txt" \
  /usr/lib/firmware/updates/brcm/brcmfmac43602-pcie.txt
echo "Installed. Set macaddr= in that file to the real Apple MAC from macOS,"
echo "then reboot. Live reload is not safe on this chip."
