#!/usr/bin/env python3
"""Task 47 audit — verify prod DB state: admin seat, shadow user, plans."""
import json
import psycopg2

vault = json.load(open("/home/z/my-project/workers/secrets/supabase.json"))
env = vault.get("railway_env", {})
url = env["DATABASE_URL"]
# strip Prisma params, ensure sslmode
base = url.split("?")[0]
if "sslmode" not in base:
    base += "?sslmode=require"

conn = psycopg2.connect(base)
cur = conn.cursor()

def q(sql, args=None):
    cur.execute(sql, args or ())
    return cur.fetchall()

print("=== Admin rows ===")
for row in q('SELECT id, email, length("passwordHash") FROM deyoung."Admin"'):
    print(row)

print("=== User rows (role admin or admin email) ===")
for row in q('SELECT id, email, role, status, provider FROM deyoung."User" WHERE role=%s OR email LIKE %s ORDER BY email', ("admin", "%deyoung%")):
    print(row)

print("=== admin-free subscriptions ===")
for row in q('SELECT id, email, "planCode", status FROM deyoung."Subscription" WHERE "planCode"=%s', ("admin-free",)):
    print(row)

print("=== Plans ===")
for row in q('SELECT code, name, "maxSecondsVideo", "maxResolution", audio, watermark FROM deyoung."Plan" ORDER BY "sortOrder"'):
    print(row)

print("=== Latest studio projects ===")
for row in q('SELECT id, email, title, status, created_at FROM deyoung."StudioProject" ORDER BY "createdAt" DESC LIMIT 5'):
    print(row)

print("=== Latest video requests (studio) ===")
for row in q('SELECT id, email, status, seconds, resolution, left(prompt,60), created_at FROM deyoung."VideoRequest" ORDER BY "createdAt" DESC LIMIT 5'):
    print(row)

print("=== RateLimit ai rows ===")
for row in q("SELECT bucket, count, to_char(\"resetAt\",'MM-DD HH24:MI') FROM deyoung.\"RateLimit\" WHERE bucket LIKE %s ORDER BY \"resetAt\" DESC LIMIT 8", ("ai:%",)):
    print(row)

conn.close()
print("DONE")
