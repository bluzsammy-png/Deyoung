#!/usr/bin/env python3
"""v2 relaunch watcher: waits for the canary kernel to complete, verifies its
output contains a real rendered scene, and ONLY THEN pushes the staged wave-2
kernels (switching per-account tokens from the vault). Any failure = wave 2
stays grounded and the reason is logged. Appends to brain/relaunch.log."""
import json
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path("/home/z/my-project")
LOG = ROOT / "brain" / "relaunch.log"
CANARY = "deyoungsltd/deyoung-v2-s01"
CANARY_OUT = ROOT / "campaign/v10/kernels/deyoung-v2-s01-out"
WAVE2 = [  # (account, slug, vault token id)
    ("jimcreat", "v2-jc-a", "w3"),
    ("bittrexminingltd", "v2-bx-a", "w4"),
    ("youngwilly", "v2-yw-a", "w7"),
    ("wikeyoung5", "v2-wk-a", "w8"),
    ("teslaprime", "v2-tp-a", "w2"),
    ("bittrexminingltd", "v2-bx-b", "w6"),
]
MAX_WAIT_MIN = 300
POLL_MIN = 10

os.environ["PATH"] = os.path.expanduser("~/.local/bin") + os.pathsep + os.environ.get("PATH", "")
TOK_PATH = os.path.expanduser("~/.kaggle/access_token")


def log(msg):
    line = f"[{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def kaggle(*args, timeout=180):
    return subprocess.run(["kaggle", *args], capture_output=True, text=True, timeout=timeout)


def set_token(tok):
    with open(TOK_PATH, "w") as f:
        f.write(tok + "\n")
    os.chmod(TOK_PATH, 0o600)


def main():
    vault = json.load(open(ROOT / "workers/secrets/kaggle_tokens.json"))
    tokens = {t.get("id") or t.get("account"): t["token"] for t in vault["tokens"]}
    owner = next(t["token"] for t in vault["tokens"] if t.get("account") == "deyoungsltd")

    # 1. wait for canary completion
    log(f"watcher start — polling {CANARY} every {POLL_MIN}min (max {MAX_WAIT_MIN})")
    waited = 0
    status = None
    while waited <= MAX_WAIT_MIN:
        try:
            r = kaggle("kernels", "status", CANARY)
            status = (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout + r.stderr).strip() else "unknown"
        except Exception as e:
            status = f"error {type(e).__name__}"
        log(f"canary status: {status} (waited {waited}min)")
        if "COMPLETE" in status.upper():
            break
        if any(x in status.upper() for x in ("ERROR", "CANCEL", "KernelWorkerStatus.KILLED")):
            log("GROUND STOP: canary ended without success — wave 2 NOT pushed")
            return
        time.sleep(POLL_MIN * 60)
        waited += POLL_MIN
    else:
        log("GROUND STOP: max wait exceeded — wave 2 NOT pushed")
        return

    # 2. verify canary output has a real scene file
    time.sleep(60)  # let Kaggle finalize output listing
    set_token(owner)
    CANARY_OUT.mkdir(parents=True, exist_ok=True)
    try:
        r = kaggle("kernels", "output", CANARY, "-p", str(CANARY_OUT), "--unzip", timeout=600)
        log("output pull: " + (r.stdout + r.stderr).strip()[:200])
    except Exception as e:
        log(f"GROUND STOP: output pull failed {type(e).__name__}: {e}")
        return
    mp4s = list(CANARY_OUT.rglob("*.mp4"))
    good = [m for m in mp4s if m.stat().st_size > 1_000_000]
    result_json = CANARY_OUT / "result.json"
    job_ok = None
    if result_json.exists():
        try:
            manifest = json.loads(result_json.read_text())
            job_ok = any(m.get("ok") for m in manifest)
        except Exception:
            pass
    log(f"verification: mp4s={[m.name for m in mp4s]} good={len(good)} result_ok={job_ok}")
    if not good or job_ok is False:
        log("GROUND STOP: no real scene file in canary output — wave 2 NOT pushed")
        return

    # 3. fire wave 2
    pushed = []
    for acct, slug, tid in WAVE2:
        d = ROOT / "campaign/v10/kernels" / slug
        if not (d / "kernel-metadata.json").exists():
            log(f"SKIP {slug}: kernel dir missing")
            continue
        set_token(tokens.get(tid) or tokens.get(acct))
        try:
            r = kaggle("kernels", "push", "-p", str(d), timeout=300)
            out = (r.stdout + r.stderr).strip()
            ok = "successfully pushed" in out.lower()
            log(f"push {acct}/{slug}: {'OK' if ok else 'FAIL'} — {out[:160]}")
            if ok:
                pushed.append(f"{acct}/{slug}")
        except Exception as e:
            log(f"push {acct}/{slug}: EXC {type(e).__name__}: {str(e)[:160]}")
        time.sleep(20)
    set_token(owner)
    log(f"WAVE2 DONE: pushed {len(pushed)}/6 -> {pushed}")


if __name__ == "__main__":
    main()
