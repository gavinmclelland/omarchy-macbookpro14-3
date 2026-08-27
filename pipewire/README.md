# CS8409 on MacBookPro14,3

Speakers work. Mic is quiet (same as macOS).

## Current graph

Apps see a **stereo** sink `cs8409_speakers`. Playback is 4ch onto analog-surround-40:

- Stereo: HPF 80 Hz + layout 57 PEQ + −6 dB headroom + Apple +1.5 dB
- FL/FR → tweeter DAC `0x02` ch0 (HP 1150 Hz + HP 650 Hz + tweeter PEQ)
- RL/RR → woofer DAC `0x03` ch2 (LP 1180 Hz + LP 1500 Hz + woofer PEQ, invert)
- Peak clamp ±0.98 (stand-in for ControlFreak / thermal)
- Hardware 4ch locked at 0 dB (`cs8409-mixer.service` retries after WirePlumber restore)

Tones (layout 57): invert **on** → 1 kHz is −4 dB vs 500 Hz; invert off → −10 dB.
Keep invert. Lodi Dodi’s 1 kHz dip on the mic was the mix, not a 26 dB polarity null.

WirePlumber keeps the raw 4ch node at `priority.session=1` so Spotify/Chromium never pick it. Default sink is `cs8409_speakers`.

- Clock 44100 (`pipewire-cs8409.conf`)
- Volume: PipeWire / Touch Bar only. ACP uses ALSA `PCM` as that fader.
- Mixer unit: mic unmute + boost. Do not force surround-40 from that unit.

Confirmed while playing: PCM `S32_LE` 4ch 44100; `0x02` stream ch0, `0x03` stream ch2. Pulse `paplay` (2ch) links to `cs8409_speakers`, not the raw 4ch node.

## Why stereo-only sounded hollow

Codec does no crossover. 2ch clones full-range onto both DACs. Tweeters and woofers fight in the midrange. Apple splits in CoreAudio.

## Files

- `60-cs8409-crossover.conf` — live layout 57 filter (generated `bq_*` nodes; `param_eq` dropped the woofer pair)
- `60-cs8409-lr4.conf` — parked 800 Hz LR4 rollback
- `51-cs8409.conf` — surround-40 profile + hide raw 4ch from session default
- `applehda/layout57.json` — distilled MAX98706 chain
- `applehda/render_filter.py` — `layout57.json` → filter conf

Rollback: move the two files out of `~/.config/*/conf.d/`, `systemctl --user restart pipewire wireplumber`, `pactl set-card-profile alsa_card.pci-0000_00_1f.3 output:analog-stereo+input:analog-stereo`.

Headphones: card is forced to surround-40; jack autoswitch is unverified.

Layout 57 biquads are in the live graph. Mozart / loudness / BuzzKill / thermal
are not (opaque blobs). Do not replace davidjo. Do not use `speakersafetyd`.
[#14](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/14).

Rollback to 800 Hz LR4: copy `60-cs8409-lr4.conf` over
`~/.config/pipewire/pipewire.conf.d/60-cs8409-crossover.conf` and restart
PipeWire.

## Mic

Internal Mic 100% + Internal Mic Boost 20 dB. Still quiet. EasyEffects compressor/gain if needed.
