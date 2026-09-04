#!/usr/bin/env python3
"""DeYoung film v3 — synth an energetic 124 BPM electronic bed (64s, 48k stereo).

Punchy kick + hats + bass pulse + arp pluck; riser into the endcard; end sting.
Ducked under dialogue at mix time. Output: campaign/film/v3/music.wav
"""
import numpy as np
import wave

SR = 48000
BPM = 124.0
BEAT = 60.0 / BPM            # 0.4839 s
BAR = BEAT * 4
TOTAL = 64.0
N = int(SR * TOTAL)
t_all = np.arange(N) / SR

mix = np.zeros(N)

def add(sig, at_s):
    i = int(at_s * SR)
    j = min(N, i + len(sig))
    if j > i:
        mix[i:j] += sig[: j - i]

def env(n, a, d, sus=0.0, r=0.05):
    """attack/decay/sustain/release envelope over n samples (times in s)"""
    t = np.arange(n) / SR
    total = a + d + sus + r
    e = np.zeros(n)
    e += np.clip(t / max(a, 1e-4), 0, 1)
    e *= np.exp(-np.maximum(t - a, 0) / max(d, 1e-4) * 3.0)
    return e[:n]

# --- instruments -----------------------------------------------------------
def kick():
    n = int(0.30 * SR)
    t = np.arange(n) / SR
    f = np.linspace(160, 42, n)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return 1.15 * np.sin(ph) * np.exp(-t * 18)

def hat(open_=False):
    n = int((0.14 if open_ else 0.05) * SR)
    t = np.arange(n) / SR
    x = np.random.default_rng(7).uniform(-1, 1, n)
    x = np.diff(x, prepend=0)  # brighten
    return 0.32 * x * np.exp(-t * (26 if open_ else 90))

def bass(freq, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(4 * np.pi * freq * t)
    return 0.42 * x * env(n, 0.004, dur * 0.9)

def pluck(freq, dur=0.22):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * freq * t)
         + 0.5 * np.sin(4 * np.pi * freq * t)
         + 0.25 * np.sin(6 * np.pi * freq * t))
    return 0.16 * x * env(n, 0.002, dur)

def riser(dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.random.default_rng(3).uniform(-1, 1, n)
    x = np.convolve(x, np.ones(24) / 24, mode="same")  # tame
    sweep = np.sin(2 * np.pi * (300 + 2400 * (t / dur) ** 2) * t)
    return 0.30 * (0.6 * x + 0.4 * sweep) * (t / dur) ** 2

def sting():
    n = int(1.6 * SR)
    t = np.arange(n) / SR
    x = sum(np.sin(2 * np.pi * f * t) * a for f, a in
            ((110, 0.5), (165, 0.3), (220, 0.25), (440, 0.15)))
    return 0.5 * x * np.exp(-t * 3.2)

# --- arrangement (56s scenes + 4s endcard; scene split at 56) --------------
SPLIT = 56.0
note_bass = {"A": 55.0, "C": 65.41, "D": 73.42, "F": 87.31, "G": 98.0}
prog = ["A", "A", "C", "D"]  # per bar, looped

bar_i = 0
bar_t = 0.0
while bar_t < SPLIT - 0.01:
    root = note_bass[prog[bar_i % len(prog)]]
    for b in range(4):
        tb = bar_t + b * BEAT
        add(kick(), tb)
        add(hat(b == 2), tb + BEAT / 2)                       # offbeat hat
        if b % 2 == 1:
            add(hat(), tb + BEAT * 0.25)
        add(bass(root, BEAT * 0.85), tb)
        arp = [root * 4, root * 6, root * 4.5, root * 6][b]   # A minor-ish color
        add(pluck(arp), tb + BEAT * 0.5)
    # subtle lift every 4th bar
    if bar_i % 4 == 3:
        add(pluck(root * 8, 0.3), bar_t + BEAT * 3.5)
    bar_i += 1
    bar_t += BAR

# riser into endcard + end sting on the card
add(riser(3.2), SPLIT - 3.2)
add(sting(), SPLIT + 0.05)
# light kick pulse under endcard
for k in range(4):
    add(kick(), SPLIT + k * BEAT * 2)

# --- master -----------------------------------------------------------------
mix = mix / max(1e-9, np.max(np.abs(mix))) * 0.85
# gentle fade out at the very end
fade = int(1.2 * SR)
mix[-fade:] *= np.linspace(1, 0, fade)
pcm = (mix * 32767).astype(np.int16)
stereo = np.repeat(pcm[:, None], 2, axis=1)

out = "/home/z/my-project/campaign/film/v3/music.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(stereo.tobytes())
print("music bed:", out, f"{TOTAL}s @ {BPM} BPM")
