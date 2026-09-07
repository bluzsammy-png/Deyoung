#!/usr/bin/env python3
"""Task 48 watcher — tracks the E2E drain test + both site-worker kernels.

Polls every 5 min:
  - prod VideoRequest row cmtr0b1c62c4191e45ff9c5b0819 (owner scene s1 re-queue)
  - kaggle status of teslaprime/deyoung-site-w01 + wikeyoung5/deyoung-site-w01
Writes progress into brain/site_drain.log and state.json (site_drain key).
Exits after the render reaches done/failed or 6h elapse.
"""
import json, pathlib, subprocess, os, time

ROOT = pathlib.Path("/home/z/my-project")
RID = "cmtr0b1c62c4191e45ff9c5b0819"
LOG = ROOT / "brain/site_drain.log"
STATE = ROOT / "brain/state.json"
ACCOUNTS = ["teslaprime", "wikeyoung5"]

def log(msg):
    line = f"[{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")

def db_row():
    import psycopg2
    sec = json.loads((ROOT / "workers/secrets/supabase.json").read_text())
    url = sec["railway_env"]["DATABASE_URL"].split("?")[0] + "?sslmode=require"
    conn = psycopg2.connect(url, connect_timeout=15)
    cur = conn.cursor()
    cur.execute('SET search_path TO deyoung')
    cur.execute('select status, notes, "resultUrl", "gpuMinutes" from "VideoRequest" where id=%s', (RID,))
    r = cur.fetchone()
    cur.execute('select "storyboardJson" is not null from "StudioProject" where id=%s',
                ("cmtrdo9hu0006lf01u1jfbk3b",))
    sb = cur.fetchone()[0]
    cur.close(); conn.close()
    return r, sb

def kstatus(acct):
    tokens = json.loads((ROOT / "workers/secrets/kaggle_tokens.json").read_text())
    tok = next(t["token"] for t in tokens["tokens"] if t["account"] == acct)
    (pathlib.Path("/home/z/.kaggle/access_token")).write_text(tok)
    env = {**os.environ, "KAGGLE_CONFIG_DIR": "/home/z/.kaggle"}
    r = subprocess.run(["/home/z/.venv/bin/kaggle", "kernels", "status", f"{acct}/deyoung-site-w01"],
                       capture_output=True, text=True, env=env)
    return (r.stdout or r.stderr).strip().split(" ")[-1].strip('"')

def update_state(d):
    try:
        s = json.loads(STATE.read_text())
        s["site_drain"] = d
        STATE.write_text(json.dumps(s, indent=1))
    except Exception as e:
        log(f"state update failed: {e!r}")

log("watcher up — tracking E2E render " + RID)
start = time.time()
last = None
while time.time() - start < 6 * 3600:
    try:
        (status, notes, url_, gpu), sb = db_row()
        ks = {a: kstatus(a) for a in ACCOUNTS}
        line = f"render={status} storyboard={sb} gpu={gpu} kernels={ks}"
        if line != last:
            log(line)
            last = line
        update_state({"render_id": RID, "status": status, "storyboard": sb,
                      "kernels": ks, "checked": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                      "resultUrl": url_ or None})
        if status in ("done", "failed", "cancelled"):
            log(f"E2E DRAIN TEST FINISHED: {status} — resultUrl={url_} storyboard={sb}")
            break
        if all("ERROR" in v or "CancelAcknowledged" in v for v in ks.values()):
            log("both worker kernels down — render will be reclaimed if claimed; watcher exits")
            break
    except Exception as e:
        log(f"poll error: {e!r}")
    time.sleep(300)
log("watcher done")
