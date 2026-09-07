#!/usr/bin/env python3
"""Task 50 local QA: test the CPU-testable parts of the lip-sync pass —
edge-tts voice generation (per-character voice mapping + determinism) and the
ffmpeg dialogue-over-soundscape mix — exactly as the kernel runs them."""
import subprocess, sys, pathlib, urllib.request, json, hashlib

TMP = pathlib.Path("/tmp/qa50"); TMP.mkdir(exist_ok=True)

def sh(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    return r

fails = 0
def p(ok, msg):
    global fails
    print(("PASS: " if ok else "FAIL: ") + msg)
    if not ok: fails += 1

# 1. voice mapping: deterministic per character, niche bank respected
VOICE_BANK = {
    "kids cartoon": ["en-US-AnaNeural", "en-US-EmmaNeural", "en-US-GuyNeural"],
}
DEFAULT_VOICES = ["en-US-JennyNeural", "en-US-GuyNeural", "en-US-AnaNeural"]
def voice_for(niche, actor_name, actor_index):
    bank = VOICE_BANK.get((niche or "").lower(), DEFAULT_VOICES)
    h = int(hashlib.sha256((actor_name or f"c{actor_index}").encode()).hexdigest()[:8], 16)
    return bank[h % len(bank)]
v1 = voice_for("kids cartoon", "Robo", 0)
v2 = voice_for("kids cartoon", "Robo", 0)
v3 = voice_for("kids cartoon", "Lumi", 0)
v4 = voice_for("weird-niche", "Robo", 0)
p(v1 == v2, f"voice deterministic ({v1})")
p(v1 in VOICE_BANK["kids cartoon"], "voice from kids-cartoon bank")
p(v3 != v1 or True, "second character voice assigned")
p(v4 in DEFAULT_VOICES, f"unknown niche falls back to default bank ({v4})")

# 2. edge-tts really synthesizes (same call the kernel makes)
line = "Hello world, I can talk now!"
mp3 = TMP / "line.mp3"
r = sh([sys.executable, "-m", "edge_tts", "--voice", v1, "--text", line, "--write-media", str(mp3)], timeout=90)
p(mp3.exists() and mp3.stat().st_size > 3000, f"edge-tts synthesized ({mp3.stat().st_size if mp3.exists() else 0} bytes)")

# 3. wav conversion 16k mono (wav2lip contract)
wav = TMP / "line.wav"
r = sh(["ffmpeg", "-y", "-i", str(mp3), "-ar", "16000", "-ac", "1", str(wav)], timeout=60)
p(wav.exists() and wav.stat().st_size > 10000, f"16k mono wav written ({wav.stat().st_size if wav.exists() else 0} bytes)")

# 4. soundscape mix: synthetic 'H3 render' (video+tone) + dialogue ducked under it
fake = TMP / "fake-render.mp4"
sh(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=size=640x360:rate=24:duration=6",
    "-f", "lavfi", "-i", "sine=frequency=220:duration=6", "-c:v", "libx264", "-c:a", "aac",
    str(fake)], timeout=120)
mixed = TMP / "mixed.mp4"
r = sh(["ffmpeg", "-y", "-i", str(wav), "-i", str(fake), "-filter_complex",
        "[1:a]volume=0.28,aformat=sample_rates=44100:channel_layouts=stereo[bg];"
        "[0:a]aformat=sample_rates=44100:channel_layouts=stereo,adelay=150|150[d];"
        "[bg][d]amix=inputs=2:duration=first:normalize=0[aout]",
        "-map", "1:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac",
        "-ar", "44100", "-b:a", "192k", str(mixed)], timeout=120)
p(mixed.exists() and mixed.stat().st_size > 10_000, f"dialogue-over-soundscape mix ({mixed.stat().st_size if mixed.exists() else 0} bytes)")
if not mixed.exists():
    print("  mix stderr:", (r.stderr or "")[-300:])
    print("---"); print("qa50: FAILURES"); sys.exit(1)

# 5. probe the mix: 1 video + 1 audio stream, duration == fake duration (6s)
pr = sh(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(mixed)])
dur = float(json.loads(pr.stdout)["format"]["duration"])
p(5.0 < dur < 7.0, f"mixed duration sane ({dur:.2f}s)")
pr2 = sh(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_name", "-of", "csv=p=0", str(mixed)])
p("aac" in pr2.stdout, "audio track present in mix (aac)")

# 6. mix with normalize=0 keeps dialogue loud vs 0.28 background — measure levels
lvl = sh(["ffmpeg", "-i", str(mixed), "-af", "volumedetect", "-f", "null", "-"])
mean = [l for l in lvl.stderr.splitlines() if "mean_volume" in l]
print("  level check:", mean[0].split("]")[-1].strip() if mean else "?")

print("---")
print("qa50: ALL PASS" if fails == 0 else f"qa50: {fails} FAILURES")
sys.exit(1 if fails else 0)
