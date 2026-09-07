#!/usr/bin/env python3
"""Task 44-c: read-only probe of the prod render queue — what is the v2 canary
working on, worker notes, and overall queue health. No mutations."""
import json
import os
import sys

import psycopg2

RAILWAY_ENV = json.load(open(os.path.join(os.path.dirname(__file__), "..", "workers", "secrets", "supabase.json")))["railway_env"]
_raw = RAILWAY_ENV["DATABASE_URL"]
URL = _raw.split("?")[0] + ("?sslmode=require" if "sslmode" in _raw else "")


def q(cur, sql):
    cur.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def main():
    conn = psycopg2.connect(URL, connect_timeout=15)
    cur = conn.cursor()

    rows = q(cur, """
        SELECT id, status, "promptSeconds", "createdAt", "claimedAt", "deliveredAt", "workerNotes"
        FROM "VideoRequest"
        ORDER BY "createdAt" DESC
        LIMIT 12
    """)
    print(f"== latest {len(rows)} VideoRequests ==")
    for r in rows:
        notes = (r["workerNotes"] or "")[-160:]
        print(f"- {r['id'][:8]} status={r['status']:<10} claimed={r['claimedAt']} notes=...{notes!r}")

    counts = q(cur, 'SELECT status, COUNT(*) AS n FROM "VideoRequest" GROUP BY status ORDER BY n DESC')
    print("\n== queue by status ==")
    for c in counts:
        print(f"- {c['status']}: {c['n']}")

    cur.close()
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
