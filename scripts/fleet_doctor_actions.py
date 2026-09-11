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
# Task 65 — measured T4 render cost is ~0.75-0.8 credits; starting below this
# floor produces a doomed render that can even push the balance negative
# (proven: 2026-09-11 the 05:09Z tick started at 0.84 and ended -0.32).
MIN_START_BALANCE = float(os.environ.get("MIN_START_BALANCE", "0.85"))
KAGGLE_KERNEL_USER = (os.environ.get("KAGGLE_USER") or "").strip()
KAGGLE_SLUG = "deyoung-worker"


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
    """Task 65 — steal-proof hygiene poke. Runs the 45-min orphan reaper via
    the site's reap_only claim mode: stuck rows are reaped, NOTHING is ever
    claimed (the Task 64 poke could steal a queued job into rendering with no
    renderer behind it — proven live on cmt12fd3a at 2026-09-11T05:09Z)."""
    try:
        body = worker_req("/api/worker/claim", {"agent": "fleet-doctor-poke", "reap_only": True}, "POST")
        if body.get("job") is not None:
            print("[fleet-doctor] WARNING: site pre-dates reap_only — poke CLAIMED a job it cannot render; it will orphan-reap on a later poke (self-heals)")
        else:
            print(f"[fleet-doctor] reap-only poke: reaped={body.get('reaped', '?')}")
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


def kaggle_session_status():
    """Read the deyoung-worker kernel status via the Kaggle CLI (token from
    env KAGGLE_API_TOKEN). Returns one of: running, idle (no live session),
    or None when the Kaggle plane is not configured/probed."""
    tok = (os.environ.get("KAGGLE_API_TOKEN") or "").strip()
    if not tok or not KAGGLE_KERNEL_USER:
        return None
    import subprocess  # noqa: PLC0415
    r = subprocess.run(
        [sys.executable, "-m", "kaggle", "kernels", "status", f"{KAGGLE_KERNEL_USER}/{KAGGLE_SLUG}"],
        capture_output=True, text=True, timeout=120,
        env={**os.environ, "KAGGLE_API_TOKEN": tok},
    )
    out = (r.stdout + r.stderr).lower()
    if r.returncode != 0:
        print(f"[fleet-doctor] kaggle status probe: {(r.stdout + r.stderr).strip()[:120]}")
        if "404" in out or "not found" in out:
            return "idle"  # kernel never pushed yet — a launch will create it
        return None  # auth/transport problems — do not push blind
    if "running" in out or "queued" in out:
        return "running"
    return "idle"


def kaggle_ensure(worker_token):
    """Task 65 — the FREE fallback plane. When the queue has work and the
    Lightning plane is balance-gated, launch/refresh one Kaggle GPU worker
    session (LTX renderer, explicit --renderer ltx so a broken kernel fails a
    job honestly instead of delivering a placeholder; --exit-idle so it stops
    burning quota when the queue drains). Idempotent: skips when a session is
    already live. Only ever runs when KAGGLE_API_TOKEN + KAGGLE_USER exist."""
    state = kaggle_session_status()
    if state == "running":
        print("[fleet-doctor] kaggle: session already running — nothing to do")
        return
    if state is None:
        print("[fleet-doctor] kaggle: probe unavailable (secrets missing or auth error) — skipping fallback plane this tick")
        return
    print("[fleet-doctor] kaggle: launching a fresh deyoung-worker GPU session (free plane)")
    rc = run(
        "scripts/kaggle_launch.py",
        "--token", worker_token,
        "--renderer", "ltx",
        "--max-minutes", "480",
        "--exit-idle",
    )
    if rc != 0:
        print(f"[fleet-doctor] kaggle launch returned {rc} — quota may be exhausted on this account; will retry next tick")


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

    # Task 65 debt guard: negative balance with a running studio = live debt.
    if bal is not None and bal < 0 and state and "Running" in str(state):
        print("[fleet-doctor] balance NEGATIVE with studio running -> emergency stop (debt guard)")
        run("scripts/h3_doctor_61.py", "--stop-studio")

    if (q or 0) + (rend or 0) == 0:
        if state and "Running" in str(state):
            print("[fleet-doctor] queue empty + studio running -> stopping machine (credit guard)")
            rc = run("scripts/h3_doctor_61.py", "--stop-studio")
            sys.exit(0 if rc == 0 else 5)
        print("[fleet-doctor] queue empty — nothing to do (studio not started; credits safe)")
        return

    # Task 65 balance gate: never start a studio that cannot finish a render.
    lightning_gated = False
    if bal is not None and bal < MIN_START_BALANCE:
        lightning_gated = True
        print(f"[fleet-doctor] balance {bal} < floor {MIN_START_BALANCE} — Lightning plane idle until top-up (a started render would die mid-way and can go negative, proven 2026-09-11)")
    elif bal is None:
        lightning_gated = True
        print("[fleet-doctor] balance unknown (probe failed) — refusing to start the studio blind")

    wt = (os.environ.get("WORKER_TOKEN") or "").strip()
    if state == "NOT_FOUND":
        die(f"studio {STUDIO_NAME} not found under project {PROJECT_ID} — check account/teamspace")
    if lightning_gated:
        kaggle_ensure(wt)
        print("[fleet-doctor] ensure complete for this tick — Lightning gated; free planes carry the queue")
        return
    if "Running" not in str(state):
        print("[fleet-doctor] work queued + studio stopped + balance ok -> starting studio")
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
