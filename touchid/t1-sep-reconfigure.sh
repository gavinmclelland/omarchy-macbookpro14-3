#!/bin/bash
# Privileged: briefly put iBridge in USB config 2 so KernelRelay iface 7 exists,
# run t1-touchid-verify --probe, then restore config 1 + touchbar.service.
# Does not load appleibridge at sysinit. Aborts if T1 is not 05ac:8600.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
DEV=/sys/bus/usb/devices/1-3
vid=$(cat "$DEV/idVendor")
pid=$(cat "$DEV/idProduct")
if [ "$vid" != "05ac" ] || [ "$pid" != "8600" ]; then
	echo "refusing: iBridge is $vid:$pid (need 05ac:8600)" >&2
	exit 1
fi

restore() {
	echo 1 >"$DEV/bConfigurationValue" 2>/dev/null || true
	systemctl start touchbar.service 2>/dev/null || true
	systemctl start touchbar-fn.service 2>/dev/null || true
	echo "restore: config=$(cat "$DEV/bConfigurationValue") pid=$(cat "$DEV/idProduct")"
}
trap restore EXIT

systemctl stop touchbar-fn.service 2>/dev/null || true
rmmod apple_ib_als 2>/dev/null || true
rmmod apple_ib_tb 2>/dev/null || true
rmmod apple_ibridge 2>/dev/null || true
# Drop kernel claims so bConfigurationValue can change.
for intf in "$DEV":*; do
	[ -e "$intf/driver" ] || continue
	drv=$(readlink -f "$intf/driver")
	echo "$(basename "$intf")" >"$drv/unbind" || true
done

timeout 8 bash -c 'echo 2 >"$1"' _ "$DEV/bConfigurationValue"
echo "config=$(cat "$DEV/bConfigurationValue") interfaces:"
ls -d "$DEV":* 2>/dev/null || true

PYTHONPATH="$ROOT/touchid" python3 "$ROOT/touchid/t1-touchid-verify" --probe
