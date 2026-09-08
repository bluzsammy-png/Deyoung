#!/usr/bin/env python3
"""Probe the 4 HF tokens: (a) fine-grained write scope via probe-space create/delete,
(b) live ZeroGPU call via FLUX.1-schnell to prove GPU-quota works per account."""
import json, time, pathlib, traceback

TOKS = json.loads(pathlib.Path("/home/z/my-project/workers/secrets/hf_tokens.json").read_text())["tokens"]
RESULTS = {"write_probe": {}, "zerogpu_probe": {}}

# ---------- (a) write scope probe ----------
try:
    from huggingface_hub import HfApi
except ImportError:
    import subprocess, sys
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "huggingface_hub"], check=True)
    from huggingface_hub import HfApi

for t in TOKS:
    tid, tok, user = t["id"], t["token"], t.get("user")
    rec = {}
    try:
        api = HfApi(token=tok)
        rid = f"{user}/deyoung-fleet-probe"
        url = api.create_repo(repo_id=rid, repo_type="space", private=True, space_sdk="gradio", exist_ok=False)
        rec["write"] = True
        rec["created"] = str(url)
        time.sleep(2)
        api.delete_repo(repo_id=rid, repo_type="space")
        rec["cleaned_up"] = True
    except Exception as e:
        msg = str(e)
        rec["write"] = False
        rec["error"] = msg[:240]
    RESULTS["write_probe"][f"{tid}:{user}"] = rec
    print(f"[write] {tid}:{user} -> {rec}")

# ---------- (b) ZeroGPU live call probe ----------
try:
    from gradio_client import Client
except ImportError:
    import subprocess, sys
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "gradio_client"], check=True)
    from gradio_client import Client

SPACE = "black-forest-labs/FLUX.1-schnell"
for t in TOKS:
    tid, tok, user = t["id"], t["token"], t.get("user")
    rec = {}
    t0 = time.time()
    try:
        cli = Client(SPACE, hf_token=tok, verbose=False)
        out = cli.predict(
            prompt="a tiny red cube on a white table, product photo",
            seed=0, randomize_seed=False, width=256, height=256,
            num_inference_steps=1, api_name="/infer",
        )
        rec["ok"] = True
        rec["seconds"] = round(time.time() - t0, 1)
        rec["out"] = str(out)[:160]
    except Exception as e:
        msg = str(e)
        rec["ok"] = False
        rec["error"] = msg[:400]
        rec["seconds"] = round(time.time() - t0, 1)
    RESULTS["zerogpu_probe"][f"{tid}:{user}"] = rec
    print(f"[zerogpu] {tid}:{user} -> ok={rec['ok']} {rec.get('seconds')}s {rec.get('error','')[:200]}")

pathlib.Path("/home/z/my-project/brain/hf_probe_results.json").write_text(json.dumps(RESULTS, indent=2))
print("saved brain/hf_probe_results.json")
