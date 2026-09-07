#!/usr/bin/env python3
"""Dry-run the DB layer of the site worker exactly as the scoped role sees it."""
import json, pathlib, re, sys

ROOT = pathlib.Path("/home/z/my-project")
sys.path.insert(0, str(ROOT / "scripts"))

# build the same DSN the maker builds
fleet = json.loads((ROOT / "workers/secrets/fleet_db.json").read_text())
supa = json.loads((ROOT / "workers/secrets/supabase.json").read_text())
m = re.match(r"postgresql://postgres\.([^.]+):[^@]+@([^:/]+):(\d+)/", supa["railway_env"]["DATABASE_URL"])
DSN = f"postgresql://deyoung_fleet.{m.group(1)}:{fleet['password']}@{m.group(2)}:5432/postgres?sslmode=require"

# 1. template syntax
src = (ROOT / "campaign/site-worker/deyoung-site-w.py").read_text()
compile(src, "deyoung-site-w.py", "exec")
print("kernel template: syntax OK")

import psycopg2, psycopg2.extras

CLAIM_SQL = '''
UPDATE deyoung."VideoRequest" SET status='rendering', notes=%(claim)s, "updatedAt"=now()
WHERE id = (
  SELECT id FROM deyoung."VideoRequest" WHERE status='queued'
  ORDER BY "queuePriority" DESC, "createdAt" ASC, id ASC LIMIT 1 FOR UPDATE SKIP LOCKED
) RETURNING id, prompt, seconds, resolution, "withAudio", watermark, notes
'''
PROJECT_SQL = 'SELECT id, title, niche, "scriptJson", "storyboardJson" FROM deyoung."StudioProject" WHERE id=%s'
SB_SQL = 'UPDATE deyoung."StudioProject" SET "storyboardJson"=%s, "updatedAt"=now() WHERE id=%s'
ASSET_SQL = '''INSERT INTO deyoung."Asset"
  (id, kind, mime, bytes, "storageKey", driver, "isPublic", sha256, "createdBy", "createdAt")
VALUES (%(id)s, %(kind)s, %(mime)s, %(bytes)s, %(storageKey)s, 'supabase', %(isPublic)s, %(sha256)s, %(createdBy)s, now())
RETURNING id'''
DONE_SQL = """UPDATE deyoung."VideoRequest" SET status='done', "gpuMinutes"=%(gpu)s,
  "resultUrl"=%(url)s, "resultAssetId"=%(asset)s, notes=%(note)s, "updatedAt"=now()
WHERE id=%(id)s AND status='rendering'"""

conn = psycopg2.connect(DSN, connect_timeout=20)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

cur.execute(CLAIM_SQL, {"claim": "dry-run claim test"})
row = cur.fetchone()
print("claim (empty queue expected):", dict(row) if row else None)
conn.rollback()  # never keep a dry-run claim

# project read + storyboard write on the real project
cur.execute(PROJECT_SQL, ("cmtrdo9hu0006lf01u1jfbk3b",))
p = cur.fetchone()
print("project read:", p["id"] if p else None, "-", p["title"] if p else None)
if p:
    cur.execute(SB_SQL, (json.dumps({"sheets": [], "keyframes": [], "_dryrun": True}), p["id"]))
    print("storyboard write: OK, rows =", cur.rowcount)
conn.rollback()

# asset insert + RETURNING inside a transaction we roll back
cur.execute(ASSET_SQL, {"id": "flt-dryrun0000000000000", "kind": "video", "mime": "video/mp4",
                        "bytes": 123, "storageKey": "renders/dryrun.mp4", "isPublic": False,
                        "sha256": "x" * 64, "createdBy": "worker:dryrun"})
print("asset insert+returning:", cur.fetchone()["id"])
conn.rollback()
print("ALL DRY-RUN CHECKS PASSED (rolled back, nothing persisted)")
cur.close(); conn.close()
