# Omarchy on MacBookPro14,3 (T1)

Full daily-driver support for this 15-inch 2017 Touch Bar Mac. **Make it work,
then make it better.** Issues are the source of truth.

T1 must stay `05ac:8600`, never recovery `1281`. Do not install T2 packages
(`tiny-dfr`, `linux-t2`).

## Status

| | State | Where |
| --- | --- | --- |
| Wi-Fi 5 GHz | works | `wifi/` |
| Speakers + mic | works, quality [#14](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/14) | `audio/` — 4ch crossover **parked** (broke Spotify) |
| FaceTime webcam | works | iBridge UVC `/dev/video0` 1280×720 |
| Esc without Touch Bar | works | `esc/` |
| Touch Bar Esc + F1–F12 | works | `touchbar/` |
| USB-C after suspend | works | `boot/` `pcie_ports=compat` |
| NVMe suspend | works | `d3cold_allowed=0` on `0000:02:00.0` |
| Radeon Pro 560 panel | works | `amdgpu` `eDP-1` |
| TB dim with screen idle | [#1](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/1) | `phase:work` |
| Chromium GPU abort | mitigated \`--disable-gpu\` | [#2](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/2) closed |
| ALS / IIO lux | works | [#3](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/3) closed |
| Bluetooth discovery | works | [#4](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/4) closed |
| Keyboard backlight | works | [#8](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/8) closed |
| TB media keys vs F-keys | fnmode=1 (hold **keyboard Fn** for F1–F12) | [#9](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/9) closed |
| Wi-Fi Apple MAC | [#10](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/10) | `phase:work` |
| Option-key EFI Boot | [#11](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/11) | `phase:work` |
| Suspend/resume | [#12](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/12) | `phase:work` |
| NVMe suspend unit quoting | works | [#13](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/13) closed |
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

## Touch Bar keys (`fnmode=1`)

The strip shows **Esc + media keys** (brightness, kbd light, volume).

**Hold the physical Fn key** on the keyboard (bottom-left, next to Control) for
F1–F12. Release Fn to get media keys back. Esc stays on the left either way.

`Fn+\`` is still Escape via keyd (`esc/`). That does not replace keyboard Fn
for the strip: `apple_ib_tb` watches `KEY_FN` on the SPI keyboard (`tbkbd`).

## Still open

Work: [#1](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/1)
[#10](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/10)
[#11](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/11)
[#12](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/12)
[#14](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/14).

Detailed log: [`notes/NOTES.md`](notes/NOTES.md). Audio experiments: [`audio/README.md`](audio/README.md).

Better (parked): [#5](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/5)
[#6](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/6)
[#7](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/7).
