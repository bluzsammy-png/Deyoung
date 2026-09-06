#!/usr/bin/env python3
"""Back up the DeYoung worker-secrets vault to a PRIVATE Kaggle dataset.

Idempotent: creates deyoungsltd/deyoung-worker-vault (private) or pushes a new
version if it already exists. Never prints token values or file contents.

Usage:
    python3 scripts/vault_backup.py            # create or update backup
    python3 scripts/vault_backup.py --verify   # verify privacy + readability only
"""
import json
import os
import sys
import time
import urllib.request

VAULT = os.path.join(os.path.dirname(__file__), "..", "workers", "secrets", "kaggle_tokens.json")
OWNER = "deyoungsltd"
SLUG = "deyoung-worker-vault"
API = "https://www.kaggle.com/api/v1"


def api(token, method, path, body=None, raw=None, ctype="application/json"):
    url = f"{API}{path}"
    data = None
    if raw is not None:
        data = raw
    elif body is not None:
        data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    if data is not None:
        req.add_header("Content-Type", ctype)
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = r.read()
    try:
        return json.loads(payload)
    except Exception:
        return {"_status": r.status, "_bytes": len(payload)}


def owner_token():
    with open(VAULT) as f:
        d = json.load(f)
    for t in d["tokens"]:
        if t.get("account") == OWNER:
            return t["token"]
    raise SystemExit("no owner token found in vault")


def verify(tok):
    # 1) owner can list it
    mine = api(tok, "GET", f"/datasets/list?user={OWNER}&search={SLUG}")
    hit = [d for d in mine if d.get("ref", "").endswith(SLUG) or d.get("slug") == SLUG]
    print(f"owner-list: found={bool(hit)}")
    if hit:
        print(f"owner-list: isPrivate={hit[0].get('isPrivate')} title={hit[0].get('title')!r}")
    # 2) a foreign token must NOT read its files
    with open(VAULT) as f:
        d = json.load(f)
    foreign = next((t["token"] for t in d["tokens"] if t.get("account") and t["account"] != OWNER), None)
    if foreign:
        try:
            api(foreign, "GET", f"/datasets/view?ownerSlug={OWNER}&datasetSlug={SLUG}")
            print("foreign-read: LEAK?? foreign token could view dataset")
        except urllib.error.HTTPError as e:
            print(f"foreign-read: blocked (HTTP {e.code}) — dataset is private OK")
        except Exception as e:
            print(f"foreign-read: blocked ({type(e).__name__}) OK")


def backup(tok):
    with open(VAULT, "rb") as f:
        blob = f.read()
    fname = "kaggle_tokens.json"
    size = len(blob)
    mtime = int(os.path.getmtime(VAULT))

    up = api(tok, "POST", f"/datasets/upload/file/{fname}?contentLength={size}&lastModifiedDateUtc={mtime}")
    token = up.get("token")
    create_url = up.get("createUrl") or up.get("uploadUrl")
    if not (token and create_url):
        print(f"upload-init failed keys={sorted(up)}")
        sys.exit(1)
    print("upload-init: OK")

    req = urllib.request.Request(create_url, data=blob, method="PUT")
    req.add_header("Content-Type", "application/octet-stream")
    with urllib.request.urlopen(req, timeout=120) as r:
        print(f"upload-put: HTTP {r.status}")

    meta = {
        "ownerSlug": OWNER,
        "slug": SLUG,
        "title": "DeYoung Worker Vault",
        "subtitle": "Private backup of worker fleet credentials (never public)",
        "isPrivate": True,
        "licenses": [{"name": "CC0-1.0"}],
        "files": [{"token": token}],
    }
    # try create; if it exists, push a version
    try:
        api(tok, "POST", "/datasets/create/new", body=meta)
        print("dataset-create: NEW (private)")
    except urllib.error.HTTPError as e:
        if e.code in (409, 400):
            body = dict(meta)
            body["versionNotes"] = f"vault refresh {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}"
            try:
                api(tok, "POST", f"/datasets/create/version/{SLUG}", body=body)
                print("dataset-version: UPDATED")
            except urllib.error.HTTPError as e2:
                print(f"version push failed: HTTP {e2.code} {e2.read()[:200]}")
                sys.exit(1)
        else:
            print(f"create failed: HTTP {e.code} {e.read()[:200]}")
            sys.exit(1)
    time.sleep(4)
    verify(tok)


if __name__ == "__main__":
    t = owner_token()
    if "--verify" in sys.argv:
        verify(t)
    else:
        backup(t)
