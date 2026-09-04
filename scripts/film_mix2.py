#!/usr/bin/env python3
"""DeYoung film mix v2 — narrator-led.
One narrator voice carries ALL speech (no fake lip-synced dialogue).
- kazi narrator lines at scene-timed offsets
- real room-tone ambience from the native with_audio takes (subtle, under narration)
- drone score ducked under the voice bus, safety limiter, exact 60.000s
Output: campaign/film/deyoung-film-voice.mp4 + public/video/deyoung-film-web.mp4
"""
import subprocess, sys, os

BASE = "/home/z/my-project"
F = f"{BASE}/campaign/film"
V = f"{BASE}/campaign/voices2"
FR = f"{BASE}/campaign/social/frames"

# id, file, offset_ms, gain_db
CLIPS = [
    ("n01", f"{V}/n01.wav",   700,  4.5),  # s01 0-5    "Every story deserves the big screen."
    ("n02", f"{V}/n02.wav",  5600,  3.5),  # s02 5-15   "Your story deserves more than fifteen seconds."
    ("n03", f"{V}/n03.wav", 15600,  4.0),  # s03 15-25  "DeYoung gives it a full sixty."
    ("n04", f"{V}/n04.wav", 25400,  3.5),  # s04+05     "Type your story. Pick your length. ..."
    ("n06", f"{V}/n06.wav", 35600,  4.0),  # s06 35-45  "Write it. We roll the cameras."
    ("n07", f"{V}/n07.wav", 45500,  3.5),  # s07+08     "Mobile or web. ..."
    ("n08", f"{V}/n08.wav", 55200,  4.5),  # endcard    "DeYoung. Sixty seconds. One pass."
]

TRIM = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.03,"
        "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.06,areverse")
VO_CHAIN = (f"{TRIM},highpass=f=85,acompressor=threshold=-19dB:ratio=2.5:attack=8:release=180:makeup=2,"
            "volume={gain}dB,aresample=44100,aformat=channel_layouts=stereo,"
            "adelay={off}|{off}")

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-1500:]); sys.exit(f"FAIL: {' '.join(cmd[:8])}…")

def main():
    inputs = ["-i", f"{F}/score.m4a"]                      # 0
    inputs += ["-i", f"{FR}/s02_audio.mp4"]                # 1 ambience A
    inputs += ["-i", f"{FR}/s03_audio.mp4"]                # 2 ambience B
    for _, path, _, _ in CLIPS:
        inputs += ["-i", path]                             # 3..9

    parts, labels = [], []
    for i, (vid, _, off, gain) in enumerate(CLIPS, start=3):
        chain = VO_CHAIN.format(gain=gain, off=off)
        parts.append(f"[{i}:a]{chain}[{vid}]")
        labels.append(f"[{vid}]")
    parts.append(f"{''.join(labels)}amix=inputs={len(CLIPS)}:duration=longest:normalize=0,apad=whole_dur=61[vox]")
    parts.append("[vox]asplit=2[voxmix][duck]")

    # native room-tone ambience (gibberish speech becomes unintelligible murmur under -22dB + lowpass)
    parts.append("[1:a]lowpass=f=7000,volume=-22dB,aresample=44100,aformat=channel_layouts=stereo,adelay=5000|5000[a2]")
    parts.append("[2:a]lowpass=f=7000,volume=-24dB,aresample=44100,aformat=channel_layouts=stereo,adelay=15000|15000[a3]")
    parts.append("[a2][a3]amix=inputs=2:duration=longest:normalize=0,apad=whole_dur=61[amb]")
    # duck ambience harder while narrator speaks
    parts.append("[amb][duck]sidechaincompress=threshold=0.03:ratio=8:attack=30:release=400[ambd]")

    # duck the score while narrator speaks
    parts.append("[0:a][duck]sidechaincompress=threshold=0.045:ratio=5:attack=40:release=350[scored]")

    parts.append("[scored][ambd][voxmix]amix=inputs=3:duration=first:normalize=0,"
                 "alimiter=limit=0.95,"
                 "aformat=sample_rates=44100:channel_layouts=stereo,atrim=0:60[out]")

    mix = f"{F}/score_voiced2.m4a"
    run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(parts),
         "-map", "[out]", "-c:a", "aac", "-b:a", "192k", mix])
    print("mix ok", os.path.getsize(mix))

    master = f"{F}/deyoung-film-voice.mp4"
    run(["ffmpeg", "-y", "-i", f"{F}/film_silent.mp4", "-i", mix,
         "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
         "-movflags", "+faststart", "-shortest", master])
    print("master ok", os.path.getsize(master))

if __name__ == "__main__":
    main()
