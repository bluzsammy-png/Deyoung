#!/usr/bin/env python3
"""Task 54: live-verify the owner-supplied Lightning AI API key and discover
what the account can actually do (teamspaces / Studios / plan state).

Usage:
  LIGHTNING_API_KEY=... LIGHTNING_USER_ID=... python3 scripts/lightning_probe_54.py

The key is NEVER hardcoded here (this file is git-tracked). Raw responses are
saved to brain/lightning54_*.json as evidence.
"""
import json
import os
import sys

import requests

BASE = os.environ.get("LIGHTNING_CLOUD_URL", "https://lightning.ai")
KEY = os.environ.get("LIGHTNING_API_KEY", "")
UID = os.environ.get("LIGHTNING_USER_ID", "")
OUT = "/home/z/my-project/brain"

if not KEY or not UID:
    print("FATAL: export LIGHTNING_API_KEY and LIGHTNING_USER_ID first")
    sys.exit(2)

S = requests.Session()
S.headers["Authorization"] = f"Bearer {KEY}"
S.headers["Accept"] = "application/json"


def call(name, path, method="GET", save=True, **kw):
    url = f"{BASE}{path}"
    r = S.request(method, url, timeout=25, **kw)
    body = None
    try:
        body = r.json()
    except Exception:
        body = {"_raw": r.text[:300]}
    if save:
        with open(f"{OUT}/lightning54_{name}.json", "w") as f:
            json.dump({"status": r.status_code, "url": url, "body": body}, f, indent=1)
    return r.status_code, body


def main():
    print(f"base: {BASE}")
    # 1. identity
    code, me = call("me", "/v1/auth/user")
    print(f"1) GET /v1/auth/user -> {code}")
    if code != 200:
        print("   body:", json.dumps(me)[:300])
        sys.exit(3)
    print(f"   id={me.get('id')} username={me.get('username')} email={me.get('email')}")
    print(f"   status={json.dumps(me.get('status', {}))[:220]}")
    print(f"   defaultOrgId={me.get('defaultOrgId')} memberOfOrgIds={me.get('memberOfOrgIds')}")

    # 2. teamspaces (projects) for this user
    code2, mem = call("memberships", "/v1/memberships")
    print(f"2) GET /v1/memberships -> {code2}")
    teams = []
    if code2 == 200:
        teams = (mem or {}).get("memberships") or []
        print(f"   {len(teams)} memberships")
        for m in teams[:10]:
            p = m.get("project") or {}
            print(f"   - project name={p.get('name')} id={p.get('id')} role={m.get('role')}")
    else:
        print("   body:", json.dumps(mem)[:300])

    # 3. studios (cloud spaces) per teamspace — membership fields are flat:
    #    projectId / name / balance / roles
    for m in teams[:6]:
        pid = m.get("projectId")
        pname = m.get("name") or pid
        print(f"3) teamspace name={pname} id={pid} balance={m.get('balance')}")
        if not pid:
            continue
        code3, cs = call(f"cloudspaces_{pname}", f"/v1/projects/{pid}/cloudspaces")
        if code3 == 200:
            items = (cs or {}).get("cloudSpaces") or (cs or {}).get("cloudspaces") or []
            print(f"   -> {code3}: {len(items)} studios")
            for c in items[:5]:
                print(f"   - {c.get('name')} id={c.get('id')} status={c.get('status')} "
                      f"machine={((c.get('spec') or {}).get('cloudSpaceMachine') or c.get('machine'))}")
        else:
            print(f"   -> {code3}: {json.dumps(cs)[:200]}")

    # 4. plan / balance (org-scoped; may fail on personal accounts - that is fine, report it)
    org = me.get("defaultOrgId") or (me.get("memberOfOrgIds") or [None])[0]
    if org:
        code4, bal = call("balance", f"/v1/orgs/{org}/billing/balance")
        print(f"4) GET /v1/orgs/{org}/billing/balance -> {code4}: {json.dumps(bal)[:200]}")
    else:
        print("4) no org on account -> org-scoped billing endpoints not applicable")
    print("done.")


if __name__ == "__main__":
    main()
