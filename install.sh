#!/bin/bash
# MacBookPro14,3 platform overlay. Safe order. Never load appleibridge at sysinit.
#
#   sudo ./install.sh
#   sudo ./install.sh firmware|cs8409|keyd|ibridge|boot|pipewire
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
USER_NAME="${SUDO_USER:-$USER}"
USER_HOME=$(getent passwd "$USER_NAME" | cut -d: -f6)
KVER=$(uname -r)

step=${1:-all}

install_firmware() {
	echo "==> firmware/brcm (BCM43602 NVRAM)"
	install -d /usr/lib/firmware/updates/brcm
	install -m644 "$ROOT/firmware/brcm/brcmfmac43602-pcie.txt" \
		/usr/lib/firmware/updates/brcm/brcmfmac43602-pcie.txt
	echo "    Set macaddr= in that file to the Apple MAC from macOS, then reboot."
	echo "    Do not rmmod brcmfmac live."
}

install_cs8409() {
	echo "==> CS8409 DKMS (davidjo)"
	if grep -q '^snd_hda_codec_cs8409 ' /proc/modules; then
		echo "    already loaded — skip clone/build"
		return 0
	fi
	"$ROOT/scripts/install-cs8409-dkms.sh"
}

install_keyd() {
	echo "==> keyd (Fn layer: TB fnmode + Fn+\` Esc)"
	pacman -S --noconfirm --needed keyd
	rm -f /etc/keyd/apple-esc.conf
	install -Dm644 "$ROOT/keyd/apple-t1.conf" /etc/keyd/apple-t1.conf
	keyd check /etc/keyd/apple-t1.conf
	install -Dm755 "$ROOT/systemd/touchbar-fn-watch.sh" /usr/local/sbin/touchbar-fn-watch.sh
	install -Dm644 "$ROOT/systemd/touchbar-fn.service" /etc/systemd/system/touchbar-fn.service
	systemctl daemon-reload
	systemctl enable --now keyd.service
	systemctl restart keyd.service
	# WantedBy=touchbar.service (not multi-user): that After= cycle skipped
	# the unit on boot. Enable here; start after ibridge if the bar is up.
	systemctl disable touchbar-fn.service 2>/dev/null || true
	systemctl enable touchbar-fn.service
	systemctl try-restart touchbar-fn.service 2>/dev/null || true
}

install_ibridge() {
	echo "==> appleibridge DKMS (late load only)"
	if grep -Eq 'usb_(driver_)?set_configuration[[:space:]]*\(udev' \
		"$ROOT/drivers/appleibridge/apple-ibridge.c"; then
		echo "refusing unsafe appleibridge source: live USB configuration switch present" >&2
		exit 1
	fi
	pacman -S --noconfirm --needed dkms linux-headers
	rm -rf /usr/src/appleibridge-0.1
	mkdir -p /usr/src/appleibridge-0.1
	cp "$ROOT"/drivers/appleibridge/{apple-ib-als.c,apple-ib-tb.c,apple-ibridge.c,apple-ibridge.h,Makefile,dkms.conf} \
		/usr/src/appleibridge-0.1/
	if dkms status appleibridge/0.1 2>/dev/null | grep -q installed; then
		dkms remove -m appleibridge -v 0.1 --all || true
	fi
	dkms add -m appleibridge -v 0.1
	dkms build -m appleibridge -v 0.1 -k "$KVER"
	dkms install -m appleibridge -v 0.1 -k "$KVER"

	install -m644 "$ROOT/modprobe.d/apple-ibridge.conf" /etc/modprobe.d/apple-ibridge.conf
	install -Dm755 "$ROOT/systemd/touchbar-enable.sh" /usr/local/sbin/touchbar-enable.sh
	install -Dm644 "$ROOT/systemd/touchbar.service" /etc/systemd/system/touchbar.service
	systemctl daemon-reload
	systemctl enable touchbar.service
	systemctl start touchbar.service
	# Fn watcher needs the TB sysfs; it is WantedBy=touchbar.service so a
	# later boot starts it after this oneshot. Start it now too.
	systemctl enable --now touchbar-fn.service
	systemctl restart touchbar-fn.service
}

install_boot() {
	echo "==> boot (pcie_ports=compat, NVMe d3cold, BOOTX64)"
	install -Dm644 "$ROOT/boot/macbook-t1.conf" /etc/limine-entry-tool.d/macbook-t1.conf
	limine-update
	install -Dm644 "$ROOT/systemd/nvme-d3cold.service" \
		/etc/systemd/system/omarchy-nvme-suspend-fix.service
	systemctl daemon-reload
	systemctl enable --now omarchy-nvme-suspend-fix.service
	if [ -f /boot/EFI/limine/limine_x64.efi ]; then
		mkdir -p /boot/EFI/BOOT
		cp -f /boot/EFI/limine/limine_x64.efi /boot/EFI/BOOT/BOOTX64.EFI
		echo "    BOOTX64.EFI installed for Option-key picker"
	else
		echo "    limine_x64.efi not found; skip BOOTX64" >&2
	fi
	echo "    pcie_ports=compat needs a reboot if it was just added."
}

install_pipewire() {
	echo "==> PipeWire CS8409 drop-ins → $USER_HOME"
	install -Dm644 "$ROOT/pipewire/cs8409-mixer.service" \
		"$USER_HOME/.config/systemd/user/macbook-internal-mic.service"
	install -Dm755 "$ROOT/pipewire/cs8409-dsp-unity-lock.sh" \
		"$USER_HOME/.local/lib/omarchy-macbookpro14-3/cs8409-dsp-unity-lock.sh"
	install -Dm644 "$ROOT/pipewire/cs8409-dsp-unity.service" \
		"$USER_HOME/.config/systemd/user/cs8409-dsp-unity.service"
	install -Dm644 "$ROOT/pipewire/pipewire-cs8409.conf" \
		"$USER_HOME/.config/pipewire/pipewire.conf.d/99-cs8409.conf"
	install -Dm644 "$ROOT/pipewire/60-cs8409-crossover.conf" \
		"$USER_HOME/.config/pipewire/pipewire.conf.d/60-cs8409-crossover.conf"
	install -d "$USER_HOME/.config/wireplumber/wireplumber.conf.d"
	install -Dm644 "$ROOT/pipewire/51-cs8409.conf" \
		"$USER_HOME/.config/wireplumber/wireplumber.conf.d/51-cs8409.conf"
	chown -R "$USER_NAME:$USER_NAME" \
		"$USER_HOME/.config/systemd/user/macbook-internal-mic.service" \
		"$USER_HOME/.config/systemd/user/cs8409-dsp-unity.service" \
		"$USER_HOME/.local/lib/omarchy-macbookpro14-3" \
		"$USER_HOME/.config/pipewire" \
		"$USER_HOME/.config/wireplumber/wireplumber.conf.d/51-cs8409.conf"
	echo "    Then as $USER_NAME: systemctl --user enable --now macbook-internal-mic.service cs8409-dsp-unity.service"
	echo "    systemctl --user restart pipewire wireplumber"
	echo "    wpctl set-default the sink named cs8409_speakers"
}

case "$step" in
all)
	install_firmware
	install_cs8409
	install_keyd
	install_ibridge
	install_boot
	install_pipewire
	;;
firmware) install_firmware ;;
cs8409) install_cs8409 ;;
keyd) install_keyd ;;
ibridge) install_ibridge ;;
boot) install_boot ;;
pipewire) install_pipewire ;;
*)
	echo "usage: $0 [all|firmware|cs8409|keyd|ibridge|boot|pipewire]" >&2
	exit 2
	;;
esac
