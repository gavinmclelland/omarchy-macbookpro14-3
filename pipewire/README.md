# CS8409 on MacBookPro14,3

Speakers work. They do not sound like macOS. Mic is quiet (same as macOS).

## Current (safe) setup

- Profile: `output:analog-stereo+input:analog-stereo`
- PipeWire clock 44100 (`pipewire/pipewire-cs8409.conf`)
- Volume: PipeWire / Touch Bar only (~40% last set). ACP uses ALSA `PCM` as that fader — do not fight it with `amixer set PCM 100%` while WP is at 40%.
- User unit: `cs8409-mixer.service` → mic unmute + boost. **Do not** force surround-40 from this unit.

## Why it sounds hollow

Four speakers (tweeter L/R, woofer L/R). Codec does no crossover. Stereo 2ch is cloned onto both DACs (`0x02` ch0 tweeters, `0x03` should be woofers). Full-range on both = midrange cancellation.

Apple does the split in CoreAudio. davidjo documents this; Linux needs a 4ch graph + HP/LP (and real Apple biquads from `AppleHDA` layouts if we can mount the macOS System volume).

## 4ch crossover (parked — broke Spotify)

Files:

- `pipewire/60-cs8409-crossover.conf` — filter-chain `cs8409_speakers` (HP/LP ~1400 Hz, woofer invert, +4 dB lowshelf 180 Hz)
- `pipewire/51-cs8409-surround40.conf` — WirePlumber profile `analog-surround-40+input:analog-stereo`

On the machine they live under `~/.config/pipewire/disabled/` and `~/.config/wireplumber/disabled/`.

When enabled: 4ch PCM confirmed (`0x02` stream ch0, `0x03` stream ch2), sound fuller, then **Spotify “can’t play current song”** (PipeWire links failed; Spotify not a PW client until stereo was restored and Spotify restarted).

Next attempt must keep a normal stereo sink that Chromium/Spotify can use, and feed 4ch only on the playback side.

## Mic

Internal Mic 100% + Internal Mic Boost 20 dB. Still quiet. EasyEffects compressor/gain if needed.
