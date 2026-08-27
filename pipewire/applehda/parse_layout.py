#!/usr/bin/env python3
"""Inflate AppleHDA layout*.xml.zlib and dump DspEqualization32 biquads.

Filter types (taprobane99 / 2017 4-speaker iMac notebook):
  0 low-pass, 1 high-pass, 4 bell, 6 notch
Band keys: 2=channel (0 L, 1 R), 5=type, 6=freq, 7=Q, 8=gain dB
  (IEEE-754 float stored as uint32).
"""
from __future__ import annotations

import argparse, json, os, plistlib, struct, sys, zlib
from pathlib import Path

FILTER = {
    0: "lowpass",
    1: "highpass",
    4: "peaking",
    6: "notch",
}

ROLE = {
    "DspFunction0": "Global_PreEQ",
    "DspFunction1": "Global_Comp",
    "DspFunction3": "Multiband_Comp",
    "DspFunction8": "WooferSym",
    "DspFunction9": "TweeterSym",
    "DspFunction10": "WooferAsym",
    "DspFunction11": "TweeterAsym",
}


def u32_to_f32(v: int) -> float:
    return struct.unpack("!f", struct.pack("!I", v & 0xFFFFFFFF))[0]


def inflate(path: Path) -> bytes:
    data = path.read_bytes()
    if data[:5] in (b"<?xml", b"<plis") or data[:6] == b"<?xml ":
        return data
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


def dsp_role(name: str) -> str:
    for key, role in sorted(ROLE.items(), key=lambda kv: -len(kv[0])):
        if key in name:
            return role
    return "Other"


def walk(node, parent: str, out: list):
    if isinstance(node, dict):
        params = node.get("ParameterInfo")
        if isinstance(params, dict) and "Filter" in params:
            for band in params["Filter"]:
                if not isinstance(band, dict):
                    continue
                ch = int(band.get("2", 0) or 0)
                typ = int(band.get("5", 4) or 4)
                freq = u32_to_f32(int(band.get("6", 0) or 0))
                q = u32_to_f32(int(band.get("7", 0) or 0))
                gain = u32_to_f32(int(band.get("8", 0) or 0))
                out.append(
                    {
                        "block": parent,
                        "role": dsp_role(parent),
                        "channel": "R" if ch == 1 else "L",
                        "type_id": typ,
                        "type": FILTER.get(typ, f"unknown_{typ}"),
                        "freq_hz": round(freq, 2),
                        "q": round(q, 4),
                        "gain_db": round(gain, 3),
                    }
                )
        for k, v in node.items():
            walk(v, str(k), out)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            walk(item, f"{parent}[{i}]", out)


def score_layout(text: str) -> dict:
    keys = ("Tweeter", "Woofer", "IntSpeaker", "DspEqualization32", "Merry", "FG", "MacBook")
    return {k: text.count(k) for k in keys}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("raw_dir", type=Path)
    ap.add_argument("-o", "--out", type=Path, default=None)
    args = ap.parse_args()
    raw_dir: Path = args.raw_dir
    files = sorted(raw_dir.glob("layout*.xml.zlib")) + sorted(raw_dir.glob("Layout*.xml.zlib"))
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
        bands: list = []
        try:
            plist = load_plist(f)
            walk(plist, "Root", bands)
        except Exception as e:
            sc["parse_error"] = str(e)
        report.append(
            {
                "file": f.name,
                "size": f.stat().st_size,
                "score": sc,
                "n_bands": len(bands),
                "roles": sorted({b["role"] for b in bands}),
                "bands": bands,
            }
        )
    # Prefer 4-speaker layouts with woofer+tweeter EQ
    def rank(r):
        s = r.get("score") or {}
        return (
            s.get("Woofer", 0) + s.get("Tweeter", 0),
            r.get("n_bands", 0),
            s.get("DspEqualization32", 0),
        )

    ranked = sorted([r for r in report if "error" not in r], key=rank, reverse=True)
    out = {
        "codec_hint": {"vendor": "0x10138409", "subsystem": "0x106b3900", "dmi": "MacBookPro14,3"},
        "ranked": [
            {
                "file": r["file"],
                "n_bands": r["n_bands"],
                "score": r["score"],
                "roles": r["roles"],
            }
            for r in ranked[:15]
        ],
        "layouts": {r["file"]: r for r in report},
    }
    dest = args.out or (raw_dir.parent / "parsed.json")
    dest.write_text(json.dumps(out, indent=2))
    print("wrote", dest)
    print("top candidates:")
    for r in ranked[:8]:
        print(f"  {r['file']:20} bands={r['n_bands']:4} score={r['score']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
