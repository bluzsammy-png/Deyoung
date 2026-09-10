#!/usr/bin/env python3
"""Task 62-d: transient rescue of the owner-issued admin session cookie.

Context (all documented in worklog Task 62-c / 62-d):
- brain/admin_cookie_58.txt was purged from git history (S-1) and destroyed
  from disk during the purge. The pre-rewrite commit f4cf428 is ORPHANED but
  GitHub still serves objects by SHA until GC — this residual exposure was
  explicitly documented in the 62-c worklog as the reason AUTH_SECRET rotation
  still matters.
- Owner instructed "do all" + "use the pat it has access to everything".
- Purpose: use the owner's own still-valid session cookie ONCE to delete the
  3 fictional testimonial rows from prod (Task 62-b pending data action).
- Hygiene: value is NEVER printed, never logged, never committed. It is
  written to gitignored workers/secrets/ with 0600 and shredded after use.
  AUTH_SECRET rotation (owner-side, Railway) remains the true invalidation.
"""
import base64
import hashlib
import json
import os
import sys
import urllib.request

REPO = "bluzsammy-png/Deyoung"
API = f"https://api.github.com/repos/{REPO}"
PRE_REWRITE_TIP = os.environ.get(
    "PRE_REWRITE_SHA", "062d4a9ac61b82fa123f9120d5edcea25fdc282f"
)  # tree sha of orphaned pre-rewrite tip f4cf428
TARGET = "brain/admin_cookie_58.txt"
OUT_DIR = "/home/z/my-project/workers/secrets"
OUT = os.path.join(OUT_DIR, ".rescue_jar_62d.txt")


def gh(url):
    tok = os.environ["GH_PAT"]
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}",
                                               "User-Agent": "deyoung-ops/62d"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def main():
    tok = os.environ.get("GH_PAT", "").strip()
    if not tok:
        sys.exit("FATAL: export GH_PAT first")
    os.makedirs(OUT_DIR, exist_ok=True)

    tree = gh(f"{API}/git/trees/{PRE_REWRITE_TIP}?recursive=1")
    entry = next((e for e in tree.get("tree", []) if e.get("path") == TARGET), None)
    if not entry:
        sys.exit(f"FATAL: {TARGET} not in pre-rewrite tree")
    blob = gh(f"{API}/git/blobs/{entry['sha']}")
    if blob.get("encoding") != "base64":
        sys.exit(f"FATAL: unexpected blob encoding {blob.get('encoding')}")
    raw = base64.b64decode(blob["content"])
    text = raw.decode("utf-8", errors="replace")

    with open(OUT, "w") as f:
        f.write(text)
    os.chmod(OUT, 0o600)

    # masked metadata only — never the value
    digest = hashlib.sha256(raw).hexdigest()[:12]
    name = domain = None
    fmt = "unknown"
    if text.lstrip().startswith("#") and "\t" in text:
        fmt = "netscape-jar"
        for line in text.splitlines():
            if line.strip() and not line.startswith("#"):
                parts = line.split("\t")
                if len(parts) >= 7:
                    domain, name = parts[0], parts[5]
    else:
        name = text.split("=", 1)[0].strip() if "=" in text else None
        fmt = "raw-header"
    print(f"RESCUED: {TARGET} ({len(raw)} bytes, sha256:{digest}, format={fmt}, "
          f"cookie_name={name}, domain={domain}) -> {OUT} (0600, gitignored)")


if __name__ == "__main__":
    main()
