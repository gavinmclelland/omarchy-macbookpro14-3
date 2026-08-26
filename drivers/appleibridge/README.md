# appleibridge — Touch Bar driver for the Apple T1

Source for the iBridge Touch Bar and ambient light sensor drivers, with two local fixes.

**Upstream:** [`F13-Kr1pt0n/macbook-pro-touchbar-driver`](https://github.com/F13-Kr1pt0n/macbook-pro-touchbar-driver),
branch `touchbar-driver-hid-driver`, commit `ecfadc3` (2025-09-02).

That fork is the most current lineage by five years. The alternatives are all older and none
of them compile on a modern kernel:

| Repo | Last commit |
| --- | --- |
| `t2linux/apple-ib-drv` master | 2018-03-14 |
| `t2linux/apple-ib-drv` ibridge-reviews | 2019-07-19 |
| `kekrby/apple-ibridge` | 2021-09-20 |
| **`F13-Kr1pt0n`** | **2025-09-02** |

It ships no `applespi.c`, which is correct — that driver is mainline since 5.3, so the
keyboard and trackpad work without any of this.

## Fix 1 — `struct tb_touch` defined after it is used

`apple-ib-tb.c`

```
apple-ib-tb.c:174:31: error: field 'touch' has incomplete type
  174 |         struct tb_touch       touch;
```

`struct appletb_device` embeds `struct tb_touch` **by value**, but upstream defines that
struct about 30 lines later. C requires the definition first, so upstream's own
`LINUX_VERSION_CODE >= KERNEL_VERSION(6,15,0)` path has never compiled on any kernel. Not a
kernel-API problem — a plain ordering bug.

Fix: move the definition above `struct appletb_device`, unchanged.

## Fix 2 — self-deadlock in `apple_ib_set_tb_mode()`

`apple-ibridge.c`. This is the one that matters, and the reason nobody gets the Touch Bar
working on a current kernel.

```
INFO: task modprobe:24033 blocked for more than 983 seconds.
INFO: task modprobe:24033 is blocked on a mutex likely owned by task modprobe:24033.
```

The recursion:

```
appleib_hid_probe()                        .probe for the iBridge HID interfaces
  └─ apple_ib_set_tb_mode()
       ├─ mutex_lock(&appleib_tbmode_lock)
       └─ usb_set_configuration()          tears down and rebuilds the USB config,
            │                              unbinding and re-binding every interface
            │                              driver SYNCHRONOUSLY, in this same task
            └─ appleib_hid_probe()         called again
                 └─ apple_ib_set_tb_mode()
                      └─ mutex_lock(&appleib_tbmode_lock)   ← already held by this task
```

Upstream calls a USB core function that invokes driver callbacks while holding its own
mutex. The wedged task is unkillable (`D` state), it hangs `sysinit.target` so the login
screen never appears, and it blocks shutdown — recovery needs a forced power-off.

Fix, two parts:

1. A re-entrancy guard, `appleib_tbmode_switching`.
2. Drop `appleib_tbmode_lock` around `usb_set_configuration()`, so the recursive call can
   reach the guard instead of blocking on the mutex. The guard alone is not enough — the
   recursion happens *while the lock is held*, so the inner call would block before ever
   testing the flag.

Lock discipline after the change, all four paths balanced:

| Path | Flow |
| --- | --- |
| no device | returns before taking the lock |
| guard hit (the recursive call) | lock → unlock → `return 0` |
| early exits | lock → `goto out_unlock` → unlock |
| config switch | lock → set flag → **unlock** → `usb_set_configuration()` → lock → clear flag → unlock |

## A zero-code workaround, worth knowing

The deadlock only fires when the driver actually *changes* USB configuration. It does not
if the requested mode already matches the current one:

```c
if (udev->actconfig && udev->actconfig->desc.bConfigurationValue == target_cv) {
        ret = 0;
        goto out_unlock;          /* usb_set_configuration() never called */
}
```

On this machine the iBridge boots in configuration 1, which contains the HID interfaces —
the driver's definition of the *keyboard* config:

```
bNumConfigurations: 3      current: 1
  1-3:1.0  class=0x0e  uvcvideo    webcam
  1-3:1.1  class=0x0e  uvcvideo    webcam
  1-3:1.2  class=0x03  usbhid      HID  -> "keyboard" config
  1-3:1.3  class=0x03  usbhid
```

`appleib_cfg_is_keyboard()` matches `USB_CLASS_HID`, `appleib_cfg_is_display()` matches
`USB_CLASS_VENDOR_SPEC`, and the default `AUTO` **prefers display** — so it tries to switch
away from config 1 and deadlocks. Loading with

```
apple_ibridge.tb_mode_param=keyboard
```

selects the config the device is already in, takes the early return, and never deadlocks
even on unpatched code. Keyboard mode is also the useful one: Esc and F1-F12.

## Build

```bash
sudo pacman -S --needed linux-headers dkms
sudo mkdir -p /usr/src/appleibridge-0.1
sudo cp apple-ib-als.c apple-ib-tb.c apple-ibridge.c apple-ibridge.h \
        Makefile dkms.conf /usr/src/appleibridge-0.1/
sudo dkms add     -m appleibridge -v 0.1
sudo dkms build   -m appleibridge -v 0.1
sudo dkms install -m appleibridge -v 0.1
```

Verified building on **7.1.8-arch1-3** with **gcc 16.2.1**.

## Load it safely

**Never put these in `/etc/modules-load.d/` while testing.** If a module wedges at boot it
hangs `sysinit.target`, the login screen never appears, and the only way out is a forced
power-off. Load by hand so a failure costs one reboot instead of your boot.

The blacklist in `/etc/limine-entry-tool.d/macbookpro14-2.conf` stops `modprobe` from
loading them at all, which is deliberate. To test without removing it, use `insmod` on the
decompressed modules — `insmod` ignores modprobe's blacklist.

Order matters: `apple_ibridge` first, it is the coordinator.

```bash
lsmod | grep -E '^apple_ib'                       # expect nothing
dmesg -w &                                        # watch it
sudo insmod apple-ibridge.ko tb_mode_param=keyboard
sudo insmod apple-ib-tb.ko
```

Working means the Touch Bar lights up with Esc and function keys. A hang means the module is
wedged in `D` state; the system stays usable over SSH but shutdown will hang, so plan on a
power-button hold.
