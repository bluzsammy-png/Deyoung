#!/usr/bin/env python3
"""
DeYoung SITE-RENDER worker — the DB-plane drain that bypasses the Railway edge.

Runs on a Kaggle GPU kernel. Talks STRAIGHT to production Postgres (scoped
role deyoung_fleet — no site API involved), so Railway's hikari edge can never
429 it. Pipeline per claimed job:

  claim (SKIP LOCKED) -> storyboard (character sheets + scene keyframes via
  SDXL) -> MiniMax-H3 image-to-video from the keyframe -> LIP-SYNC PASS
  (edge-tts voices the scene's spoken line with a per-character neural voice;
  Wav2Lip re-renders the speaking character's mouth to the voice; the dialogue
  is mixed over the H3 soundscape) -> optional watermark -> upload to Supabase
  Storage -> Asset row -> VideoRequest done.

This is how characters stay consistent: every scene starts from its own
keyframe, drawn with the exact cast descriptors from the studio script.
The lip-sync pass is fail-safe: ANY problem (no face, weights, network) skips
it gracefully and the clean H3 render ships anyway — lip-sync can only ADD,
never break.
The storyboard (sheets + keyframes) is written back onto the StudioProject so
the studio UI can SHOW the characters being created.

All secrets are injected below at kernel-make time (private kernel).
"""

import base64, glob, hashlib, json, os, pathlib, random, re, shutil, subprocess, sys, tempfile, time, urllib.request, uuid

DSN = "{{DSN}}"
SUPA_URL = "{{SUPA_URL}}"
SUPA_KEY = "{{SUPA_KEY}}"
AGENT = "{{AGENT}}"

HARD_CAP_MIN = 630
IDLE_EXIT_POLLS = 3
IDLE_POLL_SEC = 240
WATCHDOG_MIN = 360
RATE = 0.0001293650647630262  # seconds per pixel-frame (calibrated on the canary)
PORT = 8188
OUT = pathlib.Path("/kaggle/working/out")
OUT.mkdir(parents=True, exist_ok=True)
COMFY = pathlib.Path("/kaggle/tmp/ComfyUI")
T0 = time.time()
STATE = {"phase": "setup", "claimed": [], "done": [], "failed": []}

def log(*a):
    print("[site-w]", *a, flush=True)

def elapsed_min():
    return (time.time() - T0) / 60

# ---- 1. deps + ComfyUI ------------------------------------------------------
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "psycopg2-binary", "gguf", "hf_transfer", "imageio-ffmpeg", "edge-tts", "batch-face"], check=False)
if not COMFY.exists():
    log("cloning ComfyUI…")
    subprocess.run(["git", "clone", "--depth", "1", "https://github.com/comfyanonymous/ComfyUI", str(COMFY)], check=True)
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", str(COMFY / "requirements.txt")], check=False)
gguf_dir = COMFY / "custom_nodes" / "ComfyUI-GGUF"
if not gguf_dir.exists():
    subprocess.run(["git", "clone", "--depth", "1", "https://github.com/city96/ComfyUI-GGUF", str(gguf_dir)], check=True)
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", str(gguf_dir / "requirements.txt")], check=False)

# brand font (public repo, tracked)
FONT = pathlib.Path("/kaggle/working/Archivo.ttf")
if not FONT.exists():
    try:
        urllib.request.urlretrieve(
            "https://raw.githubusercontent.com/bluzsammy-png/Deyoung/main/public/fonts/Archivo.ttf", FONT)
    except Exception as e:
        log("font download failed (watermarks will use default font):", repr(e))

# ---- 2. models --------------------------------------------------------------
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

log("downloading MiniMax-H3 stack (~35 GB)…")
dl("Comfy-Org/MiniMax-H3", "diffusion_models/minimax_h3_fl2va_pruned_fp8_scaled.safetensors", "diffusion_models")
dl("Comfy-Org/MiniMax-H3", "text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors", "text_encoders")
dl("Comfy-Org/MiniMax-H3", "vae/minimax_h3_video_vae_fp16.safetensors", "vae")
dl("Comfy-Org/MiniMax-H3", "vae/minimax_h3_audio_vae_fp32.safetensors", "vae")
dl("Comfy-Org/MiniMax-H3", "loras/minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors", "loras")
log("downloading SDXL base (~7 GB) for the storyboard…")
dl("stabilityai/stable-diffusion-xl-base-1.0", "sd_xl_base_1.0.safetensors", "checkpoints")
log("models ready in", round(time.time() - T0), "s")

# ---- 3. ComfyUI headless ----------------------------------------------------
env = {**os.environ, "CUDA_VISIBLE_DEVICES": "0"}
srv = subprocess.Popen(
    [sys.executable, str(COMFY / "main.py"), "--listen", "127.0.0.1", "--port", str(PORT),
     "--output-directory", str(OUT), "--disable-auto-launch", "--reserve-vram", "0.4"],
    cwd=str(COMFY), env=env,
    stdout=open("/kaggle/working/comfy.log", "w"), stderr=subprocess.STDOUT)
BASE = f"http://127.0.0.1:{PORT}"

for _ in range(90):
    try:
        urllib.request.urlopen(BASE + "/queue", timeout=5); break
    except Exception:
        time.sleep(10)
else:
    log("ComfyUI failed to boot"); sys.exit(1)
log("ComfyUI up after", round(time.time() - T0), "s")

info = json.loads(urllib.request.urlopen(BASE + "/object_info", timeout=120).read())
def pick(cls, inp, suffix):
    lst = info[cls]["input"]["required"].get(inp) or info[cls]["input"].get("optional", {}).get(inp)
    for cand in lst[0]:
        if suffix in cand:
            return cand
    raise RuntimeError(f"model not found: {cls}/{inp}/{suffix}")

UNET = pick("UNETLoader", "unet_name", "fl2va_pruned_fp8_scaled.safetensors")
CLIP = pick("CLIPLoader", "clip_name", "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors")
VVAE = pick("VAELoader", "vae_name", "minimax_h3_video_vae_fp16.safetensors")
AVAE = pick("VAELoader", "vae_name", "minimax_h3_audio_vae_fp32.safetensors")
LORA4 = pick("LoraLoaderModelOnly", "lora_name", "fl2v_turbo_4step")
SDXL = pick("CheckpointLoaderSimple", "ckpt_name", "sd_xl_base_1.0.safetensors")
IMG_KEY = None
for k, v in (info["MiniMaxH3ImageToVideo"]["input"].get("optional") or {}).items():
    if "image" in k.lower():
        IMG_KEY = k
log("resolved:", UNET, "| img_key:", IMG_KEY)

def post(path, payload, timeout=120):
    req = urllib.request.Request(BASE + path, json.dumps(payload).encode(), {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())

def run_graph(g, timeout_min=8):
    r = post("/prompt", {"prompt": g, "client_id": AGENT})
    pid = r["prompt_id"]
    t = time.time()
    while True:
        time.sleep(5)
        if (time.time() - t) / 60 > timeout_min:
            raise RuntimeError("graph watchdog")
        h = json.loads(urllib.request.urlopen(BASE + f"/history/{pid}", timeout=60).read())
        if pid in h:
            st = h[pid].get("status", {})
            if st.get("status_str") == "error":
                raise RuntimeError("graph error: " + json.dumps(st.get("messages", []))[:500])
            outs = h[pid].get("outputs", {})
            if outs:
                files = []
                for no in outs.values():
                    for key in ("images", "gifs", "video", "videos"):
                        for f in no.get(key, []) or []:
                            if f.get("filename"):
                                files.append(OUT / f["filename"])
                return [p for p in files if p.exists()]

def free_mem():
    try:
        post("/free", {"unload_models": True, "free_memory": True})
    except Exception:
        pass

# ---- 4. DB plane (scoped role) ---------------------------------------------
import psycopg2, psycopg2.extras

CLAIM_SQL = '''
UPDATE deyoung."VideoRequest" SET status='rendering', notes=%(claim)s, "updatedAt"=now()
WHERE id = (
  SELECT id FROM deyoung."VideoRequest"
  WHERE status='queued'
    -- F-9 (W3.1): reserved rows are held back from automated claimers, exactly
    -- like the API plane (/api/worker/claim) — parity between the two claim
    -- surfaces. notes is NOT NULL DEFAULT '', so NOT LIKE is NULL-safe.
    AND notes NOT LIKE '%%reserved:%%'
  ORDER BY "queuePriority" DESC, "createdAt" ASC, id ASC LIMIT 1 FOR UPDATE SKIP LOCKED
) RETURNING id, prompt, seconds, resolution, "withAudio", watermark, notes
'''
PROJECT_SQL = 'SELECT id, title, niche, "scriptJson", "storyboardJson" FROM deyoung."StudioProject" WHERE id=%s'
SB_SQL = 'UPDATE deyoung."StudioProject" SET "storyboardJson"=%s, "updatedAt"=now() WHERE id=%s'
ASSET_SQL = '''INSERT INTO deyoung."Asset"
  (id, kind, mime, bytes, "storageKey", driver, "isPublic", sha256, "createdBy", "createdAt")
VALUES (%(id)s, %(kind)s, %(mime)s, %(bytes)s, %(storageKey)s, 'supabase', %(isPublic)s, %(sha256)s, %(createdBy)s, now())
RETURNING id'''
DONE_SQL = """UPDATE deyoung."VideoRequest" SET status='done', "gpuMinutes"=%(gpu)s,
  "resultUrl"=%(url)s, "resultAssetId"=%(asset)s, notes=%(note)s, "updatedAt"=now()
WHERE id=%(id)s AND status='rendering'"""
FAIL_SQL = """UPDATE deyoung."VideoRequest" SET status='failed', notes=%(note)s, "updatedAt"=now()
WHERE id=%(id)s AND status='rendering'"""
PROG_SQL = """UPDATE deyoung."VideoRequest" SET notes=%(note)s, "updatedAt"=now()
WHERE id=%(id)s AND status='rendering'"""

def conn():
    return psycopg2.connect(DSN, connect_timeout=20)

def db_claim():
    with conn() as c, c.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(CLAIM_SQL, {"claim": f"claimed by {AGENT} at {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}"})
        return cur.fetchone()

def db_project(pid):
    with conn() as c, c.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(PROJECT_SQL, (pid,))
        return cur.fetchone()

def db_storyboard(pid, sb):
    with conn() as c, c.cursor() as cur:
        cur.execute(SB_SQL, (json.dumps(sb), pid))

def db_asset(kind, mime, data, key, is_public, created_by):
    with conn() as c, c.cursor() as cur:
        cur.execute(ASSET_SQL, {"id": f"flt-{uuid.uuid4().hex[:20]}", "kind": kind, "mime": mime,
                                "bytes": len(data), "storageKey": key, "isPublic": is_public,
                                "sha256": hashlib.sha256(data).hexdigest(), "createdBy": created_by})
        return cur.fetchone()[0]

def db_done(jid, gpu, url, asset, note):
    with conn() as c, c.cursor() as cur:
        cur.execute(DONE_SQL, {"gpu": round(gpu, 1), "url": url, "asset": asset, "note": note[:500], "id": jid})
        return cur.rowcount == 1

def db_fail(jid, note):
    with conn() as c, c.cursor() as cur:
        cur.execute(FAIL_SQL, {"note": note[:1000], "id": jid})

def db_progress(jid, note):
    try:
        with conn() as c, c.cursor() as cur:
            cur.execute(PROG_SQL, {"note": note[:500], "id": jid})
    except Exception as e:
        log("progress skipped:", repr(e)[:120])

# ---- 5. storage -------------------------------------------------------------
def storage_put(key, data, mime):
    req = urllib.request.Request(
        f"{SUPA_URL}/storage/v1/object/deyoung-media/{key}", data=data,
        headers={"Authorization": f"Bearer {SUPA_KEY}", "Content-Type": mime, "x-upsert": "true"},
        method="POST")
    with urllib.request.urlopen(req, timeout=600) as r:
        if r.status not in (200, 201):
            raise RuntimeError(f"storage upload HTTP {r.status}")

# ---- 6. storyboard (character sheets + keyframes) ---------------------------
STYLE_HINTS = {
    "kids cartoon": "2D animated children's cartoon style with bold clean outlines",
    "product ad": "photorealistic cinematic commercial style, ultra detailed",
    "real estate": "photorealistic architectural cinematography, ultra realistic",
    "music video": "stylized music-video cinematography, dramatic and vivid",
    "explainer": "clean modern explainer animation style, friendly shapes",
    "social reel": "vibrant social-media cinematography, punchy and modern",
    "travel": "cinematic travel documentary look, ultra realistic",
    "fashion": "high-fashion editorial cinematography, elegant lighting",
    "gaming": "AAA game cinematic style, hyper detailed",
}
def style_hint(niche):
    return STYLE_HINTS.get((niche or "").lower(),
                           "cinematic film style, ultra realistic, movie-grade lighting")

NEG = "blurry, low quality, deformed, extra fingers, watermark, text, logo, caption, worst quality"

def sdxl_graph(pos, w, h, seed, steps=24):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": SDXL}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": pos}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": NEG}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0],
               "latent_image": ["4", 0], "seed": seed, "steps": steps, "cfg": 6.5,
               "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 1.0}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage", "inputs": {"images": ["6", 0], "filename_prefix": "sb/img"}},
    }

def gen_image(pos, w, h, seed):
    files = run_graph(sdxl_graph(pos, w, h, seed), timeout_min=10)
    if not files:
        raise RuntimeError("sdxl produced nothing")
    return files[0].read_bytes()

def ensure_storyboard(proj, job):
    """Draw the cast sheets + every scene keyframe once per project."""
    sb_raw = proj.get("storyboardJson")
    if sb_raw:
        try:
            sb = json.loads(sb_raw)
            if sb.get("sheets") and sb.get("keyframes"):
                return sb
        except Exception:
            pass
    script = json.loads(proj.get("scriptJson") or "{}")
    chars = script.get("characters") or []
    scenes = script.get("scenes") or []
    hint = style_hint(proj.get("niche"))
    sb = {"sheets": [], "keyframes": []}
    # character sheets — the cast, created from scratch
    for ch in chars[:3]:
        name = ch.get("name") or "Character"
        look = ch.get("look") or ""
        seed = int(hashlib.sha256(name.encode()).hexdigest()[:8], 16)
        pos = (f"character reference sheet, {hint}: {name}, {look}. "
               "Full body, front view, neutral plain background, high detail, appealing design.")
        png = gen_image(pos, 1024, 1024, seed)
        key = f"storyboard/{proj['id']}/sheet-{re.sub(r'[^a-z0-9]+', '-', name.lower())[:30]}.png"
        aid = db_asset("image", "image/png", png, key, True, f"worker:{AGENT}")
        storage_put(key, png, "image/png")
        sb["sheets"].append({"name": name, "url": f"/api/files/{aid}"})
        db_progress(job["id"], f"storyboard: character sheet '{name}' drawn")
        log("sheet:", name)
    free_mem()
    # scene keyframes — same descriptors + deterministic seeds = consistent cast
    looks = "; ".join(f"{c.get('name')}: {c.get('look', '')}" for c in chars[:3])
    for i, sc in enumerate(scenes[:10]):
        sid = sc.get("id") or f"s{i+1}"
        seed = int(hashlib.sha256((proj["id"] + sid).encode()).hexdigest()[:8], 16)
        pos = (f"{hint}. Cinematic film still, {sc.get('visual', '')}. "
               f"Cast exactly as designed — {looks}. Wide composition, high detail.")
        png = gen_image(pos, 1024, 576, seed)
        key = f"storyboard/{proj['id']}/kf-{sid}.png"
        aid = db_asset("image", "image/png", png, key, True, f"worker:{AGENT}")
        storage_put(key, png, "image/png")
        sb["keyframes"].append({"scene": sid, "url": f"/api/files/{aid}"})
        db_progress(job["id"], f"storyboard: keyframe for {sid} drawn")
        log("keyframe:", sid)
    free_mem()
    db_storyboard(proj["id"], sb)
    return sb

def fetch_keyframe_png(kf):
    """Pull a storyboard keyframe back down (signed URL) to feed H3 i2v."""
    aid = kf["url"].rsplit("/", 1)[-1]
    with conn() as c, c.cursor() as cur:
        cur.execute('SELECT "storageKey" FROM deyoung."Asset" WHERE id=%s', (aid,))
        row = cur.fetchone()
    if not row or not row[0]:
        return None
    req = urllib.request.Request(
        f"{SUPA_URL}/storage/v1/object/sign/deyoung-media/{row[0]}",
        data=json.dumps({"expiresIn": 3600}).encode(),
        headers={"Authorization": f"Bearer {SUPA_KEY}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        su = json.loads(r.read())
    url = SUPA_URL + "/storage/v1" + su["signedURL"].replace("/storage/v1", "", 1)
    return urllib.request.urlopen(url, timeout=120).read()

# ---- 7. the video (H3 image-to-video from the keyframe) ---------------------
def h3_graph(prompt, w, h, length, seed, start_image_name=None):
    node6 = {"clip": ["3", 0], "vae": ["4", 0], "prompt": prompt,
             "width": w, "height": h, "length": length}
    g = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": UNET, "weight_dtype": "default"}},
        "2": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["1", 0], "lora_name": LORA4, "strength_model": 1.0}},
        "3": {"class_type": "CLIPLoader", "inputs": {"clip_name": CLIP, "type": "minimax", "device": "default"}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": VVAE}},
        "5": {"class_type": "VAELoader", "inputs": {"vae_name": AVAE}},
        "6": {"class_type": "MiniMaxH3ImageToVideo", "inputs": node6},
        "7": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "8": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "res_multistep"}},
        "9": {"class_type": "BasicScheduler", "inputs": {"model": ["2", 0], "scheduler": "simple", "steps": 4, "denoise": 1.0}},
        "10": {"class_type": "BasicGuider", "inputs": {"model": ["2", 0], "conditioning": ["6", 0]}},
        "11": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["7", 0], "guider": ["10", 0],
                "sampler": ["8", 0], "sigmas": ["9", 0], "latent_image": ["6", 1]}},
        "12": {"class_type": "VAEDecode", "inputs": {"samples": ["11", 0], "vae": ["4", 0]}},
        "13": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["11", 0], "vae": ["5", 0]}},
        "14": {"class_type": "CreateVideo", "inputs": {"images": ["12", 0], "audio": ["13", 0], "fps": 24}},
        "15": {"class_type": "SaveVideo", "inputs": {"video": ["14", 0], "filename_prefix": "video/scene", "codec": "auto", "format": "auto"}},
    }
    if IMG_KEY and start_image_name:
        g["16"] = {"class_type": "LoadImage", "inputs": {"image": start_image_name}}
        g["6"]["inputs"][IMG_KEY] = ["16", 0]
    return g

def render_video(job, keyframe_png):
    secs = int(job["seconds"] or 5)
    length = max(121, min(289, round(secs * 24)))
    seed = random.randint(1, 2**31)
    kp = None
    if IMG_KEY and keyframe_png:
        inbox = COMFY / "input" / f"kf-{job['id']}.png"
        inbox.parent.mkdir(parents=True, exist_ok=True)
        inbox.write_bytes(keyframe_png)
        kp = inbox.name
    g = h3_graph(job["prompt"], 960, 544, length, seed, kp)
    pf = length * 960 * 544
    est = pf * RATE / 60
    db_progress(job["id"], f"rendering {length}f @960x544 (~{est:.0f} min on the GPU)")
    log(f"job {job['id']}: {length}f est={est:.0f}min keyframe={'yes' if kp else 'no'}")
    files = run_graph(g, timeout_min=WATCHDOG_MIN)
    mp4 = next((p for p in files if p.suffix == ".mp4"), None)
    if not mp4:
        raise RuntimeError("no mp4 in graph output")
    dest = OUT / f"{job['id']}.mp4"
    shutil.move(str(mp4), str(dest))
    if not job["withAudio"]:
        raw = OUT / f"{job['id']}-na.mp4"
        subprocess.run(["ffmpeg", "-y", "-i", str(dest), "-an", "-c:v", "copy", str(raw)],
                       capture_output=True)
        if raw.exists():
            dest.unlink(); raw.rename(dest)
    if job["watermark"] and FONT.exists():
        wm = OUT / f"{job['id']}-wm.mp4"
        subprocess.run(["ffmpeg", "-y", "-i", str(dest), "-vf",
                        f"drawtext=fontfile={FONT}:text='DEYOUNG':fontcolor=white@0.55:fontsize=30:x=w-tw-28:y=h-th-28",
                        "-c:a", "copy", str(wm)], capture_output=True)
        if wm.exists():
            dest.unlink(); wm.rename(dest)
    return dest

# ---- 8. lip-sync pass (edge-tts voice + Wav2Lip mouth) -----------------------
"""Per-scene dialogue: the scene's `line` is voiced with a neural voice chosen
per CHARACTER (deterministic — same character, same voice in every scene),
then Wav2Lip re-renders the mouth to the voice and the dialogue is mixed over
the H3 soundscape (ducked to 28%). Fail-safe at every step."""
W2L = pathlib.Path("/kaggle/working/Wav2Lip")
VOICE_BANK = {
    "kids cartoon": ["en-US-AnaNeural", "en-US-EmmaNeural", "en-US-GuyNeural"],
    "product ad":   ["en-US-JennyNeural", "en-US-GuyNeural", "en-US-AriaNeural"],
    "real estate":  ["en-US-AriaNeural", "en-US-JennyNeural", "en-US-ChristopherNeural"],
    "music video":  ["en-GB-SoniaNeural", "en-US-AriaNeural", "en-US-GuyNeural"],
    "explainer":    ["en-US-JennyNeural", "en-US-GuyNeural", "en-US-AnaNeural"],
    "social reel":  ["en-US-AriaNeural", "en-US-JennyNeural", "en-US-ChristopherNeural"],
    "travel":       ["en-GB-SoniaNeural", "en-US-GuyNeural", "en-US-AriaNeural"],
    "fashion":      ["en-GB-SoniaNeural", "en-US-JennyNeural", "en-US-GuyNeural"],
    "gaming":       ["en-US-GuyNeural", "en-US-AnaNeural", "en-US-AriaNeural"],
}
DEFAULT_VOICES = ["en-US-JennyNeural", "en-US-GuyNeural", "en-US-AnaNeural"]

def voice_for(niche, actor_name, actor_index):
    bank = VOICE_BANK.get((niche or "").lower(), DEFAULT_VOICES)
    h = int(hashlib.sha256((actor_name or f"c{actor_index}").encode()).hexdigest()[:8], 16)
    return bank[h % len(bank)]

def scene_line(proj, sid):
    """(line, actor_name) for a scene id, or (None, None). Actor rotation must
    mirror the script writer's: characters[i % len]."""
    try:
        script = json.loads(proj.get("scriptJson") or "{}")
        scenes = script.get("scenes") or []
        idx = next((i for i, s in enumerate(scenes) if (s.get("id") or "") == sid), None)
        if idx is None:
            return None, None
        line = (scenes[idx].get("line") or "").strip()
        if not line:
            return None, None
        chars = script.get("characters") or []
        actor = (chars[idx % len(chars)]["name"] if chars else None)
        return line, actor
    except Exception:
        return None, None

def setup_wav2lip():
    if not W2L.exists():
        subprocess.run(["git", "clone", "--depth", "1",
                        "https://github.com/justinjohn0306/Wav2Lip", str(W2L)],
                       check=True, capture_output=True)
    ck = W2L / "checkpoints" / "wav2lip_gan.pth"
    if not ck.exists() or ck.stat().st_size < 100_000_000:
        ck.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(
            "https://huggingface.co/EraSpire/wav2lip/resolve/main/wav2lip_gan.pth", ck)
    mb = W2L / "checkpoints" / "mobilenet.pth"
    if not mb.exists() or mb.stat().st_size < 5_000_000:
        urllib.request.urlretrieve(
            "https://github.com/justinjohn0306/Wav2Lip/releases/download/models/mobilenet.pth", mb)

def tts_line(text, voice, out_wav):
    mp3 = out_wav.with_suffix(".mp3")
    r = subprocess.run([sys.executable, "-m", "edge_tts", "--voice", voice,
                        "--text", text, "--write-media", str(mp3)],
                       capture_output=True, text=True, timeout=90)
    if not mp3.exists() or mp3.stat().st_size < 1000:
        raise RuntimeError(f"edge-tts failed: {(r.stderr or '')[-150:]}")
    subprocess.run(["ffmpeg", "-y", "-i", str(mp3), "-ar", "16000", "-ac", "1", str(out_wav)],
                   capture_output=True, check=True)
    return out_wav

def has_audio(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0",
                        "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True)
    return "audio" in (r.stdout or "")

def lipsync_pass(video, line, voice, jid):
    """Returns (video_path, note). Never raises — the clean H3 render is the floor."""
    try:
        db_progress(jid, "lip-sync: voicing the line with a neural voice")
        free_mem()  # unload ComfyUI models so Wav2Lip gets a clean GPU
        setup_wav2lip()
        wav = OUT / f"{jid}-line.wav"
        tts_line(line, voice, wav)
        db_progress(jid, "lip-sync: syncing the mouth to the voice")
        lip = OUT / f"{jid}-lip.mp4"
        r = subprocess.run(
            [sys.executable, str(W2L / "inference.py"),
             "--checkpoint_path", str(W2L / "checkpoints" / "wav2lip_gan.pth"),
             "--face", str(video), "--audio", str(wav), "--outfile", str(lip),
             "--pads", "0", "14", "0", "8", "--nosmooth"],
            cwd=str(W2L), capture_output=True, text=True, timeout=900)
        if not lip.exists() or lip.stat().st_size < 50_000:
            tail = (r.stderr or r.stdout or "")[-220:].replace("\n", " ")
            raise RuntimeError(f"wav2lip produced nothing: {tail}")
        if has_audio(video):
            mixed = OUT / f"{jid}-mix.mp4"
            m = subprocess.run(
                ["ffmpeg", "-y", "-i", str(lip), "-i", str(video), "-filter_complex",
                 "[1:a]volume=0.28,aformat=sample_rates=44100:channel_layouts=stereo[bg];"
                 "[0:a]aformat=sample_rates=44100:channel_layouts=stereo,adelay=150|150[d];"
                 "[bg][d]amix=inputs=2:duration=first:normalize=0[aout]",
                 "-map", "0:v", "-map", "[aout]", "-c:v", "copy",
                 "-c:a", "aac", "-ar", "44100", "-b:a", "192k", str(mixed)],
                capture_output=True, text=True)
            if mixed.exists() and mixed.stat().st_size > 50_000:
                return mixed, "lip-sync: WAV2LIP+EDGE-TTS OK (dialogue over soundscape)"
            return lip, "lip-sync: WAV2LIP+EDGE-TTS OK (dialogue only; soundscape mix failed)"
        return lip, "lip-sync: WAV2LIP+EDGE-TTS OK (dialogue track)"
    except Exception as e:
        log("lip-sync skipped for", jid, ":", repr(e)[:200])
        return video, f"lip-sync skipped ({str(e)[:140]}) — clean H3 render delivered"

# ---- 9. main loop -----------------------------------------------------------
log(f"up — agent={AGENT} cap={HARD_CAP_MIN}min idle_exit={IDLE_EXIT_POLLS}x{IDLE_POLL_SEC}s")
idle = 0
while elapsed_min() < HARD_CAP_MIN:
    try:
        job = db_claim()
    except Exception as e:
        log("claim error:", repr(e)[:200]); time.sleep(60); continue
    if not job:
        idle += 1
        log(f"queue empty ({idle}/{IDLE_EXIT_POLLS})")
        if idle >= IDLE_EXIT_POLLS:
            log("idle exit — freeing the GPU slot")
            break
        time.sleep(IDLE_POLL_SEC)
        continue
    idle = 0
    jid = job["id"]
    STATE["claimed"].append(jid)
    log("claimed", jid, f"{job['seconds']}s {job['resolution']} audio={job['withAudio']}")
    t_job = time.time()
    proj = None
    scene_sid = None
    try:
        notes = job.get("notes") or ""
        m = re.match(r"studio:([A-Za-z0-9]+):([A-Za-z0-9]+)", notes)
        keyframe_png = None
        if m:
            scene_sid = m.group(2)
            proj = db_project(m.group(1))
            if proj:
                db_progress(jid, "storyboard: creating the cast + scene keyframes")
                sb = ensure_storyboard(proj, job)
                kf = next((k for k in sb.get("keyframes", []) if k.get("scene") == scene_sid), None)
                if kf and kf.get("url", "").startswith("/api/files/"):
                    keyframe_png = fetch_keyframe_png(kf)
                log("storyboard ready:", len(sb.get("sheets", [])), "sheets,", len(sb.get("keyframes", [])), "keyframes")
        mp4 = render_video(job, keyframe_png)
        ls_note = ""
        line, actor = (scene_line(proj, scene_sid) if proj else (None, None))
        if line and job["withAudio"]:
            niche = (proj or {}).get("niche") or ""
            voice = voice_for(niche, actor, 0)
            mp4, ls_note = lipsync_pass(mp4, line, voice, jid)
            log("lip-sync:", ls_note[:120])
        elif line:
            ls_note = "lip-sync skipped (render has no audio track)"
        data = mp4.read_bytes()
        gpu = (time.time() - t_job) / 60
        db_progress(jid, "delivering the finished scene")
        key = f"renders/{jid}.mp4"
        storage_put(key, data, "video/mp4")
        asset = db_asset("video", "video/mp4", data, key, False, f"worker:{AGENT}")
        note = f"rendered by {AGENT} — H3 keyframe-anchored scene via direct-DB fleet"
        if ls_note:
            note += f"; {ls_note}"
        if db_done(jid, gpu, f"/api/files/{asset}", asset, note):
            STATE["done"].append(jid)
            log(f"DONE {jid} {len(data)/1e6:.1f}MB in {gpu:.0f}min -> asset {asset}")
        else:
            log(f"skipped done-write for {jid} (no longer rendering — cancelled?)")
    except Exception as e:
        log("render failed for", jid, ":", repr(e)[:300])
        try:
            db_fail(jid, f"render error: {str(e)[:400]}")
            STATE["failed"].append(jid)
        except Exception as fe:
            log("fail-report failed:", repr(fe)[:150])
    finally:
        free_mem()

pathlib.Path("/kaggle/working/result.json").write_text(json.dumps(STATE, indent=1))
log("SITE_WORKER_DONE", json.dumps(STATE))
