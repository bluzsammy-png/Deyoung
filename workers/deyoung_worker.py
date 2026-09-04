#!/usr/bin/env python3
"""
DeYoung universal render worker — the PATI-style execution plane.

Runs ANYWHERE (Kaggle GPU kernel, the owner's PC, any GPU/CPU box) with only
the Python standard library + ffmpeg. Loop:

    claim job -> render -> deliver (or fail honestly) -> repeat

Renderers:
    stub  — ffmpeg-only branded placeholder (runs on any CPU, used for QA,
            pipeline verification, and as an automatic fallback)
    ltx   — LTX-Video (Lightricks, open weights) text-to-video via diffusers.
            Needs a CUDA GPU (Kaggle T4/P100 is fine) and
            `pip install torch diffusers transformers accelerate imageio imageio-ffmpeg`.
            Falls back to stub automatically if anything is missing.
    auto  — ltx when CUDA is available, else stub.

Usage:
    python3 deyoung_worker.py --site https://deeyoung-production-72ef.up.railway.app \
        --token dyw_... --renderer auto --max-minutes 480

Every failure is reported back to the site (action=fail) so the queue never
clogs silently — the owner sees the reason in the admin Video Queue.
"""

import argparse
import base64
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid

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


def log(msg):
    print(f"[deyoung-worker {time.strftime('%H:%M:%S')}] {msg}", flush=True)


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


def encode_final(raw_path, out_path, seconds, width, height, watermark, job_id):
    """Normalize to target size, brand watermark, add a valid (silent) AAC track."""
    caption = os.path.join(tempfile.gettempdir(), f"dy-cap-{job_id}.txt")
    with open(caption, "w") as fh:
        fh.write(wrap_text(f"DeYoung — {job_id}"))
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},setsar=1"
    )
    font = pick_font()
    if font:
        vf += (
            f",drawtext=fontfile={font}:textfile={caption}:fontsize={28 if height <= 720 else 40}"
            ":fontcolor=white@0.92:box=1:boxcolor=black@0.45:boxborderw=14"
            ":x=(w-text_w)/2:y=h-text_h-40"
        )
        if watermark:
            vf += (
                f",drawtext=fontfile={font}:text='DEYOUNG':fontsize={20 if height <= 720 else 28}"
                ":fontcolor=white@0.55:x=w-text_w-30:y=28"
            )
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", raw_path,
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-vf", vf,
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-t", str(seconds), "-movflags", "+faststart",
        out_path,
    ]
    run(cmd)
    os.remove(caption)
    return out_path


# ---------------------------------------------------------------- renderers

def render_stub(job, workdir):
    """Branded ffmpeg-only placeholder — always available, zero deps."""
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


def render_ltx(job, workdir):
    """LTX-Video (open weights) text-to-video on CUDA. Auto-falls back to stub."""
    try:
        import torch  # noqa
        from diffusers import LTXPipeline
        from diffusers.utils import export_to_video
    except Exception as exc:  # ImportError or broken CUDA build
        log(f"ltx renderer unavailable ({exc.__class__.__name__}: {exc}) — falling back to stub")
        return render_stub(job, workdir)

    if not torch.cuda.is_available():
        log("no CUDA device — falling back to stub (LTX needs a GPU)")
        return render_stub(job, workdir)

    seconds = job["seconds"]
    frames = max(((seconds * 24 - 1) // 8) * 8 + 1, 25)
    frames = min(frames, 161)
    last_error = None
    for model in ("Lightricks/LTX-Video-0.9.7-dev", "Lightricks/LTX-Video-0.9.5", "Lightricks/LTX-Video"):
        try:
            log(f"ltx: loading {model} on {torch.cuda.get_device_name(0)}…")
            pipe = LTXPipeline.from_pretrained(model, torch_dtype=torch.float16)
            pipe.enable_model_cpu_offload()
            try:
                pipe.vae.enable_tiling()
            except Exception:
                pass
            gen = torch.Generator("cpu").manual_seed(42)
            result = pipe(
                prompt=job["prompt"],
                width=768, height=512,
                num_frames=frames,
                num_inference_steps=40,
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
    raise RuntimeError(f"all LTX checkpoints failed; last error: {last_error}")


RENDERERS = {"stub": render_stub, "ltx": render_ltx}


def render(job, renderer_mode, workdir):
    t0 = time.time()
    if renderer_mode == "auto":
        try:
            import torch  # noqa
            mode = "ltx" if torch.cuda.is_available() else "stub"
        except Exception:
            mode = "stub"
    else:
        mode = renderer_mode
    name = f"ltx" if mode == "ltx" else "stub"
    raw = RENDERERS[mode](job, workdir)
    out = os.path.join(workdir, "final.mp4")
    watermark = bool(job.get("watermark"))
    seconds, (width, height) = job["seconds"], RESOLUTIONS.get(job["resolution"], RESOLUTIONS["720p"])
    encode_final(raw, out, seconds, width, height, watermark, job["id"])
    gpu_minutes = max(0.1, round((time.time() - t0) / 60.0, 1))
    return out, gpu_minutes, name


# ---------------------------------------------------------------- main loop

def main():
    ap = argparse.ArgumentParser(description="DeYoung universal render worker")
    ap.add_argument("--site", default=os.environ.get("DEYOUNG_SITE", DEFAULT_SITE))
    ap.add_argument("--token", default=os.environ.get("DEYOUNG_WORKER_TOKEN", ""))
    ap.add_argument("--renderer", choices=["auto", "stub", "ltx"], default=os.environ.get("DEYOUNG_RENDERER", "auto"))
    ap.add_argument("--max-minutes", type=float, default=float(os.environ.get("DEYOUNG_MAX_MINUTES", "480")))
    ap.add_argument("--poll", type=int, default=int(os.environ.get("DEYOUNG_POLL", "45")))
    ap.add_argument("--agent", default=f"{os.environ.get('DEYOUNG_AGENT', 'pati-worker')}-{uuid.uuid4().hex[:6]}")
    ap.add_argument("--once", action="store_true", help="run a single claim/render/deliver cycle then exit")
    ap.add_argument("--exit-idle", action="store_true", help="exit when the queue is empty instead of polling")
    args = ap.parse_args()

    if len(args.token) < 16:
        sys.exit("worker: --token (or DEYOUNG_WORKER_TOKEN) is required — get it from the site owner")
    if not have_ffmpeg():
        sys.exit("worker: ffmpeg not found in PATH — install it first (Kaggle images ship it)")

    site = args.site.rstrip("/")
    started = time.time()
    log(f"up — site={site} renderer={args.renderer} max={args.max_minutes}min poll={args.poll}s")

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
            out, gpu_minutes, renderer_name = render(job, args.renderer, workdir)
            size_mb = os.path.getsize(out) / (1024 * 1024)
            log(f"rendered {job['id']} via {renderer_name} in {gpu_minutes} min ({size_mb:.1f}MB) — delivering")
            with open(out, "rb") as fh:
                result = http_multipart(
                    f"{site}/api/worker/jobs/{job['id']}",
                    fields={
                        "action": "deliver",
                        "gpuMinutes": str(gpu_minutes),
                        "renderer": f"{args.agent}/{renderer_name}",
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
