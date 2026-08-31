#!/bin/bash
# Mirror the keyd "fn" layer onto apple_ib_tb fnmode.
#
# keyd EVIOCGRAB's the Apple SPI keyboard. The input core then delivers
# events only to the grabber, so apple_ib_tb's tbkbd handler never sees
# KEY_FN and the strip stays on media keys while Fn is held.
#
# The same grab starves last_event_time. apple_ib_tb's idle worker then
# turns the strip off ~300s after the last trackpad/TB touch — including
# immediately after we write fnmode, so hold-Fn looks dead.
#
# keyd listen prints "+fn" / "-fn" as that layer goes up and down.
# Hold: fnmode=0 (F-keys) and idle/dim disabled so the strip stays lit.
# Release: fnmode=1 (media) and idle=300 / dim=150 restored.
set -uo pipefail

IDLE_ON=300
DIM_ON=150

log() { printf '%s %s\n' "$(date '+%H:%M:%S')" "$*"; }

tb_dir() {
	local real
	real=$(readlink -f /sys/bus/hid/devices/0003:05AC:8600.0001 2>/dev/null) || return 1
	[ -e "$real/fnmode" ] && printf '%s' "$real"
}

write_sys() {
	local p=$1 v=$2
	printf '%s' "$v" >"$p" 2>/dev/null || log "write $p=$v failed"
}

# Wake first (idle_timeout_store forces a display update), then switch mode.
# Otherwise the idle worker sees a stale last_event_time and turns the bar
# off in the same tick as the F-key mode change.
fn_down() {
	local d
	d=$(tb_dir) || return 0
	write_sys "$d/idle_timeout" -1
	write_sys "$d/dim_timeout" -1
	write_sys "$d/fnmode" 0
	log "fn down → F-keys (idle off)"
}

fn_up() {
	local d
	d=$(tb_dir) || return 0
	write_sys "$d/fnmode" 1
	write_sys "$d/idle_timeout" "$IDLE_ON"
	write_sys "$d/dim_timeout" "$DIM_ON"
	log "fn up → media"
}

i=0
while [ "$i" -lt 60 ]; do
	if [ -S /run/keyd.socket ] && tb_dir >/dev/null; then
		break
	fi
	i=$((i + 1))
	sleep 1
done

d=$(tb_dir) || { log "no Touch Bar fnmode after wait"; exit 1; }
[ -S /run/keyd.socket ] || { log "keyd socket missing"; exit 1; }
log "watching keyd fn layer → $d (0=F-keys, 1=media)"

# keyd listen dies if the daemon restarts or stdout goes away. Loop so
# systemd Restart= is not the only recovery, and so a boot race with keyd
# cannot leave Fn stuck.
while :; do
	while IFS= read -r line; do
		line=${line%$'\r'}
		case "$line" in
		+fn) fn_down ;;
		-fn) fn_up ;;
		esac
	done < <(exec /usr/bin/keyd listen)
	log "keyd listen ended; retry"
	sleep 2
done
