#!/usr/bin/env python3
"""
DeYoung H3 queue worker — runs INSIDE the deyoung-h3 Lightning studio.

This is the persistent GPU worker: it claims jobs from the site render queue
(POST /api/worker/claim, Bearer WORKER_TOKEN) and renders them with the
MiniMax-H3 ComfyUI stack permanently installed at ~/h3work/ComfyUI.

Design contract (owner brief, Task 61):
  * tmux is ONLY the session layer that keeps this process alive across
    SSH/exec disconnection. This file knows nothing about tmux.
  * Every state change is beaten to h3work/status_h3q.json (atomic write) so
    the orchestrator-side doctor can derive worker health WITHOUT trusting
    "the tmux session exists". A hung process is detectable: heartbeat age.
  * Secrets arrive via environment (h3q.env, chmod 600). Never argv, never
    committed.
  * SIGTERM/SIGINT -> stop claiming, finish current job, exit cleanly.
  * Time budget (--max-minutes) -> same clean exit. The studio itself is
    stopped by the doctor/owner (credit guard), never by this file.

Render pipeline per job (mirrors the proven c20/v4 paths):
  claim -> ensure ComfyUI up -> H3 graph (960x544 band, turbo LoRA) ->
  ffmpeg normalize (scale to requested res, audio policy, watermark) ->
  PATCH /api/worker/jobs/{id} (multipart deliver) | honest fail report
"""

import argparse
import hashlib
import io
import json
import os
import pathlib
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid

HOME = pathlib.Path("/teamspace/studios/this_studio")
WORK = HOME / "h3work"
OUT = WORK / "out"
COMFY = WORK / "ComfyUI"
STATUS = WORK / "status_h3q.json"
COMFY_LOG = WORK / "comfy_h3q.log"
PORT = 8188
BASE = f"http://127.0.0.1:{PORT}"

# H3 single-pass band, proven on the fleet (Kaggle canary + c20 + v4):
# 121 frames minimum (~5s), 289 maximum (~12s), always 8n+1, T4-safe 960x544.
BAND_MIN_F, BAND_MAX_F = 121, 289
RENDER_W, RENDER_H = 960, 544
JOB_WATCHDOG_MIN = 35          # hard ceiling for one graph render
COMFY_BOOT_TIMEOUT_S = 420     # model-heavy stack; give it 7 minutes
COMFY_RESTART_WINDOW_S = 600   # crash-rate window
COMFY_RESTART_MAX = 3          # in-window crash limit -> give up honestly

T0 = time.time()
STATE = {
    "worker": os.environ.get("DYG_WORKER_NAME", "lightning-h3"),
    "pid": os.getpid(),
    "host": os.environ.get("DYG_STUDIO_NAME", "deyoung-h3"),
    "phase": "STARTING",
    "claiming": True,
    "job": None,
    "last_delivered": None,
    "last_error": None,
    "errors": [],
    "comfy": {"up": False, "queue_size": None, "restarts": 0},
    "gpu": None,
    "h3_ready": False,
    "site": None,
    "agent": None,
    "budget_min": None,
    "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "updated_at": None,
    "updated_epoch": time.time(),
}


def log(*a):
    print(f"[h3q {time.strftime('%H:%M:%S')}]", *a, flush=True)


def beat(**kw):
    """Atomic status beat — the single source of truth for the doctor."""
    STATE.update(kw)
    STATE["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    STATE["updated_epoch"] = time.time()
    STATE["uptime_min"] = round((time.time() - T0) / 60, 1)
    tmp = STATUS.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(STATE, indent=1))
        os.replace(tmp, STATUS)
    except Exception as e:  # disk hiccup must never kill the worker
        log("beat write failed:", repr(e))


def note_error(msg):
    STATE["last_error"] = str(msg)[:300]
    STATE["errors"] = (STATE["errors"] + [str(msg)[:300]])[-10:]
    log("ERROR:", str(msg)[:200])


# ------------------------------------------------------------------ HTTP

def http_json(url, payload=None, token="", method=None, timeout=120):
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers,
                                 method=method or ("POST" if data else "GET"))
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


# --- F-10 (W3.1): customer-visible progress beats to the site ----------
# The local heartbeat (beat()) keeps the doctor honest; site_beat() keeps the
# CUSTOMER row honest: PATCH action=progress refreshes the row's notes and
# updatedAt so the 45-min orphan reaper never eats a long-but-alive H3 render,
# and the admin queue note shows real facts (frames/steps/elapsed) — never
# invented percentages (architecture §event rules).
SITE_BEAT_MIN_INTERVAL = 60.0
SITE_BEAT_CTX = {"site": "", "token": ""}
_site_beat_state = {"t": 0.0}


def site_beat(job_id, note, force=False):
    """Throttled, fail-silent progress beat to the site row (F-10)."""
    if not job_id or not SITE_BEAT_CTX["site"]:
        return
    now = time.time()
    if not force and (now - _site_beat_state["t"]) < SITE_BEAT_MIN_INTERVAL:
        return
    try:
        http_json(f"{SITE_BEAT_CTX['site']}/api/worker/jobs/{job_id}",
                  payload={"action": "progress", "notes": str(note)[:500]},
                  token=SITE_BEAT_CTX["token"], method="PATCH")
        _site_beat_state["t"] = now
    except Exception as exc:
        log(f"site_beat({job_id}) failed (render continues): {exc!r}")


def http_multipart(url, fields, filename, file_bytes, token, timeout=900):
    boundary = "----deyoung" + uuid.uuid4().hex
    buf = io.BytesIO()
    for key, value in fields.items():
        buf.write(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
    buf.write(
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: video/mp4\r\n\r\n".encode()
    )
    buf.write(file_bytes)
    buf.write(f"\r\n--{boundary}--\r\n".encode())
    req = urllib.request.Request(
        url, data=buf.getvalue(),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}",
                 "Authorization": f"Bearer {token}"},
        method="PATCH")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


# ------------------------------------------------------------------ GPU probe

def probe_gpu():
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.used",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=20)
        if r.returncode == 0 and r.stdout.strip():
            name, total, used = [x.strip() for x in r.stdout.strip().splitlines()[0].split(",")]
            gpu = {"name": name, "mem_total_mb": int(total), "mem_used_mb": int(used)}
            STATE["gpu"] = gpu
            return gpu
    except Exception as e:
        log("nvidia-smi probe failed:", repr(e))
    STATE["gpu"] = None
    return None


# ------------------------------------------------------------------ ComfyUI

def comfy_up(timeout=8):
    try:
        with urllib.request.urlopen(BASE + "/queue", timeout=timeout) as r:
            q = json.loads(r.read())
        STATE["comfy"]["up"] = True
        STATE["comfy"]["queue_size"] = len(q.get("queue_running", [])) + len(q.get("queue_pending", []))
        return True
    except Exception:
        STATE["comfy"]["up"] = False
        return False


def boot_comfy():
    """Start ComfyUI headless. Returns True when /queue answers."""
    if comfy_up():
        return True
    if not (COMFY / "main.py").exists():
        note_error(f"ComfyUI stack missing at {COMFY} — cannot render")
        beat(phase="ERROR")
        return False
    log("booting ComfyUI…")
    beat(phase="STARTING", note="booting ComfyUI")
    env = {**os.environ, "CUDA_VISIBLE_DEVICES": "0"}
    logf = open(COMFY_LOG, "a")
    logf.write(f"\n===== boot {time.strftime('%Y-%m-%dT%H:%M:%SZ')} =====\n")
    logf.flush()
    subprocess.Popen(
        [sys.executable, str(COMFY / "main.py"), "--listen", "127.0.0.1",
         "--port", str(PORT), "--output-directory", str(OUT),
         "--disable-auto-launch", "--reserve-vram", "0.4"],
        cwd=str(COMFY), env=env, stdout=logf, stderr=subprocess.STDOUT)
    t0 = time.time()
    while time.time() - t0 < COMFY_BOOT_TIMEOUT_S:
        if comfy_up():
            log(f"ComfyUI up after {round(time.time() - t0)}s")
            return True
        time.sleep(10)
    note_error("ComfyUI did not come up in time (see comfy_h3q.log)")
    return False


def h3_ready():
    """True when the MiniMax-H3 nodes are registered (model stack present)."""
    try:
        with urllib.request.urlopen(BASE + "/object_info", timeout=120) as r:
            info = json.loads(r.read())
        ok = all(k in info for k in ("MiniMaxH3ImageToVideo", "CLIPLoader",
                                     "CreateVideo", "SaveVideo", "UNETLoader"))
        STATE["h3_ready"] = ok
        return ok
    except Exception as e:
        log("object_info probe failed:", repr(e))
        STATE["h3_ready"] = False
        return False


def pick(info, class_name, input_name, suffix):
    req = info[class_name]["input"]["required"]
    opt = info[class_name]["input"].get("optional", {})
    lst = (req.get(input_name) or opt.get(input_name))[0]
    for cand in lst:
        if suffix in cand:
            return cand
    raise RuntimeError(f"{suffix} not found in {class_name}.{input_name}")


def api_graph(info, job, length, steps, seed):
    dit = pick(info, "UNETLoader", "unet_name", "fl2va_pruned_fp8_scaled.safetensors")
    clip = pick(info, "CLIPLoader", "clip_name", "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors")
    vvae = pick(info, "VAELoader", "vae_name", "minimax_h3_video_vae_fp16.safetensors")
    avae = pick(info, "VAELoader", "vae_name", "minimax_h3_audio_vae_fp32.safetensors")
    lora = pick(info, "LoraLoaderModelOnly", "lora_name",
                "fl2v_turbo_4step" if steps == 4 else "fl2v_turbo_8step")
    return {"prompt": {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": dit, "weight_dtype": "default"}},
        "2": {"class_type": "LoraLoaderModelOnly",
              "inputs": {"model": ["1", 0], "lora_name": lora, "strength_model": 1.0}},
        "3": {"class_type": "CLIPLoader",
              "inputs": {"clip_name": clip, "type": "minimax", "device": "default"}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": vvae}},
        "5": {"class_type": "VAELoader", "inputs": {"vae_name": avae}},
        "6": {"class_type": "MiniMaxH3ImageToVideo",
              "inputs": {"clip": ["3", 0], "vae": ["4", 0], "prompt": job["prompt"],
                          "width": RENDER_W, "height": RENDER_H, "length": length}},
        "7": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "8": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "res_multistep"}},
        "9": {"class_type": "BasicScheduler",
              "inputs": {"model": ["2", 0], "scheduler": "simple", "steps": steps, "denoise": 1.0}},
        "10": {"class_type": "BasicGuider",
               "inputs": {"model": ["2", 0], "conditioning": ["6", 0]}},
        "11": {"class_type": "SamplerCustomAdvanced",
               "inputs": {"noise": ["7", 0], "guider": ["10", 0],
                          "sampler": ["8", 0], "sigmas": ["9", 0], "latent_image": ["6", 1]}},
        "12": {"class_type": "VAEDecode", "inputs": {"samples": ["11", 0], "vae": ["4", 0]}},
        "13": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["11", 0], "vae": ["5", 0]}},
        "14": {"class_type": "CreateVideo",
               "inputs": {"images": ["12", 0], "audio": ["13", 0], "fps": 24}},
        "15": {"class_type": "SaveVideo",
               "inputs": {"video": ["14", 0], "filename_prefix": f"video/{job['id']}",
                          "codec": "auto", "format": "auto"}},
    }, "client_id": STATE["agent"]}


def render_h3(job):
    """Run the H3 graph for this job. Returns (mp4_path, steps_used, frames)."""
    secs = int(job.get("seconds") or 5)
    # H3 band: 8n+1 frames, clamp to [121, 289] exactly like the v4 fleet worker
    length = max(BAND_MIN_F, min(BAND_MAX_F, 8 * max(1, (secs * 24) // 8) + 1))
    # Task 64: steps=4 for ALL lengths — the v10-proven config (fl2v_turbo_4step).
    # steps=8 on shorts watchdog-failed twice on the T4 (35-min ceiling, est~136min);
    # no Lightning-T4 render has ever completed at 8 steps.
    steps = 4
    seed = int(hashlib.sha256(job["id"].encode()).hexdigest()[:8], 16)

    if not comfy_up() and not boot_comfy():
        raise RuntimeError("ComfyUI unavailable")
    with urllib.request.urlopen(BASE + "/object_info", timeout=120) as r:
        info = json.loads(r.read())
    STATE["h3_ready"] = all(k in info for k in ("MiniMaxH3ImageToVideo", "UNETLoader"))
    if not STATE["h3_ready"]:
        raise RuntimeError("MiniMax-H3 nodes missing from object_info")

    req = urllib.request.Request(BASE + "/prompt",
                                 json.dumps(api_graph(info, job, length, steps, seed)).encode(),
                                 {"Content-Type": "application/json"})
    pid = json.loads(urllib.request.urlopen(req, timeout=120).read())["prompt_id"]
    est = length * RENDER_W * RENDER_H * 0.000129 / 60
    log(f"[{job['id']}] queued {pid} len={length}f steps={steps} est~{est:.0f}min")
    beat(phase="BUSY", job={**job, "render": {"frames": length, "steps": steps,
                                              "prompt_id": pid, "est_min": round(est)}})
    # F-10: the customer row learns the real render shape immediately
    site_beat(job["id"], f"H3 sampling queued — {length} frames @ {RENDER_W}x{RENDER_H}, "
                         f"steps={steps}, est ~{est:.0f} min", force=True)
    t0 = time.time()
    while True:
        time.sleep(30)
        # progress beats: a long render must NEVER look like a hung worker
        # (the doctor flags heartbeat age > HEARTBEAT_STALE_S as UNHEALTHY)
        elapsed_min = round((time.time() - t0) / 60, 1)
        beat(phase="BUSY", job={**job, "render": {
            "frames": length, "steps": steps, "prompt_id": pid,
            "elapsed_min": elapsed_min}})
        # F-10: same truth for the customer row (throttled to ~1/min by site_beat)
        site_beat(job["id"], f"H3 sampling running — {length} frames @ "
                             f"{RENDER_W}x{RENDER_H}, steps={steps}, "
                             f"{elapsed_min} min elapsed")
        if (time.time() - t0) / 60 > JOB_WATCHDOG_MIN:
            try:
                urllib.request.urlopen(urllib.request.Request(
                    BASE + "/interrupt", b"{}", {"Content-Type": "application/json"}),
                    timeout=30)
            except Exception:
                pass
            raise RuntimeError(f"render watchdog fired after {JOB_WATCHDOG_MIN} min")
        try:
            with urllib.request.urlopen(BASE + f"/history/{pid}", timeout=60) as r:
                h = json.loads(r.read())
        except Exception as e:
            log(f"[{job['id']}] poll err {e!r}")
            continue
        if pid in h:
            st = h[pid].get("status", {})
            if st.get("status_str") == "error":
                raise RuntimeError("graph error: " + json.dumps(st.get("messages", []))[:400])
            outs = h[pid].get("outputs", {})
            vid = None
            for no in outs.values():
                for k in ("images", "gifs", "video", "videos"):
                    for f in no.get(k, []) or []:
                        if f.get("filename", "").endswith(".mp4"):
                            vid = OUT / f["filename"]
            if vid is None and outs:
                cand = sorted(OUT.rglob("*.mp4"), key=lambda p: p.stat().st_mtime)
                vid = cand[-1] if cand else None
            if vid and vid.exists():
                took = (time.time() - t0) / 60
                log(f"[{job['id']}] H3 done in {took:.0f}min -> {vid.name}")
                return vid, steps, length


# ------------------------------------------------------------------ encode

FONT_CANDIDATES = [
    os.environ.get("DEYOUNG_FONT", ""),
    str(HOME / "h3work/Archivo.ttf"),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]
RESOLUTIONS = {"720p": (1280, 720), "1080p": (1920, 1080)}


def pick_font():
    for c in FONT_CANDIDATES:
        if c and os.path.exists(c):
            return c
    return None


def run(cmd, timeout=1800):
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"cmd failed ({' '.join(cmd[:3])}…): {proc.stderr[-400:]}")


def raw_duration(path):
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(path)],
            capture_output=True, text=True, timeout=60)
        return float(r.stdout.strip())
    except Exception:
        return None


def encode_final(raw_path, out_path, seconds, resolution, watermark, job_id, with_audio):
    """Normalize: scale to requested resolution, audio policy, watermark.
    with_audio=True keeps the H3-generated soundscape; False muxes silence.
    If the H3 band is shorter than the requested seconds (single-pass cap),
    the last frame is held (tpad clone) so the deliverable duration matches."""
    width, height = RESOLUTIONS.get(resolution, RESOLUTIONS["720p"])
    vf = (f"scale={width}:{height}:force_original_aspect_ratio=increase,"
          f"crop={width}:{height},setsar=1")
    dur = raw_duration(raw_path)
    if dur and seconds > dur + 0.6:
        vf += f",tpad=stop_mode=clone:stop_duration={seconds - dur + 0.2:.2f}"
        log(f"encode: H3 band {dur:.1f}s < requested {seconds}s — holding last frame "
            f"(single-pass cap {BAND_MAX_F}f)")
    font = pick_font()
    if font and watermark:
        vf += (f",drawtext=fontfile={font}:text='DEYOUNG':fontsize=30:"
               "fontcolor=white@0.55:x=w-text_w-28:y=h-text_h-28")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw_path)]
    if with_audio:
        cmd += ["-vf", vf, "-map", "0:v:0", "-map", "0:a:0?",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
                "-t", str(seconds), "-movflags", "+faststart"]
    else:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                "-vf", vf, "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
                "-t", str(seconds), "-movflags", "+faststart"]
    cmd += [str(out_path)]
    run(cmd)
    return out_path


# ------------------------------------------------------------------ lifecycle

GRACE = {"stop": False}
JOB_T0 = {"t": None}


def on_signal(signum, _frame):
    log(f"signal {signum} — will stop claiming; finishing current step then exit")
    GRACE["stop"] = True
    STATE["claiming"] = False
    beat()


def main():
    ap = argparse.ArgumentParser(description="DeYoung H3 queue worker (studio-side)")
    ap.add_argument("--site", default=os.environ.get("DEYOUNG_SITE", "https://deyoungltd.site"))
    ap.add_argument("--token", default=os.environ.get("DEYOUNG_WORKER_TOKEN", ""))
    ap.add_argument("--max-minutes", type=float,
                    default=float(os.environ.get("DEYOUNG_MAX_MINUTES", "540")))
    ap.add_argument("--poll", type=int, default=int(os.environ.get("DEYOUNG_POLL", "30")))
    ap.add_argument("--agent", default=os.environ.get("DYG_AGENT", ""))
    args = ap.parse_args()

    if len(args.token) < 16:
        sys.exit("h3q: DEYOUNG_WORKER_TOKEN missing/short — refusing to start (no anonymous workers)")
    agent = args.agent or f"lightning-h3-{uuid.uuid4().hex[:6]}"
    STATE["site"] = args.site
    STATE["agent"] = agent
    STATE["budget_min"] = args.max_minutes
    site = args.site.rstrip("/")
    SITE_BEAT_CTX["site"] = site
    SITE_BEAT_CTX["token"] = args.token

    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)

    OUT.mkdir(parents=True, exist_ok=True)
    probe_gpu()
    beat()
    log(f"up — site={site} agent={agent} gpu={(STATE['gpu'] or {}).get('name')} budget={args.max_minutes}min")

    if not boot_comfy():
        sys.exit(2)
    h3_ready()
    beat(phase="IDLE")
    log("READY — entering claim loop")

    comfy_restarts = []  # timestamps of recent ComfyUI crashes

    while True:
        beat()
        if GRACE["stop"]:
            log("graceful stop — exiting")
            beat(phase="EXITING")
            return
        if (time.time() - T0) / 60 >= args.max_minutes:
            log("time budget reached — clean exit")
            beat(phase="EXITING", note="budget reached")
            return

        # ComfyUI liveness (only matters when we might render)
        if not comfy_up():
            now = time.time()
            comfy_restarts = [t for t in comfy_restarts if now - t < COMFY_RESTART_WINDOW_S]
            if len(comfy_restarts) >= COMFY_RESTART_MAX:
                note_error(f"ComfyUI crashed {len(comfy_restarts)}x in "
                           f"{COMFY_RESTART_WINDOW_S // 60} min — giving up this run")
                beat(phase="ERROR")
                sys.exit(3)
            if not boot_comfy():
                comfy_restarts.append(now)
                STATE["comfy"]["restarts"] = len(comfy_restarts)
                time.sleep(60)
                continue
        if not h3_ready():
            log("H3 nodes not ready yet — rechecking next cycle")
            time.sleep(args.poll)
            continue
        beat(phase="IDLE")

        job = None
        try:
            claimed = http_json(f"{site}/api/worker/claim",
                                payload={"agent": agent}, token=args.token)
            job = claimed.get("job")
        except urllib.error.HTTPError as exc:
            body = exc.read()[:200].decode(errors="replace")
            log(f"claim failed: HTTP {exc.code} {body}")
            if exc.code == 401:
                note_error("worker token rejected (401) — stopping claims")
                beat(phase="ERROR")
                sys.exit(4)
            time.sleep(args.poll)
            continue
        except Exception as exc:
            log(f"claim failed: {exc}")
            time.sleep(args.poll)
            continue

        if not job:
            time.sleep(args.poll)
            continue

        jid = job["id"]
        log(f"claimed {jid} — {job['seconds']}s {job['resolution']} audio={job['withAudio']}")
        JOB_T0["t"] = time.time()
        STATE["job"] = job
        beat(phase="BUSY")
        workdir = tempfile.mkdtemp(prefix="h3q-", dir=str(WORK))
        ok = False
        try:
            raw, steps, frames = render_h3(job)
            site_beat(jid, f"sampling done ({frames} frames) — encoding + watermark", force=True)
            final = os.path.join(workdir, "final.mp4")
            encode_final(raw, final, int(job["seconds"]), job["resolution"],
                         bool(job.get("watermark")), jid, bool(job.get("withAudio")))
            size_mb = os.path.getsize(final) / 1e6
            site_beat(jid, f"uploading {size_mb:.1f} MB to site", force=True)
            job_min = max(0.1, round((time.time() - JOB_T0["t"]) / 60, 1))
            with open(final, "rb") as fh:
                result = http_multipart(
                    f"{site}/api/worker/jobs/{jid}",
                    fields={"action": "deliver", "gpuMinutes": str(job_min),
                            "renderer": f"{agent}/h3(len{frames},s{steps})"},
                    filename=f"req-{jid}.mp4",
                    file_bytes=fh.read(), token=args.token)
            log(f"DELIVERED {jid} ({size_mb:.1f}MB, {job_min}min) -> "
                f"{result.get('request', {}).get('resultUrl')}")
            STATE["last_delivered"] = {"id": jid, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                       "mb": round(size_mb, 1), "frames": frames, "steps": steps}
            ok = True
        except Exception as exc:
            note_error(f"{jid}: {exc}")
            try:
                http_json(f"{site}/api/worker/jobs/{jid}",
                          payload={"action": "fail", "agent": agent,
                                   "notes": f"h3 worker: {exc}"[:500]},
                          token=args.token, method="PATCH")
                log(f"job {jid} marked failed on the site (honest report)")
            except Exception as fail_exc:
                log(f"could not report failure: {fail_exc}")
        finally:
            STATE["job"] = None
            beat(phase="IDLE", last_ok=ok)
            shutil.rmtree(workdir, ignore_errors=True)
            try:
                urllib.request.urlopen(urllib.request.Request(
                    BASE + "/free", json.dumps({"unload_models": True,
                                                "free_memory": True}).encode(),
                    {"Content-Type": "application/json"}), timeout=60)
            except Exception:
                pass


if __name__ == "__main__":
    main()
