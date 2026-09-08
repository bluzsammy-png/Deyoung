#!/usr/bin/env python3
"""Task 51 recovery orchestrator: restore the fleet the moment Kaggle GPU quota returns.

All 6 fleet accounts hit the 30h/week GPU cap (verified by push attempts 2026-09-08).
Renders resume at the weekly reset (Fri night -> Sat 00:00 UTC). This loop, run under
nohup, polls and auto-restores WITHOUT any human step:

  phase ground:  every 30 min, try a GPU push probe (campaign kernel to youngwilly).
                 Quota error -> sleep, retry. Success -> quota is back.
  phase restore: push campaign kernel (youngwilly first, quota-aware fallbacks)
                 + push v4 site workers (teslaprime + wikeyoung5) with REAL push
                 verification (CLI output checked for 'successfully' / quota text).
  phase watch:   poll the queued lip-sync E2E row (cmt12fd3a610...) to done/failed,
                 write brain/recovery51_state.json + brain/recovery51.log.

Idempotent across restarts: state lives in brain/recovery51_state.json.
Never prints token values. All pushes go through the vault tokens.
"""
import json, os, pathlib, re, shutil, subprocess, sys, tempfile, time

ROOT = pathlib.Path("/home/z/my-project")
LOG = ROOT / "brain/recovery51.log"
STATE = ROOT / "brain/recovery51_state.json"
VAULT = ROOT / "workers/secrets/kaggle_tokens.json"
E2E_ID = "cmt12fd3a610a05125f38d16840"
POLL_SEC = 1800
WATCH_SEC = 300
QUOTA_RE = re.compile(r"weekly GPU quota", re.I)

def log(*a):
    line = f"[{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}] " + " ".join(str(x) for x in a)
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")

def load_state():
    if STATE.exists():
        return json.load(open(STATE))
    return {"phase": "ground", "probe_account": "youngwilly", "restored": {}, "e2e": None}

def save_state(st):
    STATE.write_text(json.dumps(st, indent=1))

def kcli(acct, args, timeout=240):
    toks = json.load(open(VAULT))["tokens"]
    tok = next(t for t in toks if t["account"] == acct)
    home = pathlib.Path("/home/z/.kaggle"); home.mkdir(exist_ok=True)
    (home / "access_token").write_text(tok["token"])
    env = {**os.environ, "KAGGLE_CONFIG_DIR": str(home), "HOME": "/home/z"}
    return subprocess.run(["/home/z/.venv/bin/kaggle"] + args, capture_output=True,
                          text=True, env=env, timeout=timeout)

def push_kernel(src_dir, acct, kernel):
    td = tempfile.mkdtemp(prefix="rec51_")
    src = pathlib.Path(src_dir)
    for f in src.iterdir():
        shutil.copy2(f, pathlib.Path(td) / f.name)
    meta_p = pathlib.Path(td) / "kernel-metadata.json"
    meta = json.load(open(meta_p))
    meta["id"] = f"{acct}/{kernel}"
    meta["code_file"] = f"{kernel}.py"
    pyfiles = [p for p in src.iterdir() if p.suffix == ".py"]
    if pyfiles:
        shutil.copy2(pyfiles[0], pathlib.Path(td) / f"{kernel}.py")
    json.dump(meta, open(meta_p, "w"), indent=1)
    r = kcli(acct, ["kernels", "push", "-p", td], timeout=300)
    out = (r.stdout or "") + (r.stderr or "")
    if "successfully" in out.lower():
        return True, "pushed"
    if QUOTA_RE.search(out):
        return False, "QUOTA"
    return False, out.strip().splitlines()[-1][:120] if out.strip() else "unknown push error"

def db():
    import psycopg2
    s = json.load(open(ROOT / "workers/secrets/supabase.json"))
    url = s["railway_env"]["DATABASE_URL"].split("?")[0]
    return psycopg2.connect(url + "?sslmode=require", options="-c search_path=deyoung,public")

CAMP = str(ROOT / "campaign/v10/kernels/deyoung-v2-c01")

def push_site_worker(acct, kernel="deyoung-site-w01"):
    r = subprocess.run([sys.executable, str(ROOT / "scripts/site_worker_make.py"), acct, kernel],
                       capture_output=True, text=True, timeout=300)
    out = (r.stdout or "") + (r.stderr or "")
    if "PUSHED" in out:
        return True, "pushed"
    if QUOTA_RE.search(out):
        return False, "QUOTA"
    return False, (out.strip().splitlines()[-1][:120] if out.strip() else "unknown")

def main():
    st = load_state()
    log("recovery orchestrator up - phase:", st["phase"])
    while True:
        try:
            if st["phase"] == "ground":
                ok, msg = push_kernel(CAMP, st["probe_account"], "deyoung-v2-c01")
                log(f"ground probe {st['probe_account']}: {'QUOTA-BACK' if ok else msg}")
                if ok:
                    st["phase"] = "restore"
                    st["restored"]["campaign"] = {"account": st["probe_account"], "at": time.strftime("%Y-%m-%dT%H:%M:%SZ")}
                    save_state(st)
                    continue
                if msg != "QUOTA":
                    order = ["youngwilly", "teslaprime", "wikeyoung5", "jimcreat", "bittrexminingltd", "deyoungsltd"]
                    i = (order.index(st["probe_account"]) + 1) % len(order)
                    st["probe_account"] = order[i]
                    save_state(st)
                time.sleep(POLL_SEC)
                continue

            if st["phase"] == "restore":
                if "campaign" not in st["restored"]:
                    for acct in ["youngwilly", "teslaprime", "wikeyoung5", "jimcreat", "bittrexminingltd", "deyoungsltd"]:
                        ok, msg = push_kernel(CAMP, acct, "deyoung-v2-c01")
                        log(f"campaign push {acct}: {'OK' if ok else msg}")
                        if ok:
                            st["restored"]["campaign"] = {"account": acct, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ")}
                            break
                        if msg == "QUOTA":
                            continue
                    if "campaign" not in st["restored"]:
                        st["phase"] = "ground"
                        save_state(st); time.sleep(POLL_SEC); continue
                for acct in ["teslaprime", "wikeyoung5"]:
                    if acct in st["restored"].get("site_workers", {}):
                        continue
                    ok, msg = push_site_worker(acct)
                    log(f"site-worker v4 push {acct}: {'OK' if ok else msg}")
                    if ok:
                        st.setdefault("restored", {}).setdefault("site_workers", {})[acct] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
                    elif msg != "QUOTA":
                        log(f"  non-quota push failure on {acct} - will retry next cycle")
                save_state(st)
                if len(st["restored"].get("site_workers", {})) >= 1:
                    st["phase"] = "watch"
                    save_state(st)
                else:
                    time.sleep(POLL_SEC)
                continue

            if st["phase"] == "watch":
                with db() as c, c.cursor() as cur:
                    cur.execute('SELECT status, notes, "resultUrl" FROM "VideoRequest" WHERE id=%s', (E2E_ID,))
                    row = cur.fetchone()
                log("e2e row:", row)
                st["e2e"] = {"status": row[0], "notes": (row[1] or "")[:200], "resultUrl": row[2]}
                save_state(st)
                if row and row[0] in ("done", "failed", "cancelled"):
                    log("E2E FINISHED:", row[0], "->", row[2])
                    st["phase"] = "done"
                    save_state(st)
                    break
                time.sleep(WATCH_SEC)
                continue

            if st["phase"] == "done":
                log("recovery complete - exiting")
                break
        except Exception as e:
            log("cycle error:", repr(e)[:200])
            time.sleep(300)

if __name__ == "__main__":
    main()
