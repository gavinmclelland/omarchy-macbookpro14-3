# AppleHDA layouts (Intel CS8409)

Source: this machine’s macOS `AppleHDA.kext/Contents/Resources/layoutN.xml.zlib`
on the **System** APFS volume (not the Data volume). **Do not commit the kext
or the zlib files.**

## MacBookPro14,3 (A1707) is layout 57

| | |
| --- | --- |
| Codec | CS8409 + CS42L83 (`0x10138409` / subsystem `0x106b3900`) |
| Amps | four **MAX98706** (tweeter/woofer × L/R), TDM device `34566` |
| Vendors | GTK `0x90000`, Merry `0xC0000` — **same** SoftwareDSP chain (both IDs → 0) |
| PathMapID | 37 |

Layouts **14/15** are TAS5764L. Layout **54** is SSM3515. Do not use those
biquads on this laptop.

```bash
python3 parse_layout.py raw --layout 57 -o layout57.json
```

Coefficients: [`layout57.json`](layout57.json).

Stereo processing, then `Dsp2To4Splitter`:

| # | Apple DSP | What it is |
| --- | --- | --- |
| 0 | Equalization32 | protection highpass 80 Hz Q=0.707 |
| 1 | MozartCompressor | dynamics |
| 2 | Loudness | contour |
| 3 | Equalization32 | narrow 2.5 kHz notch |
| 4 | MozartCompressorDualBand | split ~400 / 1250 Hz |
| 5 | Equalization32 | global PEQ (16 bands, L=R) |
| 6 | GainStage | ×1.1885 (~+1.5 dB) |
| 7 | 2To4Splitter | stereo → tweeters + woofers |
| 8 | Equalization32 | tweeter HP **1150 Hz** + HP **650 Hz** + PEQ |
| 9 | Equalization32 | woofer LP **1180 Hz** + LP **1500 Hz** + PEQ |
| 10 | Delay | 5 samples |
| 11 | BuzzKill | |
| 12–13 | ControlFreak | limiters |
| 14 | ThermalSpeakerProtection4ch | Apple thermal model |
| 15 | 4ChOutput | output trim |

Live graph (`../speaker-tuning/macbookpro14-3/filter-chain.conf`) maps
0/3/5/6/8/9/10 plus LSP `limiter_stereo` on the 2ch bus and a hard clamp as
chained `bq_*` nodes. Hosted by `cs8409-speaker-tuning.service` (not a
`pipewire.conf.d` drop-in). Invert **on**, woofer delay **5 samples**.
Tones: 1 kHz vs 500 Hz **+0.5 dB** on the host (was −0.7 dB on the daemon graph).
`param_eq` fan-out left RL/RR silent. Not
1/2/4/11–14 (undocumented).

```bash
python3 render_filter.py
python3 render_filter.py --no-delay
python3 measure_crossover.py   # records cs8409_speakers.playback
```

Do **not** write a new kernel driver. Do **not** use `speakersafetyd`
(MAX98706 has no V/ISENSE).

Filter types: 0 low-pass, 1 high-pass, 4 bell, 6 notch.
