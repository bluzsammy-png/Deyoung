#!/usr/bin/env python3
"""Task 56: live status of c20 campaign — Supabase storage objects + Lightning studio."""
import json
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path("/home/z/my-project")
SUPA = json.load(open(ROOT / "workers/secrets/supabase.json"))["supabase"]
LT = json.load(open(ROOT / "workers/secrets/lightning_tokens.json"))


def lt_key():
    keys = LT.get("keys")
    if isinstance(keys, list) and keys and isinstance(keys[0], dict):
        return keys[0].get("key")
    return None


def call(url, token, method="GET", payload=None, timeout=60, ctype="application/json"):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {token}", "Content-Type": ctype})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def main():
    # 1) Supabase storage: list campaign/v20/
    url, key = SUPA["supabase_url"], SUPA["service_role_key"]
    code, body = call(f"{url}/storage/v1/object/list/deyoung-media",
                      key, "POST", {"prefix": "campaign/v20", "limit": 100, "offset": 0})
    print(f"[storage] list campaign/v20 -> {code}")
    objs = json.loads(body) if code == 200 else []
    for o in objs:
        print(f"  {o.get('name'):28s} {o.get('metadata', {}).get('size', '?'):>12} bytes  updated={o.get('updated_at')}")
    if not objs:
        print("  (empty)")

    # 2) Lightning identity + balance + studio state
    tok = lt_key()
    if not tok:
        print("[lightning] NO KEY RESOLVED")
        sys.exit(1)
    code, body = call("https://lightning.ai/v1/memberships", tok)
    print(f"[lightning] /v1/memberships -> {code}")
    if code == 200:
        mem = json.loads(body)
        for m in mem.get("memberships", []):
            proj = m.get("project") or {}
            print(f"  project={proj.get('id')} name={proj.get('name')} balance={m.get('balance')}")
            pid = proj.get("id")
    else:
        print("  body:", body[:300])
        pid = None
    if pid:
        code, body = call(f"https://lightning.ai/v1/projects/{pid}/cloudspaces", tok)
        print(f"[lightning] cloudspaces -> {code}")
        if code == 200:
            cs = json.loads(body)
            for c in cs.get("cloudSpaces") or cs.get("cloudspaces") or []:
                print(f"  {c.get('name'):22s} state={c.get('state')} phase={c.get('latestCloudSpaceInstance', {}).get('phase') if isinstance(c.get('latestCloudSpaceInstance'), dict) else c.get('instancePhase')} machine={c.get('machine', {}).get('name') if isinstance(c.get('machine'), dict) else c.get('machine')}")


if __name__ == "__main__":
    main()
