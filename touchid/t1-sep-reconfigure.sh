#!/bin/bash
# Intentionally does NOT SET_CONFIGURATION.
#
# Live test 2026-09-01: writing 2 to bConfigurationValue on this A1707's
# 05ac:8600 wedged the writer in D-state (kernel USB). Same deadlock class as
# apple_ibridge calling usb_set_configuration. Do not retry on a live iBridge.
#
# KernelRelayHost SEP (ff/f9/11) only exists in config 2. Reaching it without
# a config switch is unsolved. This script is a hard fail so installers cannot
# brick the Touch Bar stack.
set -euo pipefail
echo "refusing: SET_CONFIGURATION(2) deadlocks iBridge USB on this chassis" >&2
echo "SEP interface is config 2 iface 7; keyboard-mode TB is config 1." >&2
exit 2
