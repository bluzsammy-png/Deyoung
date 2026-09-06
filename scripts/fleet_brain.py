#!/usr/bin/env python3
"""DeYoung fleet brain — one idempotent monitoring pass over the Kaggle render fleet.

What a pass does:
  1. Load the token vault (workers/secrets/kaggle_tokens.json) — never prints token values.
  2. For every account with a known name: list kernels, auto-discover deyoung-* kernels.
  3. For each fleet kernel: read run status.
  4. If a kernel is COMPLETE and has unfetched output files: download them into
     campaign/v10/<account>__<kernel>/ and mark fetched in state (idempotent).
  5. Update brain/state.json (loop owns the "fleet" section; preserves "ops") and append
     brain/events.log (gitignored churn).

Usage:
  python3 scripts/fleet_brain.py             # single pass
  python3 scripts/fleet_brain.py --loop 60   # repeat every 60s until killed
  python3 scripts/fleet_brain.py --no-fetch  # status-only pass (no downloads)
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
VAULT = os.path.join(ROOT, "workers", "secrets", "kaggle_tokens.json")
STATE = os.path.join(ROOT, "brain", "state.json")
EVENTS = os.path.join(ROOT, "brain", "events.log")
FETCH_DIR = os.path.join(ROOT, "campaign", "v10")
API = "https://www.kaggle.com/api/v1"
FLEET_PREFIXES = ("deyoung-",)


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg):
    os.makedirs(os.path.dirname(EVENTS), exist_ok=True)
    with open(EVENTS, "a") as f:
        f.write(f"{now()} | {msg}\n")


def api(token, path, timeout=30):
    req = urllib.request.Request(f"{API}{path}")
    req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def load_vault():
    with open(VAULT) as f:
        return json.load(f)


def load_state():
    if os.path.exists(STATE):
        with open(STATE) as f:
            return json.load(f)
    return {"ops": {}}


def save_state(st):
    tmp = STATE + ".tmp"
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(tmp, "w") as f:
        json.dump(st, f, indent=2, sort_keys=True)
    os.replace(tmp, STATE)


def download_file(url, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=300) as r, open(dest, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
    return os.path.getsize(dest)


def output_url(tok, account, slug, fname):
    # fallback only; the files listing normally carries a direct presigned url
    return f"{API}/kernels/output/download?userName={account}&kernelSlug={slug}&fileName={urllib.request.quote(fname)}"


def pass_once(no_fetch=False):
    vault = load_vault()
    st = load_state()
    fleet = st.setdefault("fleet", {"kernels": {}, "accounts": {}, "history": {}})
    changed = []

    for t in vault["tokens"]:
        tok, acct = t["token"], t.get("account")
        if not acct:
            continue
        try:
            kernels = api(tok, f"/kernels/list?user={acct}&pageSize=50")
        except Exception as e:
            log(f"ERROR list {acct}: {type(e).__name__}: {e}")
            continue
        refs = []
        for k in kernels:
            ref = k.get("ref") or ""
            if not ref or "/" not in ref:
                continue
            slug = ref.split("/", 1)[1]
            if slug.startswith(FLEET_PREFIXES):
                refs.append(ref)
        fleet["accounts"][acct] = {"known_fleet_kernels": sorted(refs), "checked": now()}
        for ref in refs:
            account, slug = ref.split("/", 1)
            try:
                status = api(tok, f"/kernels/status?userName={account}&kernelSlug={slug}")
            except Exception as e:
                log(f"ERROR status {ref}: {type(e).__name__}: {e}")
                continue
            s = status.get("status", "unknown")
            prev = fleet["kernels"].get(ref, {})
            entry = {
                "status": s,
                "lastRunTime": prev.get("lastRunTime"),
                "fetched": prev.get("fetched", False),
                "files": prev.get("files", []),
                "checked": now(),
            }
            if s != prev.get("status"):
                log(f"{ref}: {prev.get('status', 'new')} -> {s}")
                changed.append(f"{ref}={s}")
            fleet["kernels"][ref] = entry

            if s == "complete" and not entry["fetched"] and not no_fetch:
                try:
                    out = api(tok, f"/kernels/output?userName={account}&kernelSlug={slug}")
                    files = out.get("files", [])
                    got = []
                    entry["files"] = [
                        {
                            "name": f.get("fileName") or f.get("name"),
                            "bytes": f.get("totalBytes"),
                        }
                        for f in files
                    ]
                    if files:
                        dest_dir = os.path.join(FETCH_DIR, f"{account}__{slug}")
                        got = []
                        for f in files:
                            fname = f.get("fileName") or f.get("name")
                            if not fname or fname.endswith(".pyc") or "/__pycache__/" in fname:
                                continue
                            dest = os.path.join(dest_dir, fname)
                            url = f.get("url") or output_url(tok, account, slug, fname)
                            try:
                                size = download_file(url, dest)
                                got.append(f"{fname} ({size}B)")
                            except Exception as e:
                                log(f"ERROR download {ref}/{fname}: {type(e).__name__}: {e}")
                        if got:
                            log(f"{ref}: fetched -> {', '.join(got)}")
                            changed.append(f"{ref}:fetched")
                        else:
                            changed.append(f"{ref}:download-failed")
                    else:
                        log(f"{ref}: complete, output listing empty")
                        changed.append(f"{ref}:empty-output")
                    entry["fetched"] = bool(got) or not files
                except Exception as e:
                    log(f"ERROR output {ref}: {type(e).__name__}: {e}")

    st["fleet"] = fleet
    st["fleet"]["last_pass"] = now()
    if changed:
        st.setdefault("ops", {})["pending_review"] = sorted(set(changed))
    save_state(st)
    if not changed:
        # keep ops clean of stale review items only if nothing new happened
        pass
    return changed


def main():
    no_fetch = "--no-fetch" in sys.argv
    if "--loop" in sys.argv:
        secs = int(sys.argv[sys.argv.index("--loop") + 1]) if len(sys.argv) > sys.argv.index("--loop") + 1 else 60
        log(f"loop mode: every {secs}s")
        while True:
            try:
                ch = pass_once(no_fetch)
                if ch:
                    print(f"[{now()}] changes: {', '.join(ch)}")
                else:
                    print(f"[{now()}] no changes")
            except KeyboardInterrupt:
                break
            except Exception as e:
                log(f"ERROR pass: {type(e).__name__}: {e}")
            time.sleep(secs)
    else:
        ch = pass_once(no_fetch)
        print(f"pass done; changes: {ch if ch else 'none'}")


if __name__ == "__main__":
    main()
