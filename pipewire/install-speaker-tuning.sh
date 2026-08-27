#!/bin/bash
# Host layout 57 as a separate PipeWire client. User-level.
# Sink is cs8409_speakers (MacBook speakers), not Omarchy's stock name.
#
#   ./pipewire/install-speaker-tuning.sh
#   ./pipewire/install-speaker-tuning.sh off
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
config_home="${XDG_CONFIG_HOME:-$HOME/.config}"
tuning_dir="$ROOT/pipewire/speaker-tuning/macbookpro14-3"
host_config_name=cs8409-speaker-tuning.conf
host_config="$config_home/pipewire/$host_config_name"
host_source="$ROOT/pipewire/cs8409-speaker-tuning.conf"
fragment_dir="$config_home/pipewire/$host_config_name.d"
fragment="$fragment_dir/90-tuning.conf"
unit_name=cs8409-speaker-tuning.service
unit="$config_home/systemd/user/$unit_name"
unit_source="$ROOT/pipewire/cs8409-speaker-tuning.service"
daemon_dropin="$config_home/pipewire/pipewire.conf.d/60-cs8409-crossover.conf"
stale_omarchy_host="$config_home/pipewire/omarchy-speaker-tuning.conf"
stale_omarchy_unit="$config_home/systemd/user/omarchy-speaker-tuning.service"
sink_name=cs8409_speakers

action="${1:-on}"

need() {
	command -v "$1" >/dev/null || {
		echo "missing $1" >&2
		exit 1
	}
}

sink_matching() {
	pactl list sinks short 2>/dev/null | awk -v p="$1" '$2 ~ p {print $2; exit}'
}

drop_stale_omarchy_host() {
	systemctl --user disable --now omarchy-speaker-tuning.service >/dev/null 2>&1 || true
	rm -f "$stale_omarchy_host" "$stale_omarchy_unit"
	rm -rf "$config_home/pipewire/omarchy-speaker-tuning.conf.d"
}

case "$action" in
off)
	systemctl --user disable --now "$unit_name" >/dev/null 2>&1 || true
	drop_stale_omarchy_host
	rm -f "$fragment" "$host_config" "$unit"
	rmdir "$fragment_dir" 2>/dev/null || true
	systemctl --user daemon-reload >/dev/null 2>&1 || true
	echo "CS8409 speaker-tuning host removed."
	;;
on)
	need pactl
	[[ -r $tuning_dir/filter-chain.conf && -r $tuning_dir/tuning.conf ]] || {
		echo "tuning files missing in $tuning_dir" >&2
		exit 1
	}
	[[ -r $host_source && -r $unit_source ]] || {
		echo "host templates missing under $ROOT/pipewire" >&2
		exit 1
	}
	[[ -r /usr/lib/lv2/lsp-plugins.lv2/limiter_stereo.ttl ]] || {
		echo "lsp-plugins-lv2 is required (limiter_stereo)." >&2
		echo "  omarchy pkg add lsp-plugins-lv2" >&2
		exit 1
	}

	unset description sink_pattern
	# shellcheck disable=SC1091
	source "$tuning_dir/tuning.conf"
	[[ -n ${sink_pattern:-} ]] || {
		echo "tuning.conf has no sink_pattern" >&2
		exit 1
	}

	speaker_sink=""
	for _ in {1..20}; do
		speaker_sink="$(sink_matching "$sink_pattern")"
		[[ -n $speaker_sink ]] && break
		sleep 0.5
	done
	[[ -n $speaker_sink ]] || {
		echo "no sink matching $sink_pattern" >&2
		exit 1
	}

	if pgrep -u "$(id -u)" -x easyeffects >/dev/null 2>&1; then
		echo "EasyEffects is running; stop it before installing the tuning." >&2
		exit 1
	fi

	mkdir -p "$fragment_dir" "$config_home/systemd/user"
	drop_stale_omarchy_host
	install -m644 "$host_source" "$host_config"
	sed "s|@SPEAKER_SINK@|$speaker_sink|g" "$tuning_dir/filter-chain.conf" >"$fragment"
	install -m644 "$unit_source" "$unit"

	need_audio_restart=0
	if [[ -e $daemon_dropin ]]; then
		rm -f "$daemon_dropin"
		need_audio_restart=1
	fi

	systemctl --user daemon-reload
	systemctl --user enable "$unit_name" >/dev/null
	if ((need_audio_restart)); then
		if command -v omarchy-restart-audio >/dev/null; then
			omarchy-restart-audio >/dev/null 2>&1 || true
		else
			systemctl --user restart pipewire pipewire-pulse wireplumber
		fi
		for _ in {1..40}; do
			pactl info >/dev/null 2>&1 && break
			sleep 0.25
		done
	fi
	systemctl --user restart "$unit_name"

	present=0
	for _ in {1..40}; do
		pactl list sinks short 2>/dev/null | awk '{print $2}' | grep -qx "$sink_name" && {
			present=1
			break
		}
		sleep 0.25
	done
	if ((!present)); then
		systemctl --user disable --now "$unit_name" >/dev/null 2>&1 || true
		rm -f "$fragment" "$host_config" "$unit"
		echo "Tuning sink never appeared. Check: systemctl --user status $unit_name" >&2
		exit 1
	fi

	pactl set-default-sink "$sink_name" >/dev/null 2>&1 || true
	pactl set-sink-volume "$sink_name" 100% >/dev/null 2>&1 || true
	echo "Installed speaker tuning: ${description:-macbookpro14-3}"
	echo "  sink     $sink_name"
	echo "  target   $speaker_sink"
	echo "  fragment $fragment"
	;;
*)
	echo "usage: $0 [on|off]" >&2
	exit 2
	;;
esac
