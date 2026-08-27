#!/usr/bin/env python3
"""Equal-level tones → filter playback + lid mic. Prints dB vs 500 Hz."""
from __future__ import annotations

import math
import struct
import subprocess
import time
import wave
from pathlib import Path

SR = 44100
AMP = 0.08
TONE = 0.45
GAP = 0.12
FREQS = [80, 125, 180, 280, 500, 1000, 2000, 6000, 10000]
PLAYBACK = "cs8409_speakers.playback"
MIC = "alsa_input.pci-0000_00_1f.3.analog-stereo"


def s16_tone(freq: float) -> bytes:
    n = int(SR * TONE)
    a = int(AMP * 32767)
    out = bytearray()
    for i in range(n):
        v = int(a * math.sin(2 * math.pi * freq * i / SR))
        out += struct.pack("<hh", v, v)
    return bytes(out) + (b"\x00\x00\x00\x00" * int(SR * GAP))


def goertzel(xs: list[float], freq: float) -> float:
    n = len(xs)
    if n < 32:
        return 1e-20
    k = int(0.5 + n * freq / SR)
    w = 2 * math.pi * k / n
    coeff = 2 * math.cos(w)
    s0 = s1 = s2 = 0.0
    for x in xs:
        s0 = x + coeff * s1 - s2
        s2, s1 = s1, s0
    return max(s1 * s1 + s2 * s2 - coeff * s1 * s2, 1e-20)


def db(x: float) -> float:
    return 10 * math.log10(max(x, 1e-20))


def read_wav(path: Path) -> tuple[int, list[list[float]]]:
    w = wave.open(str(path))
    ch, sw, sr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
    raw = w.readframes(n)
    fmt = "<" + ("h" if sw == 2 else "i") * ch
    step = sw * ch
    scale = 32768.0 if sw == 2 else 2147483648.0
    chs: list[list[float]] = [[] for _ in range(ch)]
    for i in range(len(raw) // step):
        tup = struct.unpack_from(fmt, raw, i * step)
        for c, v in enumerate(tup):
            chs[c].append(v / scale)
    return sr, chs


def main() -> int:
    wav = Path("/tmp/xo-tones.s16")
    wav.write_bytes(b"".join(s16_tone(f) for f in FREQS))
    out4 = Path("/tmp/xo-4ch.wav")
    outm = Path("/tmp/xo-mic.wav")
    for p in (out4, outm):
        try:
            p.unlink()
        except FileNotFoundError:
            pass
    p4 = subprocess.Popen(
        ["pw-record", "--target", PLAYBACK, "--rate", str(SR), "--channels", "4", str(out4)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    pm = subprocess.Popen(
        ["pw-record", "--target", MIC, "--rate", str(SR), "--channels", "2", str(outm)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(0.25)
    subprocess.run(
        ["paplay", "--raw", "--channels=2", f"--rate={SR}", "--format=s16le", str(wav)]
    )
    time.sleep(0.1)
    p4.terminate()
    pm.terminate()
    p4.wait(timeout=2)
    pm.wait(timeout=2)

    _, ch4 = read_wav(out4)
    _, mic = read_wav(outm)
    tw = [(a + b) * 0.5 for a, b in zip(ch4[0], ch4[1])]
    wf = [(a + b) * 0.5 for a, b in zip(ch4[2], ch4[3])]
    mm = [(a + b) * 0.5 for a, b in zip(mic[0], mic[1])]
    mix = [abs(tw[i]) + abs(wf[i]) for i in range(min(len(tw), len(wf)))]
    start = 0
    for i, v in enumerate(mix):
        if v > 1e-4:
            start = max(0, i - int(0.01 * SR))
            break
    block = int(SR * (TONE + GAP))
    tone_n = int(SR * TONE)
    print(f"{'Hz':>6} {'el-tw':>7} {'el-wf':>7} {'mic':>7}")
    mics = []
    for i, f in enumerate(FREQS):
        a = start + i * block
        b = a + tone_n
        et = db(goertzel(tw[a:b], f))
        ew = db(goertzel(wf[a:b], f))
        em = db(goertzel(mm[a:b] if mm else [0.0], f))
        mics.append(em)
        print(f"  {f:4d} {et:7.1f} {ew:7.1f} {em:7.1f}")
    ref = mics[FREQS.index(500)] if 500 in FREQS else mics[0]
    print("mic vs 500 Hz:")
    for f, m in zip(FREQS, mics):
        print(f"  {f:4d}  {m - ref:+6.1f} dB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
