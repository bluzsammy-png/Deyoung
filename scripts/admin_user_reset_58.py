#!/usr/bin/env python3
"""Task 58b: align the USER-table hash for admin@deyoung.site with the new password."""
import json
import subprocess

import psycopg2

NEW_PW = __import__("os").environ.get("NEW_ADMIN_PW", "")
EMAIL = "admin@deyoung.site"

supa = json.load(open("workers/secrets/supabase.json"))["supabase"]
conn = psycopg2.connect(supa["database_url_session_pooler"],
                        options="-c search_path=deyoung,public",
                        sslmode="require", connect_timeout=15)
cur = conn.cursor()

# current hash — also test the old handover password against it (root-cause evidence)
cur.execute('SELECT "passwordHash" FROM "User" WHERE email=%s', (EMAIL,))
old_hash = cur.fetchone()[0]
node_old = (
    "const c=require('crypto');"
    f"const p={old_hash!r}.split('$');"
    f"const cand=c.scryptSync(__import__("os").environ.get("OLD_ADMIN_PW", ""),p[1],64).toString('hex');"
    "console.log(p[0]==='scrypt' && cand===p[2])"
)
out = subprocess.run(["node", "-e", node_old], capture_output=True, text=True, cwd="/home/z/my-project")
print("old_handover_pw matched User-row hash BEFORE reset:", out.stdout.strip())

# new hash via repo scheme
node = (
    "const c=require('crypto');"
    f"const salt=c.randomBytes(16).toString('hex');"
    f"const h=c.scryptSync({NEW_PW!r},salt,64).toString('hex');"
    "console.log('scrypt$'+salt+'$'+h)"
)
out = subprocess.run(["node", "-e", node], capture_output=True, text=True, cwd="/home/z/my-project")
newhash = out.stdout.strip()
assert newhash.startswith("scrypt$"), out.stderr

cur.execute('UPDATE "User" SET "passwordHash"=%s WHERE email=%s', (newhash, EMAIL))
print("User UPDATE rowcount:", cur.rowcount)
conn.commit()

cur.execute('SELECT "passwordHash" FROM "User" WHERE email=%s', (EMAIL,))
stored = cur.fetchone()[0]
cur.close(); conn.close()

node_v = (
    "const c=require('crypto');"
    f"const p={stored!r}.split('$');"
    f"const cand=c.scryptSync({NEW_PW!r},p[1],64);"
    "const exp=Buffer.from(p[2],'hex');"
    "console.log(cand.length===exp.length && c.timingSafeEqual(cand,exp))"
)
out = subprocess.run(["node", "-e", node_v], capture_output=True, text=True, cwd="/home/z/my-project")
print("POST-RESET User-row verify:", out.stdout.strip())
