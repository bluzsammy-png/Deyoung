#!/usr/bin/env python3
"""Assemble the DeYoung 60s film: normalize clips, grade, subtitles, end card, score.
Usage: python scripts/assemble_film.py [outdir]
"""
import os, subprocess, sys, json

BASE = "/home/z/my-project"
FRAMES = f"{BASE}/campaign/social/frames"
OUT = sys.argv[1] if len(sys.argv) > 1 else f"{BASE}/campaign/film"
os.makedirs(OUT, exist_ok=True)

FONT = f"{BASE}/scripts/Archivo.ttf"
BLACK = f"{BASE}/scripts/ArchivoBlack.ttf"
MARK = f"{BASE}/campaign/social/mark-red.png"

SCENES = [
    # id, dur, text (None = no subtitle), speaker tag (None — narrator-led film v2)
    ("s01", 5.0,  "EVERY STORY DESERVES THE BIG SCREEN.", None),
    ("s02", 10.0, "Your story deserves more than fifteen seconds.", None),
    ("s03", 10.0, "DeYoung gives it a full sixty.", None),
    ("s04", 5.0,  "Type your story. Pick your length.", None),
    ("s05", 5.0,  "And watch it come alive.", None),
    ("s06", 10.0, "Write it. We roll the cameras.", None),
    ("s07", 5.0,  "Mobile or web. Your studio travels with you.", None),
    ("s08", 5.0,  None, None),
]

def esc(t):
    return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\\\'").replace("%", "\\%")

def norm_clip(i, sid, dur, text, tag):
    # narrator-led v2: prefer the re-generated take (with native audio we discard);
    # video is used muted — the single narrator bus carries all speech.
    src_audio = f"{FRAMES}/{sid}_audio.mp4"
    src = src_audio if os.path.exists(src_audio) else f"{FRAMES}/{sid}.mp4"
    dst = f"{OUT}/{sid}_norm.mp4"
    fade_out = dur - 0.35
    vf = [
        "scale=1280:720:force_original_aspect_ratio=increase",
        "crop=1280:720", "fps=30", "setsar=1",
        "eq=contrast=1.06:saturation=1.12:brightness=-0.015",
        "unsharp=5:5:0.4", "vignette=PI/5",
        f"fade=t=in:st=0:d=0.4", f"fade=t=out:st={fade_out:.2f}:d=0.35",
    ]
    if sid == "s08":  # dim silk for end-card text
        vf.append("eq=brightness=-0.12:saturation=0.9")
    if text:
        y = 600 if not tag else 588
        vf.append(
            f"drawtext=fontfile={FONT}:text='{esc(text)}':"
            f"fontsize=38:fontcolor=white:borderw=0:shadowx=2:shadowy=2:shadowcolor=black@0.7:"
            f"x=(w-text_w)/2:y={y}"
        )
        if tag:
            vf.append(
                f"drawtext=fontfile={BLACK}:text='{esc(tag)}':"
                f"fontsize=22:fontcolor=0xF04343:shadowx=1:shadowy=1:shadowcolor=black@0.7:"
                f"x=(w-text_w)/2:y=645"
            )
    cmd = ["ffmpeg", "-y", "-i", src, "-vf", ",".join(vf),
           "-t", f"{dur}", "-an", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", dst]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-600:]); sys.exit(f"norm fail {sid}")
    print("norm", sid)

def end_card():
    """5s brand end card on top of dimmed silk clip (s08)."""
    dst = f"{OUT}/endcard.mp4"
    vf = [
        "scale=1280:720:force_original_aspect_ratio=increase", "crop=1280:720",
        "fps=30", "setsar=1", "eq=brightness=-0.25:saturation=0.85",
        "gblur=sigma=6",
        f"fade=t=in:st=0:d=0.4", "fade=t=out:st=4.55:d=0.45",
    ]
    # logo scales in via zoompan-free approach: overlay with enable + fade using two overlays
    overlay = (
        f"[1:v]scale=170:170[mk];"
        f"[0:v]{','.join(vf)}[bg];"
        f"[bg][mk]overlay=(W-w)/2:170:enable='gte(t,0.5)'[v1];"
    )
    draw1 = (
        f"drawtext=fontfile={BLACK}:text='COMING SOON':fontsize=92:fontcolor=white:"
        f"shadowx=3:shadowy=3:shadowcolor=black@0.8:x=(w-text_w)/2:y=390:enable='gte(t,0.9)'"
    )
    draw2 = (
        f"drawtext=fontfile={FONT}:text='DEYOUNG — 60-SECOND AI FILM':fontsize=34:fontcolor=0xF04343:"
        f"shadowx=2:shadowy=2:shadowcolor=black@0.8:x=(w-text_w)/2:y=520:enable='gte(t,1.2)'"
    )
    cmd = ["ffmpeg", "-y", "-i", f"{FRAMES}/s08.mp4", "-i", MARK,
           "-filter_complex", overlay + f"[v1]{draw1},{draw2}[vout]",
           "-map", "[vout]", "-t", "5", "-an",
           "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", dst]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-800:]); sys.exit("endcard fail")
    print("endcard ok")

def score(total):
    dst = f"{OUT}/score.m4a"
    a = (
        f"aevalsrc='0.20*sin(2*PI*55*t)+0.14*sin(2*PI*110.5*t)+0.05*sin(2*PI*165*t)"
        f"+0.045*sin(2*PI*220*t)*(0.5+0.5*sin(2*PI*0.125*t))"
        f"+0.02*sin(2*PI*330*t)*(0.5+0.5*sin(2*PI*0.05*t+1.5))'"
        f":s=44100:d={total},"
        "lowpass=f=2400,"
        f"afade=t=in:st=0:d=2,afade=t=out:st={total-4}:d=4,"
        "aformat=channel_layouts=stereo"
    )
    r = subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", a, "-c:a", "aac", "-b:a", "160k", dst],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-500:]); sys.exit("score fail")
    print("score ok")

def concat():
    order = [f"{s[0]}_norm" for s in SCENES] + ["endcard"]
    lst = f"{OUT}/list.txt"
    with open(lst, "w") as f:
        for name in order:
            f.write(f"file '{OUT}/{name}.mp4'\n")
    m = f"{OUT}/film_silent.mp4"
    r = subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst,
                        "-c", "copy", m], capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-500:]); sys.exit("concat fail")
    total = sum(s[1] for s in SCENES) + 5.0
    master = f"{OUT}/deyoung-film-master.mp4"
    r = subprocess.run(["ffmpeg", "-y", "-i", m, "-i", f"{OUT}/score.m4a",
                        "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                        "-shortest", master], capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-500:]); sys.exit("mux fail")
    print("master", master, os.path.getsize(master))

for i, (sid, dur, text, tag) in enumerate(SCENES):
    norm_clip(i, sid, dur, text, tag)
end_card()
score(sum(s[1] for s in SCENES) + 5.0)
concat()
