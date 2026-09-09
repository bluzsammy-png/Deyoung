#!/usr/bin/env python3
"""Task 57: stop the idle deyoung-h3 studio via pure REST (credit-protection guard).

Owner rule: no task attached -> studio must NOT burn credits. c20 abandoned,
yet a T4 stayed attached ~11h. REST path from installed SDK openapi:
POST /v1/projects/{projectId}/cloudspaces/{id}/stop

  LIGHTNING_API_KEY=... python3 scripts/lightning_idle_stop_57.py
"""
import json
import os
import sys
import time

KEY = os.environ.get("LIGHTNING_API_KEY", "")
if not KEY:
    print("FATAL: export LIGHTNING_API_KEY first")
    sys.exit(2)

import requests

BASE = "https://lightning.ai"
PROJECT_ID = "01m1svndkgcbberk6v4yfcdr00"
STUDIO_NAME = "deyoung-h3"
OUT = "/home/z/my-project/brain/lightning57_stop.json"
H = {"Authorization": f"Bearer {KEY}"}


def balance():
    r = requests.get(f"{BASE}/v1/memberships", headers=H, timeout=25)
    for m in r.json().get("memberships", []):
        if m.get("projectId") == PROJECT_ID:
            return m.get("balance")
    return None


def cloudspace():
    r = requests.get(f"{BASE}/v1/projects/{PROJECT_ID}/cloudspaces", headers=H, timeout=25)
    body = r.json()
    items = body.get("cloudspaces", []) if isinstance(body, dict) else body
    for cs in items:
        if isinstance(cs, dict) and cs.get("name") == STUDIO_NAME:
            inst = cs.get("latestCloudSpaceInstance") or {}
            return {
                "id": cs.get("id"),
                "state": cs.get("state"),
                "instance_phase": inst.get("phase"),
                "machine": inst.get("machine"),
                "running_since": inst.get("startedAt") or inst.get("createdAt"),
            }
    return None


def main():
    ev = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    ev["balance_before"] = balance()
    cs = cloudspace()
    ev["before"] = cs
    print("before:", json.dumps(cs), ev["balance_before"])
    if not cs:
        print("STUDIO NOT FOUND"); sys.exit(1)

    if cs["state"] != "CLOUD_SPACE_STATE_STOPPED":
        r = requests.post(
            f"{BASE}/v1/projects/{PROJECT_ID}/cloudspaces/{cs['id']}/stop",
            headers=H, timeout=30)
        ev["stop_http"] = r.status_code
        print("stop POST ->", r.status_code, r.text[:200])
        time.sleep(15)

    ev["after"] = cloudspace()
    time.sleep(8)
    ev["balance_after"] = balance()
    ev["ts_done"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(OUT, "w") as f:
        json.dump(ev, f, indent=1, default=str)

    stopped = ev["after"] and ev["after"]["state"] == "CLOUD_SPACE_STATE_STOPPED"
    print("after:", json.dumps(ev["after"]), "| balance:", ev["balance_after"])
    print("STOP_OK" if stopped else "STOP_UNVERIFIED")
    sys.exit(0 if stopped else 1)


if __name__ == "__main__":
    main()
