#!/usr/bin/env python3
"""Play equal-level tones into cs8409_speakers; measure 4ch split + mic."""
from __future__ import annotations

import math
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SR = 44100
AMP = 0.07  # digital, on top of whatever the sink fader is
TONE = 0.40
GAP = 0.12
FREQS = [
    80, 125, 200, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500, 3150, 4000, 6300, 8000,
]
# The ALSA 4ch monitor remixes RL/RR to silence. Record the filter
# playback node instead (true FL/FR/RL/RR after the crossover).
SINK_MON = "cs8409_speakers.playback"
MIC = "alsa_input.pci-0000_00_1f.3.analog-stereo"


def s16_tone(freq: float, seconds: float, amp: float = AMP) -> bytes:
    n = int(SR * seconds)
    a = int(amp * 32767)
    out = bytearray()
    for i in range(n):
        v = int(a * math.sin(2 * math.pi * freq * i / SR))
        out += struct.pack("<hh", v, v)
    return bytes(out)


def s16_silence(seconds: float) -> bytes:
    n = int(SR * seconds)
    return b"\x00\x00\x00\x00" * n


def goertzel(samples: list[float], freq: float, sr: int = SR) -> float:
    n = len(samples)
    if n < 32:
        return 0.0
    k = int(0.5 + n * freq / sr)
    w = 2 * math.pi * k / n
    coeff = 2 * math.cos(w)
    s0 = s1 = s2 = 0.0
    for x in samples:
        s0 = x + coeff * s1 - s2
        s2, s1 = s1, s0
    power = s1 * s1 + s2 * s2 - coeff * s1 * s2
    return max(power, 1e-20)


def db(x: float) -> float:
    return 10 * math.log10(max(float(x), 1e-20))


def read_s32_ch(path: Path, channels: int) -> list[list[float]]:
    raw = path.read_bytes()
    n = len(raw) // (4 * channels)
    ch = [[] for _ in range(channels)]
    off = 0
    for _ in range(n):
        for c in range(channels):
            (v,) = struct.unpack_from("<i", raw, off)
            ch[c].append(v / 2147483648.0)
            off += 4
    return ch


def read_wav_ch(path: Path) -> list[list[float]]:
    import wave

    w = wave.open(str(path), "rb")
    channels, sw, n = w.getnchannels(), w.getsampwidth(), w.getnframes()
    raw = w.readframes(n)
    fmt = "<" + ("h" if sw == 2 else "i") * channels
    step = sw * channels
    scale = 32768.0 if sw == 2 else 2147483648.0
    ch = [[] for _ in range(channels)]
    for i in range(len(raw) // step):
        tup = struct.unpack_from(fmt, raw, i * step)
        for c, v in enumerate(tup):
            ch[c].append(v / scale)
    return ch


def rms(xs: list[float]) -> float:
    if not xs:
        return 0.0
    return math.sqrt(sum(x * x for x in xs) / len(xs) + 1e-20)


def rec(device: str, dest: Path, channels: int) -> subprocess.Popen:
    dest.write_bytes(b"")
    if device.endswith(".playback"):
        return subprocess.Popen(
            [
                "pw-record",
                "--target",
                device,
                "--rate",
                str(SR),
                "--channels",
                str(channels),
                str(dest.with_suffix(".wav")),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    return subprocess.Popen(
        [
            "parecord",
            "--raw",
            f"--channels={channels}",
            f"--rate={SR}",
            "--format=s32le",
            f"--device={device}",
            str(dest),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main() -> int:
    tones = b"".join(s16_tone(f, TONE) + s16_silence(GAP) for f in FREQS)
    wav = Path(tempfile.gettempdir()) / "cs8409-sweep.s16"
    wav.write_bytes(tones)
    ch4p = Path(tempfile.gettempdir()) / "cs8409-sweep-4ch.s32"
    micp = Path(tempfile.gettempdir()) / "cs8409-sweep-mic.s32"
    p4 = rec(SINK_MON, ch4p, 4)
    pm = rec(MIC, micp, 2)
    time.sleep(0.15)
    play = subprocess.run(
        [
            "paplay",
            "--raw",
            "--channels=2",
            f"--rate={SR}",
            "--format=s16le",
            str(wav),
        ]
    )
    time.sleep(0.1)
    p4.terminate()
    pm.terminate()
    p4.wait(timeout=2)
    pm.wait(timeout=2)
    if play.returncode != 0:
        print("paplay failed", play.returncode, file=sys.stderr)
        return 1

    wav4 = ch4p.with_suffix(".wav")
    ch4 = read_wav_ch(wav4) if wav4.exists() and wav4.stat().st_size > 44 else read_s32_ch(ch4p, 4)
    mic = read_s32_ch(micp, 2)
    mic_m = [(a + b) * 0.5 for a, b in zip(mic[0], mic[1])] if mic[0] else []
    block = int(SR * (TONE + GAP))
    tone_n = int(SR * TONE)
    # skip recorder preroll: align by finding first energy in ch4
    start = 0
    thresh = 1e-4
    mix = [sum(abs(ch4[c][i]) for c in range(4)) for i in range(len(ch4[0]))]
    for i, v in enumerate(mix):
        if v > thresh:
            start = max(0, i - int(0.01 * SR))
            break

    print(f"{'Hz':>6} {'twL':>7} {'twR':>7} {'wfL':>7} {'wfR':>7} {'tw/wf':>7} {'micdB':>7}")
    mic_db = []
    for i, f in enumerate(FREQS):
        a = start + i * block
        b = a + tone_n
        tw = rms(ch4[0][a:b]) + rms(ch4[1][a:b])
        wf = rms(ch4[2][a:b]) + rms(ch4[3][a:b])
        ratio = tw / (wf + 1e-12)
        g = goertzel(mic_m[a:b], f) if mic_m else 1e-20
        mdb = db(g)
        mic_db.append(mdb)
        print(
            f"{f:6d} {db(rms(ch4[0][a:b]) ** 2 + 1e-20):7.1f} "
            f"{db(rms(ch4[1][a:b]) ** 2 + 1e-20):7.1f} "
            f"{db(rms(ch4[2][a:b]) ** 2 + 1e-20):7.1f} "
            f"{db(rms(ch4[3][a:b]) ** 2 + 1e-20):7.1f} "
            f"{ratio:7.2f} {mdb:7.1f}"
        )
    # relative to 500 Hz
    if 500 in FREQS:
        ref = mic_db[FREQS.index(500)]
        print("\nmic vs 500 Hz:")
        for f, m in zip(FREQS, mic_db):
            print(f"  {f:5d}  {m - ref:+6.1f} dB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
