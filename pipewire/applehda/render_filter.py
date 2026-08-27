#!/usr/bin/env python3
"""Render PipeWire filter-chain from layout57.json.

Stereo sink cs8409_speakers → 4ch analog-surround-40.
Uses builtin bq_* nodes (param_eq In 2 / fan-out dropped the woofers).
Not Mozart, BuzzKill, ControlFreak, or thermal. Clamp is the limiter.

    python3 render_filter.py            # invert on (flatter 1 kHz on this cabinet)
    python3 render_filter.py --no-invert
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAYOUT = Path(__file__).resolve().parent / "layout57.json"
OUT = ROOT / "60-cs8409-crossover.conf"

BQ = {
    "lowpass": "bq_lowpass",
    "highpass": "bq_highpass",
    "peaking": "bq_peaking",
    "notch": "bq_notch",
}
PASS_TYPES = {"lowpass", "highpass"}


def chain_by_key(data: dict) -> dict:
    return {c["key"]: c for c in data["chain"]}


def bands(fn: dict) -> list[dict]:
    return list(fn.get("bands_l") or [])


def spa_type(b: dict) -> str:
    t = b["type"]
    if t == "notch" and abs(float(b["gain_db"])) > 0.5:
        return "bq_peaking"
    return BQ.get(t, "bq_peaking")


def spa_gain(b: dict) -> float:
    if b["type"] in PASS_TYPES:
        return 0.0
    return float(b["gain_db"])


def rows_from(items: list[dict], extra_head=None, extra_tail=None) -> list[dict]:
    rows = list(extra_head or [])
    for b in items:
        if b["type"] == "peaking" and abs(float(b["gain_db"])) < 0.05:
            continue
        rows.append(
            {
                "label": spa_type(b),
                "freq": float(b["freq_hz"]),
                "q": float(b["q"]),
                "gain": spa_gain(b),
            }
        )
    rows.extend(extra_tail or [])
    return rows


def bq_node(name: str, row: dict) -> str:
    return (
        "                    {\n"
        f"                        name = {name}\n"
        "                        type = builtin\n"
        f"                        label = {row['label']}\n"
        f'                        control = {{ "Freq" = {row["freq"]:.4f} '
        f'"Q" = {row["q"]:.4f} "Gain" = {row["gain"]:.3f} }}\n'
        "                    }"
    )


def series(prefix: str, rows: list[dict], src: str) -> tuple[list[str], list[str], str]:
    """Chain bq nodes. Returns (nodes, links, last_port)."""
    nodes, links = [], []
    prev = src
    for i, row in enumerate(rows):
        name = f"{prefix}{i}"
        nodes.append(bq_node(name, row))
        links.append(f'                    {{ output = "{prev}" input = "{name}:In" }}')
        prev = f"{name}:Out"
    return nodes, links, prev


def clamp(name: str) -> str:
    return (
        "                    {\n"
        f"                        name = {name}\n"
        "                        type = builtin\n"
        "                        label = clamp\n"
        '                        control = { "Min" = -0.98 "Max" = 0.98 }\n'
        "                    }"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--invert",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="invert woofers (default on: 1 kHz hole is smaller than --no-invert)",
    )
    args = ap.parse_args()
    invert = bool(args.invert)

    data = json.loads(LAYOUT.read_text())
    c = chain_by_key(data)
    pre = rows_from(
        bands(c["DspFunction0"]) + bands(c["DspFunction3"]) + bands(c["DspFunction5"]),
        extra_head=[{"label": "bq_highshelf", "freq": 0.0, "q": 1.0, "gain": -6.0}],
        extra_tail=[{"label": "bq_highshelf", "freq": 0.0, "q": 1.0, "gain": 1.5}],
    )
    tw = rows_from(bands(c["DspFunction8"]))
    wf = rows_from(bands(c["DspFunction9"]))

    nodes = [
        "                    { name = copyIL type = builtin label = copy }",
        "                    { name = copyIR type = builtin label = copy }",
        "                    { name = splitL type = builtin label = copy }",
        "                    { name = splitR type = builtin label = copy }",
        clamp("clTwL"),
        clamp("clTwR"),
        clamp("clWfL"),
        clamp("clWfR"),
    ]
    links: list[str] = []
    n, l, preL_out = series("preL", pre, "copyIL:Out")
    nodes.extend(n)
    links.extend(l)
    n, l, preR_out = series("preR", pre, "copyIR:Out")
    nodes.extend(n)
    links.extend(l)

    links += [
        f'                    {{ output = "{preL_out}" input = "splitL:In" }}',
        f'                    {{ output = "{preR_out}" input = "splitR:In" }}',
    ]

    n, l, twL_out = series("twL", tw, "splitL:Out")
    nodes.extend(n)
    links.extend(l)
    n, l, twR_out = series("twR", tw, "splitR:Out")
    nodes.extend(n)
    links.extend(l)
    n, l, wfL_out = series("wfL", wf, "splitL:Out")
    nodes.extend(n)
    links.extend(l)
    n, l, wfR_out = series("wfR", wf, "splitR:Out")
    nodes.extend(n)
    links.extend(l)

    if invert:
        nodes += [
            "                    { name = invL type = builtin label = invert }",
            "                    { name = invR type = builtin label = invert }",
        ]
        wfL_to_clamp = [
            f'                    {{ output = "{wfL_out}" input = "invL:In" }}',
            f'                    {{ output = "{wfR_out}" input = "invR:In" }}',
            '                    { output = "invL:Out" input = "clWfL:In" }',
            '                    { output = "invR:Out" input = "clWfR:In" }',
        ]
        invert_note = "Woofer invert ON (LR4-era acoustic)."
    else:
        wfL_to_clamp = [
            f'                    {{ output = "{wfL_out}" input = "clWfL:In" }}',
            f'                    {{ output = "{wfR_out}" input = "clWfR:In" }}',
        ]
        invert_note = "Woofer invert OFF (Apple staggered HP/LP; measure 1 kHz)."

    links += [
        f'                    {{ output = "{twL_out}" input = "clTwL:In" }}',
        f'                    {{ output = "{twR_out}" input = "clTwR:In" }}',
    ]
    links += wfL_to_clamp

    # series() already linked copyIL→preL0; drop the duplicate we skipped.

    text = f"""# Generated by applehda/render_filter.py from layout57.json.
# MacBookPro14,3: stereo sink → 4ch MAX98706. Do not edit by hand.
#
# Keep davidjo for amp/TDM. Builtin bq_* (param_eq dropped RL/RR).
# Not Mozart / BuzzKill / ControlFreak / thermal. Clamp is the limiter.
# {invert_note}
# Parked 800 Hz LR4: 60-cs8409-lr4.conf
context.modules = [
    {{ name = libpipewire-module-filter-chain
        flags = [ nofail ]
        args = {{
            node.description = "MacBook speakers"
            media.name       = "MacBook speakers"
            filter.graph = {{
                nodes = [
{chr(10).join(nodes)}
                ]
                links = [
{chr(10).join(links)}
                ]
                inputs  = [ "copyIL:In" "copyIR:In" ]
                outputs = [ "clTwL:Out" "clTwR:Out" "clWfL:Out" "clWfR:Out" ]
            }}
            capture.props = {{
                node.name             = "cs8409_speakers"
                node.description      = "MacBook speakers"
                media.class           = "Audio/Sink"
                audio.position        = [ FL FR ]
                audio.channels        = 2
                audio.rate            = 44100
                channelmix.disable    = true
                priority.session      = 1400
                priority.driver       = 1400
            }}
            playback.props = {{
                node.name             = "cs8409_speakers.playback"
                media.class           = "Stream/Output/Audio"
                audio.position        = [ FL FR RL RR ]
                audio.channels        = 4
                audio.rate            = 44100
                stream.dont-remix     = true
                channelmix.disable    = true
                node.passive          = true
                node.dont-fallback    = true
                target.object         = "alsa_output.pci-0000_00_1f.3.analog-surround-40"
            }}
        }}
    }}
]
"""
    OUT.write_text(text)
    print("wrote", OUT, "nodes", len(nodes), "links", len(links))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
