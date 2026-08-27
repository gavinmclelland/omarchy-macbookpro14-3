#!/bin/bash
# Keep the DSP sink at full scale. Omarchy volume keys resolve through it to
# analog-surround-40 (see omarchy-audio-output-sink). Locking that physical
# node (or ALSA PCM) freezes the Touch Bar fader.
#
# DspLoudness shelves are baked in the host graph (PW 1.6 ignores runtime
# set-param on filter-chain biquad Gain).
set -euo pipefail
DSP=cs8409_speakers

lock() {
	pactl set-sink-volume "$DSP" 100% >/dev/null 2>&1 || true
}

lock
pactl subscribe 2>/dev/null | while read -r _; do
	lock
done
