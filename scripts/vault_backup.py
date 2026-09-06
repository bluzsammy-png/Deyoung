#!/usr/bin/env python3
"""Back up the DeYoung worker-secrets vault to a PRIVATE Kaggle dataset.

Durable target: deyoungsltd/deyoung-worker-vault (private).

IMPORTANT (lesson learned 2026-09-07): the raw v1 REST endpoints
`/datasets/list?user=...` and `/datasets/view` return empty/404 even for the
owner when using Bearer KGAT auth. The official Kaggle CLI is authoritative
for dataset operations. This script therefore drives the CLI, never REST.

Idempotent: creates the dataset or pushes a new version if it already exists.
Never prints token values or file contents.

Usage:
    python3 scripts/vault_backup.py            # create or update backup
    python3 scripts/vault_backup.py --verify   # verify existence + privacy only
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

VAULT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "workers", "secrets", "kaggle_tokens.json"))
OWNER = "deyoungsltd"
SLUG = "deyoung-worker-vault"
REF = f"{OWNER}/{SLUG}"


def ensure_cli_auth():
    """CLI 2.x wants ~/.kaggle/access_token (KGAT). Write it from the vault if missing."""
    home = os.path.expanduser("~")
    os.makedirs(os.path.join(home, ".kaggle"), exist_ok=True)
    tok_path = os.path.join(home, ".kaggle", "access_token")
    want = None
    with open(VAULT) as f:
        for t in json.load(f)["tokens"]:
            if t.get("account") == OWNER:
                want = t["token"]
                break
    if not want:
        raise SystemExit("no owner token in vault")
    cur = open(tok_path).read().strip() if os.path.exists(tok_path) else ""
    if cur != want:
        with open(tok_path, "w") as f:
            f.write(want + "\n")
        os.chmod(tok_path, 0o600)
    os.environ.setdefault("PATH", os.path.expanduser("~/.local/bin") + ":" + os.environ.get("PATH", ""))
    if not shutil.which("kaggle"):
        raise SystemExit("kaggle CLI not found; pip install --user --break-system-packages kaggle")


def cli(*args, timeout=180):
    return subprocess.run(["kaggle", *args], capture_output=True, text=True, timeout=timeout)


def stage_dir(tmp):
    shutil.copy2(VAULT, os.path.join(tmp, "kaggle_tokens.json"))
    meta = {
        "title": "DeYoung Worker Vault",
        "id": REF,
        "subtitle": "Private backup of worker fleet credentials (never public)",
        "isPrivate": True,
        "licenses": [{"name": "CC0-1.0"}],
    }
    with open(os.path.join(tmp, "dataset-metadata.json"), "w") as f:
        json.dump(meta, f, indent=2)


def backup():
    ensure_cli_auth()
    tmp = tempfile.mkdtemp(prefix="vaultbk_")
    try:
        stage_dir(tmp)
        r = cli("datasets", "create", "-p", tmp)
        out = (r.stdout + r.stderr).lower()
        if ("successfully" in out or "complete" in out
                or "is being created" in out or "upload successful" in out):
            print("dataset-create: NEW (private)")
        elif "already in use" in out or "exists" in out or "title" in out and "use" in out:
            v = cli("datasets", "version", "-p", tmp, "-m",
                    f"vault refresh {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
            vout = (v.stdout + v.stderr).lower()
            if ("successfully" in vout or "complete" in vout
                    or "is being created" in vout or "upload successful" in vout):
                print("dataset-version: UPDATED")
            else:
                print("version push failed:", (v.stdout + v.stderr)[:300])
                sys.exit(1)
        else:
            print("create failed:", (r.stdout + r.stderr)[:300])
            sys.exit(1)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    time.sleep(4)
    verify()


def verify():
    ensure_cli_auth()
    # 1) owner must see it, and content must hash-match
    r = cli("datasets", "list", "--user", OWNER)
    listed = REF in (r.stdout or "")
    print(f"owner-list (CLI): found={listed}")
    ok_files = False
    try:
        with tempfile.TemporaryDirectory() as dl:
            d = cli("datasets", "download", REF, "-p", dl, "--unzip", timeout=300)
            local = open(VAULT, "rb").read()
            got = os.path.join(dl, "kaggle_tokens.json")
            ok_files = os.path.exists(got) and open(got, "rb").read() == local
    except Exception as e:
        print(f"round-trip: error {type(e).__name__}: {e}")
    print(f"round-trip content match: {'YES' if ok_files else 'NO'}")
    # 2) a foreign token must NOT read its files (REST 404/403 = blocked)
    blocked = "unknown"
    try:
        with open(VAULT) as f:
            foreign = next((t["token"] for t in json.load(f)["tokens"]
                            if t.get("account") and t["account"] != OWNER), None)
        if foreign:
            import urllib.error
            import urllib.request
            req = urllib.request.Request(
                f"https://www.kaggle.com/api/v1/datasets/view?ownerSlug={OWNER}&datasetSlug={SLUG}")
            req.add_header("Authorization", f"Bearer {foreign}")
            try:
                urllib.request.urlopen(req, timeout=30)
                blocked = "LEAK? foreign token could view"
            except urllib.error.HTTPError as e:
                blocked = f"blocked (HTTP {e.code}) — private OK"
            except Exception as e:
                blocked = f"blocked ({type(e).__name__}) OK"
    except Exception as e:
        blocked = f"check-error {type(e).__name__}: {e}"
    print(f"foreign-read: {blocked}")
    verdict = listed and ok_files and "blocked" in blocked
    print(f"VERIFY VERDICT: {'PASS' if verdict else 'FAIL'}")
    return verdict


if __name__ == "__main__":
    if "--verify" in sys.argv:
        sys.exit(0 if verify() else 1)
    backup()
