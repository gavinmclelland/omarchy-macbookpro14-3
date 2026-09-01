"""Userspace KernelRelayHost pipe to the T1 SEP.

The host kext (com.apple.driver.KernelRelayHost) talks to one USB bulk pair
on iBridge config 2 / interface 7 (class ff / subclass f9 / protocol 11).
AppleSSE then uses a logical relay endpoint for biometric SEP scores.

This module can open that bulk pair only when configuration 2 is already
active. It contains no message encoder and performs no USB writes.
"""

from __future__ import annotations

import ctypes
import ctypes.util
from pathlib import Path

from t1_usb import APPLE_VID, IBRIDGE_PID, SepInterface, find_sep_interface

SYSFS_DESC = Path("/sys/bus/usb/devices/1-3/descriptors")
SYSFS_CONFIG = Path("/sys/bus/usb/devices/1-3/bConfigurationValue")

LIBUSB_SUCCESS = 0
LIBUSB_ERROR_TIMEOUT = -7

class LibusbError(RuntimeError):
    def __init__(self, code: int, what: str):
        super().__init__(f"{what}: libusb {code}")
        self.code = code


def _libusb():
    name = ctypes.util.find_library("usb-1.0") or "libusb-1.0.so.0"
    lib = ctypes.CDLL(name)
    lib.libusb_init.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
    lib.libusb_init.restype = ctypes.c_int
    lib.libusb_exit.argtypes = [ctypes.c_void_p]
    lib.libusb_open_device_with_vid_pid.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint16,
        ctypes.c_uint16,
    ]
    lib.libusb_open_device_with_vid_pid.restype = ctypes.c_void_p
    lib.libusb_close.argtypes = [ctypes.c_void_p]
    lib.libusb_claim_interface.argtypes = [ctypes.c_void_p, ctypes.c_int]
    lib.libusb_claim_interface.restype = ctypes.c_int
    lib.libusb_release_interface.argtypes = [ctypes.c_void_p, ctypes.c_int]
    lib.libusb_bulk_transfer.argtypes = [
        ctypes.c_void_p,
        ctypes.c_ubyte,
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_int),
        ctypes.c_uint,
    ]
    lib.libusb_bulk_transfer.restype = ctypes.c_int
    lib.libusb_get_configuration.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_int),
    ]
    lib.libusb_get_configuration.restype = ctypes.c_int
    return lib


def verify_transport(live_config: int | None, sep: SepInterface) -> str:
    """How to reach KernelRelay.

    'bulk' — live USB config already exposes iface 7.
    'unavailable' — the active configuration has no KernelRelay interface.
    """
    if live_config == sep.config:
        return "bulk"
    return "unavailable"


class SepPipe:
    """Bulk pipe to KernelRelayHost interface 7 when config 2 is already active.

    This class never changes the live USB configuration. Both tested live
    config-switch paths D-stated the iBridge on this chassis.
    """

    def __init__(self, sep: SepInterface):
        self.sep = sep
        self._lib = _libusb()
        self._ctx = ctypes.c_void_p()
        rc = self._lib.libusb_init(ctypes.byref(self._ctx))
        if rc != LIBUSB_SUCCESS:
            raise LibusbError(rc, "libusb_init")
        self._dev = self._lib.libusb_open_device_with_vid_pid(
            self._ctx, APPLE_VID, IBRIDGE_PID
        )
        if not self._dev:
            self._lib.libusb_exit(self._ctx)
            raise RuntimeError("open 05ac:8600 failed (need root / config 2)")
        rc = self._lib.libusb_claim_interface(self._dev, sep.interface)
        if rc != LIBUSB_SUCCESS:
            self._lib.libusb_close(self._dev)
            self._lib.libusb_exit(self._ctx)
            raise LibusbError(rc, f"claim interface {sep.interface}")

    def configuration(self) -> int:
        cfg = ctypes.c_int()
        rc = self._lib.libusb_get_configuration(self._dev, ctypes.byref(cfg))
        if rc != LIBUSB_SUCCESS:
            raise LibusbError(rc, "get_configuration")
        return cfg.value

    def bulk_in(self, n: int = 512, timeout_ms: int = 1000) -> bytes:
        buf = ctypes.create_string_buffer(n)
        xfer = ctypes.c_int()
        rc = self._lib.libusb_bulk_transfer(
            self._dev,
            ctypes.c_ubyte(self.sep.ep_in),
            buf,
            n,
            ctypes.byref(xfer),
            timeout_ms,
        )
        if rc == LIBUSB_ERROR_TIMEOUT:
            return b""
        if rc != LIBUSB_SUCCESS:
            raise LibusbError(rc, "bulk in")
        return buf.raw[: xfer.value]

    def close(self) -> None:
        if getattr(self, "_dev", None):
            try:
                self._lib.libusb_release_interface(self._dev, self.sep.interface)
            except Exception:
                pass
            self._lib.libusb_close(self._dev)
            self._dev = None
        if getattr(self, "_ctx", None):
            self._lib.libusb_exit(self._ctx)
            self._ctx = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def load_sep_from_sysfs(path: Path = SYSFS_DESC) -> SepInterface:
    return find_sep_interface(path.read_bytes())


def current_config() -> int | None:
    try:
        return int(SYSFS_CONFIG.read_text().strip())
    except FileNotFoundError:
        return None
