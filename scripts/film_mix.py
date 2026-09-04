#!/usr/bin/env python3
"""Mix DeYoung film: drone score + character voice-over, duck score under dialogue.
Output: master (campaign/film/deyoung-film-voice.mp4) + web (public/video/deyoung-film-web.mp4).
"""
import subprocess, sys, os

BASE = "/home/z/my-project"
F = f"{BASE}/campaign/film"
V = f"{BASE}/campaign/voices"

# id, file, offset_ms, gain_db
CLIPS = [
    ("v01", f"{V}/v01-narrator.wav",  700,  5.0),   # s01  0-5   "Every story deserves the big screen."
    ("v02", f"{V}/v02-amara.wav",    5700,  3.8),   # s02  5-15  Amara
    ("v03", f"{V}/v03-kojo.wav",    15700,  5.0),   # s03 15-25  Kojo
    ("v06a", f"{V}/v06a-amara.wav", 35900,  0.8),   # s06 35-45  "Write it."
    ("v06b", f"{V}/v06b-kojo.wav",  37600,  3.2),   # s06        "We roll the cameras."
    ("v07", f"{V}/v07-endcard.wav", 55400,  5.5),   # endcard 55-60
]

TRIM = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.03,"
        "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.06,areverse")
VO_CHAIN = (f"{TRIM},highpass=f=85,acompressor=threshold=-19dB:ratio=2.5:attack=8:release=180:makeup=2,"
            "volume={gain}dB,aresample=44100,aformat=channel_layouts=stereo,"
            "adelay={off}|{off}")

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-1200:]); sys.exit(f"FAIL: {' '.join(cmd[:6])}…")

def main():
    inputs = ["-i", f"{F}/score.m4a"]
    for _, path, _, _ in CLIPS:
        inputs += ["-i", path]

    parts, labels = [], []
    for i, (vid, _, off, gain) in enumerate(CLIPS, start=1):
        chain = VO_CHAIN.format(gain=gain, off=off)
        parts.append(f"[{i}:a]{chain}[{vid}]")
        labels.append(f"[{vid}]")
    # sum all voices (pad to 61s so the duck key never ends before the picture)
    parts.append(f"{''.join(labels)}amix=inputs={len(CLIPS)}:duration=longest:normalize=0,apad=whole_dur=61[vox]")
    # split voice bus: one copy for final mix, one as ducking key
    parts.append("[vox]asplit=2[voxmix][duck]")
    # duck the score while anyone speaks
    parts.append("[0:a][duck]sidechaincompress=threshold=0.045:ratio=5:attack=40:release=350[ducked]")
    # final mix + safety limiter
    parts.append("[ducked][voxmix]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95,"
                 "aformat=sample_rates=44100:channel_layouts=stereo,atrim=0:60[out]")

    mix = f"{F}/score_voiced.m4a"
    run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(parts),
         "-map", "[out]", "-c:a", "aac", "-b:a", "192k", mix])
    print("mix ok", os.path.getsize(mix))

    # mux voiced score with the silent picture
    master = f"{F}/deyoung-film-voice.mp4"
    run(["ffmpeg", "-y", "-i", f"{F}/film_silent.mp4", "-i", mix,
         "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
         "-movflags", "+faststart", "-shortest", master])
    print("master ok", os.path.getsize(master))

    # web encode
    web = f"{BASE}/public/video/deyoung-film-web.mp4"
    run(["ffmpeg", "-y", "-i", master,
         "-vf", "hqdn3d=1.5:1.5:4:4,scale=1280:720",
         "-crf", "27", "-preset", "superfast", "-tune", "fastdecode",
         "-movflags", "+faststart", "-c:v", "libx264", "-c:a", "copy",
         "-nostats", "-loglevel", "error", web])
    print("web ok", os.path.getsize(web))

if __name__ == "__main__":
    main()
