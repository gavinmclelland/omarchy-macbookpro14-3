"""Userspace KernelRelayHost pipe to the T1 SEP.

The host kext (com.apple.driver.KernelRelayHost) talks to one USB bulk pair
on iBridge config 2 / interface 7 (class ff / subclass f9 / protocol 11).
AppleSSE then uses a logical relay endpoint for biometric SEP scores.

This module opens that bulk pair. Message framing follows the kext's own
_dataReceiveCompletion logs: 4 msgData bytes, msgIndex, hasBuffer, replyTo,
cmd, msgLength, dataLength.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import signal
import struct
from dataclasses import dataclass
from pathlib import Path

from t1_usb import APPLE_VID, IBRIDGE_PID, SepInterface, find_sep_interface

SYSFS_DESC = Path("/sys/bus/usb/devices/1-3/descriptors")
SYSFS_CONFIG = Path("/sys/bus/usb/devices/1-3/bConfigurationValue")

LIBUSB_SUCCESS = 0
LIBUSB_ERROR_TIMEOUT = -7
LIBUSB_ERROR_PIPE = -9

# Packed as printed by KernelRelayHost _dataReceiveCompletion (4× msgData bytes).
KR_HEADER_FMT = "<4sBBHQQII"  # fourcc, msgIndex, hasBuffer, pad16, replyTo, cmd, msgLen, dataLen
KR_HEADER_SIZE = struct.calcsize(KR_HEADER_FMT)


@dataclass
class KRHeader:
    fourcc: bytes
    msg_index: int
    has_buffer: int
    reply_to: int
    cmd: int
    msg_length: int
    data_length: int

    def pack(self) -> bytes:
        return struct.pack(
            KR_HEADER_FMT,
            self.fourcc,
            self.msg_index,
            self.has_buffer,
            0,
            self.reply_to,
            self.cmd,
            self.msg_length,
            self.data_length,
        )

    @classmethod
    def unpack(cls, blob: bytes) -> "KRHeader":
        if len(blob) < KR_HEADER_SIZE:
            raise ValueError(f"short KernelRelay header ({len(blob)})")
        fourcc, idx, has, _pad, reply, cmd, mlen, dlen = struct.unpack(
            KR_HEADER_FMT, blob[:KR_HEADER_SIZE]
        )
        return cls(fourcc, idx, has, reply, cmd, mlen, dlen)


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
    lib.libusb_set_auto_detach_kernel_driver.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
    ]
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
    lib.libusb_control_transfer.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint8,
        ctypes.c_uint8,
        ctypes.c_uint16,
        ctypes.c_uint16,
        ctypes.c_void_p,
        ctypes.c_uint16,
        ctypes.c_uint,
    ]
    lib.libusb_control_transfer.restype = ctypes.c_int
    lib.libusb_set_configuration.argtypes = [ctypes.c_void_p, ctypes.c_int]
    lib.libusb_set_configuration.restype = ctypes.c_int
    lib.libusb_kernel_driver_active.argtypes = [ctypes.c_void_p, ctypes.c_int]
    lib.libusb_kernel_driver_active.restype = ctypes.c_int
    lib.libusb_detach_kernel_driver.argtypes = [ctypes.c_void_p, ctypes.c_int]
    lib.libusb_detach_kernel_driver.restype = ctypes.c_int
    return lib


def verify_transport(
    live_config: int | None, sep: SepInterface, allow_config2: bool = False
) -> str:
    """How to reach KernelRelay.

    'bulk' — live USB config already exposes iface 7.
    'set-config2' — opt-in: libusb_set_configuration(2) then bulk (takes TB/webcam down).
    'ep0' — config 1 vendor control only.
    """
    if live_config == sep.config:
        return "bulk"
    if allow_config2:
        return "set-config2"
    return "ep0"


class SepPipe:
    """Bulk pipe to KernelRelayHost interface 7.

    Pass switch_to=2 only with an explicit CLI opt-in. Restores config 1 on close.
    """

    def __init__(self, sep: SepInterface, switch_to: int | None = None):
        self.sep = sep
        self._switch_to = switch_to
        self._switched = False
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
        self._lib.libusb_set_auto_detach_kernel_driver(self._dev, 1)
        if switch_to is not None:
            self._detach_all()
            self._set_config(switch_to)
            self._switched = True
        rc = self._lib.libusb_claim_interface(self._dev, sep.interface)
        if rc != LIBUSB_SUCCESS:
            if self._switched:
                try:
                    self._set_config(1)
                except Exception:
                    pass
            self._lib.libusb_close(self._dev)
            self._lib.libusb_exit(self._ctx)
            raise LibusbError(rc, f"claim interface {sep.interface}")

    def _detach_all(self) -> None:
        for i in range(8):
            if self._lib.libusb_kernel_driver_active(self._dev, i) == 1:
                self._lib.libusb_detach_kernel_driver(self._dev, i)

    def _set_config(self, n: int) -> None:
        def _boom(signum, frame):
            raise TimeoutError(f"libusb_set_configuration({n}) timed out")

        old = signal.signal(signal.SIGALRM, _boom)
        signal.alarm(8)
        try:
            rc = self._lib.libusb_set_configuration(self._dev, n)
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)
        if rc != LIBUSB_SUCCESS:
            raise LibusbError(rc, f"set_configuration({n})")

    def configuration(self) -> int:
        cfg = ctypes.c_int()
        rc = self._lib.libusb_get_configuration(self._dev, ctypes.byref(cfg))
        if rc != LIBUSB_SUCCESS:
            raise LibusbError(rc, "get_configuration")
        return cfg.value

    def bulk_out(self, data: bytes, timeout_ms: int = 1000) -> None:
        xfer = ctypes.c_int()
        buf = ctypes.create_string_buffer(data, len(data))
        rc = self._lib.libusb_bulk_transfer(
            self._dev,
            ctypes.c_ubyte(self.sep.ep_out),
            buf,
            len(data),
            ctypes.byref(xfer),
            timeout_ms,
        )
        if rc != LIBUSB_SUCCESS:
            raise LibusbError(rc, "bulk out")

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
            if self._switched:
                try:
                    self._set_config(1)
                except Exception as e:
                    print(f"restore config 1 failed: {e}", flush=True)
            self._lib.libusb_close(self._dev)
            self._dev = None
        if getattr(self, "_ctx", None):
            self._lib.libusb_exit(self._ctx)
            self._ctx = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class Ep0Device:
    """Open 05ac:8600 for vendor control on EP0. Does not claim iface 7 or set config."""

    def __init__(self):
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
            raise RuntimeError("open 05ac:8600 failed (need permission)")

    def configuration(self) -> int:
        cfg = ctypes.c_int()
        rc = self._lib.libusb_get_configuration(self._dev, ctypes.byref(cfg))
        if rc != LIBUSB_SUCCESS:
            raise LibusbError(rc, "get_configuration")
        return cfg.value

    def control(self, request_type: int, request: int, value: int = 0, index: int = 0, length: int = 8, timeout_ms: int = 250) -> bytes:
        buf = ctypes.create_string_buffer(length)
        rc = self._lib.libusb_control_transfer(
            self._dev,
            ctypes.c_uint8(request_type),
            ctypes.c_uint8(request),
            ctypes.c_uint16(value),
            ctypes.c_uint16(index),
            buf,
            ctypes.c_uint16(length),
            timeout_ms,
        )
        if rc < 0:
            raise LibusbError(rc, f"control {request_type:#x}/{request:#x}")
        return buf.raw[:rc]

    def close(self) -> None:
        if getattr(self, "_dev", None):
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
