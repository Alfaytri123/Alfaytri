#!/usr/bin/env python3
"""Original music bed + sound design for the ad, synthesised from scratch (no samples,
no licensed material), then mixed with the clip foley stem and loudness-normalised.

Usage: audio_design.py WORKDIR
Reads  WORKDIR/build/foley.f32 (written by compose.py)
Writes WORKDIR/audio/{music,sfx,foley,mix}.wav
"""
import json
import os
import subprocess
import sys
import wave

import numpy as np
from scipy.signal import butter, sosfilt

WORK = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
SR = 48000
DUR = 15.0
N = int(SR * DUR)
BPM = 120.0
BEAT = 60.0 / BPM
GROOVE_START = 5.0      # technician arrives: groove kicks in
END_HIT = 13.0          # end card: final chord
rng = np.random.default_rng(11)


def t_axis(sec):
    return np.arange(int(sec * SR)) / SR


def lp(x, fc, order=2):
    return sosfilt(butter(order, fc, "low", fs=SR, output="sos"), x)


def hp(x, fc, order=2):
    return sosfilt(butter(order, fc, "high", fs=SR, output="sos"), x)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "band", fs=SR, output="sos"), x)


def place(buf, sig, at, gain=1.0, pan=0.0):
    """Mix a mono signal into a stereo buffer at time `at` with constant-power pan."""
    i = int(at * SR)
    if i >= len(buf):
        return
    sig = sig[: len(buf) - i]
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[i:i + len(sig), 0] += sig * gain * l
    buf[i:i + len(sig), 1] += sig * gain * r


def env_adsr(n, a, d, s, r, sustain_len):
    a, d, r = int(a * SR), int(d * SR), int(r * SR)
    sl = max(int(sustain_len * SR), 0)
    e = np.concatenate([np.linspace(0, 1, a, endpoint=False), np.linspace(1, s, d, endpoint=False),
                        np.full(sl, s), np.linspace(s, 0, r)])
    return np.pad(e, (0, max(0, n - len(e))))[:n]


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


# ------------------------------------------------------------------ instruments
def saw(f, sec, harmonics=14, detune=0.0):
    t = t_axis(sec)
    out = np.zeros_like(t)
    for k in range(1, harmonics + 1):
        if f * k > SR / 2.2:
            break
        out += np.sin(2 * np.pi * f * k * (1 + detune) * t) / k
    return out


def pad_chord(notes, sec, bright=1800):
    sig = sum(saw(midi(n), sec, 10, d) for n in notes for d in (-0.003, 0.003))
    sig = lp(sig, bright)
    return sig * env_adsr(len(sig), 0.35, 0.3, 0.8, 0.6, sec - 1.25) / (len(notes) * 2)


def pluck(f, sec=0.45, bright=1.0):
    t = t_axis(sec)
    sig = np.zeros_like(t)
    for k in range(1, 9):
        sig += np.sin(2 * np.pi * f * k * t) * np.exp(-t * (6 + 5 * k / bright)) / k
    return sig * np.minimum(t / 0.003, 1)


def bell(f, sec=1.6):
    t = t_axis(sec)
    mod = np.sin(2 * np.pi * f * 3.5 * t) * 2.2 * np.exp(-t * 3)
    return np.sin(2 * np.pi * f * t + mod) * np.exp(-t * 2.6) * np.minimum(t / 0.002, 1)


def kick(sec=0.42):
    t = t_axis(sec)
    f = 46 + 110 * np.exp(-t * 32)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.tanh(1.6 * np.sin(ph) * np.exp(-t * 7.5))


def clap(sec=0.25):
    n = rng.normal(0, 1, int(sec * SR))
    t = t_axis(sec)
    e = np.exp(-t * 26) + 0.6 * np.exp(-((t - 0.012) * 300) ** 2) + 0.5 * np.exp(-((t - 0.024) * 300) ** 2)
    return bp(n, 900, 5200) * e * 0.8


def hat(sec=0.07, open_=False):
    n = rng.normal(0, 1, int((0.22 if open_ else sec) * SR))
    t = t_axis(len(n) / SR)
    return hp(n, 7500) * np.exp(-t * (14 if open_ else 70)) * 0.35


def sub_bass(f, sec):
    t = t_axis(sec)
    s = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)
    return np.tanh(1.3 * s) * env_adsr(len(t), 0.005, 0.08, 0.7, 0.06, sec - 0.15)


def noise_sweep(sec, f0, f1, rise=True):
    """Filtered-noise riser / whoosh with a moving band (block-wise filter sweep)."""
    n = rng.normal(0, 1, int(sec * SR))
    out = np.zeros_like(n)
    blocks = 48
    edges = np.linspace(0, len(n), blocks + 1).astype(int)
    for b in range(blocks):
        k = b / (blocks - 1)
        fc = f0 * (f1 / f0) ** k
        seg = bp(n[max(edges[b] - 512, 0):edges[b + 1]], fc * 0.6, min(fc * 1.6, SR / 2.3))
        out[edges[b]:edges[b + 1]] = seg[-(edges[b + 1] - edges[b]):]
    t = t_axis(sec)
    e = (t / sec) ** 2 if rise else np.sin(np.pi * t / sec) ** 1.5
    return out * e


# ------------------------------------------------------------------ music
def music():
    buf = np.zeros((N + SR, 2))
    # Section A (0-3s): heat. Low suspended drone + slow tick, slightly uneasy.
    drone = lp(saw(midi(38), 3.4, 8, 0.0) + saw(midi(45), 3.4, 8, 0.004) + 0.6 * saw(midi(52), 3.4, 6, -0.003), 700)
    drone *= env_adsr(len(drone), 0.6, 0.2, 0.9, 0.8, 1.8)
    place(buf, drone, 0.0, 0.22)
    for i in range(6):
        place(buf, hp(pluck(midi(81), 0.08), 2500), i * BEAT + 0.25, 0.13, 0.3 if i % 2 else -0.3)
    # Section B (3-5s): the phone. Muted arpeggio lifts the mood, riser into the groove.
    arp = [62, 66, 69, 74]
    for i in range(8):
        place(buf, lp(pluck(midi(arp[i % 4] + 12), 0.35), 3500), 3.0 + i * BEAT / 2, 0.13, 0.25 * (-1) ** i)
    place(buf, pad_chord([50, 57, 62, 66], 2.2, 1200), 3.0, 0.22)
    place(buf, noise_sweep(1.0, 300, 7000, True), GROOVE_START - 1.0, 0.10)
    # Section C (5-13s): groove, I-V-vi-IV in D major, one bar (2s) per chord.
    prog_ = [(50, [62, 66, 69]), (45, [61, 64, 69]), (47, [62, 66, 71]), (43, [62, 67, 71])]
    for bar, (root, triad) in enumerate(prog_):
        t0 = GROOVE_START + bar * 4 * BEAT
        place(buf, pad_chord(triad, 4 * BEAT + 0.3, 2200 + 600 * bar), t0, 0.20)
        for e in range(8):  # 8th-note bass
            place(buf, lp(sub_bass(midi(root - 12), BEAT / 2 * 0.9), 900), t0 + e * BEAT / 2, 0.30 if e % 2 == 0 else 0.20)
        for e in range(8):  # plucked hook
            note = triad[[0, 1, 2, 1, 2, 0, 1, 2][e]] + 12
            place(buf, lp(pluck(midi(note), 0.4), 5000), t0 + e * BEAT / 2, 0.12, 0.35 * (-1) ** e)
        for b in range(4):
            place(buf, kick(), t0 + b * BEAT, 0.55)
            if b in (1, 3):
                place(buf, clap(), t0 + b * BEAT, 0.26)
            place(buf, hat(open_=(b == 3)), t0 + b * BEAT + BEAT / 2, 0.22, 0.4)
            for g in (0.25, 0.75):  # quiet 16th ghost hats
                place(buf, hat(), t0 + b * BEAT + g * BEAT, 0.09, -0.4)
    # comfort lift at 10s: shimmer + crash-like swell
    place(buf, noise_sweep(0.5, 800, 9000, True), 9.5, 0.06)
    place(buf, hp(rng.normal(0, 1, int(1.6 * SR)), 5000) * np.exp(-t_axis(1.6) * 2.6), 10.0, 0.10)
    for i, n in enumerate([74, 78, 81, 86]):
        place(buf, bell(midi(n), 1.2), 10.0 + i * BEAT / 2, 0.07, -0.3 + 0.2 * i)
    # Section D (13-15s): resolve on D(add9) with bells, ring out.
    place(buf, kick(0.6), END_HIT, 0.6)
    place(buf, pad_chord([50, 57, 62, 64, 66, 69], 2.2, 3000), END_HIT, 0.30)
    place(buf, lp(sub_bass(midi(38), 1.6), 600), END_HIT, 0.35)
    for i, n in enumerate([74, 81, 86]):
        place(buf, bell(midi(n), 2.0), END_HIT + i * 0.09, 0.13, (-0.25, 0.0, 0.25)[i])
    m = buf[:N]
    fade = int(0.35 * SR)
    m[-fade:] *= np.linspace(1, 0, fade)[:, None] ** 1.5
    return m


# ------------------------------------------------------------------ sound effects
def sfx():
    buf = np.zeros((N + SR, 2))
    # struggling AC: low hum with irregular rattle under scene 1
    t = t_axis(3.0)
    hum = (np.sin(2 * np.pi * 98 * t) + 0.4 * np.sin(2 * np.pi * 196 * t)) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.7 * t))
    rattle = bp(rng.normal(0, 1, len(t)), 180, 900) * (np.sin(2 * np.pi * 7.3 * t) > 0.82)
    ac = lp(hum, 400) * 0.25 + rattle * 0.5
    ac *= env_adsr(len(ac), 0.3, 0.1, 1.0, 0.25, 2.3)
    place(buf, ac, 0.0, 0.22)
    place(buf, bp(rng.normal(0, 1, int(0.06 * SR)), 120, 700) * np.exp(-t_axis(0.06) * 60), 1.62, 0.5)  # clunk
    # remote clicks
    click = lambda: hp(rng.normal(0, 1, int(0.012 * SR)), 2500) * np.exp(-t_axis(0.012) * 400)
    for at in (2.32, 2.58):
        place(buf, click(), at, 0.35, 0.2)
    # frustration "dun" (low dissonant thud)
    place(buf, lp(pluck(midi(37), 0.5) + pluck(midi(38), 0.5), 600), 2.62, 0.35)
    # phone taps + UI sounds
    tap = lambda: bp(rng.normal(0, 1, int(0.02 * SR)), 1500, 6000) * np.exp(-t_axis(0.02) * 220)
    for at in (3.18, 3.42):
        place(buf, tap(), at, 0.28, -0.1)
    place(buf, noise_sweep(0.28, 1200, 6000, False), 3.62, 0.12)       # whoosh into UI
    place(buf, tap(), 4.10, 0.35)                                       # "book" tap
    for i, n in enumerate([84, 88]):                                    # confirm ding
        place(buf, bell(midi(n), 0.6), 4.32 + i * 0.08, 0.10)
    place(buf, noise_sweep(0.35, 500, 5000, False), 4.82, 0.14)        # whoosh to arrival
    # maintenance: panel click, filter slide, latch + beep, airflow
    place(buf, click(), 6.30, 0.30)
    slide = bp(rng.normal(0, 1, int(0.5 * SR)), 1800, 6000) * np.sin(np.pi * t_axis(0.5) / 0.5) ** 2
    place(buf, slide, 7.15, 0.08)
    place(buf, click(), 9.18, 0.40)
    t = t_axis(0.16)
    beep = np.sin(2 * np.pi * 2093 * t) * env_adsr(len(t), 0.004, 0.02, 0.6, 0.05, 0.08)
    place(buf, beep, 9.40, 0.10)
    air = lp(rng.normal(0, 1, int(2.6 * SR)), 1400) * env_adsr(int(2.6 * SR), 0.6, 0.2, 0.7, 0.8, 1.0)
    place(buf, air, 9.45, 0.10, -0.2)
    # payment tap + success chime
    place(buf, tap(), 12.04, 0.32)
    for i, n in enumerate([81, 85, 88]):
        place(buf, bell(midi(n), 0.9), 12.22 + i * 0.07, 0.10, (-0.2, 0, 0.2)[i])
    # end card whoosh
    place(buf, noise_sweep(0.45, 400, 6000, False), 12.75, 0.12)
    return buf[:N]


def write_wav(path, x):
    x = np.clip(x, -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())


def main():
    os.makedirs(os.path.join(WORK, "audio"), exist_ok=True)
    m, s = music(), sfx()
    foley = np.fromfile(os.path.join(WORK, "build", "foley.f32"), "<f4").reshape(-1, 2)[:N]
    foley = np.pad(foley, ((0, N - len(foley)), (0, 0)))
    foley = hp(foley.T, 70).T
    # Duck the music a little under the key story sounds (UI + payment confirmation).
    duck = np.ones(N)
    for a, b in ((4.05, 4.7), (12.0, 12.6)):
        duck[int(a * SR):int(b * SR)] = 0.75
    duck = lp(duck, 8)
    mix = m * duck[:, None] * 0.9 + s * 1.0 + foley * 0.45
    for name, x in (("music", m), ("sfx", s), ("foley", foley), ("mix_raw", mix)):
        write_wav(os.path.join(WORK, "audio", f"{name}.wav"), x / max(1e-6, np.abs(x).max()) * 0.89)
    # Two-pass EBU R128 loudness normalisation for social: -14 LUFS, -1 dBTP.
    raw = os.path.join(WORK, "audio", "mix_raw.wav")
    out = os.path.join(WORK, "audio", "mix.wav")
    p = subprocess.run(["ffmpeg", "-hide_banner", "-i", raw, "-af", "loudnorm=I=-14:TP=-1.0:LRA=9:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True)
    st = json.loads(p.stderr[p.stderr.rfind("{"):p.stderr.rfind("}") + 1])
    af = (f"loudnorm=I=-14:TP=-1.0:LRA=9:measured_I={st['input_i']}:measured_TP={st['input_tp']}:"
          f"measured_LRA={st['input_lra']}:measured_thresh={st['input_thresh']}:offset={st['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", af, "-ar", str(SR), out], check=True)
    print("audio done", st["input_i"], "->", "-14 LUFS")


if __name__ == "__main__":
    main()
