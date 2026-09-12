#!/usr/bin/env python3
"""Task 72 — raw SaveKernel push to capture the FULL 409 response body.
Uses the launcher's exact payload shape (nonce included). Prints the API's
message field — never prints tokens.
"""
import base64
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
ACCT = sys.argv[1] if len(sys.argv) > 1 else "youngwilly"

toks = json.load(open(ROOT / "workers/secrets/kaggle_tokens.json"))["tokens"]
tok = next(t["token"] for t in toks if t.get("account") == ACCT)
wt = json.load(open(ROOT / "workers/secrets/worker_token.json"))["token"]
WORKER_SRC = ROOT / "workers/deyoung_worker.py"
if not WORKER_SRC.exists():
    # fall back to wherever the launcher finds it
    import kaggle_launch  # noqa
    WORKER_SRC = kaggle_launch.WORKER_SRC
worker_b64 = base64.b64encode(WORKER_SRC.read_bytes()).decode()
stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
script = (
    f"# deyoung worker build {stamp} (nonce)\n"
    "import base64, pathlib, sys\n"
    f'src = base64.b64decode("{worker_b64}").decode()\n'
    'pathlib.Path("deyoung_worker.py").write_text(src)\n'
    "sys.argv = [\n"
    '    "deyoung_worker.py",\n'
    '    "--site", "https://deyoungltd.site",\n'
    '    "--token", "%s",\n' % wt +
    '    "--renderer", "ltx",\n'
    '    "--max-minutes", "480",\n'
    '    "--exit-idle",\n'
    ']\n'
    'print("[kaggle] booting DeYoung render worker…", flush=True)\n'
    'exec(compile(src, "deyoung_worker.py", "exec"), {"__name__": "__main__"})\n'
)

body = {
    "id": f"{ACCT}/deyoung-worker",
    "title": "deyoung-worker",
    "codeFile": "worker_kernel.py",
    "language": "python",
    "kernelType": "script",
    "isPrivate": True,
    "enableGpu": True,
    "enableInternet": True,
    "datasetDataSources": [],
    "competitionDataSources": [],
    "kernelDataSources": [],
    "modelDataSources": [],
    "scriptVersionData": script,
}
req = urllib.request.Request(
    "https://www.kaggle.com/api/v1/kernels/push",
    data=json.dumps(body).encode(),
    headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        print("HTTP", r.status, "->", r.read().decode()[:400])
except urllib.error.HTTPError as e:
    print("HTTP", e.code, "->", e.read().decode(errors="replace")[:600])
