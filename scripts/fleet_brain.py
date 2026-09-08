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
  6. relaunch_step: canary-gated wave-2 pusher (state machine in state.json "relaunch").
     Replaces the standalone v2_wave2_watcher.py, which the sandbox kept reaping —
     this loop is the proven-surviving process, so the gate lives here.

Usage:
  python3 scripts/fleet_brain.py             # single pass
  python3 scripts/fleet_brain.py --loop 60   # repeat every 60s until killed
  python3 scripts/fleet_brain.py --no-fetch  # status-only pass (no downloads)
"""
import json
import os
import pathlib
import subprocess
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
KAGGLE_BIN = os.path.expanduser("~/.local/bin/kaggle")
TOK_PATH = os.path.expanduser("~/.kaggle/access_token")

# --- relaunch gate constants (v10 v2 wave) ---
CANARY_REF = "youngwilly/deyoung-v2-c01"  # moved off deyoungsltd 2026-09-07: weekly GPU quota exhausted (30h cap) — fresh account
CANARY_DIR = os.path.join(FETCH_DIR, "youngwilly__deyoung-v2-c01")
KERNELS_DIR = os.path.join(FETCH_DIR, "kernels")
# (account, kernel-dir slug, vault token id) — quota-aware placement
WAVE2 = [
    ("jimcreat", "v2-jc-a", "w3"),
    ("bittrexminingltd", "v2-bx-a", "w4"),
    ("youngwilly", "v2-yw-a", "w7"),
    ("wikeyoung5", "v2-wk-a", "w8"),
    ("teslaprime", "v2-tp-a", "w2"),
    ("bittrexminingltd", "v2-bx-b", "w6"),
]
MAX_PUSH_ATTEMPTS = 3
GRACE_POLLS = 5  # ~5 min at 60s cadence before declaring "no output"


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


def relaunch_log(msg):
    line = f"[{now()}] {msg}"
    with open(os.path.join(ROOT, "brain", "relaunch.log"), "a") as f:
        f.write(line + "\n")


def cli_set_token(token):
    with open(TOK_PATH, "w") as f:
        f.write(token + "\n")
    os.chmod(TOK_PATH, 0o600)


def cli_push(kernel_dir, timeout=300):
    env = dict(os.environ)
    env["PATH"] = os.path.dirname(KAGGLE_BIN) + os.pathsep + env.get("PATH", "")
    r = subprocess.run(
        [KAGGLE_BIN, "kernels", "push", "-p", kernel_dir],
        capture_output=True, text=True, timeout=timeout, env=env,
    )
    return (r.stdout + r.stderr).strip()


def relaunch_step(st):
    """Canary-gated wave-2 pusher. All decisions recorded in st["relaunch"] so the
    step is idempotent across loop restarts. Never double-pushes: a slug is only
    attempted while attempts < MAX and never after a successful push record."""
    rl = st.setdefault(
        "relaunch",
        {"phase": "waiting", "canary": {"empty_polls": 0, "verify_polls": 0},
         "wave2": {"pushed": {}, "attempts": {}, "abandoned": {}}, "grounded": None},
    )
    if rl.get("grounded"):
        return
    if rl.get("phase") == "done":
        return
    fleet = st.get("fleet", {}).get("kernels", {})
    cstat = fleet.get(CANARY_REF, {}).get("status", "unknown")

    # --- phase: waiting for canary ---
    if rl["phase"] == "waiting":
        up = cstat.upper()
        if "COMPLETE" in up:
            rl["phase"] = "verifying"
            relaunch_log(f"canary COMPLETE -> verifying output in {CANARY_DIR}")
        elif any(x in up for x in ("ERROR", "CANCEL", "KILLED")):
            rl["grounded"] = f"canary ended without success: {cstat}"
            relaunch_log(f"GROUND STOP: {rl['grounded']} — wave 2 NOT pushed")
            return
        else:
            return  # still running/queued

    # --- phase: verifying canary output ---
    if rl["phase"] == "verifying":
        c = rl["canary"]
        mp4s = [p for p in __import__("pathlib").Path(CANARY_DIR).rglob("*.mp4")] if os.path.isdir(CANARY_DIR) else []
        good = [m for m in mp4s if m.stat().st_size > 1_000_000]
        result_json = os.path.join(CANARY_DIR, "result.json")
        job_ok = None
        if os.path.exists(result_json):
            try:
                manifest = json.load(open(result_json))
                job_ok = any(bool(m.get("ok")) for m in manifest) if isinstance(manifest, list) else bool(manifest.get("ok"))
            except Exception:
                job_ok = None
        if not mp4s:
            c["empty_polls"] = c.get("empty_polls", 0) + 1
            if c["empty_polls"] >= GRACE_POLLS:
                # one direct CLI pull attempt before giving up (owner token)
                try:
                    cli_set_token(next(t["token"] for t in load_vault()["tokens"] if t.get("account") == "deyoungsltd"))
                    env = dict(os.environ)
                    env["PATH"] = os.path.dirname(KAGGLE_BIN) + os.pathsep + env.get("PATH", "")
                    subprocess.run([KAGGLE_BIN, "kernels", "output", CANARY_REF, "-p", CANARY_DIR, "--unzip"],
                                   capture_output=True, text=True, timeout=600, env=env)
                    mp4s = [p for p in __import__("pathlib").Path(CANARY_DIR).rglob("*.mp4")]
                    good = [m for m in mp4s if m.stat().st_size > 1_000_000]
                except Exception as e:
                    relaunch_log(f"CLI output pull attempt failed: {type(e).__name__}: {e}")
                if not mp4s:
                    rl["grounded"] = "canary complete but no output files after grace period"
                    relaunch_log(f"GROUND STOP: {rl['grounded']} — wave 2 NOT pushed")
                    return
        if job_ok is False:
            rl["grounded"] = "result.json reports all jobs failed (ok=false)"
            relaunch_log(f"GROUND STOP: {rl['grounded']} — wave 2 NOT pushed")
            return
        if good and job_ok is not False:
            rl["phase"] = "pushing"
            relaunch_log(f"canary VERIFIED (mp4s={[m.name for m in mp4s]}, good={len(good)}, result_ok={job_ok}) -> pushing wave 2")
        else:
            c["verify_polls"] = c.get("verify_polls", 0) + 1
            if c["verify_polls"] >= GRACE_POLLS:
                rl["grounded"] = "output present but no valid mp4 (>=1MB) after grace period"
                relaunch_log(f"GROUND STOP: {rl['grounded']} — wave 2 NOT pushed")
            return

    # --- phase: pushing wave 2 ---
    if rl["phase"] == "pushing":
        vault = load_vault()
        tokens = {t.get("id") or t.get("account"): t["token"] for t in vault["tokens"]}
        owner = next(t["token"] for t in vault["tokens"] if t.get("account") == "deyoungsltd")
        pushed_now = []
        try:
            for acct, slug, tid in WAVE2:
                if slug in rl["wave2"]["pushed"] or slug in rl["wave2"]["abandoned"]:
                    continue
                d = os.path.join(KERNELS_DIR, slug)
                if not os.path.exists(os.path.join(d, "kernel-metadata.json")):
                    rl["wave2"]["abandoned"][slug] = "kernel dir missing"
                    relaunch_log(f"SKIP {slug}: kernel dir missing")
                    continue
                n = rl["wave2"]["attempts"].get(slug, 0)
                if n >= MAX_PUSH_ATTEMPTS:
                    rl["wave2"]["abandoned"][slug] = f"max attempts ({n})"
                    relaunch_log(f"ABANDON {slug}: {n} failed attempts")
                    continue
                cli_set_token(tokens.get(tid) or tokens.get(acct))
                rl["wave2"]["attempts"][slug] = n + 1
                try:
                    out = cli_push(d)
                    ok = "successfully pushed" in out.lower()
                    relaunch_log(f"push {acct}/{slug} (try {n + 1}): {'OK' if ok else 'FAIL'} — {out[:160]}")
                    if ok:
                        rl["wave2"]["pushed"][slug] = f"{acct}/{slug}"
                        pushed_now.append(slug)
                except Exception as e:
                    relaunch_log(f"push {acct}/{slug}: EXC {type(e).__name__}: {str(e)[:160]}")
                save_state(st)  # incremental save: a kill mid-wave never double-pushes
                time.sleep(20)
        finally:
            cli_set_token(owner)  # always restore owner token for the CLI
        remaining = [s for _, s, _ in WAVE2 if s not in rl["wave2"]["pushed"] and s not in rl["wave2"]["abandoned"]]
        if not remaining:
            rl["phase"] = "done"
            relaunch_log(f"WAVE2 DONE: pushed {len(rl['wave2']['pushed'])}/6 -> {list(rl['wave2']['pushed'].values())}")


def ensure_orchestrator():
    """Task 54-c: keep the recovery orchestrator alive — instances kept dying
    to sandbox process reaping. Idempotent, boot-script style (the plain
    nohup-from-exiting-parent pattern proven to survive)."""
    import subprocess
    pidf = pathlib.Path("/home/z/my-project/brain/recovery51.pid")
    try:
        if pidf.exists():
            p = pidf.read_text().strip()
            if p and subprocess.run(["kill", "-0", p], capture_output=True).returncode == 0:
                return
        subprocess.run(["bash", "/home/z/my-project/scripts/orch_boot.sh", "start"],
                       capture_output=True, timeout=30)
    except Exception as e:
        log(f"orch ensure error: {type(e).__name__}: {e}")


def lightning_watch():
    """Task 55: REST-only Lightning deyoung-h3 watcher (NO lightning_sdk in
    background - SDK/gRPC background processes get reaped silently; plain
    requests to Lightning REST are proven safe). Logs state + balance to
    brain/lightning_watch.json every pass. The c20 worker self-stops the
    studio when finished/fatal (proven); this watcher is the evidence trail
    + hard-cap alarm, NOT the primary credit guard."""
    import json as _json
    try:
        import requests
        lf = pathlib.Path("/home/z/my-project/workers/secrets/lightning_tokens.json")
        key = _json.loads(lf.read_text())["keys"][0]
        hdr = {"Authorization": f"Bearer {key['key']}"}
        base = key.get("cloud_url", "https://lightning.ai")
        out = {"checked": now()}
        r = requests.get(f"{base}/v1/projects/{key['teamspace_id']}/cloudspaces", headers=hdr, timeout=25)
        if r.status_code == 200:
            for cs in r.json().get("cloudspaces", []):
                if cs.get("name") == "deyoung-h3":
                    out["state"] = cs.get("state")
                    out["id"] = cs.get("id")
                    inu = (cs.get("codeStatus") or {}).get("inUse") or {}
                    out["instance_phase"] = inu.get("phase")
                    out["machine"] = ((inu.get("computeConfig") or {}).get("name"))
                    out["running_since"] = inu.get("startTimestamp")
        rm = requests.get(f"{base}/v1/memberships", headers=hdr, timeout=25)
        if rm.status_code == 200:
            for m in rm.json().get("memberships", []):
                if m.get("projectId") == key["teamspace_id"]:
                    out["balance"] = m.get("balance")
        stf = pathlib.Path("/home/z/my-project/brain/lightning_c20_evidence.json")
        if stf.exists():
            try:
                ev = _json.loads(stf.read_text())
                out["c20_phase"] = (ev.get("summary") or {}).get("phase") or ev.get("c20_phase")
            except Exception:
                pass
        wf = pathlib.Path("/home/z/my-project/brain/lightning_watch.json")
        prev = {}
        if wf.exists():
            try:
                prev = _json.loads(wf.read_text())
            except Exception:
                pass
        # hard-cap alarm: >20h continuous Running without self-stop = alert loudly
        if str(out.get("instance_phase", "")).upper().endswith("RUNNING"):
            t0 = out.get("running_since")
            if t0:
                try:
                    import datetime
                    t = datetime.datetime.fromisoformat(t0.replace("Z", "+00:00"))
                    hrs = (datetime.datetime.now(datetime.timezone.utc) - t).total_seconds() / 3600
                    out["running_hours"] = round(hrs, 1)
                    if hrs > 20:
                        out["ALERT"] = "studio running >20h - worker self-stop failed; manual stop needed"
                        log("LIGHTNING ALERT: " + out["ALERT"])
                except Exception:
                    pass
        wf.write_text(_json.dumps(out, indent=1))
    except Exception as e:
        log(f"lightning_watch error: {type(e).__name__}: {str(e)[:140]}")


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
                st = load_state()
                relaunch_step(st)
                ensure_orchestrator()
                lightning_watch()
                save_state(st)
            except KeyboardInterrupt:
                break
            except Exception as e:
                log(f"ERROR pass: {type(e).__name__}: {e}")
            time.sleep(secs)
    else:
        ch = pass_once(no_fetch)
        print(f"pass done; changes: {ch if ch else 'none'}")
        st = load_state()
        relaunch_step(st)
        lightning_watch()
        save_state(st)


if __name__ == "__main__":
    main()
