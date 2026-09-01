# T1 Touch ID (KernelRelayHost)

The power-button sensor is the T1 Secure Enclave on iBridge `05ac:8600`, not a
libfprint USB reader. macOS reaches it through `KernelRelayHost.kext`, which
matches USB interface **class `0xff` subclass `0xf9` protocol `0x11`**.

On this A1707 that interface is **USB configuration 2, interface 7** (bulk OUT
`0x05`, IN `0x88`). Configuration 1 (keyboard-mode Touch Bar) does not expose
it. `omarchy-hw-fingerprint` is supposed to stay false.

## Do not

- Install T2 packages (`linux-t2`, `tiny-dfr`, `t2bce`, `t2-touchid-linux`).
- `SET_CONFIGURATION(2)` at all on a live iBridge. Writing `bConfigurationValue=2`
  on this A1707 wedges the USB write in D-state (2026-09-01). Same class of hang
  as `apple_ibridge` calling `usb_set_configuration`.
- Load appleibridge at sysinit.
- Leave the iBridge in config 2: Touch Bar keyboard-mode HID goes away.

## Tools

```
PYTHONPATH=touchid python3 -m unittest tests.test_t1_usb -v
touchid/t1-touchid-verify --describe   # fixture-safe; live sysfs only if path is 1-3
touchid/t1-touchid-verify --probe      # EP0 if config 1; bulk only if already config 2
```

Never `SET_CONFIGURATION(2)` on a live iBridge.

Tracker: https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/20
