#!/usr/bin/env python3
"""Task 48 — prod DB ground truth: renders, users, studio projects, rate limits."""
import json, pathlib, sys
import psycopg2

sec = json.loads(pathlib.Path("/home/z/my-project/workers/secrets/supabase.json").read_text())
url = sec["railway_env"]["DATABASE_URL"]
# strip ALL query params (incl Prisma schema=deyoung), use options=-csearch_path
clean = url.split("?")[0] + "?sslmode=require&options=-csearch_path%3Ddeyoung"

conn = psycopg2.connect(clean, connect_timeout=15)
cur = conn.cursor()

def q(sql, label):
    try:
        cur.execute(sql)
        rows = cur.fetchall()
        print(f"--- {label} ---")
        for r in rows[:25]:
            print(r)
        if not rows:
            print("(none)")
    except Exception as e:
        print(f"--- {label} ERROR: {e}")
        conn.rollback()

q("select count(*) from \"VideoRequest\"", "VideoRequest count")
q("select id, status, priority, \"promptPreset\", \"sceneCount\", \"createdAt\" from \"VideoRequest\" order by \"createdAt\" desc limit 10", "VideoRequest rows")
q("select count(*) from \"StudioProject\"", "StudioProject count")
q("select id, title, \"createdAt\" from \"StudioProject\" order by \"createdAt\" desc limit 5", "StudioProject rows")
q("select email, role, status from \"Admin\"", "Admin rows")
q("select email, role, status, \"createdAt\" from \"User\" order by \"createdAt\" desc limit 10", "User rows")
q("select key, count, \"updatedAt\" from \"RateLimit\" order by \"updatedAt\" desc limit 8", "RateLimit rows")
q("select count(*) from \"Premiere\" where \"isPublic\"=true", "Public premieres")
cur.close(); conn.close()
print("DONE")
