# T1 Touch ID (KernelRelayHost)

The power-button sensor is the T1 Secure Enclave on iBridge `05ac:8600`, not a
libfprint USB reader. macOS reaches it through `KernelRelayHost.kext`, which
matches USB interface **class `0xff` subclass `0xf9` protocol `0x11`**.

On this A1707 that interface is **USB configuration 2, interface 7** (bulk OUT
`0x05`, IN `0x88`). Configuration 1 (keyboard-mode Touch Bar) does not expose
it. `omarchy-hw-fingerprint` is supposed to stay false.

## Status (2026-09-01)

This directory is descriptor and transport diagnostics, not a fingerprint
driver. It must not be installed into PAM and it never returns authentication
success.

Reproducible public work can select config 2 at USB enumeration with
[`apple_dfr_cfgsel`](https://github.com/xeeban/macbook-t1-linux/tree/main/touch-bar/kernel/t1-touchbar-display)
on a MacBookPro13,2. That proves a possible transport path, not Touch ID. Its
module registration reprobes an already-enumerated device, so do not load it
live on this MacBookPro14,3: both live switch mechanisms already D-stated here.

Full T1 enrollment and matching has been
[reported](https://x.com/0xBOYD/status/2092616493787730294) in the forthcoming
[`T1Bridge` package](https://x.com/0xBOYD/status/2094751333878235442), but no
reproducible source or release is public yet. Review that implementation when
published; do not reconstruct PAM from the claim.

## Do not

- Install T2 packages (`linux-t2`, `tiny-dfr`, `t2bce`, `t2-touchid-linux`).
- `SET_CONFIGURATION(2)` at all on a live iBridge. Writing `bConfigurationValue=2`
  on this A1707 wedges the USB write in D-state (2026-09-01). Same class of hang
  as `apple_ibridge` calling `usb_set_configuration`.
- Load appleibridge at sysinit.
- Leave the iBridge in config 2: Touch Bar keyboard-mode HID goes away.
- Put any diagnostic in PAM or treat a non-empty relay message as a match.

## Tools

```
PYTHONPATH=touchid python3 -m unittest tests.test_t1_usb -v
touchid/t1-touchid-diagnose --describe # fixture-safe; live sysfs only if path is 1-3
touchid/t1-touchid-diagnose --probe    # refuses config 1; reads only if already config 2
```

The old `t1-touchid-verify` name is a permanent fail-closed stub. It exists so
any stale PAM experiment fails instead of treating transport access as a match.

Never `SET_CONFIGURATION(2)` on a live iBridge.

Tracker: https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/20
