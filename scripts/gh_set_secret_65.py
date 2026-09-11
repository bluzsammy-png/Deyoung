#!/usr/bin/env python3
"""Task 65 — set GitHub Actions repo secrets via the sealed-box API.
Usage: python3 scripts/gh_set_secret_65.py NAME VALUE   (value never echoed)
Reads GH_PAT from env. Repo is bluzsammy-png/Deyoung.
"""
import base64
import json
import os
import sys
import urllib.request

REPO = "bluzsammy-png/Deyoung"
PAT = os.environ.get("GH_PAT", "")
if not PAT:
    raise SystemExit("GH_PAT env required")
if len(sys.argv) != 3:
    raise SystemExit("usage: gh_set_secret_65.py <NAME> <value-stdin-or-arg>")

name, value = sys.argv[1], sys.argv[2]

from nacl import encoding, public  # PyNaCl

req = urllib.request.Request(
    f"https://api.github.com/repos/{REPO}/actions/secrets/public-key",
    headers={"Authorization": f"token {PAT}", "Accept": "application/vnd.github+json"},
)
with urllib.request.urlopen(req, timeout=30) as r:
    pk = json.loads(r.read().decode())

pk_obj = public.PublicKey(pk["key"].encode("utf-8"), encoding.Base64Encoder())
sealed = public.SealedBox(pk_obj).encrypt(value.encode("utf-8"))

put = urllib.request.Request(
    f"https://api.github.com/repos/{REPO}/actions/secrets/{name}",
    data=json.dumps({"encrypted_value": base64.b64encode(sealed).decode(), "key_id": pk["key_id"]}).encode(),
    headers={"Authorization": f"token {PAT}", "Accept": "application/vnd.github+json"},
    method="PUT",
)
with urllib.request.urlopen(put, timeout=30) as r:
    print(f"{name}: HTTP {r.status} (201/204 = set)")
