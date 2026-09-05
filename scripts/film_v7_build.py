#!/usr/bin/env python3
"""DeYoung film v7 — MODERN build.

Fixes the v6 complaints ("1980 cartoon, sloppy"):
- Clean flat-vector cast (scripts/film_v7_art.py) with 5 mouth states,
  eye blinks, head-bob and breathing sway — not a 2-state mouth flap.
- Eased ken-burns camera on every scene, dip-to-black transitions.
- Broadcast-style lower-third captions with safe margins.
- Remastered audio: HPF'd voice, music side-chain ducked, limited & normalized.

Voices + scene timing + music reuse the proven v6 assets.
Output: campaign/v7/out/deyoung-film-v7.mp4 (1920x1080/30fps, ~46s)
"""
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from film_v7_art import render_character, CHARACTERS, CW, CH  # noqa: E402

BASE = "/home/z/my-project"
V6 = f"{BASE}/campaign/v6"
V7 = f"{BASE}/campaign/v7"
OUT = f"{V7}/out"
FRAMES = f"{V7}/frames"
os.makedirs(OUT, exist_ok=True)

FONT_B = f"{BASE}/scripts/ArchivoBlack.ttf"
FONT_R = f"{BASE}/scripts/Archivo.ttf"
FPS = 30
W, H = 1920, 1080
DURS = json.load(open(f"{V6}/voices/durations.json"))

SCENES = [
    # id, kind, asset/char, voice, caption, lead(s), pad(s)
    ("s01", "art",  f"{V6}/img/hook.png",     "n01_hook",     "EVERY STORY DESERVES THE BIG SCREEN.", 0.6, 1.6),
    ("s02", "talk", "amara",                  "n02_amara",    "Your story deserves more than fifteen seconds.", 0.45, 1.1),
    ("s03", "talk", "kossi",                  "n03_kossi",    "DeYoung gives it a full sixty.", 0.45, 1.1),
    ("s04", "talk", "zola",                   "n04_zola",     "Type your story. Pick your length.", 0.35, 0.9),
    ("s05", "art",  f"{V6}/img/alive.png",    "n05_alive",    "And watch it come alive.", 0.5, 1.4),
    ("s06", "talk", "dee",                    "n06_dee",      "Write it. We roll the cameras.", 0.4, 1.0),
    ("s07", "art",  f"{V6}/img/anywhere.png", "n07_anywhere", "Mobile or web. Your studio travels with you.", 0.45, 1.1),
    ("s08", "end",  None,                     "n08_end",      "DeYoung. Sixty seconds. One pass.", 0.7, 3.2),
]


def sh(cmd, tag=""):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FFMPEG_FAIL {tag}\n{r.stderr[-1500:]}")
        raise SystemExit(1)
    return r


def esc(t):
    return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\\\'").replace("%", "\\%")


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
    """smoothstep 0..1"""
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


# ---------- voice timeline (exact scene geometry, shared by video & audio) ----------

timeline = []
t_cursor = 0.0
for sid, kind, asset, voice, caption, lead, pad in SCENES:
    vdur = DURS[voice]
    scene_dur = lead + vdur + pad
    timeline.append({"id": sid, "kind": kind, "asset": asset, "voice": voice,
                     "caption": caption, "lead": lead, "pad": pad,
                     "voice_dur": vdur, "dur": scene_dur, "start": t_cursor,
                     "voice_start": t_cursor + lead})
    t_cursor += scene_dur
TOTAL = t_cursor
print(f"total duration {TOTAL:.2f}s")

# build the voice master track
a0, SR = read_wav(f"{V6}/voices/n01_hook.wav")
master = np.zeros(int(math.ceil(TOTAL * SR)) + SR, dtype=np.float32)
for sc in timeline:
    seg, _ = read_wav(f"{V6}/voices/{sc['voice']}.wav")
    i0 = int(sc["voice_start"] * SR)
    master[i0:i0 + len(seg)] += seg
write_wav(f"{OUT}/voice_master.wav", master, SR)
json.dump(timeline, open(f"{OUT}/plan.json", "w"), indent=1)

# ---------- envelope -> per-frame mouth states ----------

def envelope_states():
    """Return dict scene_id -> list of (mouth, blink) per frame."""
    hop = int(0.025 * SR)
    out = {}
    for sc in timeline:
        if sc["kind"] != "talk":
            continue
        seg, _ = read_wav(f"{V6}/voices/{sc['voice']}.wav")
        n_h = int(math.ceil(len(seg) / hop))
        rms = np.zeros(n_h)
        for i in range(n_h):
            s = seg[i * hop:(i + 1) * hop]
            rms[i] = math.sqrt(float((s ** 2).mean())) if len(s) else 0.0
        k = max(1, int(0.07 * SR / hop))
        sm = np.convolve(rms, np.ones(k) / k, mode="same")
        mx = float(sm.max()) or 1e-6
        # normalized 0..1 envelope
        env = sm / mx
        total_frames = int(round(sc["dur"] * FPS))
        states = []
        cur = 0
        since = 0
        MIN = 2
        for f in range(total_frames):
            t = f / FPS
            vt = t - sc["lead"]
            if 0 <= vt <= sc["voice_dur"] + 0.1:
                hf = min(n_h - 1, int(vt * SR) // hop)
                v = float(env[max(0, hf - 1):hf + 2].mean())
                target = 0 if v < 0.10 else 1 if v < 0.32 else 2 if v < 0.58 else 3 if v < 0.85 else 4
            else:
                target = 0
            if target != cur:
                if since >= MIN or target == 0:
                    cur = target
                    since = 0
                else:
                    since += 1
            else:
                since += 1
            # blink schedule: deterministic 2.6s period with jitter from scene id
            blink = 0
            if sc["kind"] == "talk":
                phase = (hash(sc["id"]) % 100) / 100
                bt = (t + phase * 2.6) % 2.6
                if 2.32 <= bt <= 2.44:
                    blink = 1
            states.append((cur, blink))
        out[sc["id"]] = states
    return out


STATES = envelope_states()

# ---------- pre-render character art (cache) ----------

CHAR_CACHE = {}
for cname in CHARACTERS:
    for m in range(5):
        for b in (0, 1):
            CHAR_CACHE[(cname, m, b)] = render_character(cname, m, b).convert("RGBA")
print("character cache ready")

# ---------- scene background builders (drawn once per scene) ----------

def brand_bg(kind="talk", word=None):
    """Master-sized background: charcoal + red glow + dot grid + ghost word."""
    mw, mh = 2060, 1159  # master > 1080p for ken-burns crop
    img = Image.new("RGB", (mw, mh), (23, 23, 26))
    d = ImageDraw.Draw(img, "RGBA")
    # radial red glow
    glow = Image.new("L", (mw, mh), 0)
    gd = ImageDraw.Draw(glow)
    gd.ellipse([mw * 0.52, -mh * 0.35, mw * 1.25, mh * 0.95], fill=70)
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    img.paste(Image.new("RGB", (mw, mh), (120, 22, 22)), (0, 0), glow)
    # dot grid
    for y in range(40, mh, 56):
        for x in range(40, mw, 56):
            d.ellipse([x, y, x + 3, y + 3], fill=(255, 255, 255, 10))
    # ghost word
    if word:
        f = ImageFont.truetype(FONT_B, 200)
        tw = d.textlength(word, font=f)
        d.text(((mw - tw) / 2, mh * 0.10), word, font=f, fill=(255, 255, 255, 14))
    return img


def art_bg(path):
    """Cover-fill an image-gen art frame into the master size + dark grade."""
    mw, mh = 2060, 1159
    src = Image.open(path).convert("RGB")
    sw, sh_ = src.size
    scale = max(mw / sw, mh / sh_)
    src = src.resize((int(sw * scale) + 1, int(sh_ * scale) + 1), Image.LANCZOS)
    x = (src.width - mw) // 2
    y = (src.height - mh) // 2
    img = src.crop((x, y, x + mw, y + mh))
    # cinematic grade: darken + red edge glow
    overlay = Image.new("RGB", (mw, mh), (10, 8, 8))
    img = Image.blend(img, overlay, 0.28)
    d = ImageDraw.Draw(img, "RGBA")
    grad = Image.new("L", (mw, mh), 0)
    gdr = ImageDraw.Draw(grad)
    for i in range(240):
        gdr.line([(0, mh - i), (mw, mh - i)], fill=int(140 * (1 - i / 240)))
    img.paste(Image.new("RGB", (mw, mh), (0, 0, 0)), (0, 0), grad)
    return img


def make_endcard():
    mw, mh = 2060, 1159
    img = Image.new("RGB", (mw, mh), (16, 15, 16))
    d = ImageDraw.Draw(img, "RGBA")
    glow = Image.new("L", (mw, mh), 0)
    gd = ImageDraw.Draw(glow)
    gd.ellipse([mw * 0.30, mh * 0.05, mw * 0.70, mh * 0.85], fill=60)
    glow = glow.filter(ImageFilter.GaussianBlur(140))
    img.paste(Image.new("RGB", (mw, mh), (120, 22, 22)), (0, 0), glow)
    for y in range(40, mh, 56):
        for x in range(40, mw, 56):
            d.ellipse([x, y, x + 3, y + 3], fill=(255, 255, 255, 8))
    return img


BG = {}
for sc in timeline:
    if sc["kind"] == "talk":
        BG[sc["id"]] = brand_bg("talk", CHARACTERS[sc["asset"]]["bg_word"])
    elif sc["kind"] == "art":
        BG[sc["id"]] = art_bg(sc["asset"])
    else:
        BG[sc["id"]] = make_endcard()
print("backgrounds ready")

# ---------- frame compositor ----------

CHAR_H = 940  # on-screen character height


def caption_bar(img, text, alpha=1.0):
    """Lower-third caption, modern broadcast style."""
    if not text:
        return
    d = ImageDraw.Draw(img, "RGBA")
    f = ImageFont.truetype(FONT_B, 52)
    tw = d.textlength(text, font=f)
    pad = 34
    bw = tw + pad * 2 + 26
    bx, by = (W - bw) // 2, int(H * 0.845)
    a = int(216 * alpha)
    d.rectangle([bx, by, bx + bw, by + 92], fill=(12, 12, 14, a))
    d.rectangle([bx, by, bx + 14, by + 92], fill=(220, 38, 38, a))
    d.text((bx + pad + 26, by + 16), text, font=f, fill=(245, 243, 240, a))


def brand_tick(img, label):
    d = ImageDraw.Draw(img, "RGBA")
    f = ImageFont.truetype(FONT_B, 30)
    d.rectangle([54, 50, 54 + 16, 88], fill=(220, 38, 38, 255))
    d.text((88, 52), label, font=f, fill=(255, 255, 255, 170))


def compose_frame(sc, fi):
    """One output frame for a scene."""
    t = fi / FPS
    # ken-burns crop window on the master bg (eased zoom-out 1.0 -> 0.932 of master)
    e = ease(fi / max(1, int(sc["dur"] * FPS) - 1))
    mw, mh = BG[sc["id"]].size
    cw = int(mw - (mw - W) * e)
    chh = int(mh - (mh - H) * e)
    cx = (mw - cw) // 2
    cy = (mh - chh) // 2
    frame = BG[sc["id"]].crop((cx, cy, cx + cw, cy + chh)).resize((W, H), Image.BILINEAR)

    if sc["kind"] == "talk":
        mouth, blink = STATES[sc["id"]][min(fi, len(STATES[sc["id"]]) - 1)]
        char = CHAR_CACHE[(sc["asset"], mouth, blink)]
        # scale once (cache by size): 1000x1150 -> CHAR_H
        ch_img = char.resize((int(CW * CHAR_H / CH), CHAR_H), Image.BILINEAR)
        bob = 7 * math.sin(2 * math.pi * 0.45 * t + hash(sc["id"]) % 7)
        sway = 4 * math.sin(2 * math.pi * 0.31 * t + 1.3)
        px = int(W * 0.615 - ch_img.width / 2 + sway)
        py = int(H - CHAR_H * 0.06) - ch_img.height + int(bob)
        # soft drop shadow under character
        shd = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shd)
        sd.ellipse([px + 40, py + ch_img.height - 60, px + ch_img.width - 40, py + ch_img.height + 40], fill=(0, 0, 0, 120))
        shd = shd.filter(ImageFilter.GaussianBlur(18))
        frame.paste(Image.alpha_composite(frame.convert("RGBA"), shd).convert("RGB"), (0, 0))
        frame.paste(ch_img, (px, py), ch_img)
        # talk lead-in: caption appears with voice
        vt = t - sc["lead"]
        cap_alpha = 1.0 if vt > 0.15 else max(0.0, vt / 0.15)
        caption_bar(frame, sc["caption"], cap_alpha)
        brand_tick(frame, "DEYOUNG")
    elif sc["kind"] == "art":
        brand_tick(frame, "DEYOUNG")
        # kinetic title: words pop in staggered
        words = sc["caption"].split()
        d = ImageDraw.Draw(frame, "RGBA")
        f = ImageFont.truetype(FONT_B, 96)
        space_w = d.textlength(" ", font=f)
        widths = [d.textlength(wd, font=f) for wd in words]
        total = sum(widths) + space_w * (len(words) - 1)
        x = (W - total) / 2
        y = H * 0.40
        per = 0.28
        for i, wd in enumerate(words):
            wt = t - 0.35 - i * per
            a = ease(wt / 0.30) if wt > 0 else 0
            if a > 0:
                aa = int(255 * a)
                d.text((x + 4, y + 4), wd, font=f, fill=(0, 0, 0, aa // 2))
                d.text((x, y), wd, font=f, fill=(245, 243, 240, aa))
            x += widths[i] + space_w
        caption_bar(frame, "" if len(words) > 3 else sc["caption"], 0.0)  # keep lower third clean
    else:  # end
        d = ImageDraw.Draw(frame, "RGBA")
        # play button scales in with overshoot
        e = ease(min(1.0, t / 0.7))
        osc = 1 + 0.12 * math.sin(min(1.0, t / 0.7) * math.pi) * (1 - e)
        r = int(150 * e * osc) + 2
        cx0, cy0 = W // 2, int(H * 0.36)
        if r > 4:
            d.ellipse([cx0 - r, cy0 - r, cx0 + r, cy0 + r], fill=(220, 38, 38, 255))
            tri = int(r * 0.52)
            d.polygon([(cx0 - tri // 2 + tri * 0.18, cy0 - tri), (cx0 - tri // 2 + tri * 0.18, cy0 + tri),
                       (cx0 - tri // 2 + tri * 0.18 + int(tri * 1.5), cy0)], fill=(245, 243, 240, 255))
        f1 = ImageFont.truetype(FONT_B, 132)
        wtxt = "DEYOUNG"
        tw = d.textlength(wtxt, font=f1)
        a = int(255 * ease((t - 0.5) / 0.5))
        if a > 0:
            d.text(((W - tw) / 2 + 5, H * 0.52 + 5), wtxt, font=f1, fill=(0, 0, 0, a // 2))
            d.text(((W - tw) / 2, H * 0.52), wtxt, font=f1, fill=(245, 243, 240, a))
        f2 = ImageFont.truetype(FONT_R, 46)
        st = "SIXTY SECONDS. ONE PASS."
        sw2 = d.textlength(st, font=f2)
        a2 = int(220 * ease((t - 0.9) / 0.5))
        if a2 > 0:
            d.text(((W - sw2) / 2, H * 0.70), st, font=f2, fill=(220, 38, 38, a2))
        f3 = ImageFont.truetype(FONT_B, 34)
        st3 = "deyoung.site  \u2014  BOOK NOW"
        sw3 = d.textlength(st3, font=f3)
        a3 = int(180 * ease((t - 1.3) / 0.5))
        if a3 > 0:
            d.text(((W - sw3) / 2, H * 0.79), st3, font=f3, fill=(255, 255, 255, a3))

    # dip-to-black at both ends of the scene (except film start)
    fi_total = int(round(sc["dur"] * FPS))
    fade_in = 6 if sc["start"] > 0.01 else 0
    fade_out = 6
    if fade_in and fi < fade_in:
        k = fi / fade_in
        frame = Image.blend(Image.new("RGB", (W, H), (0, 0, 0)), frame, k)
    if fi > fi_total - fade_out:
        k = (fi_total - fi) / fade_out
        frame = Image.blend(Image.new("RGB", (W, H), (0, 0, 0)), frame, max(0.0, k))
    return frame


# ---------- render all frames ----------

if os.path.exists(FRAMES):
    shutil.rmtree(FRAMES)
os.makedirs(FRAMES)
idx = 0
for sc in timeline:
    n = int(round(sc["dur"] * FPS))
    skip_talk_only = os.environ.get("RENDER") == "talk-only"
    print(f"render {sc['id']} ({n} frames)")
    for fi in range(n):
        path = f"{FRAMES}/f{idx:05d}.jpg"
        if skip_talk_only and sc["kind"] != "talk" and os.path.exists(path):
            idx += 1
            continue
        compose_frame(sc, fi).save(path, quality=92)
        idx += 1
print(f"frames: {idx}")

# ---------- encode video ----------

sh(f"ffmpeg -y -framerate {FPS} -i {FRAMES}/f%05d.jpg -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p {OUT}/v7_silent.mp4", "video")

# ---------- audio: HPF voice, sidechain-ducked music, limiter, loudnorm ----------

sh(
    f"ffmpeg -y -i {OUT}/v7_silent.mp4 -i {V6}/out/music.wav -i {OUT}/voice_master.wav -filter_complex "
    "\"[2:a]highpass=f=85,acompressor=threshold=0.08:ratio=2.5:attack=8:release=120[vox];"
    "[1:a]volume=0.14,afade=t=in:d=1.2,afade=t=out:st=" f"{TOTAL-2.2}" ":d=2.2[bg];"
    "[bg][vox]sidechaincompress=threshold=0.015:ratio=9:attack=25:release=350:makeup=1[duck];"
    "[duck][vox]amix=inputs=2:duration=first:dropout_transition=0,alimiter=limit=0.9,loudnorm=I=-16:TP=-1.5:LRA=11[a]\" "
    f"-map 0:v -map \"[a]\" -c:v copy -c:a aac -b:a 192k -movflags +faststart -shortest {OUT}/deyoung-film-v7.mp4",
    "mix",
)

print("DONE", f"{OUT}/deyoung-film-v7.mp4")
