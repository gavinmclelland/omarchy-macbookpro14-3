# T1 Touch ID (KernelRelayHost)

The power-button sensor is the T1 Secure Enclave on iBridge `05ac:8600`, not a
libfprint USB reader. macOS reaches it through `KernelRelayHost.kext`, which
matches USB interface **class `0xff` subclass `0xf9` protocol `0x11`**.

On this A1707 that interface is **USB configuration 2, interface 7** (bulk OUT
`0x05`, IN `0x88`). Configuration 1 (keyboard-mode Touch Bar) does not expose
it. `omarchy-hw-fingerprint` is supposed to stay false.

## Do not

- Install T2 packages (`linux-t2`, `tiny-dfr`, `t2bce`, `t2-touchid-linux`).
- `SET_CONFIGURATION(2)` while `apple_ibridge` is bound (deadlock).
- Load appleibridge at sysinit.
- Leave the iBridge in config 2: Touch Bar keyboard-mode HID goes away.

## Tools

```
PYTHONPATH=touchid python3 -m unittest touchid.tests.test_t1_usb -v
touchid/t1-touchid-verify --describe   # sysfs only
# root, apple_ibridge unloaded:
touchid/t1-touchid-verify --probe
```

Tracker: https://github.com/gavinmclelland/omarchy-macbookpro14-3/issues/20
