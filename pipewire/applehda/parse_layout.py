#!/usr/bin/env python3
"""Inflate AppleHDA layout*.xml.zlib and dump SoftwareDSP.

Filter types (taprobane99 / 2017 4-speaker notebooks):
  0 low-pass, 1 high-pass, 4 bell, 6 notch
Band keys: 2=channel (0 L, 1 R), 5=type, 6=freq, 7=Q, 8=gain dB
  (IEEE-754 float stored as uint32).

Do not commit AppleHDA.kext. Distill coefficients only:

    python3 parse_layout.py raw --layout 57 -o layout57.json
"""
from __future__ import annotations

import argparse, json, plistlib, struct, sys
from pathlib import Path

FILTER = {
    0: "lowpass",
    1: "highpass",
    4: "peaking",
    6: "notch",
}

VENDOR = {
    262144: "FG",       # 0x40000
    524288: "GGEC",     # 0x80000
    589824: "GTK",      # 0x90000
    786432: "Merry",    # 0xC0000
}


def u32_to_f32(v: int) -> float:
    return struct.unpack("!f", struct.pack("!I", int(v) & 0xFFFFFFFF))[0]


def as_floatish(v):
    if isinstance(v, int) and v > 1000:
        f = u32_to_f32(v)
        if f == f and abs(f) < 1e7:
            return round(f, 6)
    return v


def inflate(path: Path) -> bytes:
    data = path.read_bytes()
    if data[:5] in (b"<?xml", b"<plis") or data[:6] == b"<?xml ":
        return data
    import zlib

    return zlib.decompress(data)


def load_plist(path: Path):
    raw = inflate(path)
    if not raw.strip().startswith(b"<?xml") and not raw.strip().startswith(b"<plist"):
        raw = (
            b'<?xml version="1.0" encoding="UTF-8"?>\n'
            b'<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
            b'"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            b'<plist version="1.0">\n' + raw + b"\n</plist>"
        )
    return plistlib.loads(raw)


def _int(d: dict, key: str, default: int) -> int:
    v = d.get(key, default)
    if v is None:
        return default
    return int(v)


def band_from(d: dict) -> dict:
    typ = _int(d, "5", 4)
    return {
        "channel": "R" if _int(d, "2", 0) == 1 else "L",
        "type_id": typ,
        "type": FILTER.get(typ, f"unknown_{typ}"),
        "freq_hz": round(u32_to_f32(_int(d, "6", 0)), 2),
        "q": round(u32_to_f32(_int(d, "7", 0)), 4),
        "gain_db": round(u32_to_f32(_int(d, "8", 0)), 3),
        "slot": _int(d, "3", 0),
    }


def eq_role(name: str, bands: list[dict]) -> str:
    types = {b["type"] for b in bands}
    if "highpass" in types and "lowpass" not in types and any(
        b["freq_hz"] >= 400 for b in bands if b["type"] == "highpass"
    ):
        return "tweeter_crossover_eq"
    if "lowpass" in types and "highpass" not in types:
        return "woofer_crossover_eq"
    if name.endswith("0") or (len(bands) <= 4 and "highpass" in types):
        return "protection_hpf" if "highpass" in types else "global_pre_eq"
    if len(bands) >= 8:
        return "global_peq"
    return "eq"


def dump_function(key: str, fn: dict) -> dict:
    info = fn.get("FunctionInfo") or {}
    params = fn.get("ParameterInfo") or {}
    bands = []
    if isinstance(params, dict) and isinstance(params.get("Filter"), list):
        bands = [band_from(b) for b in params["Filter"] if isinstance(b, dict)]
    scalars = {
        str(k): as_floatish(v)
        for k, v in params.items()
        if k != "Filter" and not isinstance(v, (dict, list))
    }
    name = info.get("DspFuncName") or key
    out = {
        "key": key,
        "name": name,
        "instance": info.get("DspFuncInstance"),
        "index": info.get("DspFuncProcessingIndex"),
    }
    if bands:
        out["role"] = eq_role(key, bands)
        out["bands"] = bands
        # L==R on this machine; keep L as the recipe
        left = [b for b in bands if b["channel"] == "L"]
        if left and len(left) * 2 == len(bands):
            out["bands_l"] = [{k: v for k, v in b.items() if k != "channel"} for b in left]
    elif scalars:
        out["params"] = scalars
    return out


def distill_layout(path: Path) -> dict:
    pl = load_plist(path)
    pm = (pl.get("PathMapRef") or [None])[0] or {}
    spk = pm.get("IntSpeaker") or {}
    vendors = []
    for row in ((spk.get("Vendors") or {}).get("Speaker") or []):
        vid = int(row.get("Vendor") or 0)
        vendors.append(
            {
                "id": vid,
                "hex": hex(vid),
                "name": VENDOR.get(vid, "unknown"),
                "hardware_id": row.get("HardwareID"),
            }
        )
    dsp = {}
    sp_list = spk.get("SignalProcessing") or []
    if sp_list and isinstance(sp_list[0], dict):
        dsp = (sp_list[0].get("SoftwareDSP")) or {}
    chain = []
    for key in sorted(dsp, key=lambda s: (len(s), s)):
        if isinstance(dsp[key], dict) and "FunctionInfo" in dsp[key]:
            chain.append(dump_function(key, dsp[key]))
    tdm = []
    for d in pm.get("TDMDevices") or []:
        if isinstance(d, dict) and d.get("Device"):
            tdm.append(int(d["Device"]))
    comments = []
    text = inflate(path).decode("utf-8", "replace")
    import re

    for c in re.findall(r"<!--(.*?)-->", text, re.S):
        s = " ".join(c.split()).strip()
        if s:
            comments.append(s)
    return {
        "file": path.name,
        "layout_id": pl.get("LayoutID"),
        "path_map_id": pm.get("PathMapID"),
        "codec_id": (pm.get("CodecID") or [None])[0],
        "tdm_devices": tdm,
        "vendors": vendors,
        "signal_processing_ids": spk.get("SignalProcessingIDs"),
        "default_volume_raw": spk.get("DefaultVolume"),
        "maximum_boot_beep": spk.get("MaximumBootBeepValue"),
        "xml_comments": comments,
        "chain": chain,
    }


def score_layout(text: str) -> dict:
    keys = (
        "Tweeter",
        "Woofer",
        "IntSpeaker",
        "DspEqualization32",
        "MAX98706",
        "TAS5764",
        "SSM3515",
        "Merry",
        "GTK",
        "FG",
    )
    return {k: text.count(k) for k in keys}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("raw_dir", type=Path)
    ap.add_argument("-o", "--out", type=Path, default=None)
    ap.add_argument("--layout", type=int, default=None, help="distill one layout-id")
    args = ap.parse_args()
    raw_dir: Path = args.raw_dir

    if args.layout is not None:
        path = raw_dir / f"layout{args.layout}.xml.zlib"
        if not path.exists():
            print("missing", path, file=sys.stderr)
            return 1
        distilled = distill_layout(path)
        distilled["codec_hint"] = {
            "vendor": "0x10138409",
            "subsystem": "0x106b3900",
            "dmi": "MacBookPro14,3",
            "amp": "MAX98706",
        }
        dest = args.out or (raw_dir.parent / f"layout{args.layout}.json")
        dest.write_text(json.dumps(distilled, indent=2) + "\n")
        print("wrote", dest)
        print("layout", distilled["layout_id"], "pathmap", distilled["path_map_id"])
        print("vendors", distilled["vendors"])
        for fn in distilled["chain"]:
            extra = ""
            if "bands_l" in fn:
                extra = f" L-bands={len(fn['bands_l'])} role={fn.get('role')}"
            elif "params" in fn:
                extra = f" params={len(fn['params'])}"
            print(f"  {fn['key']:16} {fn['name']}{extra}")
        return 0

    files = sorted(raw_dir.glob("layout*.xml.zlib")) + sorted(
        raw_dir.glob("Layout*.xml.zlib")
    )
    if not files:
        print("no layout*.xml.zlib in", raw_dir, file=sys.stderr)
        return 1
    report = []
    for f in files:
        try:
            blob = inflate(f)
            text = blob.decode("utf-8", "replace")
        except Exception as e:
            report.append({"file": f.name, "error": str(e)})
            continue
        sc = score_layout(text)
        names: list[str] = []
        n_bands = 0
        try:
            d = distill_layout(f)
            names = [c["name"] for c in d["chain"]]
            n_bands = sum(len(c.get("bands") or []) for c in d["chain"])
        except Exception as e:
            sc["parse_error"] = str(e)
        report.append(
            {
                "file": f.name,
                "size": f.stat().st_size,
                "score": sc,
                "n_bands": n_bands,
                "dsp": names,
            }
        )

    def rank(r):
        s = r.get("score") or {}
        return (
            s.get("MAX98706", 0),
            s.get("Woofer", 0) + s.get("Tweeter", 0),
            r.get("n_bands", 0),
            s.get("DspEqualization32", 0),
        )

    ranked = sorted([r for r in report if "error" not in r], key=rank, reverse=True)
    out = {
        "codec_hint": {
            "vendor": "0x10138409",
            "subsystem": "0x106b3900",
            "dmi": "MacBookPro14,3",
        },
        "ranked": ranked[:15],
        "layouts": {r["file"]: r for r in report},
    }
    dest = args.out or (raw_dir.parent / "parsed.json")
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print("wrote", dest)
    print("top candidates:")
    for r in ranked[:8]:
        print(f"  {r['file']:20} bands={r['n_bands']:4} score={r['score']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
