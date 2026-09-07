#!/usr/bin/env python3
"""Task 49 ops: (1) restore StudioProject.storyboardJson + scoped grants,
(2) cancel owner's queued render per owner order (finish campaign first)."""
import json, psycopg2

c = json.load(open('/home/z/my-project/workers/secrets/supabase.json'))
db = c['railway_env']['DATABASE_URL']
base = db.split('?')[0]
fleet = json.load(open('/home/z/my-project/workers/secrets/fleet_db.json'))
fleet_pw = fleet['password'] if isinstance(fleet, dict) and 'password' in fleet else None

conn = psycopg2.connect(base + '?sslmode=require', options='-c search_path=deyoung,public')
conn.autocommit = True
cur = conn.cursor()

# 1. Restore storyboardJson column if missing
cur.execute("SELECT column_name FROM information_schema.columns "
            "WHERE table_name='StudioProject' AND table_schema='deyoung' AND column_name='storyboardJson'")
if cur.fetchone():
    print('storyboardJson: already present')
else:
    cur.execute('ALTER TABLE "StudioProject" ADD COLUMN "storyboardJson" TEXT')
    print('storyboardJson: ADDED')

# 2. Re-apply scoped fleet-role grants (idempotent)
cur.execute("SELECT rolname FROM pg_roles WHERE rolname='deyoung_fleet'")
if cur.fetchone():
    cur.execute('GRANT SELECT ON "StudioProject" TO deyoung_fleet')
    cur.execute('GRANT UPDATE ("storyboardJson") ON "StudioProject" TO deyoung_fleet')
    cur.execute('GRANT SELECT ON "VideoRequest" TO deyoung_fleet')
    cur.execute('GRANT UPDATE (status, notes, "gpuMinutes", "resultUrl", "resultAssetId", "updatedAt") ON "VideoRequest" TO deyoung_fleet')
    cur.execute('GRANT INSERT ON "Asset" TO deyoung_fleet')
    print('scoped grants re-applied for deyoung_fleet')
else:
    print('deyoung_fleet role missing (kernels hold own creds) - skipping grants')

# 3. Cancel owner's queued render (owner order: finish campaign video first)
cur.execute("SELECT id, status FROM \"VideoRequest\" WHERE id='cmtr0b1c62c4191e45ff9c5b0819'")
row = cur.fetchone()
if row:
    rid, st = row
    if st == 'queued':
        cur.execute("UPDATE \"VideoRequest\" SET status='cancelled', "
                    "notes=COALESCE(notes,'') || ' | cancelled by owner 2026-09-07: prioritize campaign video' "
                    "WHERE id=%s AND status='queued'", (rid,))
        print(f'E2E render {rid}: queued -> cancelled (owner order)')
    else:
        print(f'E2E render {rid}: status={st} (already not queued)')
else:
    print('E2E render row not found')

# 4. Verify: no other queued owner renders remain
cur.execute("SELECT id, status, notes FROM \"VideoRequest\" WHERE status IN ('queued','processing') ORDER BY \"createdAt\" DESC")
rows = cur.fetchall()
print(f'remaining queued/processing renders: {len(rows)}')
for r in rows:
    print('  ', r)

# 5. Verify column + grant stuck
cur.execute("SELECT column_name FROM information_schema.columns "
            "WHERE table_name='StudioProject' AND table_schema='deyoung' AND column_name='storyboardJson'")
print('storyboardJson present now:', bool(cur.fetchone()))
conn.close()
