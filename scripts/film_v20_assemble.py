#!/usr/bin/env python3
"""Assemble the v20 20s UGC launch film.

4 scenes (768x1344 -> 1080x1920) + in-scene lip-synced dialogue (u1/u4)
+ narrator VO (vo2/vo3 on the UI/montage scenes) + lo-fi music bed
+ burned UGC captions + domain endcard. loudnorm -14 LUFS.
Output: /home/z/my-project/download/deyoung-ugc-launch-20s.mp4
"""
import pathlib
import subprocess

BASE = pathlib.Path("/home/z/my-project/campaign/film/v20")
CLIPS = BASE / "clips"
FONT = "/home/z/my-project/scripts/ArchivoBlack.ttf"
OUT = pathlib.Path("/home/z/my-project/download/deyoung-ugc-launch-20s.mp4")


def dur(p):
    return float(subprocess.check_output(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)]).strip())


clips = [CLIPS / f"u{i}.mp4" for i in (1, 2, 3, 4)]
for c in clips:
    assert c.exists(), f"missing clip {c}"
durs = [round(dur(c), 3) for c in clips]
b = [0.0, durs[0], durs[0] + durs[1], durs[0] + durs[1] + durs[2]]
total = round(sum(durs), 3)
print("scene durations:", durs, "bounds:", [round(x, 2) for x in b], "total:", total)

vo2 = str(BASE / "vo/vo2_chuichui.wav")
vo3 = str(BASE / "vo/vo3_chuichui.wav")
music = str(BASE / "audio/music.wav")

CAPS = [
    (b[0] + 0.30, durs[0] - 0.10, "I typed ONE sentence...", 58),
    (b[1] + 0.30, b[1] + durs[1] - 0.10, "script + cast + storyboard", 54),
    (b[2] + 0.30, b[2] + durs[2] - 0.10, "rendered LIVE by the GPU fleet", 50),
    (b[3] + 0.30, total - 1.60, "type it. watch it. post it.", 54),
]
END_AT = total - 1.50


def cap_filters():
    parts = []
    for (a, e, txt, sz) in CAPS:
        parts.append(
            f"drawtext=fontfile={FONT}:text='{txt}':fontsize={sz}:fontcolor=white:"
            f"borderw=4:bordercolor=black@0.9:shadowx=3:shadowy=3:shadowcolor=black@0.6:"
            f"x=(w-text_w)/2:y=h-300:enable='between(t\\,{a:.2f}\\,{e:.2f})'")
    parts.append(
        f"drawtext=fontfile={FONT}:text='deyoungltd.site':fontsize=84:fontcolor=white:"
        f"borderw=5:bordercolor=black@0.9:shadowx=4:shadowy=4:shadowcolor=black@0.6:"
        f"x=(w-text_w)/2:y=(h-text_h)/2-40:"
        f"alpha='if(lt(t\\,{END_AT:.2f})\\,0\\,min(1\\,(t-{END_AT:.2f})/0.45))':enable='gte(t\\,{END_AT:.2f})'")
    return ",".join(parts)


vchain = []
for i in range(4):
    vchain.append(
        f"[{i}:v]scale=1080x1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        f"fps=30,trim=duration={durs[i]},setpts=PTS-STARTPTS,setsar=1,format=yuv420p[v{i}]")
vchain.append("[v0][v1][v2][v3]concat=n=4:v=1:a=0[vcat]")
vchain.append(
    f"[vcat]{cap_filters()},fade=t=in:st=0:d=0.3,fade=t=out:st={total - 0.5:.2f}:d=0.5[vout]")


def ms(x):
    return int(round(x * 1000))


achain = [
    # HER dialogue lines (clean TTS, lip movement sells it on screen)
    f"[7:a]aformat=sample_rates=44100:channel_layouts=stereo,atrim=0:5,"
    f"adelay=350|350,volume=2.0[au1]",
    f"[8:a]aformat=sample_rates=44100:channel_layouts=stereo,atrim=0:5,"
    f"adelay={ms(b[3] + 0.25)}|{ms(b[3] + 0.25)},volume=2.0[au4]",
    f"[4:a]aformat=sample_rates=44100:channel_layouts=stereo,atrim=0:5,"
    f"adelay={ms(b[1])}|{ms(b[1])},volume=2.0[av2]",
    f"[5:a]aformat=sample_rates=44100:channel_layouts=stereo,atrim=0:5,"
    f"adelay={ms(b[2])}|{ms(b[2])},volume=2.0[av3]",
    f"[6:a]aformat=sample_rates=44100:channel_layouts=stereo,atrim=0:{total},volume=0.17[am]",
    f"[au1][au4][av2][av3][am]amix=inputs=5:duration=longest:normalize=0,"
    f"atrim=0:{total},loudnorm=I=-14:TP=-1.5:LRA=11,"
    f"afade=t=out:st={total - 0.45:.2f}:d=0.45[aout]",
]

cmd = ["ffmpeg", "-y"]
for c in clips:
    cmd += ["-i", str(c)]
cmd += ["-i", vo2, "-i", vo3, "-i", music,
        "-i", str(BASE / "vo/line_u1.wav"), "-i", str(BASE / "vo/line_u4.wav")]
cmd += [
    "-filter_complex", ";".join(vchain + achain),
    "-map", "[vout]", "-map", "[aout]",
    "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-r", "30",
    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
    "-movflags", "+faststart", str(OUT),
]
r = subprocess.run(cmd, capture_output=True, text=True)
if r.returncode != 0:
    print(r.stderr[-3000:])
    raise SystemExit(1)
print("WROTE", OUT, round(OUT.stat().st_size / 1e6, 1), "MB")
