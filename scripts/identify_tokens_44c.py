#!/usr/bin/bin/env python3
"""Task 44-c: identify 8 owner-supplied KGAT tokens -> account map, then
attempt offsite vault recovery (dataset deyoungsltd/deyoung-worker-vault).
Never prints full token values (masked). Output: /tmp/token_map.json
"""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

HOME = os.path.expanduser("~")
KAGGLE_BIN = os.path.join(HOME, ".venv/bin/kaggle")
TOK_PATH = os.path.join(HOME, ".kaggle", "access_token")
REC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "workers", "secrets", "vault_recovery"))

# Tokens are supplied at runtime via a temp file (one KGAT token per line) and
# NEVER embedded here: scripts/ is git-tracked and the auto-checkpoint commits
# the working tree — literals in this file once landed in a local commit and
# tripped the prepush secret scan (purged before push; lesson recorded).
TOKENS: list[str] = []
if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
    TOKENS = [ln.strip() for ln in open(sys.argv[1]) if ln.strip().startswith("KGAT_")]
if not TOKENS:
    print("usage: identify_tokens_44c.py <tokens-file> (one KGAT_ token per line, untracked path)")
    sys.exit(2)


def mask(tok: str) -> str:
    return tok[:9] + "..." + tok[-4:]


def set_cli_token(tok: str):
    os.makedirs(os.path.dirname(TOK_PATH), exist_ok=True)
    with open(TOK_PATH, "w") as f:
        f.write(tok + "\n")
    os.chmod(TOK_PATH, 0o600)


def whoami_cli(tok: str) -> str | None:
    """Identify account via CLI: kernels list --mine returns refs 'user/slug'."""
    set_cli_token(tok)
    env = dict(os.environ)
    try:
        r = subprocess.run(
            [KAGGLE_BIN, "kernels", "list", "--mine", "--page-size", "1"],
            capture_output=True, text=True, timeout=60, env=env,
        )
        out = (r.stdout or "") + (r.stderr or "")
        if r.returncode == 0 and "/" in out:
            for line in out.splitlines():
                line = line.strip()
                if "/" in line and not line.startswith(("ref", "Warning")):
                    ref = line.split()[0]
                    return ref.split("/")[0]
        else:
            print(f"  cli fail rc={r.returncode}: {out[:120]!r}")
    except Exception as e:
        print(f"  cli error: {e}")
    return None


def whoami_http(tok: str) -> str | None:
    """Fallback: hello endpoint with Bearer."""
    req = urllib.request.Request(
        "https://www.kaggle.com/api/v1/hello",
        headers={"Authorization": f"Bearer {tok}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            msg = data.get("message", "")
            # message looks like "Hello <name>!" — not the username; try identity key
            for k in ("username", "user"):
                if k in data:
                    return data[k]
            return None
    except urllib.error.HTTPError as e:
        print(f"  http {e.code}")
        return None
    except Exception as e:
        print(f"  http error: {e}")
        return None


def recover_vault(owner_tok: str) -> bool:
    """Download the offsite vault dataset with the owner token."""
    os.makedirs(REC_DIR, exist_ok=True)
    set_cli_token(owner_tok)
    try:
        r = subprocess.run(
            [KAGGLE_BIN, "datasets", "download", "deyoungsltd/deyoung-worker-vault",
             "-p", REC_DIR, "--unzip"],
            capture_output=True, text=True, timeout=180,
        )
        out = (r.stdout or "") + (r.stderr or "")
        files = os.listdir(REC_DIR) if os.path.isdir(REC_DIR) else []
        print(f"  recovery rc={r.returncode}, files={files}")
        if r.returncode != 0:
            print(f"  recovery msg: {out[:200]!r}")
        return bool(files)
    except Exception as e:
        print(f"  recovery error: {e}")
        return False


def main():
    mapping = []
    for i, tok in enumerate(TOKENS, 1):
        print(f"[{i}/8] {mask(tok)}")
        user = whoami_cli(tok)
        if not user:
            user = whoami_http(tok)
        print(f"  -> account: {user}")
        mapping.append({"idx": i, "masked": mask(tok), "account": user, "token": tok})

    ok = [m for m in mapping if m["account"]]
    print(f"\nIDENTIFIED: {len(ok)}/8")
    json.dump(mapping, open("/tmp/token_map.json", "w"), indent=1)

    owners = [m for m in mapping if m["account"] == "deyoungsltd"]
    if owners:
        print("\nOFFSITE VAULT RECOVERY (deyoungsltd/deyoung-worker-vault):")
        got = recover_vault(owners[0]["token"])
        print(f"  recovered: {got}")
    else:
        print("\nNO deyoungsltd token — cannot attempt offsite recovery")
    return 0


if __name__ == "__main__":
    sys.exit(main())
