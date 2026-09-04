#!/usr/bin/env python3
"""DeYoung promo v3.5 — INTERIM master while video API is rate-limited.

s1+s2: real generated talking clips (lip-sync audio) — trimmed, captioned, loudnorm.
s3..s8: cinematic Ken Burns motion segments from character plates + burned captions
        + music bed slices from music.wav (64s master bed).
endcard: 2s zoom-fade.
All segments encoded with identical params -> concat -c copy -> faststart.
Usage: python3 scripts/v35_assemble.py [--no-ship]
"""
import os, subprocess, sys

BASE = "/home/z/my-project/campaign/film/v3"
CLIPS, CHARS = f"{BASE}/clips", "/home/z/my-project/campaign/v3/chars"
OUT_MASTER = f"{BASE}/deyoung-film-v35-web.mp4"
PUBLIC = "/home/z/my-project/public/video/deyoung-film-web.mp4"
ENDCARD = f"{BASE}/endcard.png"
MUSIC = f"{BASE}/music.wav"
FONT = "/home/z/my-project/public/fonts/Archivo.ttf"

# (id, dur, caption, kind, motion)
SEGMENTS = [
    ("s1", 7.0, "One sentence. Sixty seconds. Done.", "talk", None),
    ("s2", 5.0, "Sign up? Ten seconds. Three ways.", "talk", None),
    ("s3", 7.0, "It’s already making my video.", "still", "zoom_in"),
    ("s4", 7.0, "Watch it build — scene by scene.", "still", "zoom_pan_r"),
    ("s5", 7.0, "My movie arrived. Ready to post.", "still", "zoom_out"),
    ("s6", 7.0, "Same prompt. Every style you can imagine.", "still", "pan_lr"),
    ("s7", 8.0, "Straight to my feed. Zero editing.", "still", "zoom_in_fast"),
    ("s8", 8.0, "DeYoung. If you can say it, you can film it.", "still", "zoom_out_slow"),
]
ENDCARD_DUR = 2.0
CHAR_FILE = {"s3": "maya", "s4": "yuki", "s5": "bea", "s6": "duo", "s7": "felix", "s8": "lineup"}

V_ENC = ["-c:v", "libx264", "-preset", "medium", "-profile:v", "high", "-r", "30",
         "-pix_fmt", "yuv420p", "-crf", "22", "-maxrate", "2100k", "-bufsize", "4200k"]
A_ENC = ["-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2"]

def sh(cmd, timeout=420):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        print("CMD FAIL:", cmd[:200], "\n", r.stderr[-600:])
        sys.exit(1)

def esc(t):
    return t.replace("\\", "").replace(":", "\\:").replace("'", "")

def caption_vf(dur, line):
    text = esc(line)
    start, end = 0.40, dur - 0.20
    return (
        f"drawtext=fontfile={FONT}"
        f":text='{text}':fontsize=58:fontcolor=white"
        ":borderw=4:bordercolor=black:shadowx=0:shadowy=3:shadowcolor=black@0.6"
        f":x=(w-tw)/2:y=h-170:enable='between(t,{start},{end})'"
    )

def zoompan_expr(motion, dur):
    D = int(dur * 30)
    cx, cy = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    if motion == "zoom_in":
        return f"zoompan=z='min(1.0+0.0009*on,1.20)':x='{cx}':y='{cy}':d={D}:s=1920x1080:fps=30"
    if motion == "zoom_in_fast":
        return f"zoompan=z='min(1.0+0.0013*on,1.25)':x='{cx}':y='{cy}':d={D}:s=1920x1080:fps=30"
    if motion == "zoom_out":
        return f"zoompan=z='max(1.18-0.0009*on,1.0)':x='{cx}':y='{cy}':d={D}:s=1920x1080:fps=30"
    if motion == "zoom_out_slow":
        return f"zoompan=z='max(1.15-0.0007*on,1.0)':x='{cx}':y='{cy}':d={D}:s=1920x1080:fps=30"
    if motion == "zoom_pan_r":
        return (f"zoompan=z='min(1.0+0.0010*on,1.22)':x='(iw-iw/zoom)*(on/{D})'"
                f":y='{cy}':d={D}:s=1920x1080:fps=30")
    if motion == "pan_lr":
        return (f"zoompan=z='1.10':x='(iw-iw/zoom)*(on/{D})'"
                f":y='{cy}':d={D}:s=1920x1080:fps=30")
    raise ValueError(motion)

def build_talk(sid, dur, line):
    out = f"{BASE}/seg35_{sid}.mp4"
    if os.path.exists(out) and os.path.getsize(out) > 300000:
        print(f"seg {sid}: exists, skip"); return out
    vf = ("scale=1920:1080:force_original_aspect_ratio=decrease,"
          "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,"
          + caption_vf(dur, line) + ","
          + f"fade=t=in:st=0:d=0.25,fade=t=out:st={dur-0.22:.2f}:d=0.22")
    af = (f"loudnorm=I=-16:TP=-1.5:LRA=11,"
          f"afade=t=in:st=0:d=0.12,afade=t=out:st={dur-0.25:.2f}:d=0.25")
    sh(f'ffmpeg -y -loglevel error -i "{CLIPS}/{sid}.mp4" -t {dur} '
       f'-vf "{vf}" -af "{af}" {" ".join(V_ENC)} {" ".join(A_ENC)} -movflags +faststart "{out}"')
    print(f"seg {sid}: talk {dur}s built")
    return out

def build_still(sid, dur, line, motion, music_off):
    out = f"{BASE}/seg35_{sid}.mp4"
    if os.path.exists(out) and os.path.getsize(out) > 300000:
        print(f"seg {sid}: exists, skip"); return out
    img = f"{CHARS}/{CHAR_FILE[sid]}.png"
    vf = ("scale=2880:1620:force_original_aspect_ratio=increase,"
          "crop=2880:1620:(iw-2880)/2:(ih-1620)/2,"
          + zoompan_expr(motion, dur) + ","
          + caption_vf(dur, line) + ","
          + f"fade=t=in:st=0:d=0.25,fade=t=out:st={dur-0.22:.2f}:d=0.22")
    af = (f"volume=0.16,afade=t=in:st=0:d=0.8,afade=t=out:st={dur-0.9:.2f}:d=0.9")
    sh(f'ffmpeg -y -loglevel error -i "{img}" -ss {music_off:.2f} -t {dur} -i "{MUSIC}" '
       f'-filter_complex "[0:v]{vf}[vout];[1:a]{af}[aout]" '
       f'-map "[vout]" -map "[aout]" -t {dur} '
       f'{" ".join(V_ENC)} {" ".join(A_ENC)} -movflags +faststart "{out}"')
    print(f"seg {sid}: still {motion} {dur}s built")
    return out

def build_endcard():
    out = f"{BASE}/seg35_end.mp4"
    if os.path.exists(out) and os.path.getsize(out) > 100000:
        print("seg endcard: exists, skip"); return out
    d = ENDCARD_DUR
    vf = (f"zoompan=z='min(1.0+0.04*on/{d*30:.0f},1.06)':d={int(d*30)}:s=1920x1080:fps=30,"
          f"fade=t=in:st=0:d=0.3,fade=t=out:st={d-0.3:.2f}:d=0.3")
    sh(f'ffmpeg -y -loglevel error -loop 1 -i "{ENDCARD}" -f lavfi -i anullsrc=r=44100:cl=stereo '
       f'-filter_complex "[0:v]{vf}[vout]" -map "[vout]" -map 1:a -t {d} '
       f'{" ".join(V_ENC)} {" ".join(A_ENC)} -movflags +faststart "{out}"')
    print("seg endcard: built")
    return out

def main():
    ship = "--no-ship" not in sys.argv
    # cumulative music offsets for still segments
    off, offsets = 0.0, {}
    for sid, dur, _, kind, _ in SEGMENTS:
        if kind == "still":
            offsets[sid] = off
        off += dur
    segs = []
    for sid, dur, line, kind, motion in SEGMENTS:
        if kind == "talk":
            if not os.path.exists(f"{CLIPS}/{sid}.mp4"):
                print(f"missing talk clip {sid} — abort"); sys.exit(2)
            segs.append(build_talk(sid, dur, line))
        else:
            segs.append(build_still(sid, dur, line, motion, offsets[sid]))
    segs.append(build_endcard())
    lst = f"{BASE}/concat35.txt"
    with open(lst, "w") as f:
        for s in segs:
            f.write(f"file '{s}'\n")
    sh(f'ffmpeg -y -loglevel error -f concat -safe 0 -i "{lst}" -c copy -movflags +faststart "{OUT_MASTER}"')
    total = subprocess.run(
        f'ffprobe -v error -show_entries format=duration -of csv=p=0 "{OUT_MASTER}"',
        shell=True, capture_output=True, text=True).stdout.strip()
    mb = os.path.getsize(OUT_MASTER) / 1e6
    print(f"master: {float(total):.2f}s, {mb:.1f}MB")
    if ship:
        sh(f'cp "{OUT_MASTER}" "{PUBLIC}"')
        os.makedirs("/home/z/my-project/download", exist_ok=True)
        sh(f'cp "{OUT_MASTER}" "/home/z/my-project/download/deyoung-film-v35-web.mp4"')
        print("SHIPPED to public/video/deyoung-film-web.mp4")

if __name__ == "__main__":
    main()
