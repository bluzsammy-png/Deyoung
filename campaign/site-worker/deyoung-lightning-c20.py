#!/usr/bin/env python3
"""Deyoung Lightning campaign worker c20 — runs INSIDE the deyoung-h3 studio.

Phases:
  1. repair torchaudio ABI (previous attempt crashed ComfyUI boot: undefined
     symbol torch_library_impl) with escalating strategies, evidence-logged
  2. boot ComfyUI headless from the pre-installed 54G stack at ~/h3work/ComfyUI
  3. render the 4-scene 20s UGC launch cut (960x544, 24fps, turbo loras,
     dialogue scenes on 8-step, action scenes on 4-step)
  4. upload each mp4 to Supabase storage campaign/v20/<id>.mp4
  5. beat status to ~/h3work/status_c20.json after every state change

Secrets arrive as env: SUPA_URL, SUPA_KEY. No secrets are hardcoded here.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
import urllib.request

HOME = pathlib.Path("/teamspace/studios/this_studio")
WORK = HOME / "h3work"
COMFY = WORK / "ComfyUI"
OUT = WORK / "out"
OUT.mkdir(parents=True, exist_ok=True)
STATUS = WORK / "status_c20.json"
PORT = 8188
HARD_CAP_MIN = 16 * 60
JOB_WATCHDOG_MIN = 8 * 60
RATE = 0.0001293650647630262  # seconds per pixel-frame, calibrated on Kaggle fleet
T0 = time.time()
STATE = {"phase": "setup", "done": [], "failed": [], "uploads": [], "fix": None,
         "rate_s_per_pf": RATE, "errors": []}


def log(*a, **kw):
    print("[c20]", *a, flush=True)


def self_stop():
    """Stop this studio from inside (platform auth) - the credit guard.
    Proven live 2026-09-08: inner SDK stop works; the studio lands Stopped."""
    try:
        from lightning_sdk import Studio
        s = Studio(name="deyoung-h3", teamspace="default-project", user="deyoungsltd")
        if "Stopped" in str(s.status):
            return
        s.stop()
        print("[c20] SELF-STOP issued", flush=True)
    except Exception as e:
        # self-stop killing our own session can surface as an exception - not fatal
        msg = repr(e)[:200]
        print("[c20] self_stop note:", msg, flush=True)
        if "no running instances" in msg or "Failed to reach" in msg:
            print("[c20] SELF-STOP likely succeeded (session cut)", flush=True)


def beat(**kw):
    STATE.update(kw)
    STATE["elapsed_min"] = round((time.time() - T0) / 60, 1)
    STATE["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    STATUS.write_text(json.dumps(STATE, indent=1))


def est_min(job):
    pf = job["length"] * job["width"] * job["height"]
    return (pf * STATE["rate_s_per_pf"]) / 60.0


# ---- jobs: the 20s UGC launch cut (4 scenes x 5s, 960x544) ------------------
JOBS_LIST = [
    {
        "id": "u1",
        "prompt": ("integrated_multimodal_description: [Shot 1] UGC selfie-style handheld framing, a cheerful young woman creator with curly hair filming herself landscape in a cozy bedroom with warm LED strip glow, phone-camera feel with slight handheld wobble, she points at the viewer with a big grin and says: <d>[English] I typed one sentence - and got a whole video.</d> then she holds up her phone showing a glowing video timeline.\noverall_soundscape: room tone, soft breath, faint LED hum.\nnon_diegetic_music: lo-fi pop bounce, medium tempo."),
        "width": 960, "height": 544, "length": 121, "steps": 8, "seed": 90001,
    },
    {
        "id": "u2",
        "prompt": ("integrated_multimodal_description: [Shot 1] The camera pushes over her shoulder onto the phone screen: a sleek dark studio interface, a single prompt box glows, the typed sentence lifts off the keyboard as light particles and fans out into three floating scene cards with tiny storyboard sketches that snap into a timeline.\noverall_soundscape: soft keyboard taps, crystalline UI chimes as the cards fan out.\nnon_diegetic_music: lo-fi bounce with sparkle accents."),
        "width": 960, "height": 544, "length": 121, "steps": 4, "seed": 90002,
    },
    {
        "id": "u3",
        "prompt": ("integrated_multimodal_description: [Shot 1] Rapid joyful montage on the phone screen: three scene cards burst into tiny video thumbnails that stack like polaroids, a progress ring sweeps around a glowing GPU spark, and an audio waveform dances under the thumbnails.\noverall_soundscape: whooshing card transitions, rising render hum, waveform blips.\nnon_diegetic_music: build-up with claps."),
        "width": 960, "height": 544, "length": 121, "steps": 4, "seed": 90003,
    },
    {
        "id": "u4",
        "prompt": ("integrated_multimodal_description: [Shot 1] Back to selfie framing: she holds the phone up next to her face playing the finished clip, throws a double thumbs-up at the camera and says: <d>[English] Deyoung dot site - type it, watch it, post it.</d> then she winks as the screen light flares softly.\noverall_soundscape: happy exhale, soft flare shimmer.\nnon_diegetic_music: final lo-fi resolve on a warm chord."),
        "width": 960, "height": 544, "length": 121, "steps": 8, "seed": 90004,
    },
]

# ---- 1. torchaudio repair ---------------------------------------------------
def torchaudio_ok():
    r = subprocess.run([sys.executable, "-c", "import torchaudio; print('ok', torchaudio.__version__)"],
                       capture_output=True, text=True, timeout=300)
    return r.returncode == 0, (r.stdout + r.stderr)[-300:]


def fix_torchaudio():
    ok, info = torchaudio_ok()
    if ok:
        STATE["fix"] = "already-ok"
        beat()
        return True
    log("torchaudio broken:", info.strip()[-160:])
    attempts = [
        ["-q", "--no-deps", "--force-reinstall", "torchaudio==2.8.0"],
        ["-q", "torch==2.8.0", "torchaudio==2.8.0", "--index-url",
         "https://download.pytorch.org/whl/cu128"],
    ]
    for i, args in enumerate(attempts):
        log(f"fix attempt {i}: pip install", *args[:4])
        r = subprocess.run([sys.executable, "-m", "pip", "install", *args],
                           capture_output=True, text=True, timeout=1800)
        ok, info = torchaudio_ok()
        STATE["fix"] = f"attempt{i}_{'ok' if ok else 'fail'}"
        STATE["errors"].append(info[-200:] if not ok else f"attempt{i} fixed")
        beat()
        if ok:
            return True
    return False


# ---- 2. ComfyUI boot --------------------------------------------------------
def boot_comfy():
    if not (COMFY / "main.py").exists():
        STATE["phase"] = "fatal"
        STATE["errors"].append("ComfyUI missing at " + str(COMFY))
        beat()
        log("FATAL: stack missing")
        sys.exit(1)
    env = {**os.environ, "CUDA_VISIBLE_DEVICES": "0"}
    srv = subprocess.Popen(
        [sys.executable, str(COMFY / "main.py"), "--listen", "127.0.0.1",
         "--port", str(PORT), "--output-directory", str(OUT),
         "--disable-auto-launch", "--reserve-vram", "0.4"],
        cwd=str(COMFY), env=env,
        stdout=open(WORK / "comfy_c20.log", "w"), stderr=subprocess.STDOUT)
    base = f"http://127.0.0.1:{PORT}"
    for i in range(120):
        try:
            urllib.request.urlopen(base + "/queue", timeout=5)
            log("ComfyUI up after", round(time.time() - T0), "s")
            return base
        except Exception:
            time.sleep(10)
    # capture tail for evidence
    tail = (WORK / "comfy_c20.log").read_text()[-1500:]
    STATE["phase"] = "fatal"
    STATE["errors"].append("comfy_boot_failed: " + tail)
    beat()
    log("FATAL: comfy boot")
    sys.exit(2)


# ---- 3. render --------------------------------------------------------------
def pick(info, class_name, input_name, suffix):
    req = info[class_name]["input"]["required"]
    opt = info[class_name]["input"].get("optional", {})
    lst = (req.get(input_name) or opt.get(input_name))[0]
    for cand in lst:
        if suffix in cand:
            return cand
    raise RuntimeError(f"{suffix} not found in {class_name}.{input_name}")


def api_graph(info, job):
    dit = pick(info, "UNETLoader", "unet_name", "fl2va_pruned_fp8_scaled.safetensors")
    clip = pick(info, "CLIPLoader", "clip_name", "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors")
    vvae = pick(info, "VAELoader", "vae_name", "minimax_h3_video_vae_fp16.safetensors")
    avae = pick(info, "VAELoader", "vae_name", "minimax_h3_audio_vae_fp32.safetensors")
    lora = pick(info, "LoraLoaderModelOnly", "lora_name",
                "fl2v_turbo_4step" if job["steps"] == 4 else "fl2v_turbo_8step")
    return {"prompt": {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": dit, "weight_dtype": "default"}},
        "2": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["1", 0], "lora_name": lora, "strength_model": 1.0}},
        "3": {"class_type": "CLIPLoader", "inputs": {"clip_name": clip, "type": "minimax", "device": "default"}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": vvae}},
        "5": {"class_type": "VAELoader", "inputs": {"vae_name": avae}},
        "6": {"class_type": "MiniMaxH3ImageToVideo", "inputs": {"clip": ["3", 0], "vae": ["4", 0],
                                                                "prompt": job["prompt"], "width": job["width"],
                                                                "height": job["height"], "length": job["length"]}},
        "7": {"class_type": "RandomNoise", "inputs": {"noise_seed": job["seed"]}},
        "8": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "res_multistep"}},
        "9": {"class_type": "BasicScheduler", "inputs": {"model": ["2", 0], "scheduler": "simple",
                                                          "steps": job["steps"], "denoise": 1.0}},
        "10": {"class_type": "BasicGuider", "inputs": {"model": ["2", 0], "conditioning": ["6", 0]}},
        "11": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["7", 0], "guider": ["10", 0],
                                                                  "sampler": ["8", 0], "sigmas": ["9", 0],
                                                                  "latent_image": ["6", 1]}},
        "12": {"class_type": "VAEDecode", "inputs": {"samples": ["11", 0], "vae": ["4", 0]}},
        "13": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["11", 0], "vae": ["5", 0]}},
        "14": {"class_type": "CreateVideo", "inputs": {"images": ["12", 0], "audio": ["13", 0], "fps": 24}},
        "15": {"class_type": "SaveVideo", "inputs": {"video": ["14", 0], "filename_prefix": f"video/{job['id']}",
                                                      "codec": "auto", "format": "auto"}},
    }, "client_id": "deyoung-c20"}


def post(base, path, payload):
    req = urllib.request.Request(base + path, json.dumps(payload).encode(),
                                 {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=120).read())


def render_job(base, info, job):
    jid = job["id"]
    before = set(OUT.rglob("*.mp4"))
    r = post(base, "/prompt", api_graph(info, job))
    pid = r["prompt_id"]
    log(f"[{jid}] queued {pid} steps={job['steps']} est={est_min(job):.0f}min")
    beat(phase="rendering", job=jid, est_min=round(est_min(job)))
    t = time.time()
    while True:
        time.sleep(30)
        try:
            h = json.loads(urllib.request.urlopen(base + f"/history/{pid}", timeout=60).read())
        except Exception as e:
            log(f"[{jid}] poll err {e!r}")
            continue
        if pid in h:
            st = h[pid].get("status", {})
            if st.get("status_str") == "error":
                log(f"[{jid}] ERROR", json.dumps(st.get("messages", []))[:500])
                return False
            outs = h[pid].get("outputs", {})
            if outs:
                vid = None
                for no in outs.values():
                    for k in ("images", "gifs", "video", "videos"):
                        for f in no.get(k, []) or []:
                            n = f.get("filename")
                            if n and n.endswith(".mp4"):
                                vid = OUT / n
                if vid is None:
                    cand = sorted(set(OUT.rglob("*.mp4")) - before, key=lambda p: p.stat().st_mtime)
                    vid = cand[-1] if cand else None
                if vid and vid.exists():
                    dest = OUT / (jid + ".mp4")
                    if vid.resolve() != dest.resolve():
                        shutil.move(str(vid), str(dest))
                    took = (time.time() - t) / 60
                    pf = job["length"] * job["width"] * job["height"]
                    STATE["rate_s_per_pf"] = max(0.001, (time.time() - t) / pf)
                    log(f"[{jid}] DONE {took:.0f}min {dest.stat().st_size/1e6:.1f}MB")
                    beat(job=jid, last_minutes=round(took, 1), calibrated_rate=STATE["rate_s_per_pf"])
                    return True
        if (time.time() - t) / 60 > JOB_WATCHDOG_MIN:
            log(f"[{jid}] WATCHDOG abort")
            return False


# ---- 4. upload --------------------------------------------------------------
def upload(jid):
    data = (OUT / (jid + ".mp4")).read_bytes()
    key = f"campaign/v20/{jid}.mp4"
    req = urllib.request.Request(
        f"{os.environ['SUPA_URL']}/storage/v1/object/deyoung-media/{key}", data=data,
        headers={"Authorization": f"Bearer {os.environ['SUPA_KEY']}",
                 "Content-Type": "video/mp4", "x-upsert": "true"}, method="POST")
    with urllib.request.urlopen(req, timeout=900) as r:
        good = r.status in (200, 201)
    log(f"[{jid}] upload {'OK' if good else 'FAIL'} {len(data)/1e6:.1f}MB -> {key}")
    STATE["uploads"].append({"id": jid, "key": key, "bytes": len(data), "ok": good})
    beat()
    return good


def main():
    try:
        _run()
    except SystemExit:
        self_stop()
        raise
    except Exception as e:
        log("UNCAUGHT", repr(e)[:300])
        STATE["phase"] = "fatal"
        STATE["errors"].append("uncaught: " + repr(e)[:250])
        beat()
        self_stop()
        raise
    self_stop()


def _run():
    if not fix_torchaudio():
        log("FATAL: torchaudio unrepairable")
        sys.exit(3)
    base = boot_comfy()
    info = json.loads(urllib.request.urlopen(base + "/object_info", timeout=90).read())
    for k in ("MiniMaxH3ImageToVideo", "CLIPLoader", "CreateVideo", "SaveVideo"):
        if k not in info:
            log("FATAL: node missing", k)
            STATE["phase"] = "fatal"; STATE["errors"].append("missing node " + k); beat(); sys.exit(4)
    beat(phase="ready")
    ok = 0
    for job in JOBS_LIST:
        elapsed = (time.time() - T0) / 60
        if elapsed + est_min(job) + 15 > HARD_CAP_MIN:
            log(f"[{job['id']}] skip: over hard cap")
            STATE["failed"].append(job["id"]); beat(); continue
        good = False
        try:
            good = render_job(base, info, job)
            if good:
                good = upload(job["id"])
        except Exception as e:
            log(f"[{job['id']}] EXC", repr(e)[:300])
            STATE["errors"].append(f"{job['id']}: " + repr(e)[:250])
        ok += 1 if good else 0
        (STATE["done"] if good else STATE["failed"]).append(job["id"])
        beat(phase="between_jobs", last_ok=good)
        try:
            post(base, "/free", {"unload_models": True, "free_memory": True})
        except Exception:
            pass
    log(f"C20_DONE ok={ok}/4")
    beat(phase="finished", ok=ok, total=4)


if __name__ == "__main__":
    main()
