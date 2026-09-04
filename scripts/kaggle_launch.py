#!/usr/bin/env python3
"""
Launch the DeYoung render worker as a Kaggle GPU kernel — the free compute layer.

What it does:
  1. Reads your Kaggle credentials (KAGGLE_API_TOKEN env — the new KGAT_ style —
     or ~/.kaggle/kaggle.json classic credentials).
  2. Bakes workers/deyoung_worker.py + your site URL + WORKER_TOKEN into a
     private GPU kernel (internet enabled).
  3. Pushes it with the official Kaggle CLI. Kaggle immediately runs a fresh
     GPU session that claims jobs from your site's queue for --max-minutes,
     renders them with LTX-Video, and delivers each result back automatically.

Usage:
  python3 scripts/kaggle_launch.py --token dyw_xxxxxxxxxxxxxxxx [--max-minutes 480] [--watch]

Weekly budget reality: Kaggle gives ~30 free GPU-hours per week. One worker
session at a time is the polite default; re-run this script whenever you want
another session (it updates the same kernel version).
"""

import argparse
import base64
import json
import os
import pathlib
import subprocess
import sys
import time

HOME = pathlib.Path.home()
WORKER_SRC = pathlib.Path(__file__).resolve().parent.parent / "workers" / "deyoung_worker.py"
KERNEL_DIR = pathlib.Path("/tmp/deyoung-kaggle-kernel")
SLUG = "deyoung-worker"


def kaggle_creds():
    """Return (username, auth_env) for the Kaggle CLI, or exit with guidance."""
    token = os.environ.get("KAGGLE_API_TOKEN", "").strip()
    if token:
        return None, {"KAGGLE_API_TOKEN": token}
    kj = HOME / ".kaggle" / "kaggle.json"
    if kj.exists():
        data = json.loads(kj.read_text())
        return data["username"], {"KAGGLE_USERNAME": data["username"], "KAGGLE_KEY": data["key"]}
    sys.exit(
        "No Kaggle credentials found.\n"
        "  • Set KAGGLE_API_TOKEN=<KGAT_…> (kaggle.com → Settings → API → Create New Token), or\n"
        "  • Place ~/.kaggle/kaggle.json ({\"username\": …, \"key\": …}).\n"
        "Never paste the token in chat — put it straight into this command's environment."
    )


def ensure_kaggle_cli():
    subprocess.run([sys.executable, "-m", "pip", "show", "-q", "kaggle"], check=False)
    probe = subprocess.run([sys.executable, "-m", "kaggle", "--version"], capture_output=True, text=True)
    if probe.returncode != 0:
        print("[kaggle-launch] installing the kaggle CLI…")
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "kaggle"], check=True)


def main():
    ap = argparse.ArgumentParser(description="Launch DeYoung render worker on Kaggle GPU")
    ap.add_argument("--token", required=True, help="the site WORKER_TOKEN (not your Kaggle token)")
    ap.add_argument("--site", default=os.environ.get("DEYOUNG_SITE", "https://deeyoung-production-72ef.up.railway.app"))
    ap.add_argument("--max-minutes", type=int, default=480, help="worker session budget (Kaggle GPU cap ~540)")
    ap.add_argument("--renderer", choices=["auto", "stub", "ltx"], default="auto")
    ap.add_argument("--slug", default=SLUG)
    ap.add_argument("--watch", action="store_true", help="poll kernel status until it finishes")
    args = ap.parse_args()

    username, auth_env = kaggle_creds()
    ensure_kaggle_cli()

    worker_b64 = base64.b64encode(WORKER_SRC.read_bytes()).decode()
    kernel_id = f"{username}/{args.slug}" if username else args.slug

    boot = f'''
import base64, pathlib, sys
src = base64.b64decode("{worker_b64}").decode()
pathlib.Path("deyoung_worker.py").write_text(src)
sys.argv = [
    "deyoung_worker.py",
    "--site", "{args.site}",
    "--token", "{args.token}",
    "--renderer", "{args.renderer}",
    "--max-minutes", "{args.max_minutes}",
    "--agent", "kaggle-gpu",
]
print("[kaggle] booting DeYoung render worker…", flush=True)
exec(compile(src, "deyoung_worker.py", "exec"), {{"__name__": "__main__"}})
'''

    KERNEL_DIR.mkdir(parents=True, exist_ok=True)
    (KERNEL_DIR / "worker_kernel.py").write_text(boot)
    (KERNEL_DIR / "kernel-metadata.json").write_text(
        json.dumps(
            {
                "id": kernel_id,
                "title": args.slug,
                "code_file": "worker_kernel.py",
                "language": "python",
                "kernel_type": "script",
                "is_private": "true",
                "enable_gpu": "true",
                "enable_internet": "true",
                "dataset_sources": [],
                "competition_sources": [],
                "kernel_sources": [],
                "model_sources": [],
            },
            indent=2,
        )
    )

    print(f"[kaggle-launch] pushing GPU kernel {kernel_id} (private, internet on)…")
    proc = subprocess.run(
        [sys.executable, "-m", "kaggle", "kernels", "push", "-p", str(KERNEL_DIR)],
        capture_output=True, text=True, env={**os.environ, **auth_env},
    )
    out = (proc.stdout + proc.stderr).strip()
    print(out)
    if proc.returncode != 0:
        sys.exit("[kaggle-launch] kernel push failed — see message above")

    print(f"[kaggle-launch] LIVE: https://www.kaggle.com/code/{kernel_id}")
    print("[kaggle-launch] The kernel now claims, renders and delivers jobs from your queue automatically.")
    print("[kaggle-launch] NOTE: the WORKER_TOKEN is baked into a PRIVATE kernel — rotate it if it ever leaks.")

    if args.watch:
        url = f"https://www.kaggle.com/api/v1/kernels/status/{kernel_id}"
        print("[kaggle-launch] watching kernel status (ctrl-c to stop watching; the kernel keeps running)…")
        while True:
            time.sleep(60)
            proc = subprocess.run(
                [sys.executable, "-m", "kaggle", "kernels", "status", kernel_id],
                capture_output=True, text=True, env={**os.environ, **auth_env},
            )
            print(" ", (proc.stdout + proc.stderr).strip())


if __name__ == "__main__":
    main()
