#!/usr/bin/env python3
"""Task 50 orchestrator: wait for v3 site-workers to exit -> push lip-sync v4 ->
queue an owner-tier test scene WITH dialogue -> watch to delivery.
Logs to brain/lipsync50.log. Run under nohup."""
import json, pathlib, subprocess, sys, time, secrets

ROOT = pathlib.Path("/home/z/my-project")
LOG = ROOT / "brain/lipsync50.log"

def log(*a):
    line = f"[{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}] " + " ".join(str(x) for x in a)
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")

def kaggle_env(acct):
    toks = json.load(open(ROOT / "workers/secrets/kaggle_tokens.json"))
    tok = next(t for t in toks["tokens"] if t["account"] == acct)
    home = pathlib.Path("/home/z/.kaggle"); home.mkdir(exist_ok=True)
    (home / "access_token").write_text(tok["token"])
    return {"KAGGLE_CONFIG_DIR": str(home), "HOME": "/home/z"}

def kaggle(args, acct):
    env = {**__import__("os").environ, **kaggle_env(acct)}
    return subprocess.run(["/home/z/.venv/bin/kaggle"] + args, capture_output=True, text=True, env=env, timeout=120)

def kstatus(acct, slug):
    r = kaggle(["kernels", "status", f"{acct}/{slug}"], acct)
    out = (r.stdout or r.stderr)
    if "RUNNING" in out: return "running"
    if "COMPLETE" in out or "complete" in out: return "complete"
    if "ERROR" in out: return "error"
    if "CANCEL" in out: return "cancelled"
    return out.strip()[:60]

def db():
    import psycopg2
    s = json.load(open(ROOT / "workers/secrets/supabase.json"))
    url = s["railway_env"]["DATABASE_URL"].split("?")[0]
    return psycopg2.connect(url + "?sslmode=require", options="-c search_path=deyoung,public")

log("TASK 50 orchestrator up — waiting for v3 site-workers to free their GPU slots")
ACCTS = [("teslaprime", "deyoung-site-w01"), ("wikeyoung5", "deyoung-site-w01")]

# ---- phase 1: wait for v3 to exit (idle-exit expected ~15 min after setup) ----
deadline = time.time() + 100 * 60
while time.time() < deadline:
    st = {a: kstatus(a, s) for a, s in ACCTS}
    log("v3 status:", st)
    if all(v in ("complete", "error", "cancelled") for v in st.values()):
        log("v3 workers all exited — pushing v4")
        break
    time.sleep(300)
else:
    log("TIMEOUT waiting for v3 — pushing anyway (push may queue)")

# ---- phase 2: push v4 to both accounts (retry while old session drains) ------
pushed = []
for attempt in range(6):
    ok_all = True
    for acct, slug in ACCTS:
        r = subprocess.run([sys.executable, str(ROOT / "scripts/site_worker_make.py"), acct, slug],
                           capture_output=True, text=True, timeout=180)
        out = (r.stdout or r.stderr).strip().splitlines()[-1:] 
        ok = "PUSHED" in (r.stdout + r.stderr)
        log(f"push attempt {attempt+1} {acct}: {'OK' if ok else 'blocked — ' + (out[0] if out else '?')[:80]}")
        if not ok: ok_all = False
    if ok_all:
        pushed = [a for a, _ in ACCTS]
        break
    time.sleep(180)
if not pushed:
    log("FATAL: could not push v4 — giving up")
    sys.exit(1)
log("v4 PUSHED to", pushed)

# ---- phase 3: wait for v4 to be RUNNING, then queue the test render ----------
time.sleep(120)
st = {a: kstatus(a, s) for a, s in ACCTS}
log("v4 status after boot:", st)

proj_id = "cmt" + secrets.token_hex(12)
req_id = "cmt" + secrets.token_hex(12)
script = {
    "title": "The Talking Machine",
    "logline": "A little robot speaks his very first words to his best friend — and the world hears him.",
    "characters": [
        {"name": "Robo", "look": "a small round hero robot with oversized curious digital eyes, glossy white-and-red shell and a bright backpack", "voice": "chirpy and eager"},
        {"name": "Lumi", "look": "a shy glowing firefly with tiny translucent wings and a warm golden light", "voice": "soft whisper"},
    ],
    "scenes": [{
        "id": "s1", "title": "The First Words", "seconds": 8,
        "line": "Hello world! I can talk now!",
        "visual": "Close-up of Robo's face as his digital eyes light up with joy while Lumi the firefly circles his head; sleeping city skyline at night behind, warm window lights, Pixar-heart with Ghibli wonder.",
    }],
}
prompt = ("Close-up of a small round hero robot with oversized curious digital eyes as a shy glowing "
          "firefly circles his head; sleeping city skyline at night, warm window lights, Pixar-heart "
          "with Ghibli wonder. 2D animated children's cartoon style with bold clean outlines.")

with db() as c, c.cursor() as cur:
    # admin user id (owner sees this project in their studio)
    cur.execute("SELECT id FROM \"User\" WHERE email='admin@deyoung.site' LIMIT 1")
    row = cur.fetchone()
    if not row:
        log("FATAL: admin user not found"); sys.exit(1)
    admin_uid = row[0]
    cur.execute(
        'INSERT INTO "StudioProject" (id, "userId", title, niche, brief, "scriptJson", status, "createdAt", "updatedAt") '
        'VALUES (%s, %s, %s, %s, %s, %s, %s, now(), now())',
        (proj_id, admin_uid, script["title"], "kids cartoon",
         "a little robot speaks his first words to his best friend the firefly",
         json.dumps(script), "scripted"))
    cur.execute(
        'INSERT INTO "VideoRequest" (id, email, prompt, seconds, resolution, "withAudio", watermark, '
        '"queuePriority", status, "dedupKey", "fromCache", notes, "createdAt", "updatedAt") '
        'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now(), now())',
        (req_id, "admin@deyoung.site", prompt, 8, "1080p", True, False,
         100, "queued", f"lipsync-test-{int(time.time())}", False,
         f"studio:{proj_id}:s1"))
    c.commit()
log(f"TEST QUEUED: request={req_id} project={proj_id} (owner studio, 8s close-up WITH dialogue)")

# ---- phase 4: watch the row to delivery --------------------------------------
deadline = time.time() + 210 * 60
last = ""
while time.time() < deadline:
    with db() as c, c.cursor() as cur:
        cur.execute('SELECT status, notes, "resultUrl" FROM "VideoRequest" WHERE id=%s', (req_id,))
        r = cur.fetchone()
    if r != last:
        log("render row:", r)
        last = r
    if r and r[0] in ("done", "failed", "cancelled"):
        break
    time.sleep(120)

with db() as c, c.cursor() as cur:
    cur.execute('SELECT status, "resultUrl", notes FROM "VideoRequest" WHERE id=%s', (req_id,))
    fin = cur.fetchone()
log("FINAL:", fin)
(ROOT / "brain/lipsync50_result.json").write_text(json.dumps(
    {"request": req_id, "project": proj_id, "status": fin[0], "resultUrl": fin[1], "notes": fin[2]}, indent=1))
log("orchestrator done")
