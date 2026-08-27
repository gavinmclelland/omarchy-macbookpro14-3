#!/bin/bash
# Keep CS8409 analog-surround-40 and ALSA PCM at 0 dB.
# App volume is only cs8409_speakers. WirePlumber restores the speaker
# route (~60–75%) and ACP copies that onto PCM, double-attenuating.
set -euo pipefail
SINK=alsa_output.pci-0000_00_1f.3.analog-surround-40

lock() {
	pactl set-sink-volume "$SINK" 100% >/dev/null 2>&1 || true
	amixer -q -c PCH set PCM 100% >/dev/null 2>&1 || true
}

lock
pactl subscribe 2>/dev/null | while read -r _; do
	lock
done
