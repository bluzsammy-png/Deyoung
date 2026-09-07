#!/usr/bin/env python3
"""Canary completion watcher: polls deyoung-v2-s01 status every 60s (max 95 min).
When the run ends, waits for 4 brain passes (gate verify + wave-2 push), then
dumps the full verdict to brain/canary_watch.log."""
import json
import os
import subprocess
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
KAGGLE = os.path.expanduser("~/.venv/bin/kaggle")
TOK = os.path.expanduser("~/.kaggle/access_token")
CANARY = "deyoungsltd/deyoung-v2-s01"
LOG = os.path.join(ROOT, "brain", "canary_watch.log")
CANARY_DIR = os.path.join(ROOT, "campaign", "v10", "deyoungsltd__deyoung-v2-s01")


def out(msg):
    line = f"[{time.strftime('%H:%M:%SZ', time.gmtime())}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def status():
    try:
        r = subprocess.run([KAGGLE, "kernels", "status", CANARY],
                           capture_output=True, text=True, timeout=60)
        return (r.stdout or r.stderr).strip()
    except Exception as e:
        return f"probe-error: {e}"


def main():
    out(f"watcher armed — polling {CANARY} every 60s (max 95 min)")
    t0 = time.time()
    ended = None
    last = None
    while time.time() - t0 < 95 * 60:
        s = status()
        if s != last:
            out(f"status: {s}")
            last = s
        if "RUNNING" not in s and "probe-error" not in s and "queued" not in s.lower():
            ended = s
            break
        time.sleep(60)

    if not ended:
        out("TIMEOUT: canary still RUNNING after 95 min — no verdict captured")
        return

    out(f"CANARY ENDED: {ended} — giving brain 4 passes (~4 min) to verify + react")
    for i in range(4):
        time.sleep(60)
        out(f"  brain pass {i+1}/4 done")

    out("== brain/events.log tail ==")
    try:
        with open(os.path.join(ROOT, "brain", "events.log")) as f:
            for ln in f.read().splitlines()[-12:]:
                out(f"  ev | {ln}")
    except Exception as e:
        out(f"  events read error: {e}")

    out("== canary output dir ==")
    if os.path.isdir(CANARY_DIR):
        for dirpath, _, files in os.walk(CANARY_DIR):
            for fn in files:
                p = os.path.join(dirpath, fn)
                out(f"  file | {os.path.relpath(p, CANARY_DIR)} ({os.path.getsize(p)} bytes)")
        rj = os.path.join(CANARY_DIR, "result.json")
        if os.path.exists(rj):
            out(f"  result.json: {open(rj).read()[:500]}")
    else:
        out("  (output not fetched yet)")

    out("watcher done")


if __name__ == "__main__":
    main()
