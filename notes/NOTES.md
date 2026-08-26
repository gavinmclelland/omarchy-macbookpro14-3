# Work notes — MacBookPro14,3 on Omarchy

Machine: **MacBookPro14,3** (15-inch 2017 Touch Bar), hostname `omabook-pro`.  
OS: Omarchy 4.0.1, kernel **7.1.9-arch1-2**.  
T1: **`05ac:8600` iBridge** (must not be recovery `05ac:1281`).  
Repo: this tree. Issues are the tracker. Do not install T2 packages (`tiny-dfr`, `linux-t2`).

Written 2026-08-25–26. This is what actually landed on the laptop, including failed experiments.

---

## Hardware map

| Piece | Linux view |
| --- | --- |
| T1 / iBridge | USB `1-3`, `05ac:8600`, config **1** (HID keyboard + Touch Bar + ALS + UVC webcam) |
| Wi-Fi | BCM43602 `brcmfmac`, iface `wlp3s0` |
| Bluetooth | UART BCM20703A2, `hci0` from ROM |
| GPU | AMD Polaris11 Radeon Pro 560 `amdgpu` `renderD128` drives `eDP-1` 2880×1800 @1.6 scale; Intel HD 630 `i915` `renderD129` usually runtime-suspended via `apple_gmux` |
| Audio | CS8409/CS42L83 on HDA PCH (`0x106b3900`), DKMS `snd_hda_macbookpro` / `snd_hda_codec_cs8409` |
| NVMe | Samsung `0000:02:00.0`, `d3cold_allowed=0` |
| Keyboard/trackpad | mainline `applespi`; kbd backlight `spi::kbd_backlight` |
| Display brightness | `gmux_backlight` |
| Sleep | `/sys/power/mem_sleep` is `s2idle [deep]` — current mode **deep**, never tested this boot |

Four T1 functions share the iBridge: Touch Bar, FaceTime webcam, Touch ID (no Linux driver), ALS.

No iBridge die temperature is exposed. Closest skin sensors (`Ts0P`/`Ts1P`) were ~30–32 °C while CPU ~78–81 °C and GPU edge ~64 °C.

---

## What works

### Wi-Fi 5 GHz (`wifi/`)

NVRAM in **`/usr/lib/firmware/updates/brcm/`** (not `/lib/firmware/brcm/`, which pacman owns). Live link at 5200 MHz / 40 MHz.

**Do not `rmmod brcmfmac` live** — a bad NVRAM wedged the chip; only a full power-off recovered it.

Apple MAC from macOS `en0` (NetworkInterfaces.plist) is `8c:85:90:1d:13:36`. That is written in the **live** NVRAM file. The running iface is still `00:90:4c:0d:f4:3e` until reboot. Git copy stays `macaddr=xx:xx:xx:xx:xx:xx`. See [#10](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/10).

### Audio — speakers and mic exist (`audio/`, [#14](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/14))

davidjo CS8409 DKMS. Analog Stereo Duplex. Internal mic unmuted, boost 20 dB. Mic level is low **by design** (same as macOS); EasyEffects if you need loud capture.

**Quality work (2026-08-26):**

1. ALSA `PCM` was **25% (−38 dB)** while PipeWire showed ~23%. Those are the **same fader** (ACP uses PCM). Raising PCM without understanding that fights WirePlumber. Use **only** the PipeWire/Touch Bar volume.
2. CS8409 is happiest at **44.1 kHz S32_LE**. PipeWire default 48 kHz was resampling. Drop-in: `audio/pipewire-cs8409.conf` → `~/.config/pipewire/pipewire.conf.d/99-cs8409.conf`.
3. Four speakers: left/right **tweeter** + left/right **woofer**. Driver node chain `0x02→0x24` (first two channels, tweeters), `0x03→0x25` (next two, woofers). Stereo 2ch **duplicates** full-range onto both DACs. That sounds **hollow** (tweeters and woofers fight in the midrange). Apple does the split in CoreAudio, not in the codec.
4. **Crossover experiment (reverted as default):** switched card to `analog-surround-40`, PipeWire filter `cs8409_speakers` (HP tweeters / LP woofers at 1.4–1.6 kHz, later woofer invert + 4 dB lowshelf at 180 Hz). Confirmed 4ch PCM: `0x02` stream ch0, `0x03` stream ch2. Sounded fuller but still no “depth”. **Spotify then failed** (`can't play current song`): WirePlumber `SiStandardLink` 2/2 links failed; Spotify never attached to PipeWire after the graph restart.
5. **Current default:** analog-stereo, sink ~40%, crossover configs **parked** in `~/.config/pipewire/disabled/` and `~/.config/wireplumber/disabled/`. Filter files remain in `audio/60-cs8409-crossover.conf` for a later Spotify-safe graph.

Linux will not match Apple’s DSP without a working 4ch filter that apps can play into.

User service: `~/.config/systemd/user/macbook-internal-mic.service` (PCM 100% when it is the hardware max, internal mic unmute). Do **not** force surround-40 from that unit.

### Touch Bar (`touchbar/`)

DKMS `appleibridge` from the F13-Kr1pt0n lineage, **late load** only:

- `REMAKE_INITRD=no`, dest `/updates/dkms`
- blacklist `apple_ibridge` `apple_ib_tb` `apple_ib_als` — **never** `modules-load.d`
- `touchbar.service` after `multi-user.target`, `insmod` (ignores blacklist)
- `tb_mode_param=keyboard` so `usb_set_configuration()` is not called (self-deadlock)
- Steal HID `0003:05AC:8600.0002` from `hid-sensor-hub` → `apple-ibridge-hid`

`fnmode=1`: Esc + **media keys** (brightness, kbd light, volume). **Hold keyboard Fn** (bottom-left, next to Control) for F1–F12. Esc stays.

Native path: `apple_ib_tb` watches `KEY_FN` on the SPI keyboard (`tbkbd`). That does **not** fire while keyd has `EVIOCGRAB` on `event4` — the input core then delivers events only to the grabber, so `last_fn_pressed` stays false and the strip never leaves special mode. Confirmed: `tbkbd` is attached, SPI `KEY_FN` is present, `event4` grab returns `-EBUSY`.

Workaround (`esc/touchbar-fn.service`): `keyd listen` emits `+fn`/`-fn` for the keyd `fn` layer. The watcher writes `fnmode=0` (F-keys) on hold and `fnmode=1` (media) on release. Keep the layer named `fn`. keyd `Fn+\`` Esc is unchanged. **User-confirmed:** hold Fn switches the strip to F1–F12. [#16](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/16) closed.

Idle: `idle_timeout=300` `dim_timeout=150` (lock / screensaver). Not user-confirmed yet. [#1](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/1).

Custom pixels / Siri orb: needs iBridge **USB config 2** + DRM (`xeeban` `appletbdrm`/`dfrd`). `tiny-dfr` is T2-only. Parked [#6](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/6).

### Escape without the strip (`esc/`)

keyd: `fn = layer(fn)`, `[fn] grave = esc`. Chord `fn+grave` (50 ms) still types backtick. That grab is also why Fn did not switch the Touch Bar until `touchbar-fn.service` ([#16](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/16) closed).

### Keyboard backlight ([#8](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/8) closed)

`/sys/class/leds/spi::kbd_backlight` max 255. Was at 0; `brightnessctl -d spi::kbd_backlight set 25` works as user. With `fnmode=1` the strip also has kbd-illum keys.

### ALS ([#3](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/3) closed)

`insmod apple-ib-als` failed until `modprobe industrialio_triggered_buffer` (`Unknown symbol iio_triggered_buffer_setup_ext`). Then IIO `iio:device0` name=`als`, `in_illuminance_input=3`. Userspace unused → [#7](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/7).

### Webcam

iBridge UVC `/dev/video0`, MJPEG 1280×720. First ffmpeg frame is black (AGC); after ~30 frames a real picture. PipeWire lists `iBridge (V4L2)`. **User-tested, works.** No extra driver. T1 firmware must be `8600`.

### Bluetooth ([#4](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/4) closed)

`hci0` up from ROM. 8 s scan found LE devices (including a Bose). Apple `BCM20703-MiniDriver-uart.hex` is **not** a Linux HCI `.hcd`. Do not drop a guessed `BCM.hcd`.

### Chromium GPU ([#2](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/2) closed)

Chromium 151 `LOG(FATAL)` `GPU process isn't usable` on Polaris11 `renderD128` (two SIGTRAPs during `gh auth login --web`). Not OOM, not Omarchy. Workaround: `--disable-gpu` in `~/.config/chromium-flags.conf`. Later process list showed `--use-gl=disabled`. Details: `notes/chromium-gpu.md`.

### Spotify CEF abort ([#15](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/15))

`spotify 1:1.2.96.518-1` PID 67730, SIGTRAP 2026-08-26 00:39:02 PDT. Not OOM. Not Omarchy. **Not** [#2](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/2).

CEF `libcef.so` **main/UI thread** `ImmediateCrash` (`int3; ud2`) after:

```
out_of_range was thrown in -fno-exceptions mode with message "string_view::substr"
```

`string_view::substr(pos)` with `pos > size()`. PipeWire thread was in `epoll_wait`. Timeline: `systemctl --user daemon-reload` bounced PipeWire at 00:38:32; abort 30 s later. Correlation, not a proven cause. Relaunch did not dump. `--disable-gpu` is **not** the fix unless a later dump shows the GPU path.

Distinct from [#14](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/14) “can’t play current song” (Spotify never attached after 4ch sink). This is a later process abort.

Sanitized: [`notes/spotify-crash.md`](spotify-crash.md).

### NVMe suspend ([#13](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/13) closed)

Omarchy unit had `0000\:02\:00.0`; systemd logged `Ignoring unknown escape sequences`. Replaced with unescaped path in `boot/nvme-d3cold.service`. `d3cold_allowed` is 0.

### USB-C after suspend (`boot/macbook-t1.conf`)

`pcie_ports=compat` on the Limine drop-in. Three xHCI: onboard active, one TB controller suspended, one active (dongle).

### Option-key EFI Boot ([#11](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/11))

`limine_x64.efi` copied to `/boot/EFI/BOOT/BOOTX64.EFI` with **no** `limine.conf` beside it. Confirm by holding Option. Needs a reboot to see the picker.

### Dual boot layout

```
nvme0n1p1  300M  vfat EFI          Apple ESP (T1 firmware) — do not format
nvme0n1p2  698G  apfs              macOS, mounted /mnt/macos
nvme0n1p3    2G  vfat OMARCHY_EFI  /boot
nvme0n1p4  231G  LUKS/btrfs        Omarchy
```

---

## Failed / parked experiments

| Experiment | Result |
| --- | --- |
| `fnmode=0` (Esc+F-keys always) | No brightness/volume/kbd on the strip. Switched to `fnmode=1`. |
| `apple_ib_tb` KEY_FN while keyd grabs SPI | `tbkbd` attached but starved. Fixed: `keyd listen` → `fnmode` 0/1. User-confirmed. |
| Guessed `BCM.hcd` | Do not. Can take UART BT offline. |
| Touch Bar modules at sysinit | Deadlock / hang `sysinit.target`; forced power-off. Late `insmod` only. |
| iBridge USB config 2 (display mode) | `usb_set_configuration` self-deadlock. Stay `tb_mode_param=keyboard`. |
| 4ch PipeWire crossover as **default sink** | Fuller sound, then **Spotify cannot play**. Parked. |
| Spotify CEF `string_view::substr` abort | SIGTRAP ~30 s after a PipeWire bounce. One dump; relaunch clean. [#15](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/15). |
| Extract Linux `.hcd` from Apple MiniDriver `.hex` | Wrong image (ARM MiniDriver, not HCI PatchRAM). |

---

## Open work (phase:work)

| Issue | Needs |
| --- | --- |
| [#1](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/1) TB dim | Leave idle ~150 s / 300 s and confirm |
| [#10](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/10) Wi-Fi Apple MAC | **Reboot** (NVRAM already written) |
| [#11](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/11) Option EFI Boot | **Reboot**, hold Option |
| [#12](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/12) suspend/resume | One `systemctl suspend` / lid: TB, ALS, USB-C, Wi-Fi, T1 still `8600` |
| [#14](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/14) speaker quality | Spotify-safe 4ch crossover / Apple layout EQ |
| [#15](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/15) Spotify CEF abort | Repro or close as one-off `substr` trap |

## Open better (parked)

[#5](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/5) voice/F9, [#6](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/6) custom TB UI, [#7](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/7) ALS-driven TB brightness.

---

## Safety rules paid for the hard way

- T1 firmware lives on **Apple’s ESP** (`nvme0n1p1`). A full-disk Linux install → `05ac:1281` and TB/webcam/ALS/Touch ID die.
- Touch Bar: `insmod` after multi-user, never initramfs / `modules-load.d`.
- Wi-Fi: NVRAM under `firmware/updates`; never live-reload `brcmfmac` after a bad file.
- Bluetooth: no invented `.hcd`.
- Audio: do not set a 4ch virtual sink as default until Spotify/Chromium attach to it.
- Chromium on this dual GPU: `--disable-gpu` if it `SIGTRAP`s.
- Spotify CEF abort (`string_view::substr`) is **not** the Chromium GPU fatal; do not apply `--disable-gpu` as the fix unless a later dump shows that path.
