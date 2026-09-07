#!/usr/bin/env python3
"""Task 46: restore workers/secrets vault after sandbox rebuild #2 (11:43Z).
Reads the 8 KGAT tokens from an UNTRACKED temp file (never tracked files),
identifies each via Kaggle HTTP API (masked output), downloads the offsite
vault dataset with the deyoungsltd token, and restores all vault files.
"""
import base64, json, os, sys, urllib.request, zipfile, io, time

VAULT = "/home/z/my-project/workers/secrets"
TMP_TOKENS = os.path.join(VAULT, "tmp_tokens.json")

def http_get(url, token):
    req = urllib.request.Request(url)
    b64 = base64.b64encode(f"{token}:{token}".encode()).decode()
    req.add_header("Authorization", f"Basic {b64}")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code in (400, 401):
            # KGAT tokens use Bearer auth
            req2 = urllib.request.Request(url)
            req2.add_header("Authorization", f"Bearer {token}")
            with urllib.request.urlopen(req2, timeout=30) as r:
                return r.read()
        raise

def main():
    os.makedirs(VAULT, exist_ok=True)
    with open(TMP_TOKENS) as f:
        tokens = json.load(f)["tokens"]

    owner = None
    for t in tokens:
        tid, tok = t["id"], t["token"]
        try:
            blob = http_get(
                "https://www.kaggle.com/api/v1/datasets/download/deyoungsltd/deyoung-worker-vault",
                tok)
            if blob[:2] == b"PK":
                owner = tok
                print(f"{tid}: UNLOCKED the private vault dataset (zip signature OK)")
                break
            print(f"{tid}: response not a zip ({blob[:60]!r})")
        except Exception as e:
            print(f"{tid}: no access ({str(e)[:70]})")
        time.sleep(0.4)
    if not owner:
        print("NO token could download the vault dataset — aborting")
        sys.exit(1)

    print("extracting offsite vault ...")
    zf = zipfile.ZipFile(io.BytesIO(blob))
    restored = []
    for name in zf.namelist():
        if name.endswith("/"):
            continue
        out = os.path.join(VAULT, os.path.basename(name))
        with open(out, "wb") as f:
            f.write(zf.read(name))
        os.chmod(out, 0o600)
        restored.append(os.path.basename(name))
    print("RESTORED:", ", ".join(sorted(restored)))

    # record which chat token unlocked the vault (masked note only)
    vault_kaggle = os.path.join(VAULT, "kaggle_tokens.json")
    with open(vault_kaggle) as f:
        vault = json.load(f)
    vault["restore_46"] = {
        "restored": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "method": "offsite dataset download attempted with each supplied chat token; first zip-success wins",
    }
    with open(vault_kaggle, "w") as f:
        json.dump(vault, f, indent=1)
    os.chmod(vault_kaggle, 0o600)

    os.remove(TMP_TOKENS)
    print("VAULT RESTORE COMPLETE (tmp token file removed)")

if __name__ == "__main__":
    main()
