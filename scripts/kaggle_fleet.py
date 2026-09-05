#!/usr/bin/env python3
"""
Launch a FLEET of DeYoung GPU workers on Kaggle — one kernel per account.

The user's agency-agents architecture, implemented:
  * every provided Kaggle account (KGAT_ token) becomes one GPU worker kernel
  * each worker runs a DIFFERENT local LTX-Video checkpoint on its own GPU
  * all workers claim scenes from the same site queue (atomic claim — no
    double renders), render in parallel, and deliver scene clips back
  * the site-side merge stage then joins, audits and verifies the film

Usage:
  KAGGLE_TOKENS='KGAT_a,KGAT_b[,KGAT_c]' python3 scripts/kaggle_fleet.py \
      --token dyw_... [--max-minutes 480] [--watch]

State (kernel refs, live URLs) is written to scripts/kaggle_fleet_state.json.
"""

import argparse
import base64
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.request


def introspect_username(kgat):
    """Resolve the Kaggle username behind a KGAT_ token (official token introspection)."""
    req = urllib.request.Request(
        "https://api.kaggle.com/v1/security.OAuthService/IntrospectToken",
        data=json.dumps({"token": kgat}).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {kgat}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    if not data.get("active") or not data.get("username"):
        raise RuntimeError(f"token inactive or username missing: {data}")
    return data["username"]

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORKER_SRC = ROOT / "workers" / "deyoung_worker.py"
DB_WORKER_SRC = ROOT / "workers" / "deyoung_db_worker.py"
DB_SECRET_FILE = pathlib.Path(__file__).resolve().parent / ".worker_db_secret"
STATE_FILE = pathlib.Path(__file__).resolve().parent / "kaggle_fleet_state.json"
KERNEL_DIR = pathlib.Path("/tmp/deyoung-kaggle-fleet")

FLEET = [
    {"suffix": "a", "title": "deyoung worker a", "prefer": "a", "model": "LTX-Video-0.9.5"},
    {"suffix": "b", "title": "deyoung worker b", "prefer": "b", "model": "LTX-Video-0.9.1"},
    {"suffix": "c", "title": "deyoung worker c", "prefer": "c", "model": "LTX-Video-0.9.0"},
]


def ensure_kaggle_cli():
    try:
        import kaggle  # noqa: F401
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--break-system-packages", "kaggle"], check=True)


def read_worker_db_dsn():
    """Least-privilege Postgres DSN for the fleet (worker_bot role)."""
    if not DB_SECRET_FILE.exists():
        sys.exit("missing scripts/.worker_db_secret — run scripts/worker_db_apply.py first")
    for line in DB_SECRET_FILE.read_text().splitlines():
        if line.startswith("WORKER_DB_DSN="):
            return line.split("=", 1)[1].strip().strip("'")
    sys.exit("scripts/.worker_db_secret has no WORKER_DB_DSN line")


def push_worker(tokens, args):
    ensure_kaggle_cli()
    worker_b64 = base64.b64encode(WORKER_SRC.read_bytes()).decode()
    db_worker_b64 = base64.b64encode(DB_WORKER_SRC.read_bytes()).decode()
    db_dsn = read_worker_db_dsn()
    results = []
    for i, kgat in enumerate(tokens):
        fleet = FLEET[i % len(FLEET)]
        username = introspect_username(kgat)
        slug = f"deyoung-worker-{fleet['suffix']}"
        agent = f"kaggle-gpu-{fleet['suffix']}"
        print(f"[fleet] account {i + 1}: {username} -> kernel {slug} ({fleet['model']})")
        boot = f'''
import base64, os, pathlib, subprocess, sys
print("[kaggle] installing local TTS + Postgres driver…", flush=True)
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "piper-tts", "psycopg2-binary"], check=False)
pathlib.Path("deyoung_worker.py").write_text(base64.b64decode("{worker_b64}").decode())
pathlib.Path("deyoung_db_worker.py").write_text(base64.b64decode("{db_worker_b64}").decode())
os.environ["WORKER_DB_DSN"] = "{db_dsn}"
os.environ["DEYOUNG_PREFER"] = "{fleet['prefer']}"
os.environ["DEYOUNG_JOB_BUDGET"] = "3.0"
sys.argv = [
    "deyoung_db_worker.py",
    "--renderer", "film",
    "--prefer", "{fleet['prefer']}",
    "--job-budget", "3.0",
    "--max-minutes", "{args.max_minutes}",
    "--exit-idle",
    "--agent", "{agent}",
]
print("[kaggle] booting DeYoung film worker ({fleet['model']}) — direct-DB fleet mode…", flush=True)
import runpy
runpy.run_path("deyoung_db_worker.py", run_name="__main__")
'''
        d = KERNEL_DIR / fleet["suffix"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "worker_kernel.py").write_text(boot)
        (d / "kernel-metadata.json").write_text(json.dumps({
            "id": f"{username}/{slug}",
            "title": fleet["title"],
            "code_file": "worker_kernel.py",
            "language": "python",
            "kernel_type": "script",
            "is_private": "true",
            "enable_gpu": "true",
            "machine_shape": "NvidiaTeslaT4",
            "enable_internet": "true",
            "dataset_sources": [],
            "competition_sources": [],
            "kernel_sources": [],
            "model_sources": [],
        }, indent=2))

        print(f"[fleet] pushing kernel {slug} (worker {agent}, prefers {fleet['model']})…")
        env = {**os.environ, "KAGGLE_API_TOKEN": kgat}
        proc = subprocess.run(
            [sys.executable, "-m", "kaggle", "kernels", "push", "-p", str(d)],
            capture_output=True, text=True, env=env,
        )
        out = (proc.stdout + proc.stderr).strip()
        print("  " + out.replace("\n", "\n  ")[:1200])
        m = re.search(r"kaggle\.com/code/([\w.-]+/[\w.-]+)", out)
        ref = m.group(1) if m else slug
        results.append({
            "index": i + 1,
            "username": username,
            "slug": slug,
            "ref": ref,
            "agent": agent,
            "checkpoint": fleet["model"],
            "url": f"https://www.kaggle.com/code/{ref}",
            "push_ok": proc.returncode == 0,
        })

    STATE_FILE.write_text(json.dumps(results, indent=2))
    print(f"[fleet] state saved to {STATE_FILE}")
    for r in results:
        live = "LIVE " if r["push_ok"] else "PUSH FAILED"
        print(f"[fleet] {live}: {r['ref']} — {r['url']}")
    return results


def watch(results, args):
    print("[fleet] watching kernel status (ctrl-c stops watching; kernels keep running)…")
    while True:
        for i, r in enumerate(results):
            try:
                token = (args.tokens or os.environ.get("KAGGLE_TOKENS", "")).split(",")[i].strip()
                env = {**os.environ, "KAGGLE_API_TOKEN": token}
                proc = subprocess.run(
                    [sys.executable, "-m", "kaggle", "kernels", "status", r["ref"]],
                    capture_output=True, text=True, env=env,
                )
                print(f"  [{r['slug']}] {(proc.stdout + proc.stderr).strip()[:160]}")
            except Exception as exc:
                print(f"  [{r['slug']}] status error: {exc}")
        print("  (next poll in 120s)")
        time.sleep(120)


def main():
    ap = argparse.ArgumentParser(description="Launch the DeYoung Kaggle GPU fleet")
    ap.add_argument("--tokens", default="", help="comma-separated KGAT_ tokens (or set KAGGLE_TOKENS env)")
    ap.add_argument("--token", required=True, help="the site WORKER_TOKEN (not the Kaggle token)")
    ap.add_argument("--site", default=os.environ.get("DEYOUNG_SITE", "https://deeyoung-production-72ef.up.railway.app"))
    ap.add_argument("--max-minutes", type=int, default=480)
    ap.add_argument("--watch", action="store_true")
    args = ap.parse_args()

    raw = args.tokens or os.environ.get("KAGGLE_TOKENS", "")
    tokens = [t.strip() for t in raw.split(",") if t.strip()]
    if not tokens:
        sys.exit("no Kaggle tokens given — set KAGGLE_TOKENS='KGAT_…,KGAT_…' or pass --tokens")
    print(f"[fleet] {len(tokens)} account(s) -> {len(tokens)} GPU worker kernel(s)")

    results = push_worker(tokens, args)
    if args.watch:
        watch(results, args)


if __name__ == "__main__":
    main()
