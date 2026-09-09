#!/usr/bin/env python3
"""Task 47 URGENT repair — set correct scrypt hash for BOTH admin rows from the
vault password. Exact app scheme (src/lib/auth.ts):
  scrypt$<salt:16B hex>$<hash:64B hex>, scryptSync defaults N=16384 r=8 p=1 dklen=64."""
import json

import psycopg2

vault = json.load(open("/home/z/my-project/workers/secrets/supabase.json"))
pw = vault["admin_bootstrap"]["password"]

salt = __import__("secrets").token_bytes(16)
digest = hashlib_scrypt(pw, salt) if False else None

import hashlib  # noqa: E402


def app_hash(password: str) -> str:
    s = __import__("secrets").token_bytes(16)
    d = hashlib.scrypt(password.encode(), salt=s, n=16384, r=8, p=1, dklen=64)
    return f"scrypt${s.hex()}${d.hex()}"


h = app_hash(pw)
assert len(h) == 168 and h.count("$") == 2, h[:30]

url = vault["railway_env"]["DATABASE_URL"].split("?")[0] + "?sslmode=require"
conn = psycopg2.connect(url)
cur = conn.cursor()
cur.execute('UPDATE deyoung."Admin" SET "passwordHash"=%s', (h,))
print("rows updated:", cur.rowcount)
conn.commit()

# read back and verify round-trip
cur.execute('SELECT email, "passwordHash" FROM deyoung."Admin"')
ok_all = True
for email, stored in cur.fetchall():
    scheme, salt_hex, dig_hex = stored.split("$")
    cand = hashlib.scrypt(pw.encode(), salt=bytes.fromhex(salt_hex), n=16384, r=8, p=1, dklen=64)
    ok = scheme == "scrypt" and cand.hex() == dig_hex
    print(f"{email}: verifies -> {ok}")
    ok_all = ok_all and ok
conn.close()
print("REPAIR VERDICT:", "OK — owner can log in" if ok_all else "STILL BROKEN")
