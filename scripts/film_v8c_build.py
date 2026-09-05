#!/usr/bin/env python3
"""DeYoung film v8c — "EVERY STYLE" mixed-style commercial, rebuilt 100% locally.

User brief (hard constraints):
- MIX of styles like the site slideshow: children's cartoon, anime,
  real life, stick man — NOT one flat 2D/3D look.
- Voice-over AND characters actually talking (lip-synced), not VO alone.
- >= 60 seconds of REAL content — no dead padding to fake the length.

Everything on-screen is drawn or assembled locally (PIL + ffmpeg):
- Kids-cartoon talker: the kite kid cropped from the AI style master,
  cartoon mouth states drawn over his face (closed/mid/open flap).
- Anime: cinematic push-in, red slash wipes, dramatic line card.
- Stick man: drawn from scratch per-frame in the exact sc_stick style
  (cream paper, black round lines, red accent), waving + lip flap.
- Real life: the filmmaker master, slow push, letterbox + film grain.
- Dee (brand mascot diptych) closes with the sign-up CTA, lip-synced.
- NEW real content: works montage (8 real works), GPU-fleet scene
  (many GPUs, one queue -> merged/audited/verified/delivered),
  deyo model lineup (deyo.1 .. deyo-MAX flagship).
Voices are re-cut from the existing 63.5s voice master (known absolute
positions), music re-synthesized (124 BPM bed), remastered mix chain.

Output: campaign/v8/out/deyoung-film-v8.mp4 (1920x1080/30fps, 63.6s)
"""
import json
import math
import os
import shutil
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

BASE = "/home/z/my-project"
V8 = f"{BASE}/campaign/v8"
V6 = f"{BASE}/campaign/v6"
OUT = f"{V8}/out"
FRAMES = f"{V8}/frames"
PUB = f"{BASE}/public/video"
FONT_B = f"{BASE}/scripts/ArchivoBlack.ttf"
FONT_R = f"{BASE}/scripts/Archivo.ttf"
FPS = 30
W, H = 1920, 1080
MW, MH = 2060, 1159  # master > 1080p for ken-burns crop
RED = (220, 38, 38)
CREAM = (245, 243, 240)
INK = (23, 19, 16)
PAPER = (242, 236, 216)

os.makedirs(OUT, exist_ok=True)


def sh(cmd, tag=""):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FFMPEG_FAIL {tag}\n{r.stderr[-1500:]}")
        raise SystemExit(1)
    return r


def read_wav(p):
    with wave.open(p, "rb") as w:
        n, ch, sw, sr = w.getnframes(), w.getnchannels(), w.getsampwidth(), w.getframerate()
        raw = w.readframes(n)
    a = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if ch > 1:
        a = a.reshape(-1, ch).mean(axis=1)
    return a, sr


def write_wav(p, a, sr):
    x = np.clip(a, -1, 1)
    pcm = (x * 32767).astype("<i2").tobytes()
    with wave.open(p, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm)


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


# ---------------- 1. cut voices from the existing master --------------------
# old plan absolute positions (voice_start, voice_dur) from out/plan.json
OLD = {
    "v01": (0.7, 4.8), "v02": (7.5, 2.7), "v03": (11.7, 2.7),
    "v04": (15.9, 2.7), "v05": (20.1, 4.1), "v06": (25.7, 4.1),
    "v07": (31.2, 2.7), "v08": (35.6, 3.4), "v09": (40.9, 3.4),
}
master, SR = read_wav(f"{OUT}/voice_master.wav")
os.makedirs(f"{V8}/voices", exist_ok=True)
SEG = {}
for vid, (vs, vd) in OLD.items():
    i0 = max(0, int((vs - 0.05) * SR))
    i1 = min(len(master), int((vs + vd + 0.18) * SR))
    seg = master[i0:i1].copy()
    SEG[vid] = seg
    write_wav(f"{V8}/voices/{vid}.wav", seg, SR)
    print(f"voice {vid}: {len(seg)/SR:.2f}s")
VDUR = {k: len(v) / SR for k, v in SEG.items()}

# ---------------- 2. timeline (12 scenes, real content, 63.6s) --------------
SCENES = [
    # id   kind     asset/arg                    voice  caption                                        chip                  lead pad
    ("s01", "art",   f"{V8}/img/quad.png",         "v01", "EVERY STYLE.",                                 None,                 0.7, 1.5),
    ("s02", "talk2", "kid",                        "v02", "Hi! I'm your Saturday-morning cartoon!",       "CHILDREN'S CARTOON", 0.5, 1.6),
    ("s03", "anime", f"{V8}/img/sc_anime.png",     "v03", "STRAIGHT OUT OF AN ANIME.",                    "ANIME",              0.5, 1.2),
    ("s04", "stick", None,                         "v04", "Stick man! Two lines, one big idea.",          "STICK FIGURE",       0.5, 1.6),
    ("s05", "real",  f"{V8}/img/sc_real.png",      "v05", "And I'm real life — shot like a cinema ad.",   "REAL LIFE",          0.5, 1.2),
    ("s06", "montage", [f"{V8}/img/sc_kids.png", f"{V8}/img/sc_anime.png",
                         f"{V8}/img/sc_stick.png", f"{V8}/img/sc_real.png"],
                                    "v06", None,                                           None,                 0.5, 0.9),
    ("s07", "works", None,                         None,  None,                                           None,                 0.0, 6.4),
    ("s08", "fleet", None,                         None,  None,                                           None,                 0.0, 4.5),
    ("s09", "models", None,                        None,  None,                                           None,                 0.0, 3.6),
    ("s10", "art",   f"{V6}/img/anywhere.png",     "v07", "TYPE. PICK. ROLL.",                            None,                 0.6, 1.2),
    ("s11", "talk2", "dee",                        "v08", "Sign up, pick your plan — your studio lives.", "DEYOUNG STUDIO",     0.5, 1.4),
    ("s12", "end",   f"{V6}/out/endcard.png",      "v09", None,                                           None,                 0.8, 2.8),
]
timeline, t_cursor = [], 0.0
for sid, kind, asset, voice, caption, chip, lead, pad in SCENES:
    vdur = VDUR[voice] if voice else 0.0
    dur = lead + vdur + pad
    timeline.append({"id": sid, "kind": kind, "asset": asset, "voice": voice,
                     "caption": caption, "chip": chip, "lead": lead, "pad": pad,
                     "voice_dur": vdur, "dur": dur, "start": t_cursor,
                     "voice_start": t_cursor + lead})
    t_cursor += dur
TOTAL = t_cursor
assert TOTAL >= 60.0, f"timeline under 60s: {TOTAL}"
print(f"timeline: {TOTAL:.2f}s across {len(timeline)} scenes")

# new voice master at new positions
nm = np.zeros(int(TOTAL * SR) + SR)
for sc in timeline:
    if sc["voice"]:
        i0 = int(sc["voice_start"] * SR)
        nm[i0:i0 + len(SEG[sc["voice"]])] += SEG[sc["voice"]]
write_wav(f"{OUT}/voice_master2.wav", nm[: int(TOTAL * SR)], SR)
json.dump(timeline, open(f"{OUT}/plan.json", "w"), indent=1, default=str)

# ---------------- 3. music bed (124 BPM, 64s, stereo) ------------------------
def synth_music(path, total=64.0, split=None):
    sr = 48000
    beat = 60.0 / 124.0
    bar = beat * 4
    n = int(sr * total)
    mix = np.zeros(n)

    def add(sig, at):
        i = int(at * sr)
        j = min(n, i + len(sig))
        if j > i:
            mix[i:j] += sig[: j - i]

    def env_(nn, a, d):
        t = np.arange(nn) / sr
        e = np.clip(t / max(a, 1e-4), 0, 1)
        e *= np.exp(-np.maximum(t - a, 0) / max(d, 1e-4) * 3.0)
        return e

    def kick():
        m = int(0.30 * sr)
        t = np.arange(m) / sr
        f = np.linspace(160, 42, m)
        return 1.15 * np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-t * 18)

    def hat(open_=False):
        m = int((0.14 if open_ else 0.05) * sr)
        t = np.arange(m) / sr
        x = np.diff(np.random.default_rng(7).uniform(-1, 1, m), prepend=0)
        return 0.32 * x * np.exp(-t * (26 if open_ else 90))

    def bass(freq, dur):
        m = int(dur * sr)
        t = np.arange(m) / sr
        x = np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(4 * np.pi * freq * t)
        return 0.42 * x * env_(m, 0.004, dur * 0.9)

    def pluck(freq, dur=0.22):
        m = int(dur * sr)
        t = np.arange(m) / sr
        x = (np.sin(2 * np.pi * freq * t) + 0.5 * np.sin(4 * np.pi * freq * t)
             + 0.25 * np.sin(6 * np.pi * freq * t))
        return 0.16 * x * env_(m, 0.002, dur)

    def riser(dur):
        m = int(dur * sr)
        t = np.arange(m) / sr
        x = np.convolve(np.random.default_rng(3).uniform(-1, 1, m), np.ones(24) / 24, mode="same")
        sweep = np.sin(2 * np.pi * (300 + 2400 * (t / dur) ** 2) * t)
        return 0.30 * (0.6 * x + 0.4 * sweep) * (t / dur) ** 2

    def sting():
        m = int(1.6 * sr)
        t = np.arange(m) / sr
        x = sum(np.sin(2 * np.pi * f * t) * a for f, a in
                ((110, 0.5), (165, 0.3), (220, 0.25), (440, 0.15)))
        return 0.5 * x * np.exp(-t * 3.2)

    split = split if split is not None else total - 7.0
    notes = {"A": 55.0, "C": 65.41, "D": 73.42, "F": 87.31, "G": 98.0}
    prog = ["A", "A", "C", "D"]
    bi, bt = 0, 0.0
    while bt < split - 0.01:
        root = notes[prog[bi % len(prog)]]
        for b in range(4):
            tb = bt + b * beat
            add(kick(), tb)
            add(hat(b == 2), tb + beat / 2)
            if b % 2 == 1:
                add(hat(), tb + beat * 0.25)
            add(bass(root, beat * 0.85), tb)
            add(pluck([root * 4, root * 6, root * 4.5, root * 6][b]), tb + beat * 0.5)
        if bi % 4 == 3:
            add(pluck(root * 8, 0.3), bt + beat * 3.5)
        bi += 1
        bt += bar
    add(riser(3.2), split - 3.2)
    add(sting(), split + 0.05)
    for k in range(4):
        add(kick(), split + k * beat * 2)
    mix = mix / max(1e-9, np.max(np.abs(mix))) * 0.85
    fade = int(1.2 * sr)
    mix[-fade:] *= np.linspace(1, 0, fade)
    pcm = (mix * 32767).astype(np.int16)
    stereo = np.repeat(pcm[:, None], 2, axis=1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(stereo.tobytes())
    print(f"music: {total}s -> {path}")

MUSIC = f"{OUT}/music.wav"
synth_music(MUSIC, total=64.0, split=timeline[-1]["start"])

# ---------------- 4. panels --------------------------------------------------
def load_panels_diptych(path):
    src = Image.open(path).convert("RGB")
    half = src.size[0] // 2
    out = []
    for x0 in (0, half):
        panel = src.crop((x0, 0, x0 + half, src.size[1]))
        s = max(MW / panel.size[0], MH / panel.size[1])
        panel = panel.resize((int(panel.size[0] * s) + 1, int(panel.size[1] * s) + 1), Image.LANCZOS)
        x = (panel.size[0] - MW) // 2
        y = (panel.size[1] - MH) // 2
        out.append(panel.crop((x, y, x + MW, y + MH)))
    closed, open_ = out
    return closed, Image.blend(closed, open_, 0.5), open_

def grade(img):
    overlay = Image.new("RGB", (MW, MH), (10, 8, 8))
    img = Image.blend(img, overlay, 0.20)
    d = ImageDraw.Draw(img, "RGBA")
    grad = Image.new("L", (MW, MH), 0)
    gdr = ImageDraw.Draw(grad)
    for i in range(240):
        gdr.line([(0, MH - i), (MW, MH - i)], fill=int(120 * (1 - i / 240)))
    img.paste(Image.new("RGB", (MW, MH), (0, 0, 0)), (0, 0), grad)
    return img

def art_bg(path):
    src = Image.open(path).convert("RGB")
    s = max(MW / src.size[0], MH / src.size[1])
    src = src.resize((int(src.size[0] * s) + 1, int(src.size[1] * s) + 1), Image.LANCZOS)
    x = (src.size[0] - MW) // 2
    y = (src.size[1] - MH) // 2
    return grade(src.crop((x, y, x + MW, y + MH)))

# kids-cartoon talker: crop the kite kid, draw cartoon mouth states
def build_kid_panels():
    src = Image.open(f"{V8}/img/sc_kids.png").convert("RGB")
    # face center (1690, 315), mouth (1655, 385) in source coords
    cw_, chh = 880, int(880 / (W / H))             # 16:9 window 880x495
    x0, y0 = 1690 - int(0.42 * cw_), 315 - int(0.42 * chh)
    crop = src.crop((x0, y0, x0 + cw_, y0 + chh))
    s = max(MW / crop.size[0], MH / crop.size[1])
    base = crop.resize((int(crop.size[0] * s) + 1, int(crop.size[1] * s) + 1), Image.LANCZOS)
    bx, by = (base.size[0] - MW) // 2, (base.size[1] - MH) // 2
    base = base.crop((bx, by, bx + MW, by + MH))
    # mouth center in window coords (1671-x0, 374-y0) -> master coords
    mx, my = int((1671 - x0) * s - bx), int((374 - y0) * s - by)
    mw_ = int(62 * s)   # lip span in master px
    LIP = (128, 48, 34, 255)
    LIP_DK = (60, 22, 16, 230)
    LIP_MID = (110, 36, 26, 255)
    panels = []
    for state in (0, 1, 2):
        img = base.copy()
        d = ImageDraw.Draw(img, "RGBA")
        if state == 2:
            pass            # open = the artwork's own big open smile, untouched
        else:               # grin (resting + mid): cap lower 2/3, top teeth peek
            d.ellipse([mx - int(mw_ * 0.80), my - int(mw_ * 0.06),
                       mx + int(mw_ * 0.80), my + int(mw_ * 0.62)],
                      fill=LIP_MID, outline=LIP_DK, width=4)
        panels.append(img)
    return panels

PANELS = {}
PANELS["kid"] = build_kid_panels()
PANELS["dee"] = load_panels_diptych(f"{V6}/img/dee.png")
print("panels ready (kid drawn mouths, dee diptych)")

# ---------------- 5. backgrounds / stills ------------------------------------
BG, MONT, WORKS = {}, {}, []
for sc in timeline:
    if sc["kind"] == "art":
        BG[sc["id"]] = art_bg(sc["asset"])
    elif sc["kind"] == "montage":
        MONT = [art_bg(p) for p in sc["asset"]]
    elif sc["kind"] in ("anime", "real"):
        BG[sc["id"]] = art_bg(sc["asset"])
    elif sc["kind"] == "end":
        src = Image.open(sc["asset"]).convert("RGB")
        s = max(MW / src.size[0], MH / src.size[1])
        src = src.resize((int(src.size[0] * s) + 1, int(src.size[1] * s) + 1), Image.LANCZOS)
        x = (src.size[0] - MW) // 2
        y = (src.size[1] - MH) // 2
        BG[sc["id"]] = src.crop((x, y, x + MW, y + MH))

_work_pref = ["portrait-01", "brand-02", "editorial-01", "event-02",
              "studio-01", "commercial-02", "portrait-04", "commercial-01"]
_work_dir = f"{BASE}/public/works"
for wp in _work_pref:
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        p = f"{_work_dir}/{wp}{ext}"
        if os.path.exists(p):
            img = Image.open(p).convert("RGB")
            s = max(MW / img.size[0], MH / img.size[1])
            img = img.resize((int(img.size[0] * s) + 1, int(img.size[1] * s) + 1), Image.LANCZOS)
            x = (img.size[0] - MW) // 2
            y = (img.size[1] - MH) // 2
            WORKS.append((wp.split("-")[0].upper(), img.crop((x, y, x + MW, y + MH))))
            break
print(f"stills ready: bg x{len(BG)}, montage x{len(MONT)}, works x{len(WORKS)}")

# ---------------- 6. lip-flap envelopes --------------------------------------
def envelope_states(seg, dur, lead):
    hop = int(0.025 * SR)
    n_h = int(math.ceil(len(seg) / hop))
    rms = np.zeros(n_h)
    for i in range(n_h):
        s_ = seg[i * hop:(i + 1) * hop]
        rms[i] = math.sqrt(float((s_ ** 2).mean())) if len(s_) else 0.0
    k = max(1, int(0.07 * SR / hop))
    env = np.convolve(rms, np.ones(k) / k, mode="same")
    env = env / (float(env.max()) or 1e-6)
    total_frames = int(round(dur * FPS))
    states, cur, since = [], 0, 0
    for f in range(total_frames):
        vt = f / FPS - lead
        if 0 <= vt <= len(seg) / SR + 0.08:
            hf = min(n_h - 1, int(vt * SR) // hop)
            v = float(env[max(0, hf - 1):hf + 2].mean())
            target = 0 if v < 0.16 else 1 if v < 0.55 else 2
        else:
            target = 0
        if target != cur:
            if since >= 2 or target == 0:
                cur, since = target, 0
            else:
                since += 1
        else:
            since += 1
        states.append(cur)
    return states

STATES = {sc["id"]: envelope_states(SEG[sc["voice"]], sc["dur"], sc["lead"])
          for sc in timeline if sc["kind"] in ("talk2", "stick")}
print("lip-flap envelopes ready")

# ---------------- 7. overlays -------------------------------------------------
def caption_bar(img, text, alpha=1.0):
    if not text:
        return
    d = ImageDraw.Draw(img, "RGBA")
    f = ImageFont.truetype(FONT_B, 46)
    tw = min(d.textlength(text, font=f), W - 220)
    pad = 30
    bw = tw + pad * 2 + 24
    bx, by = (W - bw) // 2, int(H * 0.85)
    a = int(216 * alpha)
    d.rectangle([bx, by, bx + bw, by + 84], fill=(12, 12, 14, a))
    d.rectangle([bx, by, bx + 14, by + 84], fill=(*RED, a))
    f2 = ImageFont.truetype(FONT_B, 38) if d.textlength(text, font=f) > W - 240 else f
    d.text((bx + pad + 24, by + (84 - 46) // 2), text, font=f2, fill=(*CREAM, a))

def brand_tick(img, label="DEYOUNG"):
    d = ImageDraw.Draw(img, "RGBA")
    f = ImageFont.truetype(FONT_B, 30)
    d.rectangle([54, 50, 70, 88], fill=(*RED, 255))
    d.text((88, 52), label, font=f, fill=(255, 255, 255, 170))

def style_chip(img, label, alpha=1.0):
    if not label:
        return
    d = ImageDraw.Draw(img, "RGBA")
    f = ImageFont.truetype(FONT_B, 26)
    tw = d.textlength(label, font=f)
    bw = tw + 40
    a = int(230 * alpha)
    bx, by = W - bw - 54, 50
    d.rectangle([bx, by, bx + bw, by + 56], fill=(*RED, a))
    d.text((bx + 20, by + 13), label, font=f, fill=(255, 255, 255, a))

def ken_burns(img, fi, dur, bob_amp=0):
    e = ease(fi / max(1, int(dur * FPS) - 1))
    cw = int(MW - (MW - W) * e)
    chh = int(MH - (MH - H) * e)
    cx = (MW - cw) // 2
    bob = int(bob_amp * math.sin(2 * math.pi * 0.45 * fi / FPS)) if bob_amp else 0
    cy = max(0, min(MH - chh, (MH - chh) // 2 + bob))
    return img.crop((cx, cy, cx + cw, cy + chh)).resize((W, H), Image.BILINEAR)

def fades(img, fi, total_fi, first):
    k = 1.0
    if not first and fi < 6:
        k = fi / 6
    if fi > total_fi - 6:
        k = min(k, (total_fi - fi) / 6)
    if k < 1.0:
        return Image.blend(Image.new("RGB", (W, H), (0, 0, 0)), img, max(0.0, k))
    return img

# ---------------- 8. live-drawn scenes ---------------------------------------
def draw_stick(frame, sc, fi, mouth, t):
    d = ImageDraw.Draw(frame, "RGBA")
    lw = 16
    cx, ground = W // 2 - 140, int(H * 0.78)
    # ground hatch (like sc_stick)
    for i in range(9):
        x0 = 120 + i * 210
        d.line([x0, ground + 130, x0 + 150, ground + 130], fill=(23, 19, 16, 90), width=5)
    bob = int(10 * math.sin(2 * math.pi * 0.8 * t))
    hy = ground - 430 + bob
    hr = 110
    # head
    d.ellipse([cx - hr, hy - hr, cx + hr, hy + hr], outline=INK, width=lw)
    # cap (brand red)
    d.pieslice([cx - hr, hy - hr, cx + hr, hy + hr], 180, 360, fill=(*RED, 255))
    d.rectangle([cx - hr - 26, hy - 26, cx + hr + 26, hy - 6], fill=(*RED, 255))
    # eyes
    d.ellipse([cx - 52, hy - 10, cx - 22, hy + 26], fill=INK)
    d.ellipse([cx + 22, hy - 10, cx + 52, hy + 26], fill=INK)
    # mouth by state
    mcy = hy + 62
    if mouth == 0:
        d.line([cx - 40, mcy, cx + 40, mcy + 6], fill=INK, width=10)
    else:
        oh = 26 if mouth == 1 else 52
        d.ellipse([cx - 38, mcy - oh // 2, cx + 38, mcy + oh], fill=(91, 20, 20))
    # body + legs
    d.line([cx, hy + hr, cx, ground], fill=INK, width=lw)
    d.line([cx, ground, cx - 90, ground + 90], fill=INK, width=lw)
    d.line([cx, ground, cx + 90, ground + 90], fill=INK, width=lw)
    # left arm holding clapperboard
    d.line([cx, hy + hr + 60, cx - 170, ground - 60], fill=INK, width=lw)
    bx0, by0 = cx - 330, ground - 150
    d.rectangle([bx0, by0, bx0 + 240, by0 + 130], outline=INK, width=12)
    d.polygon([bx0, by0, bx0 + 240, by0, bx0 + 210, by0 - 46, bx0 - 20, by0 - 46],
              outline=INK, width=12)
    for i in range(4):
        d.line([bx0 + 20 + i * 56, by0 - 44, bx0 + 48 + i * 56, by0 - 2], fill=INK, width=12)
    # waving right arm — out to the SIDE, never over the face
    ang = 0.55 * math.sin(2 * math.pi * 1.6 * t)
    sx, sy = cx + 10, hy + hr + 46
    ex = sx + int(185 * math.cos(-0.55 + ang))
    ey = sy - int(185 * math.sin(-0.55 + ang))
    d.line([sx, sy, ex, ey], fill=INK, width=lw)
    d.ellipse([ex - 16, ey - 16, ex + 16, ey + 16], fill=INK)

def draw_fleet(frame, t):
    d = ImageDraw.Draw(frame, "RGBA")
    fT = ImageFont.truetype(FONT_B, 72)
    fL = ImageFont.truetype(FONT_B, 30)
    fS = ImageFont.truetype(FONT_R, 26)
    title = "MANY GPUS. ONE QUEUE."
    tw = d.textlength(title, font=fT)
    d.text(((W - tw) / 2 + 4, 114), title, font=fT, fill=(0, 0, 0, 160))
    d.text(((W - tw) / 2, 110), title, font=fT, fill=CREAM)
    sub = "scenes render in parallel — then merged, audited, verified, delivered"
    sw = d.textlength(sub, font=fS)
    d.text(((W - sw) / 2, 205), sub, font=fS, fill=(255, 255, 255, 150))
    cw_, chh, gap = 520, 300, 60
    x0 = (W - 3 * cw_ - 2 * gap) // 2
    y0 = 330
    rates = [0.34, 0.27, 0.40]
    names = ["WORKER A", "WORKER B", "WORKER C"]
    subs = ["KAGGLE GPU · LTX", "KAGGLE GPU · LTX", "QA · STILLS · RETRY"]
    for i in range(3):
        x, y = x0 + i * (cw_ + gap), y0
        prog = min(1.0, max(0.0, t * rates[i]))
        on = prog < 1.0
        d.rounded_rectangle([x, y, x + cw_, y + chh], radius=22,
                            fill=(18, 16, 16, 240),
                            outline=(*RED, 255) if on else (70, 66, 64, 255), width=4)
        d.text((x + 30, y + 26), names[i], font=fL, fill=CREAM)
        d.text((x + 30, y + 68), subs[i], font=fS, fill=(255, 255, 255, 140))
        # progress bar
        bw_, bh_ = cw_ - 60, 34
        bx, by = x + 30, y + 150
        d.rounded_rectangle([bx, by, bx + bw_, by + bh_], radius=10, fill=(38, 34, 34, 255))
        fill_w = int(bw_ * prog)
        if fill_w > 10:
            d.rounded_rectangle([bx, by, bx + fill_w, by + bh_], radius=10, fill=(*RED, 255))
        d.text((bx, by + 46), f"{int(prog * 100)}%", font=fL, fill=CREAM)
        d.text((bx + 130, by + 46), f"SCENE {min(6, int(prog * 6) + 1)}/6", font=fL,
               fill=(255, 255, 255, 150))
    # checklist ticks after 2.5s
    steps = ["MERGED", "AUDITED", "VERIFIED", "DELIVERED"]
    st0 = 2.5
    fx, fy = x0, y0 + chh + 56
    for i, s_ in enumerate(steps):
        a = ease((t - st0 - i * 0.35) / 0.25)
        if a <= 0:
            continue
        aa = int(255 * a)
        d.rounded_rectangle([fx, fy, fx + 380, fy + 62], radius=12,
                            fill=(24, 21, 21, int(230 * a)))
        # check mark
        d.line([fx + 24, fy + 32, fx + 44, fy + 48], fill=(*RED, aa), width=8)
        d.line([fx + 44, fy + 48, fx + 76, fy + 16], fill=(*RED, aa), width=8)
        d.text((fx + 96, fy + 14), s_, font=fL, fill=(*CREAM, aa))
        fx += 410

def draw_models(frame, t):
    d = ImageDraw.Draw(frame, "RGBA")
    fT = ImageFont.truetype(FONT_B, 72)
    fC = ImageFont.truetype(FONT_B, 38)
    fM = ImageFont.truetype(FONT_B, 52)
    fS = ImageFont.truetype(FONT_R, 26)
    title = "THE DEYO LINE"
    tw = d.textlength(title, font=fT)
    d.text(((W - tw) / 2 + 4, 124), title, font=fT, fill=(0, 0, 0, 160))
    d.text(((W - tw) / 2, 120), title, font=fT, fill=CREAM)
    rows = [
        ["deyo.1", "deyo.1 PRO", "deyo.2", "deyo.2 PRO"],
        ["deyo.3", "deyo.3 PRO", "deyo-MAX"],
    ]
    order = ["deyo.1", "deyo.1 PRO", "deyo.2", "deyo.2 PRO",
             "deyo.3", "deyo.3 PRO", "deyo-MAX"]
    gap = 26
    y0 = 350
    for row_i, row in enumerate(rows):
        # measure row width from per-chip text widths
        widths = []
        for m in row:
            wf = fM if m == "deyo-MAX" else fC
            widths.append(int(d.textlength(m, font=wf)) + (96 if m == "deyo-MAX" else 64))
        rw = sum(widths) + gap * (len(row) - 1)
        x = (W - rw) // 2
        y = y0 + row_i * 190
        for m, cw_ in zip(row, widths):
            a = ease((t - 0.25 - order.index(m) * 0.26) / 0.3)
            if a <= 0:
                x += cw_ + gap
                continue
            aa = int(255 * a)
            flagship = m == "deyo-MAX"
            chh = 112 if flagship else 92
            yy = y + (int((1 - a) * 40))
            wf = fM if flagship else fC
            if flagship:
                glow = Image.new("RGBA", (cw_ + 90, chh + 90), (0, 0, 0, 0))
                gd = ImageDraw.Draw(glow)
                gd.rounded_rectangle([45, 45, 45 + cw_, 45 + chh], radius=22,
                                     fill=(234, 179, 8, int(140 * a)))
                glow = glow.filter(ImageFilter.GaussianBlur(24))
                frame.paste(glow, (int(x - 45), int(yy - 45)), glow)
                d = ImageDraw.Draw(frame, "RGBA")
            d.rounded_rectangle([x, yy, x + cw_, yy + chh], radius=20,
                                fill=(234, 179, 8, aa) if flagship else (30, 26, 26, aa),
                                outline=(234, 179, 8, aa) if flagship else (*RED, aa), width=4)
            tw2 = d.textlength(m, font=wf)
            d.text((x + (cw_ - tw2) / 2, yy + (chh - (52 if flagship else 38)) / 2), m,
                   font=wf, fill=(20, 16, 12, aa) if flagship else (*CREAM, aa))
            x += cw_ + gap
    sub = "FROM FIRST RENDER TO OUR FLAGSHIP"
    sw = d.textlength(sub, font=fS)
    d.text(((W - sw) / 2, y0 + 2 * 190 + 8), sub, font=fS,
           fill=(255, 255, 255, int(180 * ease((t - 2.2) / 0.4))))

# ---------------- 9. compose --------------------------------------------------
def grain(img, fi, amp=0.045):
    noise = np.random.default_rng(int(fi * 7) % 9999).integers(0, 255, (135, 240, 1), dtype=np.uint8)
    noise = np.repeat(noise, 8, axis=0).repeat(8, axis=1)
    nimg = Image.fromarray(np.repeat(noise, 3, axis=2), "RGB").resize((W, H))
    return Image.blend(img, nimg, amp)

def compose(sc, fi):
    t = fi / FPS
    total_fi = int(round(sc["dur"] * FPS))
    first = sc["start"] < 0.01
    kind = sc["kind"]

    if kind == "talk2":
        mouth = STATES[sc["id"]][min(fi, len(STATES[sc["id"]]) - 1)]
        closed, mid, open_ = PANELS[sc["asset"]]
        panel = (closed, mid, open_)[mouth]
        frame = ken_burns(panel, fi, sc["dur"], bob_amp=6)
        cap_a = 1.0 if t > sc["lead"] + 0.15 else max(0.0, (t - sc["lead"]) / 0.15)
        caption_bar(frame, sc["caption"], cap_a)
        brand_tick(frame)
        style_chip(frame, sc["chip"], cap_a)
        return fades(frame, fi, total_fi, first)

    if kind == "stick":
        mouth = STATES[sc["id"]][min(fi, len(STATES[sc["id"]]) - 1)]
        frame = Image.new("RGB", (W, H), PAPER)
        draw_stick(frame, sc, fi, mouth, t)
        cap_a = 1.0 if t > sc["lead"] + 0.15 else max(0.0, (t - sc["lead"]) / 0.15)
        caption_bar(frame, sc["caption"], cap_a)
        brand_tick(frame)
        style_chip(frame, sc["chip"], cap_a)
        return fades(frame, fi, total_fi, first)

    if kind == "art":
        frame = ken_burns(BG[sc["id"]], fi, sc["dur"])
        brand_tick(frame)
        if sc["caption"]:
            d = ImageDraw.Draw(frame, "RGBA")
            words = sc["caption"].split()
            f = ImageFont.truetype(FONT_B, 104)
            space_w = d.textlength(" ", font=f)
            widths = [d.textlength(wd, font=f) for wd in words]
            total = sum(widths) + space_w * (len(words) - 1)
            x, y = (W - total) / 2, H * 0.40
            for i, wd in enumerate(words):
                wt = t - 0.35 - i * 0.26
                a = ease(wt / 0.30) if wt > 0 else 0
                if a > 0:
                    aa = int(255 * a)
                    d.text((x + 4, y + 4), wd, font=f, fill=(0, 0, 0, aa // 2))
                    d.text((x, y), wd, font=f, fill=(*CREAM, aa))
                x += widths[i] + space_w
        return fades(frame, fi, total_fi, first)

    if kind == "anime":
        frame = ken_burns(BG[sc["id"]], fi, sc["dur"])
        d = ImageDraw.Draw(frame, "RGBA")
        # red slash wipes on entry/exit
        slash_t = min(t / 0.4, 1.0) if t < sc["dur"] - 0.5 else (sc["dur"] - t) / 0.5
        sk = ease(min(1.0, max(0.0, slash_t)))
        if 0 < sk < 1:
            for off in (0, 260, 520):
                y0 = int(H * 0.25) + off
                x0 = int((W + 700) * (1 - sk)) - 700 + off // 3
                d.polygon([(x0, y0), (x0 + 90, y0), (x0 - 210 + 90, y0 + 300),
                           (x0 - 210, y0 + 300)], fill=(*RED, 200))
        cap_a = 1.0 if t > sc["lead"] + 0.15 else max(0.0, (t - sc["lead"]) / 0.15)
        caption_bar(frame, sc["caption"], cap_a)
        brand_tick(frame)
        style_chip(frame, sc["chip"], cap_a)
        return fades(frame, fi, total_fi, first)

    if kind == "real":
        frame = ken_burns(BG[sc["id"]], fi, sc["dur"], bob_amp=4)
        frame = grain(frame, fi)
        d = ImageDraw.Draw(frame, "RGBA")
        d.rectangle([0, 0, W, 92], fill=(0, 0, 0, 255))
        d.rectangle([0, H - 92, W, H], fill=(0, 0, 0, 255))
        cap_a = 1.0 if t > sc["lead"] + 0.15 else max(0.0, (t - sc["lead"]) / 0.15)
        caption_bar(frame, sc["caption"], cap_a)
        brand_tick(frame)
        style_chip(frame, sc["chip"], cap_a)
        return fades(frame, fi, total_fi, first)

    if kind == "montage":
        per = sc["dur"] / len(MONT)
        idx_ = min(len(MONT) - 1, int(t / per))
        frame = ken_burns(MONT[idx_], fi - int(idx_ * per * FPS), per)
        d = ImageDraw.Draw(frame, "RGBA")
        chips = ["CHILDREN'S CARTOON", "ANIME", "STICK FIGURE", "REAL LIFE"]
        f = ImageFont.truetype(FONT_B, 34)
        label = chips[idx_]
        tw = d.textlength(label, font=f)
        d.rectangle([54, H - 130, 54 + tw + 44, H - 66], fill=(12, 12, 14, 220))
        d.rectangle([54, H - 130, 68, H - 66], fill=(*RED, 255))
        d.text((90, H - 118), label, font=f, fill=(*CREAM, 255))
        brand_tick(frame)
        return fades(frame, fi, total_fi, first)

    if kind == "works":
        per = sc["dur"] / len(WORKS)
        idx_ = min(len(WORKS) - 1, int(t / per))
        frame = ken_burns(WORKS[idx_][1], fi - int(idx_ * per * FPS), per)
        d = ImageDraw.Draw(frame, "RGBA")
        f = ImageFont.truetype(FONT_B, 30)
        label = WORKS[idx_][0] + " — MADE WITH DEYOUNG"
        tw = d.textlength(label, font=f)
        d.rectangle([54, H - 118, 54 + tw + 44, H - 62], fill=(12, 12, 14, 210))
        d.rectangle([54, H - 118, 68, H - 62], fill=(*RED, 255))
        d.text((90, H - 107), label, font=f, fill=(*CREAM, 255))
        brand_tick(frame)
        return fades(frame, fi, total_fi, first)

    if kind == "fleet":
        frame = Image.new("RGB", (W, H), (11, 10, 10))
        draw_fleet(frame, t)
        brand_tick(frame)
        return fades(frame, fi, total_fi, first)

    if kind == "models":
        frame = Image.new("RGB", (W, H), (11, 10, 10))
        draw_models(frame, t)
        brand_tick(frame)
        return fades(frame, fi, total_fi, first)

    if kind == "end":
        frame = ken_burns(BG[sc["id"]], fi, sc["dur"])
        brand_tick(frame)
        return fades(frame, fi, total_fi, first)

    raise SystemExit(f"unknown kind {kind}")

# ---------------- 10. render (scene-selective via SCENES_ONLY=s02,s09) -------
ONLY = [s_ for s_ in os.environ.get("SCENES_ONLY", "").split(",") if s_]
idx = 0
for sc in timeline:
    n = int(round(sc["dur"] * FPS))
    if ONLY and sc["id"] not in ONLY:
        idx += n
        continue
    print(f"render {sc['id']} {sc['kind']} ({n} frames) [f{idx:05d}..f{idx+n-1:05d}]")
    for f in range(n):
        fi = f
        compose(sc, fi).save(f"{FRAMES}/f{idx:05d}.jpg", quality=92)
        idx += 1
print(f"frames: {idx} ({idx / FPS:.2f}s)")

sh(f"ffmpeg -y -framerate {FPS} -i {FRAMES}/f%05d.jpg -c:v libx264 -preset medium "
   f"-crf 18 -pix_fmt yuv420p {OUT}/v8c_silent.mp4", "video")

# ---------------- 11. remaster + mux -----------------------------------------
sh(
    f"ffmpeg -y -i {OUT}/v8c_silent.mp4 -i {MUSIC} -i {OUT}/voice_master2.wav -filter_complex "
    "\"[2:a]highpass=f=85,acompressor=threshold=0.08:ratio=2.5:attack=8:release=120[vox];"
    "[1:a]volume=0.16,afade=t=in:d=1.2,afade=t=out:st=" f"{TOTAL-2.2}" ":d=2.2[bg];"
    "[bg][vox]sidechaincompress=threshold=0.015:ratio=9:attack=25:release=350:makeup=1[duck];"
    "[duck][vox]amix=inputs=2:duration=first:dropout_transition=0,alimiter=limit=0.9,"
    "loudnorm=I=-16:TP=-1.5:LRA=11[a]\" "
    f"-map 0:v -map \"[a]\" -c:v copy -c:a aac -b:a 192k -movflags +faststart -shortest "
    f"{OUT}/deyoung-film-v8.mp4",
    "mix",
)

# ---------------- 12. QA gate -------------------------------------------------
probe = sh(f"ffprobe -v error -show_entries format=duration -show_entries "
           f"stream=codec_name,width,height,channels -of json {OUT}/deyoung-film-v8.mp4", "probe")
meta = json.loads(probe.stdout)
dur = float(meta["format"]["duration"])
vstreams = [s for s in meta["streams"] if s["codec_name"] == "h264"]
astreams = [s for s in meta["streams"] if s["codec_name"] == "aac"]
black = sh(f"ffmpeg -i {OUT}/deyoung-film-v8.mp4 -vf blackdetect=d=0.5:pix_th=0.02 "
           f"-an -f null - 2>&1 | grep black_start || true", "black")
print(f"QA: dur={dur:.2f}s video={len(vstreams)} audio={len(astreams)}")
print(f"QA blackdetect: {black.strip() or 'clean'}")
assert dur >= 59.5, f"UNDER 60s: {dur}"
assert len(vstreams) == 1 and len(astreams) == 1
size = os.path.getsize(f"{OUT}/deyoung-film-v8.mp4")
assert size > 3_000_000, f"suspiciously small: {size}"

# ---------------- 13. ship to public + poster --------------------------------
shutil.copyfile(f"{OUT}/deyoung-film-v8.mp4", f"{PUB}/deyoung-film-web.mp4")
poster_t = int((timeline[1]["start"] + 1.2) * FPS)  # kid talking frame
sh(f"ffmpeg -y -i {OUT}/deyoung-film-v8.mp4 -vf \"select=eq(n\\,{poster_t})\" -vframes 1 "
   f"{PUB}/film-poster.jpg", "poster")
print(f"SHIPPED {PUB}/deyoung-film-web.mp4 ({size/1e6:.1f}MB, {dur:.2f}s) + poster")
