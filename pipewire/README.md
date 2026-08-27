# CS8409 on MacBookPro14,3 (A1707)

Speakers work. Mic is quiet (same as macOS).

## Current graph

Apps see stereo sink **`cs8409_speakers`** (description: MacBook speakers).
Playback is 4ch onto analog-surround-40:

- Stereo, Apple order: HPF 80 Hz → Mozart compressor (−18 dB / 1.8 / +6 dB) → Loudness shelves 300 Hz +4 / 2 kHz +3 → layout 57 PEQ (280 Hz **−20 dB** XML) → dual-band 400/1250 Hz → +1.5 dB → limiter
- FL/FR → tweeter DAC `0x02` ch0 (HP 1150 Hz + HP 650 Hz + tweeter PEQ)
- RL/RR → woofer DAC `0x03` ch2 (LP 1180 Hz + LP 1500 Hz + woofer PEQ, invert, delay 5 samples)
- Peak clamp ±0.98 (stand-in for ControlFreak / thermal)
- DSP sink locked at 0 dB (`cs8409-dsp-unity.service`). Touch Bar volume is the physical 4ch node (`omarchy-audio-output-sink` walks through any virtual default). Do not lock analog-surround-40 / PCM.

Host is a **separate PipeWire client** (`pipewire -c cs8409-speaker-tuning.conf`), not a daemon drop-in and not Omarchy’s stock `omarchy_speaker_tuning` name. Switching it does not restart `pipewire-pulse` (Spotify stays connected).

Full Apple range on this hardware is **80 Hz–16 kHz** (Apple’s own HPF and last
EQ band). Mozart + dual-band + Loudness shelves are on the 2ch bus so the
280 Hz XML dip is not a dry hole. PipeWire 1.6 does not apply runtime
`set-param` on filter-chain biquad Gain, so Loudness is a baked mid-curve
(+4 / +3 dB) rather than TB-tracking. Invert + 5-sample delay kept. BuzzKill /
thermal still opaque.

WirePlumber keeps the raw 4ch node at `priority.session=1` so Spotify/Chromium never pick it.

- Clock 44100 (`pipewire-cs8409.conf`)
- Volume: PipeWire / Touch Bar only. ACP uses ALSA `PCM` as that fader.
- Mixer unit: mic unmute + boost. Do not force surround-40 from that unit.

## Why stereo-only sounded hollow

Codec does no crossover. 2ch clones full-range onto both DACs. Tweeters and woofers fight in the midrange. Apple splits in CoreAudio.

## Files

- `speaker-tuning/macbookpro14-3/` — live layout 57 host graph + `tuning.conf`
- `cs8409-speaker-tuning.conf` / `.service` — PipeWire client host
- `install-speaker-tuning.sh` — install host, substitute `@SPEAKER_SINK@`, remove the daemon drop-in
- `60-cs8409-crossover.conf` — parked daemon rollback (no LV2 limiter)
- `60-cs8409-lr4.conf` — parked 800 Hz LR4 rollback
- `51-cs8409.conf` — surround-40 profile + hide raw 4ch from session default
- `applehda/layout57.json` — distilled MAX98706 chain
- `applehda/render_filter.py` — `layout57.json` → daemon + host confs

```bash
omarchy pkg add lsp-plugins-lv2
./pipewire/install-speaker-tuning.sh
systemctl --user enable --now macbook-internal-mic.service cs8409-dsp-unity.service
```

Rollback: `./pipewire/install-speaker-tuning.sh off`, copy `60-cs8409-crossover.conf` back to `~/.config/pipewire/pipewire.conf.d/`, `omarchy restart audio`.

Headphones: card is forced to surround-40; jack autoswitch is unverified.

Layout 57 biquads are in the live graph. Mozart / loudness / BuzzKill / thermal
are not (opaque blobs). Do not replace davidjo. Do not use `speakersafetyd`.
ArchProAudio / EasyEffects are not this path (DAW latency / generic EQ).
[#14](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/14).

## Mic

Internal Mic 100% + Internal Mic Boost 20 dB. Still quiet. EasyEffects compressor/gain if needed.
