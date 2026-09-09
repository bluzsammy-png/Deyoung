#!/usr/bin/env python3
"""Task 58: RESET the prod admin password (verified flow).
- compute scrypt hash with the EXACT repo scheme (scrypt$salt$hash, keylen 64)
- UPDATE Admin row for admin@deyoung.site in prod DB
- verify by re-reading + scrypt-compare
- persist new password to vault .env.local ADMIN_BOOTSTRAP_PASSWORD
"""
import json
import re
import subprocess
import time

import psycopg2

NEW_PW = __import__("os").environ.get("NEW_ADMIN_PW", "")
EMAIL = "admin@deyoung.site"

# 1) hash with repo scheme
node = (
    "const c=require('crypto');"
    f"const salt=c.randomBytes(16).toString('hex');"
    f"const h=c.scryptSync({NEW_PW!r},salt,64).toString('hex');"
    "console.log('scrypt$'+salt+'$'+h)"
)
out = subprocess.run(["node", "-e", node], capture_output=True, text=True, cwd="/home/z/my-project")
newhash = out.stdout.strip()
assert newhash.startswith("scrypt$") and len(newhash) > 100, out.stderr
print("hash computed:", newhash[:30], "...")

# 2) update prod row
supa = json.load(open("workers/secrets/supabase.json"))["supabase"]
conn = psycopg2.connect(supa["database_url_session_pooler"],
                        options="-c search_path=deyoung,public",
                        sslmode="require", connect_timeout=15)
cur = conn.cursor()
cur.execute('UPDATE "Admin" SET "passwordHash"=%s WHERE email=%s', (newhash, EMAIL))
print("UPDATE rowcount:", cur.rowcount)
conn.commit()

# 3) verify by re-read + repo verify logic
cur.execute('SELECT "passwordHash" FROM "Admin" WHERE email=%s', (EMAIL,))
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
print("POST-RESET VERIFY match:", out.stdout.strip())

# 4) persist to vault .env.local
envp = "/home/z/my-project/.env.local"
txt = open(envp).read()
newtxt = re.sub(r"ADMIN_BOOTSTRAP_PASSWORD=.*", f"ADMIN_BOOTSTRAP_PASSWORD={NEW_PW}", txt)
open(envp, "w").write(newtxt)
print(".env.local updated:", "ADMIN_BOOTSTRAP_PASSWORD=" in newtxt)
print("NEW ADMIN PASSWORD:", NEW_PW)
