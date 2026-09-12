#!/usr/bin/env python3
"""Task 72 — per-account Kaggle GPU quota probe (read-only, no burn).

Tries the internal quota endpoints community tools use; falls back to honest
'not queryable' per account. Never prints token values. Results also appended
to brain/kaggle_quota_72.json.
"""
import json
import pathlib
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
SECRETS = ROOT / "workers" / "secrets" / "kaggle_tokens.json"
EVIDENCE = ROOT / "brain" / "kaggle_quota_72.json"

ENDPOINTS = [
    "https://www.kaggle.com/api/i/gpu.QuotaService/GetRemainingSessionQuota",
    "https://www.kaggle.com/api/i/gpu.QuotaService/ListSessionQuota",
]

results = {}
toks = json.load(open(SECRETS))["tokens"]
seen_users = {}
for t in toks:
    tok, tid = t["token"], t.get("id", "?")
    user = t.get("account") or t.get("user") or tid
    out = None
    for url in ENDPOINTS:
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                body = json.loads(r.read().decode())
                out = {"endpoint": url.rsplit('/', 1)[-1], "status": r.status, "body_keys": list(body)[:6]}
                # try common shapes
                for k in ("remainingOverallQuota", "remainingGpuQuota", "quota"):
                    if k in body:
                        out["remaining_raw"] = body[k]
                results.setdefault(user, out)
                break
        except urllib.error.HTTPError as e:
            out = {"endpoint": url.rsplit('/', 1)[-1], "status": e.code}
        except Exception as e:
            out = {"endpoint": url.rsplit('/', 1)[-1], "err": type(e).__name__}
    results.setdefault(user, out or {"status": "unreachable"})

for user, r in results.items():
    print(f"{user}: {r}")
(EVIDENCE).write_text(json.dumps({"generated_utc": __import__('time').strftime('%FT%TZ', __import__('time').gmtime()), "accounts": results}, indent=2))
print("evidence ->", EVIDENCE)
