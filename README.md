# Omarchy on MacBookPro14,3 (T1)

Working tree of the fixes that actually landed on this 15-inch 2017 Touch Bar
Mac (Omarchy 4.0.1, kernel 7.1.9). T1 must stay `05ac:8600`, never recovery
`1281`. Do not install T2 packages (`tiny-dfr`, `linux-t2`).

## Status

| | State | Fix |
| --- | --- | --- |
| Wi-Fi 5 GHz | works | `wifi/` NVRAM in `/usr/lib/firmware/updates/brcm/` |
| Speakers + mic | works | `audio/` davidjo CS8409 DKMS (mic ships muted) |
| Esc without Touch Bar | works | `esc/` keyd: Fn as **layer**, `` ` `` → Esc |
| Touch Bar Esc + F1–F12 | works | `touchbar/` DKMS + late `insmod`, steal HID `.0002` |
| USB-C after suspend | works | `boot/` `pcie_ports=compat` |
| NVMe suspend | works | Omarchy stock `d3cold_allowed=0` |
| Radeon Pro 560 panel | works | `amdgpu` on `eDP-1`; Intel runtime-suspended |
| Bluetooth | ROM only | do **not** drop a guessed `BCM.hcd` |
| ALS / TB dim with screen | not done | `idle_timeout=-1`; `apple_ib_als` not loaded |
| Siri / custom TB UI | can't | T1 driver has canned layouts only |
| Chromium GPU abort | open | `notes/chromium-gpu.md` |

## Install (each needs sudo)

```bash
sudo ./wifi/install.sh       # then set macaddr, reboot
sudo ./audio/install.sh      # reboot
sudo ./esc/install.sh
sudo ./touchbar/install.sh   # late load; never modules-load.d
sudo ./boot/install.sh       # reboot
```

Touch Bar modules are blacklisted and loaded after `multi-user.target` on
purpose. Loading them at sysinit can hang the box with no login screen.

## Still to find

- Hook Touch Bar dim/off to screen idle (or load ALS — it will not do that
  by itself).
- Why Chromium's GPU process dies on Polaris11 (`renderD128`) with i915 present.
- A real HCI PatchRAM for BCM20703A2 UART BT, if ROM is not enough.
- Voice: F9 is already Voxtype PTT; no Siri glyph on this driver.
