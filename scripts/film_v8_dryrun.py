#!/usr/bin/env python3
"""Dry-run prep for film v8: stand-in assets so the build pipeline can be
validated end-to-end BEFORE the real images/voices finish generating.
Creates:
  - voices: 2-second sine wavs for any missing line (real ones are kept)
  - diptychs: v6 panels copied over any missing v8 diptych
Run film_v8_build.py afterwards, then DELETE this dir to revert.
"""
import os
import shutil
import wave

import numpy as np

BASE = "/home/z/my-project"
V8 = f"{BASE}/campaign/v8"
V6 = f"{BASE}/campaign/v6"

for p in ["v01_hook", "v02_kid", "v03_anime", "v04_stick", "v05_real",
          "v06_styles", "v07_make", "v08_join", "v09_end"]:
    dst = f"{V8}/voices/{p}.wav"
    if os.path.exists(dst):
        continue
    sr = 24000
    dur = 2.0 + (hash(p) % 5) * 0.7  # varied 2..4.8s so timing math is real
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    a = (0.5 * np.sin(2 * np.pi * 220 * t) * 32767).astype("<i2")
    with wave.open(dst, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(a.tobytes())
    print("placeholder voice", p, round(dur, 2), "s")

STANDINS = {
    "kid": f"{V6}/img/amara.png",
    "anime": f"{V6}/img/kossi.png",
    "stick": f"{V6}/img/zola.png",
    "real": f"{V6}/img/dee.png",
}
for name, src in STANDINS.items():
    dst = f"{V8}/img/{name}.png"
    if not os.path.exists(dst):
        shutil.copy(src, dst)
        print("placeholder diptych", name, "from", os.path.basename(src))

print("DRYRUN_ASSETS_READY")
