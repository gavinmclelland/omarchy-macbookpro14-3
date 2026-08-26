# Omarchy on MacBookPro14,3 (T1)

Full daily-driver support for this 15-inch 2017 Touch Bar Mac. **Make it work,
then make it better.** Issues are the source of truth.

T1 must stay `05ac:8600`, never recovery `1281`. Do not install T2 packages
(`tiny-dfr`, `linux-t2`).

## Status

| | State | Where |
| --- | --- | --- |
| Wi-Fi 5 GHz | works | `wifi/` |
| Speakers + mic | works | `audio/` |
| Esc without Touch Bar | works | `esc/` |
| Touch Bar Esc + F1–F12 | works | `touchbar/` |
| USB-C after suspend | works | `boot/` `pcie_ports=compat` |
| NVMe suspend | works | `d3cold_allowed=0` on `0000:02:00.0` |
| Radeon Pro 560 panel | works | `amdgpu` `eDP-1` |
| TB dim with screen idle | [#1](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/1) | `phase:work` |
| Chromium GPU abort | [#2](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/2) | `phase:work` |
| ALS / IIO lux | [#3](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/3) | `phase:work` |
| Bluetooth ROM vs PatchRAM | [#4](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/4) | `phase:work` |
| Voice / default agent | [#5](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/5) | `phase:better` |
| Custom Touch Bar UI | [#6](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/6) | `phase:better` |
| ALS-driven TB brightness | [#7](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/7) | `phase:better` |

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

## Still open

Work: [#1](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/1)
[#2](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/2)
[#3](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/3)
[#4](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/4).

Better (parked): [#5](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/5)
[#6](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/6)
[#7](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/7).
