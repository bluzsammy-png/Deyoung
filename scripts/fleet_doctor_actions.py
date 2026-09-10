#!/usr/bin/env python3
"""Task 63 — fleet doctor for GitHub Actions (sandbox-immune control plane).

Runs the SAME repo scripts the sandbox doctor uses, so a sandbox rebuild can
never again leave the render fleet unmanaged:

    mode=ensure  queue has work -> start studio (if stopped) + ensure worker
                 (lightning_start_61.py + h3_doctor_61.py --ensure --recover)
    mode=status  read-only: queue counts + studio state + credit balance
    mode=stop    credit guard: stop the deyoung-h3 studio (h3_doctor_61 --stop-studio)

FAIL-SAFE: if the queue cannot be verified (missing WORKER_TOKEN, 401/503),
`ensure` REFUSES to start anything — a studio is never started blind.

Secrets arrive as env (GH Actions secrets / local export), never argv, never
printed: LIGHTNING_API_KEY, WORKER_TOKEN.
"""
import json
import os
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = os.environ.get("DEYOUNG_SITE", "https://deyoungltd.site")
PROJECT_ID = "01m1svndkgcbberk6v4yfcdr00"
STUDIO_NAME = "deyoung-h3"


def die(msg, code=1):
    print(f"[fleet-doctor] {msg}", flush=True)
    sys.exit(code)


def queue_counts():
    tok = (os.environ.get("WORKER_TOKEN") or "").strip()
    if len(tok) < 16:
        die("WORKER_TOKEN not set/short — queue cannot be verified; refusing blind fleet actions")
    req = urllib.request.Request(
        f"{SITE}/api/worker/status", headers={"Authorization": f"Bearer {tok}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        die(f"queue probe failed: HTTP {e.code} — refusing blind fleet actions")
    except Exception as e:  # noqa: BLE001
        die(f"queue probe failed: {type(e).__name__}: {str(e)[:120]} — refusing blind fleet actions")
    q = body.get("queue") or {}
    return int(q.get("queued", 0)), int(q.get("rendering", 0))


def worker_req(path, data=None, method="GET"):
    tok = (os.environ.get("WORKER_TOKEN") or "").strip()
    req = urllib.request.Request(
        f"{SITE}{path}",
        data=json.dumps(data).encode() if data else None,
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def reaper_poke():
    """Task 64 — the 45-min orphan reaper lives inside POST /api/worker/claim;
    with no live worker nobody triggers it. One claim poke per tick runs the
    reaper (empty queue -> 'Queue is empty', side effect: stuck rows reaped)."""
    try:
        worker_req("/api/worker/claim", {"agent": "fleet-doctor-poke"}, "POST")
    except Exception as e:  # noqa: BLE001
        print(f"[fleet-doctor] reaper poke: {type(e).__name__}: {str(e)[:90]}")


def requeue_orphaned():
    """Task 64 — auto-requeue reaper-orphaned rows (worker died mid-render:
    sandbox rebuilds, freezes, credit exhaustion). Orphans are infrastructure
    deaths, not prompt problems; each retry costs real credits so the loop is
    self-limiting. Watchdog-class rows stay operator-manual (possible poison
    prompts must not auto-loop)."""
    try:
        body = worker_req("/api/worker/jobs?status=failed")
    except Exception as e:  # noqa: BLE001
        print(f"[fleet-doctor] failed-row list unavailable: {type(e).__name__}: {str(e)[:100]}")
        return 0
    n = 0
    for j in body.get("jobs", []):
        if "orphaned:" not in (j.get("notes") or ""):
            continue
        try:
            worker_req(f"/api/worker/jobs/{j['id']}", {"action": "requeue", "agent": "fleet-doctor"}, "PATCH")
            n += 1
            print(f"[fleet-doctor] requeued orphaned row {j['id']}")
        except Exception as e:  # noqa: BLE001
            print(f"[fleet-doctor] requeue {j['id']} failed: {type(e).__name__}: {str(e)[:90]}")
    return n


def lightning_rest():
    key = (os.environ.get("LIGHTNING_API_KEY") or "").strip()
    if not key:
        die("LIGHTNING_API_KEY not set — Lightning plane unavailable")
    import requests  # noqa: PLC0415

    H = {"Authorization": f"Bearer {key}"}

    def api(method, path, timeout=30):
        r = requests.request(method, f"https://lightning.ai{path}", headers=H, timeout=timeout)
        r.raise_for_status()
        return r.json() if r.content else {}

    bal = None
    for m in api("GET", "/v1/memberships").get("memberships", []):
        if m.get("projectId") == PROJECT_ID:
            bal = m.get("balance")
            break
    state, machine = "NOT_FOUND", None
    body = api("GET", f"/v1/projects/{PROJECT_ID}/cloudspaces")
    items = body.get("cloudspaces", []) if isinstance(body, dict) else body
    for cs in items:
        if isinstance(cs, dict) and cs.get("name") == STUDIO_NAME:
            inst = cs.get("latestCloudSpaceInstance") or {}
            state, machine = cs.get("state"), inst.get("machine")
            break
    return state, machine, bal


def run(script, *args):
    print(f"[fleet-doctor] run: {script} {' '.join(args)}", flush=True)
    r = subprocess.run(
        [sys.executable, str(ROOT / script), *args],
        cwd=str(ROOT), capture_output=True, text=True, timeout=1500,
    )
    tail = (r.stdout or "").strip().splitlines()[-12:]
    print("\n".join(tail), flush=True)
    if r.returncode != 0:
        print((r.stderr or "").strip().splitlines()[-5:], flush=True)
    return r.returncode


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "ensure"
    q, rend = queue_counts() if mode in ("ensure", "status") else (None, None)
    state = machine = bal = None
    if (os.environ.get("LIGHTNING_API_KEY") or "").strip():
        try:
            state, machine, bal = lightning_rest()
        except Exception as e:  # noqa: BLE001
            print(f"[fleet-doctor] lightning probe failed: {type(e).__name__}: {str(e)[:120]}", flush=True)

    if mode == "status":
        print(f"[fleet-doctor] queue: queued={q} rendering={rend} | studio: {state} machine={machine} | balance: {bal}")
        return

    if mode == "stop":
        rc = run("scripts/h3_doctor_61.py", "--stop-studio")
        sys.exit(0 if rc == 0 else 5)

    # mode == ensure
    reaper_poke()
    requeued = requeue_orphaned() if mode == "ensure" else 0
    q, rend = queue_counts()
    print(f"[fleet-doctor] requeued {requeued} orphaned row(s) | queue: queued={q} rendering={rend} | studio: {state} | balance: {bal}")
    if (q or 0) + (rend or 0) == 0:
        if state and "Running" in str(state):
            print("[fleet-doctor] queue empty + studio running -> stopping machine (credit guard)")
            rc = run("scripts/h3_doctor_61.py", "--stop-studio")
            sys.exit(0 if rc == 0 else 5)
        print("[fleet-doctor] queue empty — nothing to do (studio not started; credits safe)")
        return
    if state == "NOT_FOUND":
        die(f"studio {STUDIO_NAME} not found under project {PROJECT_ID} — check account/teamspace")
    if "Running" not in str(state):
        print("[fleet-doctor] work queued + studio stopped -> starting studio")
        if run("scripts/lightning_start_61.py") != 0:
            die("studio start failed (see output above)", 6)
    else:
        print("[fleet-doctor] studio already running")
    rc = run("scripts/h3_doctor_61.py", "--ensure", "--recover")
    if rc != 0:
        die(f"doctor recovery returned {rc} — check heartbeat/ComfyUI in output", 7)
    print("[fleet-doctor] ensure complete — worker should claim the queued job within ~30s")


if __name__ == "__main__":
    main()
