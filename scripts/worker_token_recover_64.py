#!/usr/bin/env python3
"""Task 64 — extract DEYOUNG_WORKER_TOKEN from the studio's h3q.env WITHOUT
printing it, store 0600 as workers/secrets/worker_token.json, then probe the
prod worker-status endpoint (queue counts only). The token value is never
echoed to stdout/logs — only queue counts and pass/fail."""
import base64
import json
import os
import pathlib
import sys
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
os.environ.setdefault("LIGHTNING_API_KEY", "")
if not os.environ.get("LIGHTNING_API_KEY"):
    os.environ["LIGHTNING_API_KEY"] = json.loads(
        (ROOT / "workers/secrets/lightning_tokens.json").read_text()
    )["keys"][0]["key"]

from h3_doctor_61 import run_inside  # noqa: E402  (SDK helper, TERM-safe)

out = run_inside(
    "source /teamspace/studios/this_studio/h3work/h3q.env 2>/dev/null; "
    'printf %s "$DEYOUNG_WORKER_TOKEN" | base64 -w0', timeout=60
)
tok = ""
if out:
    line = [l for l in str(out).strip().splitlines() if l.strip()]
    if line:
        try:
            tok = base64.b64decode(line[-1].strip()).decode().strip()
        except Exception:
            tok = ""
if len(tok) < 16:
    print("FATAL: could not read worker token from studio (len<16) — worker may be running anyway")
    sys.exit(1)

f = ROOT / "workers/secrets/worker_token.json"
f.write_text(json.dumps({"token": tok, "source": "studio h3q.env", "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, indent=1))
f.chmod(0o600)
print(f"worker_token.json written (len={len(tok)}, value not shown)")


def queue():
    req = urllib.request.Request(
        "https://deyoungltd.site/api/worker/status",
        headers={"Authorization": f"Bearer {tok}"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode()).get("queue", {})


for i in range(3):
    try:
        print("prod queue:", queue())
        break
    except Exception as e:  # noqa: BLE001
        print(f"probe attempt {i+1} failed: {type(e).__name__}: {str(e)[:100]}")
        time.sleep(5)
