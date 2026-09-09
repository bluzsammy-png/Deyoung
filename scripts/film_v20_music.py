#!/usr/bin/env python3
"""DeYoung film v20 — synth a light 106 BPM lo-fi bounce bed (21s, 48k stereo).

Same instrument recipe as the shipped film_v3_music.py (kick+hat+bass+pluck arp),
scaled to a 20s UGC cut: Am7 / Fmaj7 / C / G loop, soft end shimmer at 19s.
Output: campaign/film/v20/audio/music.wav  (mixed quiet under VO at assemble time)
"""
import numpy as np
import wave

SR = 48000
BPM = 106.0
BEAT = 60.0 / BPM
BAR = BEAT * 4
TOTAL = 21.0
N = int(SR * TOTAL)
rng = np.random.default_rng(20)
mix = np.zeros(N)


def add(sig, at_s):
    i = int(at_s * SR)
    j = min(N, i + len(sig))
    if j > i:
        mix[i:j] += sig[: j - i]


def env(n, a, d, r=0.05):
    t = np.arange(n) / SR
    e = np.clip(t / max(a, 1e-4), 0, 1)
    e *= np.exp(-np.maximum(t - a, 0) / max(d, 1e-4) * 3.0)
    return e[:n]


def kick():
    n = int(0.28 * SR)
    t = np.arange(n) / SR
    f = np.linspace(150, 44, n)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return 0.9 * np.sin(ph) * np.exp(-t * 20)


def hat(open_=False):
    n = int((0.12 if open_ else 0.045) * SR)
    t = np.arange(n) / SR
    x = np.diff(rng.uniform(-1, 1, n), prepend=0)
    return 0.16 * x * np.exp(-t * (22 if open_ else 95))


def bass(freq, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(4 * np.pi * freq * t)
    return 0.34 * x * env(n, 0.006, dur * 0.85)


def pluck(freq, dur=0.24):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * freq * t) + 0.4 * np.sin(4 * np.pi * freq * t)
         + 0.15 * np.sin(6 * np.pi * freq * t))
    return 0.20 * x * env(n, 0.003, dur * 0.7)


def shimmer(freqs, dur=1.8):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = sum(np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) for f in freqs)
    return 0.10 * x * env(n, 0.01, dur * 0.55)


# Am7 / Fmaj7 / C / G — root freqs + arp notes
CHORDS = [
    (55.00, [220.00, 261.63, 329.63, 392.00]),   # A2  Am7
    (43.65, [174.61, 220.00, 261.63, 329.63]),   # F1  Fmaj7
    (65.41, [261.63, 329.63, 392.00, 523.25]),   # C2  C
    (49.00, [196.00, 246.94, 293.66, 392.00]),   # G1  G
]

n_bars = int(np.ceil(TOTAL / BAR))
for bar in range(n_bars):
    t0 = bar * BAR
    root, arp = CHORDS[bar % 4]
    # kick on 1 and 3, soft
    add(kick(), t0)
    add(kick(), t0 + 2 * BEAT)
    # hats on 8ths (swing the off-beat slightly later, quieter)
    for e in range(8):
        sw = 0.02 if e % 2 else 0.0
        add(hat(open_=(e == 7)), t0 + e * BEAT / 2 + sw)
    # bass: root on 1, octave/fifth stab on 3.5
    add(bass(root, BEAT * 1.8), t0)
    add(bass(root * 1.5, BEAT * 0.9), t0 + 3.5 * BEAT)
    # pluck arp 8ths
    for e in range(8):
        note = arp[e % 4] * (2 if e in (3, 7) else 1)
        add(pluck(note), t0 + e * BEAT / 2 + 0.01)

# end shimmer + final Am add9 bloom under the CTA
add(shimmer([440.00, 523.25, 659.26, 987.77], 2.2), TOTAL - 2.4)
add(bass(55.0, 2.0), TOTAL - 2.2)

# gentle low-pass feel via simple one-pole and normalize to -6 dBFS peak
out = np.zeros((N, 2))
out[:, 0] = mix
out[:, 1] = np.roll(mix, int(0.0004 * SR))  # micro-stereo width
peak = np.abs(out).max()
if peak > 0:
    out = out / peak * 0.5
pcm = (out * 32767).astype(np.int16)
with wave.open("/home/z/my-project/campaign/film/v20/audio/music.wav", "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("music.wav written", TOTAL, "s")
