#!/usr/bin/env python3
"""Verify owner-supplied HuggingFace tokens (whoami-v2).

Tokens are NOT hardcoded here (GitHub push protection blocks that).
They live in workers/secrets/hf_tokens.json (0600, also inside vault.enc).
If that file doesn't exist yet, seed it by pasting tokens into a temp file
and running: python3 scripts/hf_tokens_seed.py < tokens.txt
"""
import json, os, pathlib, urllib.request, urllib.error

SECRETS = pathlib.Path("/home/z/my-project/workers/secrets/hf_tokens.json")
if not SECRETS.exists():
    raise SystemExit("workers/secrets/hf_tokens.json missing — restore vault first (scripts/selfheal.sh).")

data = json.loads(SECRETS.read_text())
TOKENS = [(t["id"], t["token"]) for t in data["tokens"]]

def whoami(tok: str):
    req = urllib.request.Request(
        "https://huggingface.co/api/whoami-v2",
        headers={"Authorization": f"Bearer {tok}", "User-Agent": "deyoung-fleet/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "body": e.read().decode()[:300]}
    except Exception as e:
        return {"error": str(e)}

results = {}
for label, tok in TOKENS:
    info = whoami(tok)
    if "error" in info:
        results[label] = {"valid": False, "error": info["error"], "body": info.get("body", "")}
    else:
        acc = (info.get("auth") or {}).get("accessToken") or {}
        results[label] = {
            "valid": True,
            "user": info.get("name"),
            "fullname": info.get("fullname"),
            "isPro": bool(info.get("isPro")),
            "emailVerified": info.get("emailVerified"),
            "tokenRole": acc.get("role"),
            "tokenName": acc.get("displayName"),
            "type": info.get("type"),
            "orgs": [o.get("name") for o in (info.get("orgs") or [])][:5],
        }
    print(json.dumps({label: {k: v for k, v in results[label].items() if k != "token"}}, indent=2))

ok = sum(1 for v in results.values() if v.get("valid"))
pro = sum(1 for v in results.values() if v.get("isPro"))
wr = sum(1 for v in results.values() if v.get("tokenRole") == "write")
print(f"SUMMARY: {ok}/{len(TOKENS)} valid | {pro} PRO | {wr} write-role")
