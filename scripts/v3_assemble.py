#!/usr/bin/env python3
"""DeYoung promo v3 — Step 5: assemble final 60s web master.

Per segment: trim -> scale/pad 1080p30 -> loudnorm -> fade -> burn caption (ASS)
All segments encoded with identical params, then concat -c copy + faststart.
Usage: python3 scripts/v3_assemble.py
"""
import json, os, subprocess, sys

BASE = "/home/z/my-project/campaign/film/v3"
CLIPS, CAPS = f"{BASE}/clips", f"{BASE}/caps"
OUT_MASTER = f"{BASE}/deyoung-film-v3-web.mp4"
PUBLIC = "/home/z/my-project/public/video/deyoung-film-web.mp4"
ENDCARD = f"{BASE}/endcard.png"
FONT_DIR = "/home/z/my-project/public/fonts"
os.makedirs(CAPS, exist_ok=True)

# storyboard timings: 6x7s + 8s + 8s + 2s endcard = 60s
SEGMENTS = [
    ("s1", 7.0, "One sentence. Sixty seconds. Done."),
    ("s2", 7.0, "Sign up? Ten seconds. Three ways."),
    ("s3", 7.0, "It's already making my video."),
    ("s4", 7.0, "Watch it build — scene by scene."),
    ("s5", 7.0, "My movie arrived. Ready to post."),
    ("s6", 7.0, "Same prompt. Every style you can imagine."),
    ("s7", 8.0, "Straight to my feed. Zero editing."),
    ("s8", 8.0, "DeYoung. If you can say it, you can film it."),
]
ENDCARD_DUR = 2.0

V_ENC = ["-c:v", "libx264", "-preset", "medium", "-profile:v", "high", "-r", "30",
         "-pix_fmt", "yuv420p", "-crf", "22", "-maxrate", "2100k", "-bufsize", "4200k"]
A_ENC = ["-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2"]

def sh(cmd, timeout=300):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        print("CMD FAIL:", cmd[:160], "\n", r.stderr[-500:])
        sys.exit(1)

def probe_dur(path):
    r = subprocess.run(
        f'ffprobe -v error -show_entries format=duration -of csv=p=0 "{path}"',
        shell=True, capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0

def esc(t):
    # drawtext text escaping (inside single-quoted shell + drawtext colon escape)
    return t.replace("\\", "").replace(":", "\\:").replace("'", "")

def caption_vf(dur, line):
    text = esc(line)
    start, end = 0.40, dur - 0.20
    return (
        "drawtext=fontfile=/home/z/my-project/public/fonts/Archivo.ttf"
        f":text='{text}':fontsize=58:fontcolor=white"
        ":borderw=4:bordercolor=black:shadowx=0:shadowy=3:shadowcolor=black@0.6"
        f":x=(w-tw)/2:y=h-170:enable='between(t,{start},{end})'"
    )

def build_segment(sid, dur, line, idx):
    out = f"{BASE}/seg_{sid}.mp4"
    if os.path.exists(out) and os.path.getsize(out) > 300000:
        print(f"seg {sid}: exists, skip")
        return out
    actual = probe_dur(f"{CLIPS}/{sid}.mp4")
    if actual < 2.0:
        print(f"seg {sid}: clip too short ({actual:.2f}s) — abort"); sys.exit(3)
    if actual < dur:
        print(f"seg {sid}: target {dur}s > clip {actual:.2f}s — using {actual - 0.05:.2f}s")
        dur = actual - 0.05
    vf = (
        "scale=1920:1080:force_original_aspect_ratio=decrease,"
        "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,"
        + caption_vf(dur, line) + ","
        + f"fade=t=in:st=0:d=0.25,fade=t=out:st={dur-0.22:.2f}:d=0.22"
    )
    af = (f"loudnorm=I=-16:TP=-1.5:LRA=11,"
          f"afade=t=in:st=0:d=0.12,afade=t=out:st={dur-0.25:.2f}:d=0.25")
    sh(f'ffmpeg -y -loglevel error -i "{CLIPS}/{sid}.mp4" -t {dur} '
       f'-vf "{vf}" -af "{af}" {" ".join(V_ENC)} {" ".join(A_ENC)} -movflags +faststart "{out}"', timeout=420)
    print(f"seg {sid}: built {dur}s")
    return out

def build_endcard():
    out = f"{BASE}/seg_end.mp4"
    if os.path.exists(out) and os.path.getsize(out) > 100000:
        print("seg endcard: exists, skip")
        return out
    d = ENDCARD_DUR
    vf = (f"zoompan=z='min(1.0+0.04*on/{d*30:.0f},1.06)':d={int(d*30)}:s=1920x1080:fps=30,"
          f"fade=t=in:st=0:d=0.3,fade=t=out:st={d-0.3:.2f}:d=0.3")
    sh(f'ffmpeg -y -loglevel error -loop 1 -i "{ENDCARD}" -f lavfi -i anullsrc=r=44100:cl=stereo '
       f'-filter_complex "[0:v]{vf}[vout]" -map "[vout]" -map 1:a -t {d} '
       f'{" ".join(V_ENC)} {" ".join(A_ENC)} -movflags +faststart "{out}"', timeout=300)
    print("seg endcard: built")
    return out

def main():
    # 0) endcard asset
    if not os.path.exists(ENDCARD) or os.path.getsize(ENDCARD) < 50000:
        sh("python3 /home/z/my-project/scripts/v3_endcard.py")
    # 1) segments
    segs = []
    for i, (sid, dur, line) in enumerate(SEGMENTS):
        if not os.path.exists(f"{CLIPS}/{sid}.mp4"):
            print(f"missing clip {sid} — abort"); sys.exit(2)
        segs.append(build_segment(sid, dur, line, i))
    segs.append(build_endcard())
    # 2) concat
    lst = f"{BASE}/concat.txt"
    with open(lst, "w") as f:
        for s in segs:
            f.write(f"file '{s}'\n")
    sh(f'ffmpeg -y -loglevel error -f concat -safe 0 -i "{lst}" -c copy "{OUT_MASTER}"')
    total = float(subprocess.run(f'ffprobe -v error -show_entries format=duration -of csv=p=0 "{OUT_MASTER}"',
                                 shell=True, capture_output=True, text=True).stdout.strip())
    mb = os.path.getsize(OUT_MASTER) / 1e6
    print(f"master: {total:.2f}s, {mb:.1f}MB")
    # 3) ship to public + download
    sh(f'cp "{OUT_MASTER}" "{PUBLIC}"')
    os.makedirs("/home/z/my-project/download", exist_ok=True)
    sh(f'cp "{OUT_MASTER}" "/home/z/my-project/download/deyoung-film-v3-web.mp4"')
    print("SHIPPED to public/video/deyoung-film-web.mp4")

if __name__ == "__main__":
    main()
