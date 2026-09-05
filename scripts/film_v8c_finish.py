#!/usr/bin/env python3
"""v8c finisher: frames (already on disk) -> encode -> remastered mux -> QA -> ship."""
import json
import os
import shutil
import subprocess
import sys
import wave

import numpy as np

BASE = "/home/z/my-project"
V8 = f"{BASE}/campaign/v8"
OUT = f"{V8}/out"
FRAMES = f"{V8}/frames"
PUB = f"{BASE}/public/video"
FPS = 30
TOTAL = 65.7


def sh(cmd, tag=""):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FAIL {tag}\n{r.stderr[-1200:]}")
        raise SystemExit(1)
    return r


print("encode video…")
sh(f"ffmpeg -y -framerate {FPS} -i {FRAMES}/f%05d.jpg -c:v libx264 -preset fast "
   f"-crf 18 -pix_fmt yuv420p {OUT}/v8c_silent.mp4", "video")
print("encode done")

print("remaster + mux…")
sh(
    f"ffmpeg -y -i {OUT}/v8c_silent.mp4 -i {OUT}/music.wav -i {OUT}/voice_master2.wav -filter_complex "
    "\"[2:a]highpass=f=85,acompressor=threshold=0.08:ratio=2.5:attack=8:release=120[vox];"
    "[1:a]volume=0.16,afade=t=in:d=1.2,afade=t=out:st=63.5:d=2.2[bg];"
    "[bg][vox]sidechaincompress=threshold=0.015:ratio=9:attack=25:release=350:makeup=1[duck];"
    "[duck][vox]amix=inputs=2:duration=first:dropout_transition=0,alimiter=limit=0.9,"
    "loudnorm=I=-16:TP=-1.5:LRA=11[a]\" "
    f"-map 0:v -map \"[a]\" -c:v copy -c:a aac -b:a 192k -movflags +faststart -shortest "
    f"{OUT}/deyoung-film-v8.mp4",
    "mix",
)

probe = sh(f"ffprobe -v error -show_entries format=duration -show_entries "
           f"stream=codec_name,width,height -of json {OUT}/deyoung-film-v8.mp4", "probe")
meta = json.loads(probe.stdout)
dur = float(meta["format"]["duration"])
vs = [s for s in meta["streams"] if s["codec_name"] == "h264"]
as_ = [s for s in meta["streams"] if s["codec_name"] == "aac"]
black = sh(f"ffmpeg -i {OUT}/deyoung-film-v8.mp4 -vf blackdetect=d=0.5:pix_th=0.02 "
           f"-an -f null - 2>&1 | grep black_start || true", "black")
size = os.path.getsize(f"{OUT}/deyoung-film-v8.mp4")
print(f"QA: dur={dur:.2f}s v={len(vs)} a={len(as_)} size={size/1e6:.1f}MB")
print(f"QA blackdetect: {black.strip() or 'clean'}")
assert dur >= 59.5 and len(vs) == 1 and len(as_) == 1 and size > 3_000_000

shutil.copyfile(f"{OUT}/deyoung-film-v8.mp4", f"{PUB}/deyoung-film-web.mp4")
poster_t = int(9.6 * FPS)  # kid talking, mid-scene
sh(f"ffmpeg -y -i {OUT}/deyoung-film-v8.mp4 -vf \"select=eq(n\\,{poster_t})\" -vframes 1 "
   f"-q:v 3 {PUB}/film-poster.jpg", "poster")
print(f"SHIPPED {PUB}/deyoung-film-web.mp4 ({size/1e6:.1f}MB, {dur:.2f}s) + poster")
