# CS8409 on MacBookPro14,3

Speakers work. Mic is quiet (same as macOS).

## Current graph

Apps see a **stereo** sink `cs8409_speakers`. Playback is 4ch onto analog-surround-40:

- FL/FR → tweeter DAC `0x02` channel 0 (LR4 highpass 800 Hz)
- RL/RR → woofer DAC `0x03` channel 2 (LR4 lowpass 800 Hz, invert, +2 dB lowshelf 150 Hz)

Internal mic sweep: without invert, **26 dB hole at 1 kHz**. With invert + 800 Hz split, that notch is gone.

WirePlumber keeps the raw 4ch node at `priority.session=1` so Spotify/Chromium never pick it. Default sink is `cs8409_speakers`.

- Clock 44100 (`pipewire-cs8409.conf`)
- Volume: PipeWire / Touch Bar only. ACP uses ALSA `PCM` as that fader.
- Mixer unit: mic unmute + boost. Do not force surround-40 from that unit.

Confirmed while playing: PCM `S32_LE` 4ch 44100; `0x02` stream ch0, `0x03` stream ch2. Pulse `paplay` (2ch) links to `cs8409_speakers`, not the raw 4ch node.

## Why stereo-only sounded hollow

Codec does no crossover. 2ch clones full-range onto both DACs. Tweeters and woofers fight in the midrange. Apple splits in CoreAudio.

## Files

- `60-cs8409-crossover.conf` — stereo filter-chain sink
- `51-cs8409.conf` — surround-40 profile + hide raw 4ch from session default
- `applehda/parse_layout.py` — inflate Apple `DspEqualization32`
- `applehda/layout57.json` — this machine’s layout (MAX98706, GTK/Merry same chain)

Rollback: move the two files out of `~/.config/*/conf.d/`, `systemctl --user restart pipewire wireplumber`, `pactl set-card-profile alsa_card.pci-0000_00_1f.3 output:analog-stereo+input:analog-stereo`.

Headphones: card is forced to surround-40; jack autoswitch is unverified.

AppleHDA **layout 57** is distilled (`applehda/layout57.json`) but **not** in
this graph yet. Apple’s split is tweeter HP 1150+650 Hz / woofer LP 1180+1500 Hz,
plus stereo PEQ, compressor, delay, and thermal protection. Next: map those
biquads + a software peak limiter onto `cs8409_speakers`. Do not use
`speakersafetyd`. [#14](https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/14).

## Mic

Internal Mic 100% + Internal Mic Boost 20 dB. Still quiet. EasyEffects compressor/gain if needed.
