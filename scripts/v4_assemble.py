#!/usr/bin/env python3
"""DeYoung promo v4 — FULL TALKING master.

partA = v3.5 master [0:12]  (s1 cartoon boy + s2 stick-man, already captioned+talking)
partB = NEW verified clips s3..s8 (trim to storyboard, caption, loudnorm, fades)
partC = v3.5 master [56:58] (endcard)
All parts encoded with identical params -> concat -c copy -> faststart -> ship.
Usage: python3 scripts/v4_assemble.py [--no-ship]
"""
import os, subprocess, sys

BASE = "/home/z/my-project/campaign/film/v3"
CLIPS = f"{BASE}/clips"
MASTER35 = "/home/z/my-project/public/video/deyoung-film-web.mp4"
OUT_MASTER = f"{BASE}/deyoung-film-v4-web.mp4"
PUBLIC = "/home/z/my-project/public/video/deyoung-film-web.mp4"
FONT = "/home/z/my-project/public/fonts/Archivo.ttf"

# storyboard: s1 7 + s2 5 (in partA) | new: s3 7, s4 7, s5 7, s6 7, s7 8, s8 8 | endcard 2
NEW_SEGS = [
    ("s3", 7.0, "It’s already making my video."),
    ("s4", 7.0, "Watch it build — scene by scene."),
    ("s5", 7.0, "My movie arrived. Ready to post."),
    ("s6", 7.0, "Same prompt. Every style you can imagine."),
    ("s7", 8.0, "Straight to my feed. Zero editing."),
    ("s8", 8.0, "DeYoung. If you can say it, you can film it."),
]

V_ENC = ["-c:v", "libx264", "-preset", "medium", "-profile:v", "high", "-r", "30",
         "-pix_fmt", "yuv420p", "-crf", "22", "-maxrate", "2100k", "-bufsize", "4200k"]
A_ENC = ["-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2"]

def sh(cmd, timeout=420):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        print("CMD FAIL:", cmd[:200], "\n", r.stderr[-600:])
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
    return t.replace("\\", "").replace(":", "\\:").replace("'", "")

def caption_vf(dur, line):
    text = esc(line)
    return (
        f"drawtext=fontfile={FONT}"
        f":text='{text}':fontsize=58:fontcolor=white"
        ":borderw=4:bordercolor=black:shadowx=0:shadowy=3:shadowcolor=black@0.6"
        f":x=(w-tw)/2:y=h-170:enable='between(t,0.40,{dur-0.20:.2f})'"
    )

def build_new(sid, dur, line):
    out = f"{BASE}/segv4_{sid}.mp4"
    if os.path.exists(out) and os.path.getsize(out) > 300000:
        print(f"seg {sid}: exists, skip"); return out
    clip = f"{CLIPS}/{sid}.mp4"
    actual = probe_dur(clip)
    if actual < 2.0:
        print(f"seg {sid}: clip too short ({actual:.2f}s)"); sys.exit(3)
    if actual < dur:
        print(f"seg {sid}: target {dur}s > clip {actual:.2f}s — using {actual-0.05:.2f}s")
        dur = actual - 0.05
    vf = ("scale=1920:1080:force_original_aspect_ratio=decrease,"
          "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,"
          + caption_vf(dur, line) + ","
          + f"fade=t=in:st=0:d=0.25,fade=t=out:st={dur-0.22:.2f}:d=0.22")
    af = (f"loudnorm=I=-16:TP=-1.5:LRA=11,"
          f"afade=t=in:st=0:d=0.12,afade=t=out:st={dur-0.25:.2f}:d=0.25")
    sh(f'ffmpeg -y -loglevel error -i "{clip}" -t {dur} '
       f'-vf "{vf}" -af "{af}" {" ".join(V_ENC)} {" ".join(A_ENC)} -movflags +faststart "{out}"')
    print(f"seg {sid}: built {dur}s")
    return out

def cut_master(start, dur, out):
    if os.path.exists(out) and os.path.getsize(out) > 100000:
        print(f"part {os.path.basename(out)}: exists, skip"); return out
    vf = (f"fade=t=out:st={dur-0.22:.2f}:d=0.22" if start > 0
          else "fade=t=in:st=0:d=0.25,fade=t=out:st=11.78:d=0.22")
    af = f"afade=t=out:st={dur-0.25:.2f}:d=0.25"
    sh(f'ffmpeg -y -loglevel error -ss {start} -i "{MASTER35}" -t {dur} '
       f'-vf "{vf}" -af "loudnorm=I=-16:TP=-1.5:LRA=11,{af}" '
       f'{" ".join(V_ENC)} {" ".join(A_ENC)} -movflags +faststart "{out}"')
    print(f"part {os.path.basename(out)}: built ({start}s+{dur}s)")
    return out

def main():
    ship = "--no-ship" not in sys.argv
    if not os.path.exists(MASTER35):
        print("v3.5 master missing — abort"); sys.exit(2)
    segs = [cut_master(0, 12.0, f"{BASE}/segv4_partA.mp4")]
    for sid, dur, line in NEW_SEGS:
        if not os.path.exists(f"{CLIPS}/{sid}.mp4"):
            print(f"missing clip {sid} — abort"); sys.exit(2)
        segs.append(build_new(sid, dur, line))
    segs.append(cut_master(56.0, 2.0, f"{BASE}/segv4_partC.mp4"))
    lst = f"{BASE}/concatv4.txt"
    with open(lst, "w") as f:
        for s in segs:
            f.write(f"file '{s}'\n")
    sh(f'ffmpeg -y -loglevel error -f concat -safe 0 -i "{lst}" -c copy -movflags +faststart "{OUT_MASTER}"')
    total = probe_dur(OUT_MASTER)
    mb = os.path.getsize(OUT_MASTER) / 1e6
    print(f"master v4: {total:.2f}s, {mb:.1f}MB")
    if ship:
        sh(f'cp "{OUT_MASTER}" "{PUBLIC}"')
        os.makedirs("/home/z/my-project/download", exist_ok=True)
        sh(f'cp "{OUT_MASTER}" "/home/z/my-project/download/deyoung-film-v4-web.mp4"')
        print("SHIPPED to public/video/deyoung-film-web.mp4")

if __name__ == "__main__":
    main()
