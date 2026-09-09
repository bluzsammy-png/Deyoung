#!/usr/bin/env python3
"""Task 52: free-GPU fleet research battery — real searches, saved digests."""
import json, subprocess, sys, pathlib, time

OUT = pathlib.Path("/home/z/my-project/research")
OUT.mkdir(exist_ok=True)

QUERIES = [
    # A. deferred candidates from the repo survey
    ("modal_free",       "Modal labs free tier $30 monthly credits GPU serverless 2026 starter plan no credit card"),
    ("lightning_free",   "Lightning AI free tier 2026 monthly free GPU credits Studios T4 pricing"),
    ("studiolab_status", "AWS SageMaker Studio Lab discontinued shut down 2025 2026 status"),
    ("colab_free",       "Google Colab free tier GPU limits 2026 T4 usage cap compute units"),
    ("azure_students",   "Azure for Students 2026 $100 credit no credit card required GPU NC series"),
    # B. wide pool + rules
    ("kaggle_tos",       "Kaggle terms of service one account per person multiple accounts allowed rule"),
    ("hf_grants",        "Hugging Face community GPU grant program apply free A100 ZeroGPU pro quota 2026"),
    ("free_gpu_2026",    "free cloud GPU providers 2026 comparison serverless free tier Modal Lightning Novita Baseten Beam"),
    ("paperspace_free",  "Paperspace DigitalOcean free GPU notebook tier 2026 gradient free tier status"),
    ("intel_tiber",      "Intel Tiber AI Cloud free tier 2026 GPU credits developers"),
    # C. paid upgrade path (first-revenue math)
    ("runpod_price",     "RunPod serverless pricing 2026 per second A100 RTX 4090 T4 cost per hour"),
    ("vast_price",       "vast.ai pricing 2026 RTX 4090 per hour cheapest GPU rental interruptible"),
    ("modal_paid",       "Modal pricing 2026 GPU per second H100 A10 T4 cost"),
]

for name, q in QUERIES:
    of = OUT / f"{name}.json"
    if of.exists():
        print(f"skip {name} (exists)"); continue
    t0 = time.time()
    r = subprocess.run(["z-ai", "function", "-n", "web_search", "-a",
                        json.dumps({"query": q, "num": 8}), "-o", str(of)],
                       capture_output=True, text=True, timeout=90)
    ok = of.exists()
    print(f"{name}: {'OK' if ok else 'FAIL'} ({time.time()-t0:.1f}s)")
print("done")
