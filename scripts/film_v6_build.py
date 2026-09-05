#!/usr/bin/env python3
"""DeYoung film v6 — TALKING CHARACTERS build.

For each talking scene: crop the diptych into closed/open mouth panels,
analyze the TTS wav envelope, and lip-flap the panels in sync with speech
(hysteresis + min-state so it reads as natural cartoon talking).
Non-talking scenes get gentle push-in motion. Subtitles are baked per line,
synth music bed ducked under the dialogue, loudness-normalized master.

Output: /home/z/my-project/campaign/v6/out/deyoung-film-v6.mp4 (1920x1080/30)
"""
import json
import math
import os
import struct
import subprocess
import wave

import numpy as np

BASE = "/home/z/my-project"
V6 = f"{BASE}/campaign/v6"
IMG = f"{V6}/img"
VOX = f"{V6}/voices"
OUT = f"{V6}/out"
os.makedirs(OUT, exist_ok=True)

FONT = f"{BASE}/scripts/Archivo.ttf"
FPS = 30
W, H = 1920, 1080
DURS = json.load(open(f"{VOX}/durations.json"))

# id, kind (talk|still|end), asset, voice file, subtitle, lead (s before voice)
SCENES = [
    ("s01", "still", f"{IMG}/hook.png",     "n01_hook",     "EVERY STORY DESERVES THE BIG SCREEN.", 0.6),
    ("s02", "talk",  f"{IMG}/amara.png",    "n02_amara",    "Your story deserves more than fifteen seconds.", 0.45),
    ("s03", "talk",  f"{IMG}/kossi.png",    "n03_kossi",    "DeYoung gives it a full sixty.", 0.45),
    ("s04", "talk",  f"{IMG}/zola.png",     "n04_zola",     "Type your story. Pick your length.", 0.35),
    ("s05", "still", f"{IMG}/alive.png",    "n05_alive",    "And watch it come alive.", 0.5),
    ("s06", "talk",  f"{IMG}/dee.png",      "n06_dee",      "Write it. We roll the cameras.", 0.4),
    ("s07", "still", f"{IMG}/anywhere.png", "n07_anywhere", "Mobile or web. Your studio travels with you.", 0.45),
    ("s08", "end",   None,                  "n08_end",      "DeYoung. Sixty seconds. One pass.", 0.7),
]
PAD = {"s01": 1.6, "s02": 1.1, "s03": 1.1, "s04": 0.9, "s05": 1.4, "s06": 1.0, "s07": 1.1, "s08": 3.2}


def sh(cmd, tag=""):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FFMPEG_FAIL {tag}\n{r.stderr[-1200:]}")
        raise SystemExit(1)
    return r


def esc(t):
    return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\\\'").replace("%", "\\%")


def wav_dur(p):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
        capture_output=True, text=True).stdout.strip()
    return float(out)


def read_wav(p):
    with wave.open(p, "rb") as w:
        n = w.getnframes()
        ch = w.getnchannels()
        sw = w.getsampwidth()
        sr = w.getframerate()
        raw = w.readframes(n)
    if sw != 2:
        raise SystemExit(f"unexpected sample width {sw} in {p}")
    a = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if ch > 1:
        a = a.reshape(-1, ch).mean(axis=1)
    return a, sr


def flap_timeline(wav_path, lead, scene_dur):
    """Return concat entries [(panel, seconds)] at 30fps for one talking scene."""
    a, sr = read_wav(wav_path)
    hop = int(0.032 * sr)
    n_hops = int(math.ceil(len(a) / hop))
    rms = np.zeros(n_hops)
    for i in range(n_hops):
        seg = a[i * hop:(i + 1) * hop]
        rms[i] = np.sqrt((seg ** 2).mean()) if len(seg) else 0.0
    # smooth
    k = max(1, int(0.06 * sr / hop))
    kernel = np.ones(k) / k
    sm = np.convolve(rms, kernel, mode="same")
    thr_open = max(0.32 * float(sm.max()), 1e-4)
    thr_close = 0.55 * thr_open

    frame = 1.0 / FPS
    total_frames = int(round(scene_dur * FPS))
    voice_start_f = int(round(lead * FPS))
    voice_frames = int(math.ceil((len(a) / sr) * FPS))
    states = []  # per output frame: True=open
    cur_open = False
    since_change = 0
    MIN_OPEN = 3
    MIN_CLOSE = 2
    for f in range(total_frames):
        t = f * frame
        if t < lead - 0.05 or f >= voice_start_f + voice_frames + int(0.12 * FPS):
            speaking_frame = False
        else:
            hf = int((t - lead) * sr) // hop
            hf = min(hf, n_hops - 1)
            v = sm[max(0, hf - 1):hf + 2].mean() if n_hops > 3 else sm[hf]
            speaking_frame = v > (thr_open if cur_open else thr_close)
        prev = cur_open
        if speaking_frame != cur_open:
            # hysteresis with min-state lengths
            need = MIN_OPEN if cur_open else MIN_CLOSE
            if since_change >= need:
                cur_open = speaking_frame
                since_change = 0
        since_change += 1
        states.append(cur_open)
        _ = prev

    # compress to runs
    runs = []
    for f, s in enumerate(states):
        if runs and runs[-1][0] == s:
            runs[-1][1] += 1
        else:
            runs.append([s, 1])
    entries = []
    for s, cnt in runs:
        entries.append(("open" if s else "closed", cnt * frame))
    # ensure last state is closed for a clean cut
    if entries and entries[-1][0] == "open":
        entries[-1] = ("open", entries[-1][1])
    return entries


def panels(char_id):
    """Crop diptych into two 1920x1080 panels (closed, open)."""
    src = f"{IMG}/{char_id}.png"
    for side, xoff in (("closed", 0), ("open", 1)):
        dst = f"{OUT}/{char_id}_{side}.png"
        if os.path.exists(dst):
            continue
        sh(f'ffmpeg -y -i "{src}" -vf "crop=1440:832:{xoff * 1440}:0,scale={W}:-2,'
           f'crop={W}:{H}:0:14" -frames:v 1 "{dst}"', f"panel {char_id}/{side}")


def render_talk(sid, char_id, wav, lead, dur, text):
    entries = flap_timeline(wav, lead, dur)
    lst = f"{OUT}/{sid}_list.txt"
    with open(lst, "w") as f:
        for panel, d in entries:
            f.write(f"file '{OUT}/{char_id}_{panel}.png'\nduration {d:.4f}\n")
        f.write(f"file '{OUT}/{char_id}_{entries[-1][0] if entries else 'closed'}.png'\n")
    t0 = lead
    t1 = min(lead + wav_dur(wav) + 0.3, dur - 0.1)
    vf = (f"fps={FPS},drawtext=fontfile={FONT}:text='{esc(text)}':fontsize=46:fontcolor=white:"
          f"borderw=0:shadowx=2:shadowy=2:shadowcolor=black@0.75:"
          f"x=(w-text_w)/2:y=950:enable='between(t,{t0:.2f},{t1:.2f})',"
          f"fade=t=in:st=0:d=0.35,fade=t=out:st={dur - 0.3:.2f}:d=0.3")
    sh(f'ffmpeg -y -f concat -safe 0 -i "{lst}" -vf "{vf}" -t {dur:.3f} '
       f'-an -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p "{OUT}/{sid}.mp4"', f"talk {sid}")


def render_still(sid, still, wav, lead, dur, text):
    t0 = lead
    t1 = min(lead + wav_dur(wav) + 0.3, dur - 0.1)
    zmax = 1.07
    vf = (f"zoompan=z='1+{zmax - 1:.3f}*on/({int(dur * FPS)})':d=1:"
          f"x='iw/2-(iw/zoom/2)':y='ih/3-(ih/zoom/3)':s={W}x{H}:fps={FPS},"
          f"drawtext=fontfile={FONT}:text='{esc(text)}':fontsize=46:fontcolor=white:"
          f"borderw=0:shadowx=2:shadowy=2:shadowcolor=black@0.75:"
          f"x=(w-text_w)/2:y=950:enable='between(t,{t0:.2f},{t1:.2f})',"
          f"fade=t=in:st=0:d=0.35,fade=t=out:st={dur - 0.3:.2f}:d=0.3")
    sh(f'ffmpeg -y -loop 1 -i "{still}" -vf "{vf}" -t {dur:.3f} '
       f'-an -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p "{OUT}/{sid}.mp4"', f"still {sid}")


def render_end(sid, lead, dur, wav, text):
    from PIL import Image, ImageDraw, ImageFont
    card = f"{OUT}/endcard.png"
    black = Image.new("RGB", (W, H), (10, 10, 10))
    d = ImageDraw.Draw(black)
    # red play mark
    cx, cy, r = W // 2, 330, 150
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(220, 38, 38))
    tri = 62
    d.polygon([(cx - tri * 0.55, cy - tri), (cx - tri * 0.55, cy + tri), (cx + tri, cy)], fill=(255, 255, 255))
    f_big = ImageFont.truetype(f"{BASE}/scripts/ArchivoBlack.ttf", 170)
    f_mid = ImageFont.truetype(FONT, 56)
    f_small = ImageFont.truetype(FONT, 40)
    def center(draw, y, s, font, fill):
        bb = draw.textbbox((0, 0), s, font=font)
        draw.text(((W - (bb[2] - bb[0])) / 2, y), s, font=font, fill=fill)
    center(d, 530, "DEYOUNG", f_big, (255, 255, 255))
    center(d, 760, "SIXTY SECONDS. ONE PASS.", f_mid, (220, 38, 38))
    center(d, 880, "deyoung.site  —  BOOK NOW", f_small, (235, 235, 235))
    black.save(card)
    t0 = lead
    t1 = min(lead + wav_dur(wav) + 0.4, dur - 0.3)
    vf = (f"fps={FPS},drawtext=fontfile={FONT}:text='{esc(text)}':fontsize=44:fontcolor=white:"
          f"borderw=0:shadowx=2:shadowy=2:shadowcolor=black@0.75:"
          f"x=(w-text_w)/2:y=1005:enable='between(t,{t0:.2f},{t1:.2f})',"
          f"fade=t=in:st=0:d=0.4,fade=t=out:st={dur - 0.5:.2f}:d=0.5")
    sh(f'ffmpeg -y -loop 1 -i "{card}" -vf "{vf}" -t {dur:.3f} '
       f'-an -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p "{OUT}/{sid}.mp4"', f"end {sid}")


def synth_music(total):
    """Clean 124 BPM electronic bed, py3.13-safe wav writing."""
    p = f"{OUT}/music.wav"
    if os.path.exists(p):
        return p
    SR = 48000
    N = int(SR * (total + 1.0))
    t = np.arange(N) / SR
    bpm = 124.0
    beat = 60.0 / bpm
    mix = np.zeros(N)

    def add(sig, at):
        i = int(at * SR)
        j = min(N, i + len(sig))
        if j > i:
            mix[i:j] += sig[: j - i]

    def kick():
        n = int(0.28 * SR)
        tt = np.arange(n) / SR
        f = np.linspace(150, 44, n)
        ph = 2 * np.pi * np.cumsum(f) / SR
        return np.sin(ph) * np.exp(-tt * 11) * 0.9

    def hat(open_):
        n = int((0.09 if open_ else 0.04) * SR)
        tt = np.arange(n) / SR
        x = np.random.default_rng(7).uniform(-1, 1, n)
        hp = x - np.concatenate(([0], x[:-1])) * 0.92
        return hp * np.exp(-tt * (38 if open_ else 90)) * 0.16

    def bass(freq, ln):
        n = int(ln * SR)
        tt = np.arange(n) / SR
        e = np.minimum(tt / 0.01, 1) * np.exp(-tt / (ln * 0.7)) * 0.30
        return (np.sin(2 * np.pi * freq * tt) + 0.35 * np.sin(4 * np.pi * freq * tt)) * e

    n_beats = int(total / beat) + 1
    for b in range(n_beats):
        at = b * beat
        add(kick(), at)
        add(hat(b % 2 == 1), at + beat / 2)
        if b % 2 == 0:
            root = 55.0 * (2 ** ((b % 8) // 2 * 0))  # steady A1 pulse
            add(bass(root, beat * 0.9), at)
    # light pad every 4 bars
    n = int(2.0 * SR)
    tt = np.arange(n) / SR
    pad = (np.sin(2 * np.pi * 220 * tt) + np.sin(2 * np.pi * 277.18 * tt) + np.sin(2 * np.pi * 329.63 * tt)) / 3
    pad *= np.minimum(tt / 0.4, 1) * np.exp(-tt / 1.4) * 0.05
    for b in range(0, n_beats, 16):
        add(pad, b * beat)
    # gentle limiter
    mix = np.tanh(mix * 1.4) * 0.9
    st = (np.stack([mix, mix], axis=1) * 32767).astype(np.int16)
    with wave.open(p, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(st.tobytes())
    return p


def main():
    # scene timings
    plan = []
    t = 0.0
    for sid, kind, asset, vox, text, lead in SCENES:
        vd = DURS[vox]
        dur = round(lead + vd + PAD[sid], 2)
        plan.append({"sid": sid, "kind": kind, "asset": asset, "vox": vox, "vox_path": f"{VOX}/{vox}.wav",
                     "text": text, "lead": lead, "vd": vd, "dur": dur, "start": round(t, 2)})
        t += dur
    total = round(t, 2)
    print("plan:")
    for s in plan:
        print(f"  {s['sid']} {s['kind']:5s} start={s['start']:6.2f} dur={s['dur']:5.2f} vox={s['vox']}({s['vd']:.2f}s)")
    print(f"total {total}s")
    json.dump(plan, open(f"{OUT}/plan.json", "w"), indent=2)

    # panels for talkers
    for s in plan:
        if s["kind"] == "talk":
            panels(s["asset"].rsplit("/", 1)[1][:-4])

    # render scenes
    for s in plan:
        dst = f"{OUT}/{s['sid']}.mp4"
        if os.path.exists(dst) and os.path.getsize(dst) > 50000:
            print(f"SKIP render {s['sid']}")
            continue
        if s["kind"] == "talk":
            char_id = s["asset"].rsplit("/", 1)[1][:-4]
            render_talk(s["sid"], char_id, s["vox_path"], s["lead"], s["dur"], s["text"])
        elif s["kind"] == "still":
            render_still(s["sid"], s["asset"], s["vox_path"], s["lead"], s["dur"], s["text"])
        else:
            render_end(s["sid"], s["lead"], s["dur"], s["vox_path"], s["text"])
        print(f"rendered {s['sid']}")

    # music
    music = synth_music(total)

    # dialogue bus
    inputs = []
    filters = []
    for i, s in enumerate(plan):
        inputs.append(f'-i "{s["vox_path"]}"')
        delay = int((s["start"] + s["lead"]) * 1000)
        filters.append(f"[{i + 1}:a]aresample=48000,adelay={delay}|{delay}[d{i}]")
    mix_in = "".join(f"[d{i}]" for i in range(len(plan)))
    fc = ";" .join(filters) + f";{mix_in}amix=inputs={len(plan)}:normalize=0[bus]"

    # final mix: dialogue + music (ducked), loudnorm, mux
    concat_lst = f"{OUT}/concat.txt"
    with open(concat_lst, "w") as f:
        for s in plan:
            f.write(f"file '{OUT}/{s['sid']}.mp4'\n")

    final = f"{OUT}/deyoung-film-v6.mp4"
    sh(f'ffmpeg -y -f concat -safe 0 -i "{concat_lst}" '
       f'-i "{music}" { " ".join(inputs) } '
       f'-filter_complex "[{len(plan) + 1}:a]volume=0.16,afade=t=out:st={total - 2.5:.2f}:d=2.5[m];'
       f'{fc};[bus][m]amix=inputs=2:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11[aout]" '
       f'-map 0:v -map "[aout]" -c:v copy -c:a aac -b:a 192k -movflags +faststart -t {total:.2f} "{final}"',
       "final mix")
    print("FINAL " + final)
    d = wav_dur(final)
    print(f"final duration {d:.2f}s (target {total:.2f}s)")


if __name__ == "__main__":
    main()
