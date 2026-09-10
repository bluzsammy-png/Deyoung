#!/usr/bin/env python3
"""Task 62: poll GitHub commit statuses for CI (gitleaks + prod-selftest) and the
Railway deploy status written back to GitHub. Uses the PAT from env (never saved)."""
import json, os, sys, time, urllib.request

PAT = os.environ["GH_PAT"]
REPO = "bluzsammy-png/Deyoung"
SHA = sys.argv[1] if len(sys.argv) > 1 else "f4cf428"
HEAD = f"https://api.github.com/repos/{REPO}"

def get(url):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {PAT}", "Accept": "application/vnd.github+json",
        "User-Agent": "deyoung-task62"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)

def snapshot():
    st = get(f"{HEAD}/commits/{SHA}/statuses")
    latest = {}
    for s in st:  # statuses come newest-first; keep first per context
        if s["context"] not in latest:
            latest[s["context"]] = (s["state"], s.get("target_url") or "")
    return latest

deadline = time.time() * 60 * 60  # unused; loop bounded by attempts below
for attempt in range(60):
    latest = snapshot()
    states = {c: s for c, (s, _) in latest.items()}
    print(f"[{attempt:02d}] " + json.dumps({c: s for c, (s, u) in latest.items()}), flush=True)
    if latest and all(s == "success" for s, _ in latest.values()) and len(latest) >= 1:
        print("ALL SUCCESS"); break
    if any(s == "failure" for s, _ in latest.values()):
        print("FAILURE DETECTED"); break
    time.sleep(30)
else:
    print("TIMEOUT waiting for all-green")

# final detail dump
for ctx, (state, url) in snapshot().items():
    print(f"  {ctx}: {state} {url}")
