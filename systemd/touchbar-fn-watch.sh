#!/bin/bash
# Mirror the keyd "fn" layer onto apple_ib_tb fnmode.
#
# keyd EVIOCGRAB's the Apple SPI keyboard. The input core then delivers
# events only to the grabber, so apple_ib_tb's tbkbd handler never sees
# KEY_FN and the strip stays on media keys while Fn is held.
#
# keyd listen prints "+fn" / "-fn" as that layer goes up and down.
# fnmode=0 is F-keys only; fnmode=1 is media keys (F-keys while last_fn_pressed).
# last_fn_pressed stays false under the grab, so writing 0/1 is the switch.
set -uo pipefail

log() { printf '%s %s\n' "$(date '+%H:%M:%S')" "$*"; }

fnmode_path() {
	local real
	real=$(readlink -f /sys/bus/hid/devices/0003:05AC:8600.0001 2>/dev/null) || return 1
	[ -e "$real/fnmode" ] && printf '%s' "$real/fnmode"
}

set_mode() {
	local p
	p=$(fnmode_path) || return 0
	printf '%s' "$1" >"$p" 2>/dev/null || log "write fnmode=$1 failed"
}

i=0
while [ "$i" -lt 60 ]; do
	if [ -S /run/keyd.socket ] && fnmode_path >/dev/null; then
		break
	fi
	i=$((i + 1))
	sleep 1
done

p=$(fnmode_path) || { log "no Touch Bar fnmode after wait"; exit 1; }
[ -S /run/keyd.socket ] || { log "keyd socket missing"; exit 1; }
log "watching keyd fn layer → $p (0=F-keys, 1=media)"

# keyd listen dies if the daemon restarts or stdout goes away. Loop so
# systemd Restart= is not the only recovery, and so a boot race with keyd
# cannot leave Fn stuck.
while :; do
	while IFS= read -r line; do
		case "$line" in
		+fn) set_mode 0 ;;
		-fn) set_mode 1 ;;
		esac
	done < <(exec /usr/bin/keyd listen)
	log "keyd listen ended; retry"
	sleep 2
done
