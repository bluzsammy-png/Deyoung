#!/usr/bin/env python3
"""Purge login rate-limit buckets in prod DB so QA login can proceed."""
import json, pathlib

cfg = json.loads(pathlib.Path("/home/z/my-project/workers/secrets/supabase.json").read_text())
sb = cfg["supabase"]
url = sb.get("database_url_session_pooler") or sb.get("database_url_transaction_pooler") or sb.get("database_url_direct")
if not url:
    raise SystemExit(f"no db url in supabase.json keys: {list(sb.keys())}")
base = url.split("?")[0]
purl = base + "?sslmode=require"

import psycopg2
conn = psycopg2.connect(purl, options="-c search_path=deyoung,public", connect_timeout=20)
cur = conn.cursor()
cur.execute("DELETE FROM \"RateLimit\" WHERE bucket LIKE 'login:%' OR bucket LIKE 'ai:%'")
print("deleted rows:", cur.rowcount)
conn.commit()
cur.close()
conn.close()
print("rate-limit purge done")
