# CS8409 on MacBookPro14,3 (A1707)

Speakers work. Mic is quiet (same as macOS).

## Current graph

Apps see stereo sink **`cs8409_speakers`** (description: MacBook speakers).
Playback is 4ch onto analog-surround-40:

- Stereo: HPF 80 Hz + layout 57 PEQ + Apple +1.5 dB + LSP `limiter_stereo` (`alr=0` `boost=0`, `g_in` ≈ −5.3 dB)
- FL/FR → tweeter DAC `0x02` ch0 (HP 1150 Hz + HP 650 Hz + tweeter PEQ)
- RL/RR → woofer DAC `0x03` ch2 (LP 1180 Hz + LP 1500 Hz + woofer PEQ, invert, delay 5 samples)
- Peak clamp ±0.98 (stand-in for ControlFreak / thermal)
- DSP sink locked at 0 dB (`cs8409-dsp-unity.service`). Touch Bar volume is the physical 4ch node (`omarchy-audio-output-sink` walks through any virtual default). Do not lock analog-surround-40 / PCM.

Host is a **separate PipeWire client** (`pipewire -c cs8409-speaker-tuning.conf`), not a daemon drop-in and not Omarchy’s stock `omarchy_speaker_tuning` name. Switching it does not restart `pipewire-pulse` (Spotify stays connected).

Tones (layout 57, lid mic vs 500 Hz): invert off −10 dB at 1 kHz; invert on −4 dB;
invert + 5-sample woofer delay was **−0.7 dB** on the daemon graph. Host + limiter:
1 kHz **+0.5 dB**, electrical 200-ish Hz on woofers, 1.6 kHz on tweeters. Keep invert
+ delay. 280 Hz scoop is Apple.

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
