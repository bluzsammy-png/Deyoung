#!/usr/bin/env python3
"""DeYoung promo v5 — POST-DUBBED full-talking master.

Every scene: real generated clip (muted) + clean TTS dub + caption + fades.
partA = v3.5 master [0:12] video (s1+s2 captions baked) + dubs s1/s2.
s3..s8 = clips from CLIPS dir; MISSING scenes fall back to v3.5 master still
segments (music kept, dub layered).
partC = v3.5 master [56:58] endcard.
Usage: python3 scripts/v5_assemble.py [--no-ship]
"""
import os, subprocess, sys

BASE = "/home/z/my-project/campaign/film/v3"
CLIPS, DUB = f"{BASE}/clips", f"{BASE}/dub"
MASTER35 = "/home/z/my-project/public/video/deyoung-film-web.mp4"
OUT_MASTER = f"{BASE}/deyoung-film-v5-web.mp4"
PUBLIC = "/home/z/my-project/public/video/deyoung-film-web.mp4"
FONT = "/home/z/my-project/public/fonts/Archivo.ttf"

# id, target dur, caption, master-fallback bounds (None if clip expected)
SEGS = [
    ("s3", 7.0, "It’s already making my video.", (12.0, 19.0)),
    ("s4", 7.0, "Watch it build — scene by scene.", (19.0, 26.0)),
    ("s5", 7.0, "My movie arrived. Ready to post.", (26.0, 33.0)),
    ("s6", 7.0, "Same prompt. Every style you can imagine.", (33.0, 40.0)),
    ("s7", 8.0, "Straight to my feed. Zero editing.", (40.0, 48.0)),
    ("s8", 8.0, "DeYoung. If you can say it, you can film it.", (48.0, 56.0)),
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
    return (
        f"drawtext=fontfile={FONT}"
        f":text='{esc(line)}':fontsize=58:fontcolor=white"
        ":borderw=4:bordercolor=black:shadowx=0:shadowy=3:shadowcolor=black@0.6"
        f":x=(w-tw)/2:y=h-170:enable='between(t,0.40,{dur-0.20:.2f})'"
    )

def fit_dub(path, window):
    """If dub longer than window, atempo it. Returns fitted wav path."""
    out = path.replace(".wav", "_fit.wav")
    d = probe_dur(path)
    if d > window > 0:
        tempo = min(1.45, d / window + 0.03)
        sh(f'ffmpeg -y -loglevel error -i "{path}" -af "atempo={tempo:.4f}" "{out}"')
        return out
    sh(f'cp "{path}" "{out}"')
    return out

def build_seg(sid, dur, line, fb):
    out = f"{BASE}/segv5_{sid}.mp4"
    if os.path.exists(out) and os.path.getsize(out) > 300000:
        print(f"seg {sid}: exists, skip"); return out
    clip = f"{CLIPS}/{sid}.mp4"
    use_clip = os.path.exists(clip) and probe_dur(clip) >= 2.0
    dubs = [p for p in os.listdir(DUB)
            if p.endswith(".wav") and "_fit" not in p and "_trim" not in p
            and (p == f"{sid}.wav"
                 or (p.startswith(sid) and len(p) > len(sid) + 4
                     and p[len(sid)].isalpha() and p[len(sid)].islower()))]
    dubs = sorted(dubs)
    # fit dubs
    n = len(dubs)
    fitted = []
    for i, p in enumerate(dubs):
        win = (dur - 1.2) / max(1, n) - (0.15 if i else 0)
        fitted.append(fit_dub(f"{DUB}/{p}", win))
    if use_clip:
        actual = probe_dur(clip)
        if actual < dur:
            print(f"seg {sid}: clip {actual:.2f}s < {dur}s — using {actual-0.05:.2f}s")
            dur = actual - 0.05
        vf = ("scale=1920:1080:force_original_aspect_ratio=decrease,"
              "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,"
              + caption_vf(dur, line) + ","
              + f"fade=t=in:st=0:d=0.25,fade=t=out:st={dur-0.22:.2f}:d=0.22")
        inputs = f'-i "{clip}"'
        for fp in fitted:
            inputs += f' -i "{fp}"'
        # delay each dub: i-th starts at 0.6 + i*(dur/n)
        fc_parts, mix_in = [], ""
        for i, fp in enumerate(fitted):
            start = int((0.6 + i * (dur - 1.0) / max(1, n)) * 1000)
            fc_parts.append(f"[{i+1}:a]adelay={start}|{start},apad[a{i}]")
            mix_in += f"[a{i}]"
        fc_parts.append(f"{mix_in}amix=inputs={len(fitted)}:normalize=0,"
                        f"loudnorm=I=-16:TP=-1.5:LRA=11,"
                        f"afade=t=in:st=0:d=0.12,afade=t=out:st={dur-0.25:.2f}:d=0.25[aout]")
        fc = ";".join(fc_parts)
        sh(f'ffmpeg -y -loglevel error {inputs} -t {dur} '
           f'-filter_complex "{fc}" -map 0:v:0 -map "[aout]" '
           f'-vf "{vf}" {" ".join(V_ENC)} {" ".join(A_ENC)} -movflags +faststart "{out}"')
        print(f"seg {sid}: REAL clip + {len(fitted)} dub(s), {dur}s")
    else:
        start, end = fb
        dur = end - start
        vf = caption_vf(dur, line) if False else "null"  # captions already burned in stills
        inputs = f'-ss {start} -i "{MASTER35}"'
        for fp in fitted:
            inputs += f' -i "{fp}"'
        fc_parts = []
        music_idx = len(fitted) + 1
        fc_parts.append(f"[0:a]volume=0.5[am]")
        mix_in = "[am]"
        for i, fp in enumerate(fitted):
            st_ms = int((0.8 + i * 2.0) * 1000)
            fc_parts.append(f"[{i+1}:a]adelay={st_ms}|{st_ms},apad[ad{i}]")
            mix_in += f"[ad{i}]"
        fc_parts.append(f"{mix_in}amix=inputs={len(fitted)+1}:normalize=0,"
                        f"loudnorm=I=-16:TP=-1.5:LRA=11,"
                        f"afade=t=out:st={dur-0.3:.2f}:d=0.3[aout]")
        fc = ";".join(fc_parts)
        sh(f'ffmpeg -y -loglevel error {inputs} -t {dur} '
           f'-filter_complex "{fc}" -map 0:v:0 -map "[aout]" '
           f'-vf "fade=t=out:st={dur-0.22:.2f}:d=0.22" '
           f'{" ".join(V_ENC)} {" ".join(A_ENC)} -movflags +faststart "{out}"')
        print(f"seg {sid}: FALLBACK still + {len(fitted)} dub(s), {dur}s")
    return out

def build_partA():
    out = f"{BASE}/segv5_partA.mp4"
    if os.path.exists(out) and os.path.getsize(out) > 300000:
        print("partA: exists, skip"); return out
    d1 = fit_dub(f"{DUB}/s1.wav", 5.8)
    d2 = fit_dub(f"{DUB}/s2.wav", 3.8)
    fc = ("[1:a]adelay=700|700,apad[a1];[2:a]adelay=7800|7800,apad[a2];"
          "[a1][a2]amix=inputs=2:normalize=0,"
          "loudnorm=I=-16:TP=-1.5:LRA=11,"
          "afade=t=out:st=11.75:d=0.25[aout]")
    sh(f'ffmpeg -y -loglevel error -i "{MASTER35}" -i "{d1}" -i "{d2}" -t 12 '
       f'-filter_complex "{fc}" -map 0:v:0 -map "[aout]" '
       f'{" ".join(V_ENC)} {" ".join(A_ENC)} -movflags +faststart "{out}"')
    print("partA: built (s1+s2 video, fresh dubs)")
    return out

def build_partC():
    out = f"{BASE}/segv5_partC.mp4"
    if os.path.exists(out) and os.path.getsize(out) > 100000:
        print("partC: exists, skip"); return out
    sh(f'ffmpeg -y -loglevel error -ss 56 -i "{MASTER35}" -t 2 '
       f'-vf "fade=t=out:st=1.78:d=0.22" -af "loudnorm=I=-16:TP=-1.5:LRA=11" '
       f'{" ".join(V_ENC)} {" ".join(A_ENC)} -movflags +faststart "{out}"')
    print("partC: built (endcard)")
    return out

def main():
    ship = "--no-ship" not in sys.argv
    if not os.path.exists(MASTER35):
        print("v3.5 master missing — abort"); sys.exit(2)
    segs = [build_partA()]
    for sid, dur, line, fb in SEGS:
        segs.append(build_seg(sid, dur, line, fb))
    segs.append(build_partC())
    lst = f"{BASE}/concatv5.txt"
    with open(lst, "w") as f:
        for s in segs:
            f.write(f"file '{s}'\n")
    sh(f'ffmpeg -y -loglevel error -f concat -safe 0 -i "{lst}" -c copy -movflags +faststart "{OUT_MASTER}"')
    total = probe_dur(OUT_MASTER)
    mb = os.path.getsize(OUT_MASTER) / 1e6
    print(f"master v5: {total:.2f}s, {mb:.1f}MB")
    if ship:
        sh(f'cp "{OUT_MASTER}" "{PUBLIC}"')
        os.makedirs("/home/z/my-project/download", exist_ok=True)
        sh(f'cp "{OUT_MASTER}" "/home/z/my-project/download/deyoung-film-v5-web.mp4"')
        print("SHIPPED to public/video/deyoung-film-web.mp4")

if __name__ == "__main__":
    main()
