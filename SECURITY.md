# Security

This tree is hardware enablement for a T1 MacBook Pro on Omarchy. Keep it boring.

- The T1 must stay `05ac:8600`. If it enumerates as `05ac:1281`, firmware is missing. Do not try to “fix” that with a driver.
- Do not commit or install a guessed `brcm/BCM.hcd`. A bad UART PatchRAM can take Bluetooth offline.
- The Wi-Fi NVRAM in `wifi/` must keep `macaddr=xx:xx:xx:xx:xx:xx` in git. Set the real Apple MAC only on the machine.
- Do not install T2 packages (`tiny-dfr`, `linux-t2`) on a T1.
- Touch Bar modules must not load from `modules-load.d` / initramfs. A wedged load hangs `sysinit.target`.
