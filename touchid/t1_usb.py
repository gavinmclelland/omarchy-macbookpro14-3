"""Locate the T1 KernelRelayHost / SEP USB interface on iBridge 05ac:8600.

KernelRelayHost.kext IOKit personality (OCLP KernelRelayHost-v1.0.0):
  IOUSBHostInterface, idVendor=0x05ac, class=0xff subclass=0xf9 protocol=0x11

On this chassis that interface is USB configuration 2, interface 7
(bulk OUT 0x05, bulk IN 0x88). It does not exist in configuration 1
(keyboard-mode Touch Bar). Switching configuration is a separate,
privileged step — this module only parses descriptors.
"""

from __future__ import annotations

from dataclasses import dataclass

APPLE_VID = 0x05AC
IBRIDGE_PID = 0x8600
SEP_CLASS = 0xFF
SEP_SUBCLASS = 0xF9
SEP_PROTOCOL = 0x11

DT_DEVICE = 1
DT_CONFIG = 2
DT_INTERFACE = 4
DT_ENDPOINT = 5


@dataclass(frozen=True)
class Endpoint:
    addr: int
    attributes: int
    max_packet: int

    @property
    def is_bulk(self) -> bool:
        return (self.attributes & 0x03) == 2

    @property
    def is_in(self) -> bool:
        return bool(self.addr & 0x80)


@dataclass(frozen=True)
class Interface:
    number: int
    alt: int
    if_class: int
    subclass: int
    protocol: int
    endpoints: tuple[Endpoint, ...]


@dataclass(frozen=True)
class Configuration:
    value: int
    interfaces: tuple[Interface, ...]


@dataclass(frozen=True)
class SepInterface:
    config: int
    interface: int
    ep_out: int
    ep_in: int


def parse_descriptors(raw: bytes) -> tuple[int, int, list[Configuration]]:
    """Return (idVendor, idProduct, configurations) from a sysfs descriptors blob."""
    vid = pid = 0
    configs: list[Configuration] = []
    cur: dict | None = None
    ifaces: list[Interface] = []
    iface: dict | None = None

    def flush_iface() -> None:
        nonlocal iface
        if iface is None:
            return
        ifaces.append(
            Interface(
                iface["number"],
                iface["alt"],
                iface["class"],
                iface["subclass"],
                iface["protocol"],
                tuple(iface["eps"]),
            )
        )
        iface = None

    i = 0
    n = len(raw)
    while i + 1 < n:
        length = raw[i]
        dtype = raw[i + 1]
        if length < 2 or i + length > n:
            break
        data = raw[i : i + length]
        if dtype == DT_DEVICE and length >= 18:
            vid = int.from_bytes(data[8:10], "little")
            pid = int.from_bytes(data[10:12], "little")
        elif dtype == DT_CONFIG and length >= 9:
            flush_iface()
            if cur is not None:
                configs.append(Configuration(cur["value"], tuple(ifaces)))
            ifaces = []
            cur = {"value": data[5]}
        elif dtype == DT_INTERFACE and length >= 9:
            flush_iface()
            iface = {
                "number": data[2],
                "alt": data[3],
                "class": data[5],
                "subclass": data[6],
                "protocol": data[7],
                "eps": [],
            }
        elif dtype == DT_ENDPOINT and length >= 7 and iface is not None:
            mps = int.from_bytes(data[4:6], "little")
            iface["eps"].append(Endpoint(data[2], data[3], mps))
        i += length
    flush_iface()
    if cur is not None:
        configs.append(Configuration(cur["value"], tuple(ifaces)))
    return vid, pid, configs


def find_sep_interface(raw: bytes) -> SepInterface:
    vid, pid, configs = parse_descriptors(raw)
    if vid != APPLE_VID or pid != IBRIDGE_PID:
        raise LookupError(f"not iBridge (got {vid:04x}:{pid:04x})")
    for cfg in configs:
        for iface in cfg.interfaces:
            if (
                iface.alt == 0
                and iface.if_class == SEP_CLASS
                and iface.subclass == SEP_SUBCLASS
                and iface.protocol == SEP_PROTOCOL
            ):
                bulk = [e for e in iface.endpoints if e.is_bulk]
                outs = [e.addr for e in bulk if not e.is_in]
                ins = [e.addr for e in bulk if e.is_in]
                if not outs or not ins:
                    continue
                return SepInterface(cfg.value, iface.number, outs[0], ins[0])
    raise LookupError("KernelRelayHost SEP interface ff/f9/11 not in descriptors")


def sep_in_config(raw: bytes, config_value: int) -> bool:
    vid, pid, configs = parse_descriptors(raw)
    if vid != APPLE_VID or pid != IBRIDGE_PID:
        return False
    for cfg in configs:
        if cfg.value != config_value:
            continue
        for iface in cfg.interfaces:
            if (
                iface.if_class == SEP_CLASS
                and iface.subclass == SEP_SUBCLASS
                and iface.protocol == SEP_PROTOCOL
            ):
                return True
    return False
