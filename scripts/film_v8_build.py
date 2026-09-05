#!/usr/bin/env python3
"""DeYoung film v8 — "EVERY STYLE" mixed-style commercial (>= 60s).

The user's brief, verbatim constraints:
- NOT one flat 2D/3D look: the commercial must MIX styles like the site
  slideshow — children's cartoon, anime, real life, stick man.
- Voice-over AND characters actually talking (lip-synced), not VO alone.
- Not a second under 60 seconds.

Engine (adapted from the proven v7 build):
- AI diptych talking heads in 4 styles + brand mascot; 3-level lip flap
  (closed / mid / open) driven by a smoothed RMS envelope with hysteresis.
- Montage scene that cuts across the four style worlds while one narrator
  line plays over it.
- Eased ken-burns camera, dip-to-black cuts, broadcast lower-thirds,
  style chips, remastered audio (HPF voice, side-chain ducked music,
  limiter, loudnorm). End pad auto-extends so TOTAL >= 63s.

Output: campaign/v8/out/deyoung-film-v8.mp4 (1920x1080 / 30fps)
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
os.makedirs(OUT, exist_ok=True)

FONT_B = f"{BASE}/scripts/ArchivoBlack.ttf"
FONT_R = f"{BASE}/scripts/Archivo.ttf"
FPS = 30
W, H = 1920, 1080
MW, MH = 2060, 1159  # master > 1080p for ken-burns crop
MIN_TOTAL = 63.0


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


def wav_dur(p):
    a, sr = read_wav(p)
    return len(a) / sr


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


# ---------------- script ----------------------------------------------------
# id, kind, asset(s), voice, caption, chip, lead, pad
SCENES = [
    ("s01", "art", f"{V8}/img/quad.png", "v01_hook",
     "EVERY STYLE.", None, 0.7, 1.5),
    ("s02", "talk2", f"{V8}/img/kid.png", "v02_kid",
     "Hi! I'm your Saturday-morning cartoon!", "CHILDREN'S CARTOON", 0.5, 1.0),
    ("s03", "talk2", f"{V8}/img/anime.png", "v03_anime",
     "Straight out of an anime — powered by one prompt.", "ANIME", 0.5, 1.0),
    ("s04", "talk2", f"{V8}/img/stick.png", "v04_stick",
     "Stick man! Two lines, one big idea.", "STICK FIGURE", 0.5, 1.0),
    ("s05", "talk2", f"{V8}/img/real.png", "v05_real",
     "I am real life — shot like a cinema commercial.", "REAL LIFE", 0.5, 1.0),
    ("s06", "montage",
     [f"{V8}/img/sc_kids.png", f"{V8}/img/sc_anime.png", f"{V8}/img/sc_stick.png", f"{V8}/img/sc_real.png"],
     "v06_styles", None, None, 0.5, 0.8),
    ("s06b", "art", f"{V8}/img/sc_split.png", "v06b_split",
     "SAME PROMPT. TWO WORLDS.", None, 0.5, 0.8),
    ("s07", "art", f"{V8}/img/sc_make.png", "v07_make",
     "TYPE. PICK. ROLL.", None, 0.6, 1.2),
    ("s08", "talk2", f"{V8}/img/host.png", "v08_join",
     "Sign up, pick your plan — your studio comes alive.", "DEYOUNG STUDIO", 0.5, 1.1),
    ("s09", "end", None, "v09_end", None, None, 0.8, 3.4),
]

timeline = []
t_cursor = 0.0
for sid, kind, asset, voice, caption, chip, lead, pad in SCENES:
    vdur = wav_dur(f"{V8}/voices/{voice}.wav") if voice else 0.0
    dur = lead + vdur + pad
    timeline.append({
        "id": sid, "kind": kind, "asset": asset, "voice": voice,
        "caption": caption, "chip": chip, "lead": lead, "pad": pad,
        "voice_dur": vdur, "dur": dur, "start": t_cursor,
        "voice_start": t_cursor + lead,
    })
    t_cursor += dur

# ---- guarantee: never under 60s (user's hard floor); target >= 63s --------
TOTAL = t_cursor
if TOTAL < MIN_TOTAL:
    extra = MIN_TOTAL - TOTAL
    timeline[-1]["pad"] += extra
    timeline[-1]["dur"] += extra
    TOTAL += extra
    print(f"end card extended by {extra:.2f}s to honour the 60s floor")
print(f"total duration {TOTAL:.2f}s")

# ---------------- voice master ---------------------------------------------
a0, SR = read_wav(f"{V8}/voices/{timeline[0]['voice']}.wav")
master = np.zeros(int(math.ceil(TOTAL * SR)) + SR, dtype=np.float32)
for sc in timeline:
    if not sc["voice"]:
        continue
    seg, _ = read_wav(f"{V8}/voices/{sc['voice']}.wav")
    i0 = int(sc["voice_start"] * SR)
    master[i0:i0 + len(seg)] += seg
write_wav(f"{OUT}/voice_master.wav", master[: int(TOTAL * SR) + SR // 2], SR)
json.dump(timeline, open(f"{OUT}/plan.json", "w"), indent=1, default=str)

# ---------------- lip-flap envelope (3 levels + hysteresis) -----------------

def envelope_states(sc):
    seg, _ = read_wav(f"{V8}/voices/{sc['voice']}.wav")
    hop = int(0.025 * SR)
    n_h = int(math.ceil(len(seg) / hop))
    rms = np.zeros(n_h)
    for i in range(n_h):
        s = seg[i * hop:(i + 1) * hop]
        rms[i] = math.sqrt(float((s ** 2).mean())) if len(s) else 0.0
    k = max(1, int(0.07 * SR / hop))
    env = np.convolve(rms, np.ones(k) / k, mode="same")
    env = env / (float(env.max()) or 1e-6)
    total_frames = int(round(sc["dur"] * FPS))
    states, cur, since = [], 0, 0
    MIN_HOLD = 2
    for f in range(total_frames):
        vt = f / FPS - sc["lead"]
        if 0 <= vt <= sc["voice_dur"] + 0.08:
            hf = min(n_h - 1, int(vt * SR) // hop)
            v = float(env[max(0, hf - 1):hf + 2].mean())
            target = 0 if v < 0.16 else 1 if v < 0.55 else 2
        else:
            target = 0
        if target != cur:
            if since >= MIN_HOLD or target == 0:
                cur, since = target, 0
            else:
                since += 1
        else:
            since += 1
        states.append(cur)
    return states


STATES = {sc["id"]: envelope_states(sc) for sc in timeline if sc["kind"] == "talk2"}
print("lip-flap envelopes ready")

# ---------------- diptych panels --------------------------------------------

def load_panels(path):
    """Split a diptych into closed/open full-scene panels (master-sized)."""
    src = Image.open(path).convert("RGB")
    sw, sh_ = src.size
    half = sw // 2
    out = []
    for x0 in (0, half):
        panel = src.crop((x0, 0, x0 + half, sh_))
        pw, ph = panel.size
        scale = max(MW / pw, MH / ph)
        panel = panel.resize((int(pw * scale) + 1, int(ph * scale) + 1), Image.LANCZOS)
        x = (panel.width - MW) // 2
        y = (panel.height - MH) // 2
        out.append(panel.crop((x, y, x + MW, y + MH)))
    closed, open_ = out
    mid = Image.blend(closed, open_, 0.5)
    return closed, mid, open_


PANELS = {}
for sc in timeline:
    if sc["kind"] == "talk2":
        PANELS[sc["id"]] = load_panels(sc["asset"])
print("diptych panels ready")

# ---------------- art backgrounds -------------------------------------------

def grade(img):
    overlay = Image.new("RGB", (MW, MH), (10, 8, 8))
    img = Image.blend(img, overlay, 0.24)
    d = ImageDraw.Draw(img, "RGBA")
    grad = Image.new("L", (MW, MH), 0)
    gdr = ImageDraw.Draw(grad)
    for i in range(240):
        gdr.line([(0, MH - i), (MW, MH - i)], fill=int(130 * (1 - i / 240)))
    img.paste(Image.new("RGB", (MW, MH), (0, 0, 0)), (0, 0), grad)
    return img


def art_bg(path):
    src = Image.open(path).convert("RGB")
    sw, sh_ = src.size
    scale = max(MW / sw, MH / sh_)
    src = src.resize((int(sw * scale) + 1, int(sh_ * scale) + 1), Image.LANCZOS)
    x = (src.width - MW) // 2
    y = (src.height - MH) // 2
    return grade(src.crop((x, y, x + MW, y + MH)))


BG = {}
for sc in timeline:
    if sc["kind"] == "art":
        BG[sc["id"]] = art_bg(sc["asset"])
    elif sc["kind"] == "montage":
        BG[sc["id"]] = [art_bg(p) for p in sc["asset"]]
print("art backgrounds ready")

# ---------------- overlays ---------------------------------------------------

def caption_bar(img, text, alpha=1.0):
    if not text:
        return
    d = ImageDraw.Draw(img, "RGBA")
    f = ImageFont.truetype(FONT_B, 46)
    tw = d.textlength(text, font=f)
    tw = min(tw, W - 220)
    pad = 30
    bw = tw + pad * 2 + 24
    bx, by = (W - bw) // 2, int(H * 0.85)
    a = int(216 * alpha)
    d.rectangle([bx, by, bx + bw, by + 84], fill=(12, 12, 14, a))
    d.rectangle([bx, by, bx + 14, by + 84], fill=(220, 38, 38, a))
    # shrink text if it would overflow (long lines)
    f2 = f
    if d.textlength(text, font=f2) > W - 240:
        f2 = ImageFont.truetype(FONT_B, 38)
    d.text((bx + pad + 24, by + (84 - 46) // 2), text, font=f2, fill=(245, 243, 240, a))


def brand_tick(img, label="DEYOUNG"):
    d = ImageDraw.Draw(img, "RGBA")
    f = ImageFont.truetype(FONT_B, 30)
    d.rectangle([54, 50, 70, 88], fill=(220, 38, 38, 255))
    d.text((88, 52), label, font=f, fill=(255, 255, 255, 170))


def style_chip(img, label, alpha=1.0):
    if not label:
        return
    d = ImageDraw.Draw(img, "RGBA")
    f = ImageFont.truetype(FONT_B, 26)
    tw = d.textlength(label, font=f)
    pad = 20
    bw = tw + pad * 2
    a = int(230 * alpha)
    bx, by = W - bw - 54, 50
    d.rectangle([bx, by, bx + bw, by + 56], fill=(220, 38, 38, a))
    d.text((bx + pad, by + 13), label, font=f, fill=(255, 255, 255, a))


def ken_burns(img, fi, dur, bob_amp=0):
    e = ease(fi / max(1, int(dur * FPS) - 1))
    cw = int(MW - (MW - W) * e)
    chh = int(MH - (MH - H) * e)
    cx = (MW - cw) // 2
    bob = int(bob_amp * math.sin(2 * math.pi * 0.45 * fi / FPS)) if bob_amp else 0
    cy = max(0, min(MH - chh, (MH - chh) // 2 + bob))
    return img.crop((cx, cy, cx + cw, cy + chh)).resize((W, H), Image.BILINEAR)


def scene_frame_fades(fi, total_fi, first):
    fade_in = 6 if not first else 0
    fade_out = 6
    k_in = fi / fade_in if fade_in and fi < fade_in else 1.0
    k_out = (total_fi - fi) / fade_out if fi > total_fi - fade_out else 1.0
    return min(k_in, k_out)


# ---------------- compose ----------------------------------------------------

def compose(sc, fi):
    t = fi / FPS
    total_fi = int(round(sc["dur"] * FPS))
    first = sc["start"] < 0.01

    if sc["kind"] == "talk2":
        mouth = STATES[sc["id"]][min(fi, len(STATES[sc["id"]]) - 1)]
        closed, mid, open_ = PANELS[sc["id"]]
        panel = (closed, mid, open_)[mouth]
        frame = ken_burns(panel, fi, sc["dur"], bob_amp=6)
        cap_alpha = 1.0 if t > sc["lead"] + 0.15 else max(0.0, (t - sc["lead"]) / 0.15)
        caption_bar(frame, sc["caption"], cap_alpha)
        brand_tick(frame)
        style_chip(frame, sc["chip"], cap_alpha)

    elif sc["kind"] == "art":
        frame = ken_burns(BG[sc["id"]], fi, sc["dur"])
        brand_tick(frame)
        # kinetic title
        words = sc["caption"].split()
        d = ImageDraw.Draw(frame, "RGBA")
        f = ImageFont.truetype(FONT_B, 104)
        space_w = d.textlength(" ", font=f)
        widths = [d.textlength(wd, font=f) for wd in words]
        total = sum(widths) + space_w * (len(words) - 1)
        x = (W - total) / 2
        y = H * 0.40
        per = 0.26
        for i, wd in enumerate(words):
            wt = t - 0.35 - i * per
            a = ease(wt / 0.30) if wt > 0 else 0
            if a > 0:
                aa = int(255 * a)
                d.text((x + 4, y + 4), wd, font=f, fill=(0, 0, 0, aa // 2))
                d.text((x, y), wd, font=f, fill=(245, 243, 240, aa))
            x += widths[i] + space_w

    elif sc["kind"] == "montage":
        # 4 style cuts; one narrator line plays over the whole scene.
        n = len(BG[sc["id"]])
        cut = total_fi / n
        idx = min(n - 1, int(fi / cut))
        local_fi = int(fi - idx * cut)
        local_n = int(cut)
        frame = ken_burns(BG[sc["id"]][idx], local_fi, local_n / FPS)
        brand_tick(frame)
        chips = ["CHILDREN'S CARTOON", "ANIME", "STICK FIGURE", "REAL LIFE"]
        # dip between cuts
        boundary = 5
        k = 1.0
        if local_fi < boundary and idx > 0:
            k = local_fi / boundary
        if local_fi > local_n - boundary and idx < n - 1:
            k = min(k, (local_n - local_fi) / boundary)
        if k < 1.0:
            frame = Image.blend(Image.new("RGB", (W, H), (0, 0, 0)), frame, max(0.0, k))
        cap_alpha = 1.0 if t > sc["lead"] + 0.15 else max(0.0, (t - sc["lead"]) / 0.15)
        style_chip(frame, chips[idx], cap_alpha)
        caption_bar(frame, "One engine speaks every visual language.", cap_alpha)

    else:  # end card
        d = ImageDraw.Draw(frame := Image.new("RGB", (W, H), (16, 15, 16)), "RGBA")
        # red glow + dot grid
        glow = Image.new("L", (W, H), 0)
        gd = ImageDraw.Draw(glow)
        gd.ellipse([W * 0.30, H * 0.05, W * 0.70, H * 0.85], fill=60)
        glow = glow.filter(ImageFilter.GaussianBlur(140))
        frame.paste(Image.new("RGB", (W, H), (120, 22, 22)), (0, 0), glow)
        for yy in range(40, H, 56):
            for xx in range(40, W, 56):
                d.ellipse([xx, yy, xx + 3, yy + 3], fill=(255, 255, 255, 8))
        # play button scales in
        e = ease(min(1.0, t / 0.7))
        osc = 1 + 0.12 * math.sin(min(1.0, t / 0.7) * math.pi) * (1 - e)
        r = int(150 * e * osc) + 2
        cx0, cy0 = W // 2, int(H * 0.33)
        if r > 4:
            d.ellipse([cx0 - r, cy0 - r, cx0 + r, cy0 + r], fill=(220, 38, 38, 255))
            tri = int(r * 0.52)
            d.polygon([(cx0 - tri // 2 + tri * 0.18, cy0 - tri),
                       (cx0 - tri // 2 + tri * 0.18, cy0 + tri),
                       (cx0 - tri // 2 + tri * 0.18 + int(tri * 1.5), cy0)],
                      fill=(245, 243, 240, 255))
        f1 = ImageFont.truetype(FONT_B, 128)
        wtxt = "DEYOUNG"
        tw = d.textlength(wtxt, font=f1)
        a = int(255 * ease((t - 0.5) / 0.5))
        if a > 0:
            d.text(((W - tw) / 2 + 5, H * 0.50 + 5), wtxt, font=f1, fill=(0, 0, 0, a // 2))
            d.text(((W - tw) / 2, H * 0.50), wtxt, font=f1, fill=(245, 243, 240, a))
        f2 = ImageFont.truetype(FONT_B, 48)
        st = "EVERY STYLE. EVERY STORY. ONE ENGINE."
        sw2 = d.textlength(st, font=f2)
        a2 = int(220 * ease((t - 0.9) / 0.5))
        if a2 > 0:
            d.text(((W - sw2) / 2, H * 0.67), st, font=f2, fill=(220, 38, 38, a2))
        f3 = ImageFont.truetype(FONT_R, 40)
        st3 = "SIGN UP  —  PICK A PLAN  —  CREATE"
        sw3 = d.textlength(st3, font=f3)
        a3 = int(190 * ease((t - 1.3) / 0.5))
        if a3 > 0:
            d.text(((W - sw3) / 2, H * 0.77), st3, font=f3, fill=(255, 255, 255, a3))

    k = scene_frame_fades(fi, total_fi, first)
    if k < 1.0:
        frame = Image.blend(Image.new("RGB", (W, H), (0, 0, 0)), frame, max(0.0, k))
    return frame


# ---------------- render frames ---------------------------------------------

if os.path.exists(FRAMES):
    shutil.rmtree(FRAMES)
os.makedirs(FRAMES)
idx = 0
for sc in timeline:
    n = int(round(sc["dur"] * FPS))
    print(f"render {sc['id']} ({n} frames)")
    for fi in range(n):
        compose(sc, fi).save(f"{FRAMES}/f{idx:05d}.jpg", quality=92)
        idx += 1
print(f"frames: {idx}")

sh(f"ffmpeg -y -framerate {FPS} -i {FRAMES}/f%05d.jpg -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p {OUT}/v8_silent.mp4", "video")

# ---------------- audio: HPF voice, ducked music, limiter, loudnorm ---------
MUSIC = f"{V6}/out/music.wav"
sh(
    f"ffmpeg -y -i {OUT}/v8_silent.mp4 -i {MUSIC} -i {OUT}/voice_master.wav -filter_complex "
    "\"[2:a]highpass=f=85,acompressor=threshold=0.08:ratio=2.5:attack=8:release=120[vox];"
    "[1:a]volume=0.14,afade=t=in:d=1.2,afade=t=out:st=" f"{TOTAL-2.2}" ":d=2.2[bg];"
    "[bg][vox]sidechaincompress=threshold=0.015:ratio=9:attack=25:release=350:makeup=1[duck];"
    "[duck][vox]amix=inputs=2:duration=first:dropout_transition=0,alimiter=limit=0.9,loudnorm=I=-16:TP=-1.5:LRA=11[a]\" "
    f"-map 0:v -map \"[a]\" -c:v copy -c:a aac -b:a 192k -movflags +faststart -shortest {OUT}/deyoung-film-v8.mp4",
    "mix",
)

print("DONE", f"{OUT}/deyoung-film-v8.mp4", f"{TOTAL:.2f}s")
