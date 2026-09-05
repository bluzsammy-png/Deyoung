#!/usr/bin/env python3
"""
DeYoung universal render worker — the PATI-style execution plane.

Runs ANYWHERE (Kaggle GPU kernel, the owner's PC, any GPU/CPU box) with only
the Python standard library + ffmpeg. Loop:

    claim job -> render -> deliver (or fail honestly) -> repeat

Renderers (tried in order — the FALLBACK CHAIN):
    ltx   — LTX-Video (Lightricks, open weights, runs LOCAL on the GPU — no
            paid API, no sandbox dependency). Needs CUDA (Kaggle T4/P100 is
            fine) and `pip install diffusers transformers accelerate`.
    stub  — ffmpeg-only branded placeholder (runs on any CPU, used for QA,
            pipeline verification, and as an automatic fallback)

    auto  — chain "ltx,stub" when CUDA is available, else "stub".
    film  — strict local mode: LTX-Video ONLY (the stub can never stand in
            for a film scene), film framing (960x544 capture), per-scene
            voice synthesis with piper (local, on-device) and clean frames
            (no burned-in caption). Any failure is an honest failure.

Film scene prompts carry a header the worker parses:
    [scene 03|Welcome to DeYoung, where ideas become motion.]
    <the visual prompt continues here>
The bracketed line is what the character/narrator SPEAKS (piper TTS, voice
picked from the job's `voice` field); the rest drives the local model.

Voices (rhasspy/piper-voices, all free/open):
    amy (US female), ryan (US male), lessac (US female), joe (US male),
    alan (GB male), alba (GB female), kathleen (US female, light)
    Modifier "@up" pitches a voice up (kids), "@down" down (deep).

Usage:
    python3 deyoung_worker.py --site https://deeyoung-production-72ef.up.railway.app \
        --token dyw_... --renderer auto --max-minutes 480
Every failure is reported back to the site (action=fail) so the queue never
clogs silently — the owner sees the reason in the admin Video Queue.
"""

import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
import wave

DEFAULT_SITE = "https://deeyoung-production-72ef.up.railway.app"

FONT_CANDIDATES = [
    os.environ.get("DEYOUNG_FONT", ""),
    "/home/z/my-project/public/fonts/Archivo.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]

RESOLUTIONS = {"720p": (1280, 720), "1080p": (1920, 1080)}

SCENE_RE = re.compile(r"^\s*\[scene\s*(?P<num>\d+)\s*\|\s*(?P<line>.*?)\]\s*", re.S)

# rhaspy/piper-voices repo paths (without .onnx / .onnx.json suffix)
PIPER_VOICES = {
    "amy": "en/en_US/amy/medium/en_US-amy-medium",
    "ryan": "en/en_US/ryan/high/en_US-ryan-high",
    "lessac": "en/en_US/lessac/medium/en_US-lessac-medium",
    "joe": "en/en_US/joe/medium/en_US-joe-medium",
    "alan": "en/en_GB/alan/medium/en_GB-alan-medium",
    "alba": "en/en_GB/alba/medium/en_GB-alba-medium",
    "kathleen": "en/en_US/kathleen/low/en_US-kathleen-low",
    "narrator": "en/en_GB/alan/medium/en_GB-alan-medium",
}
HF_PIPER_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main"

# Local open-weights checkpoints, safest-first on 16GB Kaggle GPUs (all 2B).
LTX_CHECKPOINTS = {
    "a": "Lightricks/LTX-Video-0.9.5",
    "b": "Lightricks/LTX-Video-0.9.1",
    "c": "Lightricks/LTX-Video",
}

ARGS = None  # filled by main()


def log(msg):
    print(f"[deyoung-worker {time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------- scene header

def parse_scene(prompt):
    """Split '[scene NN|spoken line]' off the front of a prompt. Returns (scene|None, visual_prompt)."""
    m = SCENE_RE.match(prompt or "")
    if not m:
        return None, prompt or ""
    return {"num": int(m.group("num")), "line": m.group("line").strip()}, prompt[m.end():].strip()


def parse_voice(voice_field):
    """'amy@up' -> ('amy', 1.18). Returns (voice_key, pitch_factor)."""
    key = (voice_field or "").strip().lower() or "narrator"
    pitch = 1.0
    if "@" in key:
        key, mod = key.split("@", 1)
        pitch = {"up": 1.18, "child": 1.22, "down": 0.9}.get(mod.strip(), 1.0)
    if key not in PIPER_VOICES:
        key = "narrator"
    return key, pitch


# ---------------------------------------------------------------- HTTP layer

def http_json(url, payload=None, token="", method=None, timeout=120):
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method or ("POST" if data else "GET"))
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def http_multipart(url, fields, filename, file_bytes, token, timeout=900):
    boundary = "----deyoung" + uuid.uuid4().hex
    buf = io.BytesIO()
    for key, value in fields.items():
        buf.write(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode()
        )
    buf.write(
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: video/mp4\r\n\r\n".encode()
    )
    buf.write(file_bytes)
    buf.write(f"\r\n--{boundary}--\r\n".encode())
    body = buf.getvalue()
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Authorization": f"Bearer {token}",
        },
        method="PATCH",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


# ---------------------------------------------------------------- ffmpeg util

def have_ffmpeg():
    return bool(shutil.which("ffmpeg"))


def pick_font():
    for candidate in FONT_CANDIDATES:
        if candidate and os.path.exists(candidate):
            return candidate
    return None


def wrap_text(text, width=34, max_lines=3):
    words, lines, current = text.split(), [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        if len(trial) <= width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
        if len(lines) == max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    return "\n".join(lines)[: width * max_lines + max_lines]


def run(cmd, timeout=1800):
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"cmd failed ({' '.join(cmd[:3])}…): {proc.stderr[-500:]}")
    return proc


def run_with_budget(fn, minutes):
    """Run fn() on a worker thread; abort (raise) if it exceeds the budget."""
    box = {}

    def target():
        try:
            box["out"] = fn()
        except Exception as exc:
            box["err"] = exc

    th = threading.Thread(target=target, daemon=True)
    th.start()
    th.join(timeout=max(1.0, minutes * 60))
    if th.is_alive():
        raise RuntimeError(f"exceeded per-job budget of {minutes:.0f} min — aborted")
    if "err" in box:
        raise box["err"]
    return box["out"]


def wav_samplerate(path):
    with wave.open(path, "rb") as wf:
        return wf.getframerate()


def encode_final(raw_path, out_path, seconds, width, height, watermark, job_id, vo_wav=None, pitch=1.0, film=False):
    """Normalize to target size, extend the last frame, brand (non-film), add the VO (or a silent track)."""
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},setsar=1,format=yuv420p,"
        # the generated clip may be a hair shorter than the target seconds —
        # freeze the final frame instead of letting the video stream end early
        f"tpad=stop_mode=clone:stop_duration=3"
    )
    if not film and watermark:
        caption = os.path.join(tempfile.gettempdir(), f"dy-cap-{job_id}.txt")
        with open(caption, "w") as fh:
            fh.write(wrap_text(f"DeYoung | {job_id}"))
        font = pick_font()
        if font:
            vf += (
                f",drawtext=fontfile={font}:textfile={caption}:fontsize={28 if height <= 720 else 40}"
                ":fontcolor=white@0.92:box=1:boxcolor=black@0.45:boxborderw=14"
                ":x=(w-text_w)/2:y=h-text_h-40"
                f",drawtext=fontfile={font}:text='DEYOUNG':fontsize={20 if height <= 720 else 28}"
                ":fontcolor=white@0.55:x=w-text_w-30:y=28"
            )

    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", raw_path]
    if vo_wav and os.path.exists(vo_wav):
        rate = wav_samplerate(vo_wav)
        mods = []
        if abs(pitch - 1.0) > 0.01:
            mods.append(f"asetrate={int(rate * pitch)}")
            mods.append(f"aresample={rate}")
            mods.append(f"atempo={1.0 / pitch:.5f}")
        mods += ["loudnorm=I=-15:TP=-1.5:LRA=11", "adelay=250:all=1", "apad"]
        cmd += ["-i", vo_wav, "-filter_complex",
                f"[0:v]{vf}[v];[1:a]{','.join(mods)}[a]",
                "-map", "[v]", "-map", "[a]"]
    else:
        cmd += ["-filter_complex", f"[0:v]{vf}[v]",
                "-map", "[v]",
                "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                "-map", "1:a:0"]

    cmd += [
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
        "-t", str(seconds), "-movflags", "+faststart",
        out_path,
    ]
    run(cmd)
    return out_path


# ---------------------------------------------------------------- local TTS (piper)

_tts_ready = {"checked": False, "ok": False}


def ensure_piper():
    if _tts_ready["checked"]:
        return _tts_ready["ok"]
    _tts_ready["checked"] = True
    try:
        import piper  # noqa: F401
        _tts_ready["ok"] = True
        return True
    except ImportError:
        pass
    proc = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "piper-tts"],
        capture_output=True, text=True, timeout=600,
    )
    if proc.returncode == 0:
        import importlib
        importlib.invalidate_caches()
        try:
            import piper  # noqa: F401
            _tts_ready["ok"] = True
            return True
        except ImportError:
            log(f"piper installed but import failed: {proc.stderr[-200:]}")
    else:
        log(f"piper install failed: {(proc.stderr or proc.stdout)[-200:]}")
    return False


def piper_voice_files(key, cache_dir):
    rel = PIPER_VOICES.get(key)
    if not rel:
        return None, None
    fname = rel.split("/")[-1]
    onnx = os.path.join(cache_dir, fname + ".onnx")
    cfg = onnx + ".json"
    os.makedirs(cache_dir, exist_ok=True)
    for url, dest in ((f"{HF_PIPER_BASE}/{rel}.onnx", onnx), (f"{HF_PIPER_BASE}/{rel}.onnx.json", cfg)):
        if not os.path.exists(dest) or os.path.getsize(dest) < 1000:
            log(f"tts: downloading {os.path.basename(dest)}…")
            tmp = dest + ".part"
            urllib.request.urlretrieve(url, tmp)
            os.replace(tmp, dest)
    return onnx, cfg


def synth_vo(line, voice_key, out_wav, cache_dir):
    """Local, on-device TTS with piper. Returns out_wav or None (honestly unavailable)."""
    if not ensure_piper():
        return None
    try:
        onnx, cfg = piper_voice_files(voice_key, cache_dir)
        if not onnx:
            log(f"tts: unknown voice '{voice_key}'")
            return None
        from piper import PiperVoice
        voice = PiperVoice.load(onnx, cfg) if cfg and os.path.exists(cfg) else PiperVoice.load(onnx)
        if hasattr(voice, "synthesize_wav"):
            # piper >= 1.3: pass a real wave handle; format is set from the first chunk
            with wave.open(out_wav, "wb") as wf:
                voice.synthesize_wav(line, wf)
        else:
            # piper 1.2.x: argument order varies across builds — adapt honestly
            with wave.open(out_wav, "wb") as wf:
                try:
                    voice.synthesize(line, wf)
                except TypeError:
                    voice.synthesize(wf, text=line)
        return out_wav if os.path.getsize(out_wav) > 1000 else None
    except Exception as exc:
        log(f"tts failed: {exc.__class__.__name__}: {exc}")
        return None


# ---------------------------------------------------------------- renderers

def render_stub(job, workdir):
    """Branded ffmpeg-only placeholder — always available, zero deps. NEVER used in film mode."""
    seconds, (width, height) = job["seconds"], RESOLUTIONS.get(job["resolution"], RESOLUTIONS["720p"])
    raw = os.path.join(workdir, "raw.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    bg = (
        f"gradients=s={width}x{height}:d={seconds}:speed=0.06:"
        "c0=0x0A0A0A:c1=0xDC2626:c2=0x1A1A1A:c3=0x450A0A"
    )
    try:
        run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", bg,
             "-frames:v", "1", raw], timeout=120)
    except RuntimeError:
        bg = f"color=c=0x101014:s={width}x{height}:d={seconds}"
    cmd += [
        "-f", "lavfi", "-i", bg,
        "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:d={seconds}",
        "-vf", "format=yuv420p",
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-t", str(seconds), raw,
    ]
    run(cmd)
    return raw


def model_chain(model_name, prefer=None):
    """Map the site's deyo model line onto local LTX checkpoints (all open weights)."""
    name = (model_name or "").lower()
    if name.startswith("deyo-max") or name.startswith("deyo.3"):
        chain = ["a", "b", "c"]
    elif name.startswith("deyo.2"):
        chain = ["a", "c"]
    else:
        chain = ["b", "a", "c"]
    if prefer and prefer in LTX_CHECKPOINTS:
        if prefer in chain:
            chain.remove(prefer)
        chain.insert(0, prefer)
    return chain


def render_ltx(job, workdir, strict=False):
    """LTX-Video (open weights) text-to-video, running locally on the CUDA GPU."""
    try:
        import torch  # noqa
        from diffusers import LTXPipeline
        from diffusers.utils import export_to_video
    except Exception as exc:
        if strict:
            raise RuntimeError(f"ltx unavailable in strict mode ({exc.__class__.__name__}: {exc})")
        log(f"ltx renderer unavailable ({exc.__class__.__name__}: {exc}) — falling back to stub")
        return render_stub(job, workdir)

    if not torch.cuda.is_available():
        if strict:
            raise RuntimeError("no CUDA device — film mode refuses to render on CPU")
        log("no CUDA device — falling back to stub (LTX needs a GPU)")
        return render_stub(job, workdir)

    seconds = job["seconds"]
    scene, _visual = parse_scene(job["prompt"])
    film = scene is not None
    if film:
        width, height = 960, 544  # 32-divisible, near-16:9 capture for the campaign film
        frames = min(((seconds * 24 - 1) // 8) * 8 + 1, 193)
        steps, seed = 36, 1000 + (scene["num"] or 0)
    else:
        width, height = 768, 512
        frames = min(((seconds * 24 - 1) // 8) * 8 + 1, 161)
        steps, seed = 40, 42

    last_error = None
    for key in model_chain(job.get("model"), prefer=(ARGS.prefer if ARGS else None)):
        model = LTX_CHECKPOINTS[key]
        try:
            log(f"ltx: loading {model} on {torch.cuda.get_device_name(0)}…")
            pipe = LTXPipeline.from_pretrained(model, torch_dtype=torch.float16)
            pipe.enable_model_cpu_offload()
            try:
                pipe.vae.enable_tiling()
            except Exception:
                pass
            gen = torch.Generator("cpu").manual_seed(seed)
            result = pipe(
                prompt=_visual,
                negative_prompt="worst quality, inconsistent motion, blurry, jittery, distorted, watermark, text",
                width=width, height=height,
                num_frames=frames,
                num_inference_steps=steps,
                guidance_scale=3.0,
                generator=gen,
            ).frames[0]
            raw = export_to_video(result, fps=24)
            del pipe
            torch.cuda.empty_cache()
            return raw
        except Exception as exc:  # try next checkpoint
            last_error = exc
            log(f"ltx: {model} failed ({exc}) — trying next")
            try:
                torch.cuda.empty_cache()
            except Exception:
                pass
    raise RuntimeError(f"all LTX checkpoints failed; last error: {last_error}")


RENDERERS = {"stub": render_stub, "ltx": render_ltx}


# ---------------------------------------------------------------- QA gate

def ffprobe_json(path):
    proc = run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
        timeout=120,
    )
    return json.loads(proc.stdout)


def qa_gate(path, job, renderer_name):
    """Pre-delivery review. Returns (ok, report). Hard checks fail closed."""
    problems, notes = [], []
    try:
        info = ffprobe_json(path)
    except Exception as exc:
        return False, f"QA FAIL: ffprobe could not open the file ({exc})"
    fmt = info.get("format", {})
    streams = info.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if not v:
        problems.append("no video stream")
    if not a:
        problems.append("no audio stream")
    dur = float(fmt.get("duration", 0) or 0)
    target = float(job["seconds"])
    if not (max(1.0, target - 2.5) <= dur <= target + 6.0):
        problems.append(f"duration {dur:.2f}s outside {target:g}s tolerance")
    if v:
        w, h = int(v.get("width", 0) or 0), int(v.get("height", 0) or 0)
        tw, th = RESOLUTIONS.get(job["resolution"], RESOLUTIONS["720p"])
        if abs(w - tw) > 8 or abs(h - th) > 8:
            problems.append(f"resolution {w}x{h} != {tw}x{th}")
    size = os.path.getsize(path)
    if size < 30_000:
        problems.append(f"file too small ({size}B) — likely an empty encode")
    if size > 200 * 1024 * 1024:
        problems.append("file over the 200MB delivery cap")

    if a and job.get("withAudio"):
        try:
            proc = run(
                ["ffmpeg", "-i", path, "-af", "volumedetect", "-vn", "-f", "null", "-"],
                timeout=600,
            )
            mean_volume = None
            for line in (proc.stderr or "").splitlines():
                if "mean_volume" in line:
                    mean_volume = float(line.split("mean_volume:")[1].split()[0])
                    break
            if mean_volume is not None and mean_volume < -70:
                problems.append(f"audio track is silent (mean {mean_volume:.0f} dB)")
        except Exception as exc:
            notes.append(f"loudness scan skipped ({exc.__class__.__name__})")

    # Pixel sanity — the stub's dark slow gradient would trip these checks by
    # design, so scan only real renderers.
    if renderer_name != "stub" and v:
        try:
            proc = subprocess.run(
                ["ffmpeg", "-v", "info", "-i", path, "-vf",
                 "blackdetect=d=2.0:pix_th=0.005", "-an", "-f", "null", "-"],
                capture_output=True, text=True, timeout=600,
            )
            black = 0.0
            for line in (proc.stderr or "").splitlines():
                if "black_duration:" in line:
                    try:
                        black += float(line.split("black_duration:")[1].split()[0])
                    except (ValueError, IndexError):
                        pass
            if dur > 0 and black / dur > 0.85:
                problems.append(f"{black:.1f}s of {dur:.1f}s is pure black")
            elif black > 0:
                notes.append(f"black={black:.1f}s ok")
        except Exception as exc:
            notes.append(f"pixel scan skipped ({exc.__class__.__name__})")

    report = "QA OK" + (f" ({'; '.join(notes)})" if notes else "")
    if problems:
        report = "QA FAIL: " + "; ".join(problems)
    return (not problems), report


def parse_chain(mode):
    """Resolve the --renderer argument into an ordered list of renderer names."""
    if mode == "film":
        return ["ltx"]  # strict: the stub can never stand in for a film scene
    if mode == "auto":
        try:
            import torch  # noqa
            return ["ltx", "stub"] if torch.cuda.is_available() else ["stub"]
        except Exception:
            return ["stub"]
    names = [m.strip() for m in mode.split(",") if m.strip() in RENDERERS]
    return names or ["stub"]


def report_progress(job, site, token, pct, stage, note=""):
    """Best-effort progress heartbeat — never fails the render."""
    try:
        http_json(
            f"{site}/api/worker/jobs/{job['id']}",
            {"action": "progress", "progress": int(max(0, min(100, pct))), "stage": stage[:120], "notes": (note or f"{pct}% — {stage}")[:500]},
            token=token, method="PATCH", timeout=30,
        )
    except Exception as exc:
        log(f"progress heartbeat skipped ({exc})")


def render(job, renderer_mode, workdir, budget_scale=1.0, site="", token=""):
    """Run the fallback chain; every output must pass the QA gate.

    In film mode a claimed scene gets: local render -> local piper TTS ->
    VO mux -> QA. TTS failure fails the job (fail-closed, never silent).
    """
    t0 = time.time()
    chain = parse_chain(renderer_mode)
    strict = renderer_mode == "film"
    scene, _visual = parse_scene(job["prompt"])
    seconds, (width, height) = job["seconds"], RESOLUTIONS.get(job["resolution"], RESOLUTIONS["720p"])
    watermark = bool(job.get("watermark"))
    vo_wav, pitch = None, 1.0

    if strict and scene and scene.get("line") and job.get("withAudio"):
        voice_key, pitch = parse_voice(job.get("voice"))
        report_progress(job, site, token, 55, "voice synthesis (local piper)", f"voice {voice_key}")
        vo_wav = synth_vo(scene["line"], voice_key, os.path.join(workdir, "vo.wav"),
                          os.path.join(tempfile.gettempdir(), "dy-piper"))
        if not vo_wav:
            raise RuntimeError("local TTS unavailable for a film scene — failing closed (no silent scenes)")

    attempts = []
    log(f"chain for {job['id']}: {' -> '.join(chain)}")
    for name in chain:
        # Cost governor: generous but real wall-clock caps per renderer.
        budget = {"ltx": 2.0 + seconds * 0.8, "stub": 6.0}.get(name, 10.0) * budget_scale
        try:
            report_progress(job, site, token, 10, f"rendering with {name}", f"engine {name} starting")
            raw = run_with_budget(lambda n=name: RENDERERS[n](job, workdir), budget)
            report_progress(job, site, token, 80, "encoding master", f"{name} raw done, encoding final")
            out = os.path.join(workdir, f"final-{name}.mp4")
            encode_final(raw, out, seconds, width, height, watermark, job["id"],
                         vo_wav=vo_wav, pitch=pitch, film=bool(scene))
            report_progress(job, site, token, 92, "quality check", "QA gate running")
        except Exception as exc:
            attempts.append(f"{name}: {exc}")
            log(f"renderer {name} out — {exc}")
            continue
        gpu_minutes = max(0.1, round((time.time() - t0) / 60.0, 1))
        ok, report = qa_gate(out, job, name)
        if ok:
            report_progress(job, site, token, 97, "delivery", "QA passed, uploading")
            return out, gpu_minutes, name, report
        attempts.append(f"{name}: {report}")
        log(f"{report} — falling down the chain")
    raise RuntimeError("all renderers exhausted — " + " | ".join(attempts))


# ---------------------------------------------------------------- main loop

def main():
    global ARGS
    ap = argparse.ArgumentParser(description="DeYoung universal render worker")
    ap.add_argument("--site", default=os.environ.get("DEYOUNG_SITE", DEFAULT_SITE))
    ap.add_argument("--token", default=os.environ.get("DEYOUNG_WORKER_TOKEN", ""))
    ap.add_argument(
        "--renderer",
        default=os.environ.get("DEYOUNG_RENDERER", "auto"),
        help="auto | stub | ltx | film | comma chain e.g. 'ltx,stub'",
    )
    ap.add_argument(
        "--prefer",
        default=os.environ.get("DEYOUNG_PREFER", ""),
        help="preferred local checkpoint key (a=0.9.5, b=0.9.1, c=0.9.0) for this fleet member",
    )
    ap.add_argument(
        "--job-budget",
        type=float,
        default=float(os.environ.get("DEYOUNG_JOB_BUDGET", "1.0")),
        help="scale the per-renderer wall-clock budget (1.0 = default caps)",
    )
    ap.add_argument("--max-minutes", type=float, default=float(os.environ.get("DEYOUNG_MAX_MINUTES", "480")))
    ap.add_argument("--poll", type=int, default=int(os.environ.get("DEYOUNG_POLL", "45")))
    ap.add_argument("--agent", default=f"{os.environ.get('DEYOUNG_AGENT', 'pati-worker')}-{uuid.uuid4().hex[:6]}")
    ap.add_argument("--once", action="store_true", help="run a single claim/render/deliver cycle then exit")
    ap.add_argument("--exit-idle", action="store_true", help="exit when the queue is empty instead of polling")
    args = ap.parse_args()
    ARGS = args

    if len(args.token) < 16:
        sys.exit("worker: --token (or DEYOUNG_WORKER_TOKEN) is required — get it from the site owner")
    if not have_ffmpeg():
        sys.exit("worker: ffmpeg not found in PATH — install it first (Kaggle images ship it)")

    site = args.site.rstrip("/")
    started = time.time()
    log(f"up — site={site} renderer={args.renderer} prefer={args.prefer or 'default'} max={args.max_minutes}min poll={args.poll}s")

    while True:
        if (time.time() - started) / 60.0 >= args.max_minutes:
            log("time budget reached — stopping cleanly")
            return

        try:
            status = http_json(f"{site}/api/worker/status", token=args.token)
            q = status.get("queue", {})
            log(f"queue: {q.get('queued', '?')} queued / {q.get('rendering', '?')} rendering")
        except Exception as exc:
            log(f"status check skipped ({exc.__class__.__name__})")

        job = None
        try:
            claimed = http_json(f"{site}/api/worker/claim", payload={"agent": args.agent}, token=args.token)
            job = claimed.get("job")
        except urllib.error.HTTPError as exc:
            log(f"claim failed: HTTP {exc.code} {exc.read()[:200]}")
        except Exception as exc:
            log(f"claim failed: {exc}")

        if not job:
            if args.once or args.exit_idle:
                log("queue empty — exiting")
                return
            time.sleep(args.poll)
            continue

        log(f"claimed {job['id']} — {job['seconds']}s {job['resolution']} audio={job['withAudio']} :: {job['prompt'][:70]}…")
        workdir = tempfile.mkdtemp(prefix="deyoung-")
        try:
            out, gpu_minutes, renderer_name, qa_report = render(job, args.renderer, workdir, args.job_budget, site=site, token=args.token)
            size_mb = os.path.getsize(out) / (1024 * 1024)
            log(f"rendered {job['id']} via {renderer_name} in {gpu_minutes} min ({size_mb:.1f}MB) {qa_report} — delivering")
            with open(out, "rb") as fh:
                result = http_multipart(
                    f"{site}/api/worker/jobs/{job['id']}",
                    fields={
                        "action": "deliver",
                        "gpuMinutes": str(gpu_minutes),
                        "renderer": f"{args.agent}/{renderer_name}",
                        "qa": qa_report,
                    },
                    filename=f"req-{job['id']}.mp4",
                    file_bytes=fh.read(),
                    token=args.token,
                )
            log(f"DELIVERED {job['id']} → {result.get('request', {}).get('resultUrl')}")
        except urllib.error.HTTPError as exc:
            body = exc.read()[:300].decode(errors="replace")
            log(f"deliver failed for {job['id']}: HTTP {exc.code} {body}")
            try:
                http_json(
                    f"{site}/api/worker/jobs/{job['id']}",
                    payload={"action": "fail", "agent": args.agent, "notes": f"delivery HTTP {exc.code}: {body}"},
                    token=args.token,
                    method="PATCH",
                )
                log(f"job {job['id']} marked failed on the site")
            except Exception as fail_exc:
                log(f"could not report failure either: {fail_exc} — will retry after sleep")
                time.sleep(args.poll)
        except Exception as exc:
            log(f"render failed for {job['id']}: {exc}")
            try:
                http_json(
                    f"{site}/api/worker/jobs/{job['id']}",
                    payload={"action": "fail", "agent": args.agent, "notes": f"render error: {exc}"},
                    token=args.token,
                    method="PATCH",
                )
            except Exception as fail_exc:
                log(f"could not report failure: {fail_exc}")
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

        if args.once:
            return


if __name__ == "__main__":
    main()
