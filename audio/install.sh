#!/bin/bash
# CS8409 speakers + mic. Mainline quirk table is Dell-only; this DKMS is required.
# Downloads ~150 MB of kernel source. Mic ships muted.
set -euo pipefail
pacman -S --noconfirm --needed base-devel git wget dkms linux-headers
src=/usr/local/src/snd_hda_macbookpro
if [ ! -d "$src/.git" ]; then
  git clone https://github.com/davidjo/snd_hda_macbookpro.git "$src"
fi
"$src"/install.cirrus.driver.sh -i
echo "Reboot, then:"
echo "  wpctl set-mute @DEFAULT_AUDIO_SOURCE@ 0"
echo "  wpctl set-volume @DEFAULT_AUDIO_SOURCE@ 100%"
