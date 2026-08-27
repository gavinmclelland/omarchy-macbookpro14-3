# Omarchy on MacBookPro14,3 (T1)

Platform overlay for this 15-inch 2017 Touch Bar Mac. **Make it work,
then make it better.** Issues are the source of truth.

T1 must stay `05ac:8600`, never recovery `1281`. Do not install T2 packages
(`tiny-dfr`, `linux-t2`).

This tree is a **machine overlay**: files classified by Linux layer, for one
DMI product. Esc is the left Touch Bar key, not a separate device.

## Chip map

| Chip / bus | Devices | Layer |
| --- | --- | --- |
| T1 iBridge `05ac:8600` | TB Esc/media/F-keys, UVC cam, ALS, Touch ID (no driver) | `drivers/appleibridge/` `modprobe.d/` `systemd/touchbar*` `keyd/` |
| SPI APP000D | keys, pad, kbd light | mainline `applespi` + `keyd/` |
| PCI BCM43602 | Wi-Fi | `firmware/brcm/` |
| UART BCM20703 | BT | kernel ROM — no `.hcd` |
| PCI CS8409 | 4 speakers + mics | `scripts/install-cs8409-dkms.sh` `pipewire/` |
| Apple NVMe + xHCI | disk, USB-C | `systemd/nvme-d3cold.service` `boot/` |
| gmux + amdgpu | panel | mainline |

## Status

| | State | Where |
| --- | --- | --- |
| Wi-Fi 5 GHz | works | `firmware/brcm/` |
| Speakers + mic | works; layout 57 PEQ live | `pipewire/` [#14](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/14) — davidjo + userspace DSP, not a new kernel driver |
| Spotify CEF abort | [#15](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/15) | `string_view::substr` SIGTRAP — app, not CS8409 |
| FaceTime webcam | works | iBridge UVC `/dev/video0` 1280×720 |
| Touch Bar Esc + media + F1–F12 | works | `drivers/` + `keyd/` + `systemd/touchbar*` |
| USB-C after suspend | works | `boot/` `pcie_ports=compat` |
| NVMe suspend | works | `d3cold_allowed=0` on `0000:02:00.0` |
| Radeon Pro 560 panel | works (256 MiB visible BAR) | `amdgpu` `eDP-1` — Intel cannot drive the LCD |
| TB dim with screen idle | [#1](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/1) | `phase:work` |
| Chromium / CEF GPU abort | Chromium mitigated; Spotify still hits it | [#2](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/2) **reopened** |
| ALS / IIO lux | works | [#3](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/3) closed |
| Bluetooth discovery | works | [#4](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/4) closed |
| Keyboard backlight | works | [#8](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/8) closed |
| TB media keys vs F-keys | works (hold **keyboard Fn** for F1–F12) | [#16](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/16) closed |
| Wi-Fi Apple MAC | [#10](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/10) | reboot to confirm |
| Option-key EFI Boot | [#11](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/11) | reboot, hold Option |
| Suspend/resume | [#12](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/12) | `phase:work` |
| NVMe suspend unit quoting | works | [#13](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/13) closed |
| Voice / default agent | [#5](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/5) | `phase:better` |
| Custom Touch Bar UI | [#6](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/6) | `phase:better` |
| ALS-driven TB brightness | [#7](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/7) | `phase:better` |

## Install

```bash
sudo ./install.sh
```

Pieces: `firmware` `cs8409` `keyd` `ibridge` `boot` `pipewire`. CS8409 DKMS and
`pcie_ports=compat` need a reboot after first install. Set `macaddr=` in the
live NVRAM file before that reboot.

Touch Bar modules are blacklisted and loaded after `multi-user.target` on
purpose. Loading them at sysinit can hang the box with no login screen.

## Speakers

Apps see stereo sink `cs8409_speakers`. Hardware is 4ch `analog-surround-40`
(tweeters `0x02` ch0, woofers `0x03` ch2). Live graph is AppleHDA **layout 57**
biquads (HPF 80 Hz, 16-band PEQ, tweeter HP 1150+650 Hz, woofer LP 1180+1500 Hz,
clamp). Woofers inverted + 5-sample delay (tones: 1 kHz vs 500 Hz **−0.7 dB**).
Raw 4ch node is hidden from the session default. Omarchy volume keys
(Touch Bar) resolve through the DSP sink to that physical node — do **not**
lock it at 100%. DSP sink stays at full scale (`cs8409-dsp-unity.service`).

Keep **davidjo** for amp/TDM. Do not write a new kernel driver — macOS quality
is CoreAudio, which this filter clones from `pipewire/applehda/layout57.json`.
Not a bit-identical clone: Mozart / BuzzKill / ControlFreak / thermal stay
out (undocumented). Do not commit `AppleHDA.kext`. Do not use `speakersafetyd`
(MAX98706, no V/ISENSE). Parked 800 Hz LR4: `pipewire/60-cs8409-lr4.conf`.
Details: [`pipewire/README.md`](pipewire/README.md).

## Touch Bar

The strip shows **Esc + media keys** (brightness, kbd light, volume). Esc is
the left slot — this keyboard has no dedicated Esc key.

**Hold the physical Fn key** (bottom-left, next to Control) for F1–F12.
Release for media keys. Esc stays.

`Fn+\`` is a keyd backup Esc (`keyd/apple-t1.conf`). keyd **grabs** the SPI
keyboard, so `apple_ib_tb` never sees `KEY_FN`. `systemd/touchbar-fn.service`
watches the keyd `fn` layer and writes `fnmode` 0/1. Keep that layer named
`fn`.

## Still open

Work: [#1](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/1)
[#2](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/2)
[#10](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/10)
[#11](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/11)
[#12](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/12)
[#14](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/14)
[#15](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/15).

Detailed log: [`notes/NOTES.md`](notes/NOTES.md). Audio experiments:
[`pipewire/README.md`](pipewire/README.md).

Better (parked): [#5](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/5)
[#6](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/6)
[#7](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/7).
