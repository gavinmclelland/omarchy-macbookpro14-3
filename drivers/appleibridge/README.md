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

## Fix 2 — live USB configuration switching removed

`apple-ibridge.c`. The imported driver defaulted to `auto`, preferred display
mode, and called `usb_set_configuration()` from its HID probe when iBridge had
booted in keyboard mode.

```
INFO: task modprobe:24033 blocked for more than 983 seconds.
INFO: task modprobe:24033 is blocked on a mutex likely owned by task modprobe:24033.
```

The first observed failure was recursive probe deadlock:

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

The wedged task is unkillable (`D` state), hangs `sysinit.target`, and blocks
shutdown. A re-entrancy guard avoided that particular mutex recursion, but two
later live experiments still D-stated inside kernel USB: one through sysfs and
one through libusb after detaching the interface drivers. Recovery required a
forced reboot.

The durable fix is structural:

- the module defaults to `keyboard`, not `auto`/display;
- `apple_ib_set_tb_mode()` only validates the inherited configuration;
- a mismatch returns `-EPERM` and the HID driver declines to bind;
- the legacy-kernel path no longer calls `usb_driver_set_configuration()`.

On this machine iBridge boots in configuration 1, which contains the HID
interfaces used by the firmware-drawn keyboard strip:

```
bNumConfigurations: 3      current: 1
  1-3:1.0  class=0x0e  uvcvideo    webcam
  1-3:1.1  class=0x0e  uvcvideo    webcam
  1-3:1.2  class=0x03  usbhid      HID  -> "keyboard" config
  1-3:1.3  class=0x03  usbhid
```

Loading with

```
apple_ibridge.tb_mode_param=keyboard
```

states the expected mode and succeeds only if the device already inherited that
configuration. It never requests a live transition. Any future configuration-2
work must choose it before first enumeration in a separately reviewed boot path;
it does not belong in this HID probe.

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
