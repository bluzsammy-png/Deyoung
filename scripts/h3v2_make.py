#!/usr/bin/env python3
"""Generate MiniMax-H3 render kernel v2 (checkpointed, cap-aware).

Fixes the v1 failure (12h GPU, 0 output):
  v1: 158f @1376x768 jobs > 90-min per-job timeout on T4 -> every job
      marked TIMEOUT -> no mp4 ever written -> 12h GPU burned, empty output.
  v2: shrunk jobs (960x544, 121f, 4-step turbo) + NO mid-render abort
      (6h watchdog instead) + 12h time-budget skip-guard with adaptive
      calibration + status.json heartbeat to /kaggle/working every poll.

Usage:
  python3 scripts/h3v2_make.py --kernel deyoung-v2-s01 --account deyoungsltd \
      --jobs jobs.json --out campaign/v10/kernels/deyoung-v2-s01
jobs.json = [{"id":"s01","prompt":"..."}, ...] (w/h/len/steps injected here).
"""
import argparse
import base64
import json
import os
import pathlib
import random

W, H, LEN, STEPS = 1376, 768, 80, 4   # native 768p band (turbo lora trained there), 3.3s shots
HARD_CAP_MIN = 11 * 60          # leave 1h of the 12h cap as margin
SETUP_BUDGET_MIN = 45           # clone + 35GB download + ComfyUI boot
RESERVE_MIN = 15                # kept free between jobs
WATCHDOG_MIN = 6 * 60           # per-job hung-render abort (generous)
# conservative: v1 evidence says 158f@1376x768 took >4h on T4
BASE_RATE_S_PER_PF = (6 * 3600) / (158 * 1376 * 768)   # ~0.100 s per pixel-frame


TEMPLATE = '''\
import base64, json, os, pathlib, random, shutil, subprocess, sys, time, urllib.request

JOBS_B64 = "__JOBS_B64__"
HARD_CAP_MIN = __HARD_CAP_MIN__
SETUP_BUDGET_MIN = __SETUP_BUDGET_MIN__
RESERVE_MIN = __RESERVE_MIN__
WATCHDOG_MIN = __WATCHDOG_MIN__
RATE = __RATE__   # conservative seconds per pixel-frame; recalibrated after job 1
PORT = 8188
OUT = pathlib.Path("/kaggle/working/out")
OUT.mkdir(parents=True, exist_ok=True)
COMFY = pathlib.Path("/kaggle/tmp/ComfyUI")
STATUS = pathlib.Path("/kaggle/working/status.json")
T0 = time.time()
STATE = {"phase": "setup", "done": [], "failed": [], "skipped": [], "rate_s_per_pf": RATE}

def log(*a, **kw):
    print("[h3v2]", *a, flush=True)

def beat(**kw):
    STATE.update(kw)
    STATE["elapsed_min"] = round((time.time() - T0) / 60, 1)
    STATE["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    STATUS.write_text(json.dumps(STATE, indent=1))

def est_min(job):
    pf = job["length"] * job["width"] * job["height"]
    return (pf * STATE["rate_s_per_pf"]) / 60.0

log("GPU/CPU report:")
subprocess.run(["nvidia-smi", "--query-gpu=index,name,memory.total", "--format=csv"], check=False)
subprocess.run(["free", "-g"], check=False)

# ---- 1. ComfyUI + plugins -------------------------------------------------
if not COMFY.exists():
    log("cloning ComfyUI…")
    subprocess.run(["git", "clone", "--depth", "1", "https://github.com/comfyanonymous/ComfyUI", str(COMFY)], check=True)
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", str(COMFY / "requirements.txt")], check=False)
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "gguf", "hf_transfer", "imageio-ffmpeg"], check=False)
gguf_dir = COMFY / "custom_nodes" / "ComfyUI-GGUF"
if not gguf_dir.exists():
    subprocess.run(["git", "clone", "--depth", "1", "https://github.com/city96/ComfyUI-GGUF", str(gguf_dir)], check=True)
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", str(gguf_dir / "requirements.txt")], check=False)

# ---- 2. Model downloads ---------------------------------------------------
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
from huggingface_hub import hf_hub_download
M = COMFY / "models"
def dl(repo, fn, sub):
    dest = M / sub / fn
    if dest.exists():
        return dest
    p = hf_hub_download(repo_id=repo, filename=fn)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if pathlib.Path(p).resolve() != dest.resolve():
        shutil.copy2(p, dest)
    return dest

log("downloading MiniMax H3 open-weight stack (~35 GB)…", flush=True)
beat(phase="download")
dl("Comfy-Org/MiniMax-H3", "diffusion_models/minimax_h3_fl2va_pruned_fp8_scaled.safetensors", "diffusion_models")
dl("Comfy-Org/MiniMax-H3", "text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors", "text_encoders")
dl("Comfy-Org/MiniMax-H3", "vae/minimax_h3_video_vae_fp16.safetensors", "vae")
dl("Comfy-Org/MiniMax-H3", "vae/minimax_h3_audio_vae_fp32.safetensors", "vae")
dl("Comfy-Org/MiniMax-H3", "loras/minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors", "loras")
log("models ready in", round(time.time() - T0), "s")

# ---- 3. Serve ComfyUI headless --------------------------------------------
env = {**os.environ, "CUDA_VISIBLE_DEVICES": "0"}
srv = subprocess.Popen(
    [sys.executable, str(COMFY / "main.py"), "--listen", "127.0.0.1", "--port", str(PORT),
     "--output-directory", str(OUT), "--disable-auto-launch", "--reserve-vram", "0.4"],
    cwd=str(COMFY), env=env,
    stdout=open("/kaggle/working/comfy.log", "w"), stderr=subprocess.STDOUT)
BASE = f"http://127.0.0.1:{PORT}"

for i in range(90):
    try:
        urllib.request.urlopen(BASE + "/queue", timeout=5); break
    except Exception:
        time.sleep(10)
else:
    log("ComfyUI failed to boot"); beat(phase="fatal", reason="comfy_boot"); sys.exit(1)
log("ComfyUI up after", round(time.time() - T0), "s")
beat(phase="ready", setup_min=round((time.time() - T0) / 60, 1))

info = json.loads(urllib.request.urlopen(BASE + "/object_info", timeout=60).read())
for k in ("MiniMaxH3ImageToVideo", "CLIPLoader", "CreateVideo", "SaveVideo"):
    log("node", k, "OK" if k in info else "MISSING")
def pick(class_name, input_name, suffix):
    lst = info[class_name]["input"]["required"].get(input_name) or info[class_name]["input"].get("optional", {}).get(input_name)
    lst = lst[0]
    for cand in lst:
        if suffix in cand:
            return cand
    log("FATAL: model not in list:", class_name, input_name, suffix); beat(phase="fatal", reason="model_missing"); sys.exit(1)

UNET_CLASS = "UNETLoader"
DIT_NAME = pick(UNET_CLASS, "unet_name", "fl2va_pruned_fp8_scaled.safetensors")
CLIP_NAME = pick("CLIPLoader", "clip_name", "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors")
VVAE_NAME = pick("VAELoader", "vae_name", "minimax_h3_video_vae_fp16.safetensors")
AVAE_NAME = pick("VAELoader", "vae_name", "minimax_h3_audio_vae_fp32.safetensors")
LORA4_NAME = pick("LoraLoaderModelOnly", "lora_name", "fl2v_turbo_4step")
log("resolved:", DIT_NAME, "|", CLIP_NAME)

def api(job):
    g = {
        "1": {"class_type": UNET_CLASS, "inputs": {"unet_name": DIT_NAME, "weight_dtype": "default"}},
        "2": {"class_type": "LoraLoaderModelOnly",
              "inputs": {"model": ["1", 0], "lora_name": LORA4_NAME, "strength_model": 1.0}},
        "3": {"class_type": "CLIPLoader", "inputs": {"clip_name": CLIP_NAME, "type": "minimax", "device": "default"}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": VVAE_NAME}},
        "5": {"class_type": "VAELoader", "inputs": {"vae_name": AVAE_NAME}},
        "6": {"class_type": "MiniMaxH3ImageToVideo",
              "inputs": {"clip": ["3", 0], "vae": ["4", 0], "prompt": job["prompt"],
                         "width": job["width"], "height": job["height"], "length": job["length"]}},
        "7": {"class_type": "RandomNoise", "inputs": {"noise_seed": job["seed"]}},
        "8": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "res_multistep"}},
        "9": {"class_type": "BasicScheduler", "inputs": {"model": ["2", 0], "scheduler": "simple", "steps": job["steps"], "denoise": 1.0}},
        "10": {"class_type": "BasicGuider", "inputs": {"model": ["2", 0], "conditioning": ["6", 0]}},
        "11": {"class_type": "SamplerCustomAdvanced",
               "inputs": {"noise": ["7", 0], "guider": ["10", 0], "sampler": ["8", 0], "sigmas": ["9", 0], "latent_image": ["6", 1]}},
        "12": {"class_type": "VAEDecode", "inputs": {"samples": ["11", 0], "vae": ["4", 0]}},
        "13": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["11", 0], "vae": ["5", 0]}},
        "14": {"class_type": "CreateVideo", "inputs": {"images": ["12", 0], "audio": ["13", 0], "fps": 24}},
        "15": {"class_type": "SaveVideo", "inputs": {"video": ["14", 0], "filename_prefix": f"video/{job['id']}", "codec": "auto", "format": "auto"}},
    }
    return {"prompt": g, "client_id": "deyoung-h3v2"}

def post(path, payload):
    req = urllib.request.Request(BASE + path, json.dumps(payload).encode(), {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=120).read())

def render(job):
    jid = job["id"]
    before = set(OUT.rglob("*.mp4"))
    r = post("/prompt", api(job))
    pid = r["prompt_id"]
    log(f"[job {jid}] queued ({pid}) {job['width']}x{job['height']} len={job['length']} steps={job['steps']} est={est_min(job):.0f}min")
    beat(phase="rendering", job=jid, prompt_id=pid, est_min=round(est_min(job)))
    t = time.time()
    while True:
        time.sleep(30)
        try:
            h = json.loads(urllib.request.urlopen(BASE + f"/history/{pid}", timeout=60).read())
        except Exception as e:
            log(f"[job {jid}] poll err {e!r}"); continue
        if pid in h:
            st = h[pid].get("status", {})
            if st.get("status_str") == "error":
                log(f"[job {jid}] ERROR:", json.dumps(st.get("messages", []))[:600])
                return False
            outs = h[pid].get("outputs", {})
            if outs:
                vid = None
                for node_out in outs.values():
                    for k in ("images", "gifs", "video", "videos"):
                        for f in node_out.get(k, []) or []:
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
                    sz = dest.stat().st_size / 1e6
                    took = (time.time() - t) / 60
                    log("[job " + jid + "] DONE", round(took), "min", round(sz, 1), "MB ->", dest.name)
                    # calibrate the rate model from real data
                    pf = job["length"] * job["width"] * job["height"]
                    if pf > 0:
                        STATE["rate_s_per_pf"] = max(0.001, (time.time() - t) / pf)
                        beat(job=jid, calibrated_rate=STATE["rate_s_per_pf"])
                    return True
        if (time.time() - t) / 60 > WATCHDOG_MIN:
            log(f"[job {jid}] WATCHDOG abort after {WATCHDOG_MIN}min")
            return False

jobs = json.loads(base64.b64decode(JOBS_B64).decode())
ok = 0
manifest = []
for job in jobs:
    elapsed = (time.time() - T0) / 60
    budget = est_min(job) + RESERVE_MIN
    if elapsed + budget > HARD_CAP_MIN:
        reason = f"skip: {elapsed:.0f}min elapsed + {budget:.0f}min est > {HARD_CAP_MIN}min cap"
        log(f"[job {job['id']}]", reason)
        manifest.append({"id": job["id"], "ok": False, "skipped": reason})
        STATE["skipped"].append(job["id"]); beat()
        continue
    try:
        good = render(job)
    except Exception as e:
        log("[job " + job["id"] + "] EXC", repr(e)[:300]); good = False
    ok += 1 if good else 0
    manifest.append({"id": job["id"], "ok": good})
    if good:
        STATE["done"].append(job["id"])
    else:
        STATE["failed"].append(job["id"])
    beat(phase="between_jobs", last_ok=good)
    try:
        post("/free", {"unload_models": True, "free_memory": True})
    except Exception:
        pass
    pathlib.Path("/kaggle/working/result.json").write_text(json.dumps(manifest, indent=1))

log("H3V2_KERNEL_DONE ok=" + str(ok) + "/" + str(len(jobs)) + " elapsed=" + str(round((time.time()-T0)/60)) + "min")
beat(phase="finished", ok=ok, total=len(jobs))
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kernel", required=True)
    ap.add_argument("--account", required=True)
    ap.add_argument("--jobs", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    jobs = json.load(open(args.jobs))
    for j in jobs:
        j.setdefault("width", W); j.setdefault("height", H)
        j.setdefault("length", LEN); j.setdefault("steps", STEPS)
        j.setdefault("seed", random.randint(1, 2**31 - 1))
    b64 = base64.b64encode(json.dumps(jobs, indent=1).encode()).decode()

    code = (TEMPLATE
            .replace("__JOBS_B64__", b64)
            .replace("__HARD_CAP_MIN__", str(HARD_CAP_MIN))
            .replace("__SETUP_BUDGET_MIN__", str(SETUP_BUDGET_MIN))
            .replace("__RESERVE_MIN__", str(RESERVE_MIN))
            .replace("__WATCHDOG_MIN__", str(WATCHDOG_MIN))
            .replace("__RATE__", repr(BASE_RATE_S_PER_PF)))

    outdir = pathlib.Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / f"{args.kernel}.py").write_text(code)
    meta = {
        "id": f"{args.account}/{args.kernel}",
        "title": args.kernel,
        "code_file": f"{args.kernel}.py",
        "language": "python",
        "kernel_type": "script",
        "is_private": "true",
        "enable_gpu": "true",
        "enable_internet": "true",
        "dataset_sources": [],
        "competition_sources": [],
        "kernel_sources": [],
    }
    (outdir / "kernel-metadata.json").write_text(json.dumps(meta, indent=2))
    ests = {j["id"]: round(BASE_RATE_S_PER_PF * j["length"] * j["width"] * j["height"] / 60) for j in jobs}
    print("kernel dir:", outdir)
    print("jobs:", [(j["id"], j["width"], j["height"], j["length"], j["steps"]) for j in jobs])
    print("conservative est per job (min):", ests, "| hard cap:", HARD_CAP_MIN, "min")
    pf_total = sum(j["length"] * j["width"] * j["height"] for j in jobs)
    print(f"est total incl setup: {round(BASE_RATE_S_PER_PF * pf_total / 60 + SETUP_BUDGET_MIN)}min")


if __name__ == "__main__":
    main()
