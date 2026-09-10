#!/usr/bin/env python3
"""DeYoung H3 worker doctor — the orchestrator-side supervisor (Task 61).

Reads layered truth from the deyoung-h3 Lightning studio and derives ONE
worker state. Explicitly refuses to call a worker healthy just because its
tmux session exists:

    studio state (REST) -> tmux session -> worker pid -> heartbeat age
    -> ComfyUI API -> H3 node readiness -> GPU

State machine (owner's required vocabulary):
    OFFLINE    no machine attached / studio stopped (clean, credits safe)
    STARTING   machine up, worker booting (no full heartbeat yet)
    IDLE       worker alive + heartbeat fresh + ComfyUI up + H3 ready, no job
    BUSY       same but a job is claimed/rendering
    ONLINE     alias emitted for "reachable and serving" = IDLE|BUSY superset;
              the raw field above is always carried in `detail`
    UNHEALTHY  tmux session alive but worker pid dead OR heartbeat stale
               (> HEARTBEAT_STALE_S) — the exact false-healthy trap
    ERROR      worker exited / ComfyUI broken / H3 nodes missing / claim auth

Recovery (only while the studio is RUNNING — never starts the machine):
    UNHEALTHY / worker-dead -> re-run ensure_h3_tmux.sh inside the studio,
    with backoff: max 3 consecutive restarts, then give up until a 60 min
    cooldown. Every action logged. No infinite restart loops.

Credit guard: this tool NEVER starts the studio machine. Stopping is offered
(--stop-studio) and idle auto-stop is opt-in (--auto-stop-idle MIN).

Usage:
    python3 scripts/h3_doctor_61.py                 # one check, human output
    python3 scripts/h3_doctor_61.py --json          # machine-readable
    python3 scripts/h3_doctor_61.py --loop 120      # supervisor loop (2 min)
    python3 scripts/h3_doctor_61.py --recover       # allow recovery actions
    python3 scripts/h3_doctor_61.py --stop-worker   # graceful worker stop
    python3 scripts/h3_doctor_61.py --stop-studio   # stop machine (credits)
    python3 scripts/h3_doctor_61.py --reset-incident
State: brain/h3worker_state.json   Log: brain/h3doctor.log
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent  # repo root (sandbox + Actions portable)
VAULT = ROOT / "workers/secrets/lightning_tokens.json"
STATE_F = ROOT / "brain/h3worker_state.json"
LOG_F = ROOT / "brain/h3doctor.log"

PROJECT_ID = "01m1svndkgcbberk6v4yfcdr00"
STUDIO_NAME = "deyoung-h3"
SESSION = "h3-queue"
WORK = "/teamspace/studios/this_studio/h3work"

HEARTBEAT_STALE_S = 180
RESTART_MAX_CONSECUTIVE = 3
RESTART_COOLDOWN_S = 3600
MIN_GAP_BETWEEN_RESTARTS_S = 120
IDLE_STOP_AFTER_MIN = 20

import requests  # noqa: E402

H = {"Authorization": "Bearer (set-at-runtime)"}


def log(msg):
    line = f"[{time.strftime('%Y-%m-%dT%H:%M:%SZ')}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_F, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def load_state():
    if STATE_F.exists():
        return json.load(open(STATE_F))
    return {"incidents": 0, "consecutive_restarts": 0, "last_restart_epoch": 0,
            "cooldown_until": 0, "last_state": None, "last_state_epoch": 0,
            "idle_since": None, "history": []}


def save_state(st):
    STATE_F.write_text(json.dumps(st, indent=1))


# ------------------------------------------------------------------ REST

def key():
    k = os.environ.get("LIGHTNING_API_KEY", "")
    if not k:
        k = json.load(open(VAULT))["keys"][0]["key"]
    # the lightning_sdk reads this env var itself (Studio.run auth) — REST
    # headers alone are not enough for in-studio execution
    os.environ["LIGHTNING_API_KEY"] = k
    return k


def api(method, path, timeout=30):
    H["Authorization"] = f"Bearer {key()}"
    r = requests.request(method, f"https://lightning.ai{path}", headers=H, timeout=timeout)
    r.raise_for_status()
    return r.json() if r.content else {}


def balance():
    for m in api("GET", "/v1/memberships").get("memberships", []):
        if m.get("projectId") == PROJECT_ID:
            return m.get("balance")
    return None


def studio():
    """Return (cloudspace_id, state, machine, phase)."""
    body = api("GET", f"/v1/projects/{PROJECT_ID}/cloudspaces")
    items = body.get("cloudspaces", []) if isinstance(body, dict) else body
    for cs in items:
        if isinstance(cs, dict) and cs.get("name") == STUDIO_NAME:
            inst = cs.get("latestCloudSpaceInstance") or {}
            return (cs.get("id"), cs.get("state"), inst.get("machine"), inst.get("phase"))
    return None, "NOT_FOUND", None, None


# ------------------------------------------------------------------ in-studio probes (SDK run)

_sdk = {}


def sdk_studio():
    if "st" not in _sdk:
        key()  # ensures LIGHTNING_API_KEY is in the process env BEFORE the SDK authenticates
        from lightning_sdk import Studio
        _sdk["st"] = Studio(name=STUDIO_NAME, teamspace="default-project", user="deyoungsltd")
    return _sdk["st"]


def run_inside(cmd, timeout=60):
    """Execute a command inside the studio; returns stdout or None on failure.
    Prefixes TERM=xterm: the Jupyter exec env ships TERM empty and tmux calls
    then fail with 'server exited unexpectedly' (proven live 2026-09-10)."""
    try:
        out = sdk_studio().run("export TERM=xterm; " + cmd)
        return out if isinstance(out, str) else (out or "")
    except Exception as e:
        log(f"run_inside failed ({cmd[:40]}…): {e!r}"[:180])
        return None


def push_file(local: pathlib.Path, remote: str):
    """b64-drop a file into the studio + sha256 verify."""
    import base64, hashlib
    code = local.read_bytes()
    b64 = base64.b64encode(code).decode()
    sha = hashlib.sha256(code).hexdigest()
    out = run_inside(
        f"mkdir -p {os.path.dirname(remote)} && "
        f"echo '{b64}' | base64 -d > {remote} && sha256sum {remote}", timeout=120)
    remote_sha = out.strip().split()[0] if out and out.strip() else "none"
    ok = remote_sha == sha
    log(f"push {remote}: sha {'MATCH' if ok else 'MISMATCH(' + remote_sha[:12] + ')'}")
    return ok


# ------------------------------------------------------------------ probes

def probe_all():
    """Collect every layer. Never raises — a failed probe is a result.
    L0 truth = the SDK's studio status: the REST cloudspace record STOPPED
    returning instance data after the T4 switch (observed live 2026-09-10:
    machine=null in REST while st.status=Running and credits burning), so
    REST alone would report false OFFLINE. SDK status reads are metadata-only
    and never start the machine."""
    p = {"checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"), "epoch": time.time()}
    cs_id, rest_state, rest_machine, phase = studio()
    p.update({"cloudspace": cs_id, "rest_state": rest_state, "balance": balance()})
    try:
        st = sdk_studio()
        p["studio_state"] = str(st.status)
        p["machine"] = str(getattr(st, "machine", None))
    except Exception as e:
        log(f"sdk status read failed: {e!r}"[:160])
        p["studio_state"] = rest_state
        p["machine"] = rest_machine
    p["phase"] = phase
    status = str(p["studio_state"])
    if "Running" not in status and "Start" not in status:
        p["reachable"] = False
        return p
    p["reachable"] = "Running" in status
    if not p["reachable"]:
        return p

    p["tmux_session"] = run_inside(
        f"tmux has-session -t {SESSION} 2>/dev/null && echo YES || echo NO")
    p["tmux_windows"] = run_inside(f"tmux list-windows -t {SESSION} -F '#W' 2>/dev/null | tr '\\n' ','")
    p["worker_pid"] = run_inside("pgrep -f h3_queue_worker.py | head -1")
    hb_raw = run_inside(f"cat {WORK}/status_h3q.json 2>/dev/null | head -c 4000")
    try:
        p["heartbeat"] = json.loads(hb_raw) if hb_raw and hb_raw.strip().startswith("{") else None
    except Exception:
        p["heartbeat"] = None
    p["heartbeat_age_s"] = (
        max(0, p["epoch"] - p["heartbeat"]["updated_epoch"])
        if p["heartbeat"] and p["heartbeat"].get("updated_epoch") else None)
    p["comfy_http"] = run_inside(
        "curl -s -o /dev/null -w '%{http_code}' --max-time 8 http://127.0.0.1:8188/queue 2>/dev/null")
    p["gpu"] = run_inside(
        "nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader 2>/dev/null | head -1")
    p["log_tail"] = run_inside(f"tail -3 {WORK}/h3q.log 2>/dev/null | tr '\\n' ' | '")
    return p


def derive(p):
    """Map layered probes -> ONE state. tmux-alive alone NEVER means healthy."""
    if not p.get("reachable"):
        return "OFFLINE", "studio machine not running"
    if p.get("studio_state") and "START" in str(p.get("studio_state")):
        return "STARTING", "studio machine transitioning"
    tmux_yes = p.get("tmux_session") == "YES"
    pid = (p.get("worker_pid") or "").strip()
    hb = p.get("heartbeat") or {}
    age = p.get("heartbeat_age_s")
    phase = str(hb.get("phase", "")).upper() if hb else ""

    if not hb:
        if tmux_yes or pid:
            return "STARTING", "worker present but no heartbeat yet"
        return "ERROR", "no worker process and no tmux session (worker never started or exited)"

    # worker dead while tmux alive = the exact trap the owner warned about
    if tmux_yes and not pid:
        return "UNHEALTHY", "tmux session exists but worker pid is dead"
    if pid and age is not None and age > HEARTBEAT_STALE_S:
        return "UNHEALTHY", f"heartbeat stale {int(age)}s (limit {HEARTBEAT_STALE_S}s) — process hung or machine frozen"
    if not pid and not tmux_yes:
        return "ERROR", f"worker exited (last phase was {phase or 'unknown'})"

    if phase in ("ERROR",):
        return "ERROR", f"worker reported ERROR: {hb.get('last_error')}"
    if phase in ("EXITING",):
        return "ONLINE", "worker finishing a graceful exit"

    comfy_ok = p.get("comfy_http") == "200"
    if pid and not comfy_ok:
        return "ERROR", "worker alive but ComfyUI API is down (renderer broken)"
    if pid and comfy_ok and not hb.get("h3_ready"):
        return "ERROR", "ComfyUI up but MiniMax-H3 nodes missing (stack problem)"

    if phase == "BUSY":
        return "BUSY", f"rendering job {((hb.get('job') or {}).get('id'))}"
    if phase in ("IDLE", "READY", "BETWEEN_JOBS"):
        return "IDLE", "worker alive, heartbeat fresh, ComfyUI up, H3 ready"
    return "STARTING", f"worker phase={phase or 'unknown'}"


# ------------------------------------------------------------------ actions

def deploy_worker_files():
    """Push worker code + env file (secrets pulled from vault, never printed)."""
    ok1 = push_file(ROOT / "workers/lightning/h3_queue_worker.py",
                    f"{WORK}/h3_queue_worker.py")
    push_file(ROOT / "workers/lightning/ensure_h3_tmux.sh",
              f"{WORK}/ensure_h3_tmux.sh")
    tok = json.load(open(ROOT / "workers/secrets/kaggle_tokens.json"))["worker_plane"]["current_token"]
    env_content = (
        f"DEYOUNG_SITE=https://deyoungltd.site\n"
        f"DEYOUNG_WORKER_TOKEN={tok}\n"
        f"DYG_WORKER_NAME=lightning-h3\n"
        f"DYG_STUDIO_NAME={STUDIO_NAME}\n"
    )
    import base64
    b64 = base64.b64encode(env_content.encode()).decode()
    out = run_inside(
        f"mkdir -p {WORK} && echo '{b64}' | base64 -d > {WORK}/h3q.env && "
        f"chmod 600 {WORK}/h3q.env && wc -c < {WORK}/h3q.env")
    ok3 = bool(out and out.strip().isdigit() and int(out.strip()) > 50)
    log(f"env file pushed (0600): {'OK' if ok3 else 'FAIL'}")
    return ok1 and ok3


def ensure_worker():
    out = run_inside(f"cd {WORK} && bash ensure_h3_tmux.sh", timeout=240)
    log("ensure output: " + ((out or "").strip()[-400:]))
    return out or ""


def stop_worker():
    # SIGTERM the worker; tmux session closes when its process exits.
    out = run_inside(
        f"pkill -TERM -f h3_queue_worker.py && echo TERM_SENT || echo NO_PROC", timeout=60)
    log("stop-worker: " + (out or "").strip())
    return (out or "").strip()


def stop_studio():
    cs_id, _, _, _ = studio()
    if not cs_id:
        log("stop-studio: cloudspace not found")
        return False
    try:
        api("POST", f"/v1/projects/{PROJECT_ID}/cloudspaces/{cs_id}/stop")
        log("stop-studio: STOP issued")
        return True
    except Exception as e:
        log(f"stop-studio failed: {e!r}")
        return False


# details that a restart can plausibly fix; anything else (auth 401, missing
# stack, ComfyUI fatal) is NOT restartable — restarting would just burn cycles
RESTARTABLE = ("worker exited (last phase was unknown)", "pid is dead", "stale",
               "never started", "no worker process")


def maybe_recover(st, state, detail):
    restartable = state == "UNHEALTHY" or (
        state == "ERROR" and any(k in detail for k in RESTARTABLE))
    if not restartable:
        return state, detail  # renderer/auth errors are not restartable here
    now = time.time()
    if now < st.get("cooldown_until", 0):
        return state, f"recovery suppressed (cooldown {int((st['cooldown_until'] - now) / 60)}min left)"
    if st.get("consecutive_restarts", 0) >= RESTART_MAX_CONSECUTIVE:
        st["cooldown_until"] = now + RESTART_COOLDOWN_S
        st["consecutive_restarts"] = 0
        save_state(st)
        log(f"recovery gave up after {RESTART_MAX_CONSECUTIVE} restarts — "
            f"cooldown {RESTART_COOLDOWN_S // 60}min (no infinite loop)")
        return "ERROR", "recovery gave up after " + str(RESTART_MAX_CONSECUTIVE) + " restarts; cooldown started"
    if now - st.get("last_restart_epoch", 0) < MIN_GAP_BETWEEN_RESTARTS_S:
        return state, "recovery gap not elapsed yet"

    log(f"RECOVERY: restarting worker inside tmux (attempt {st.get('consecutive_restarts', 0) + 1})"
        f" — reason: {detail}")
    out = ensure_worker()
    ok = "OK: worker alive" in out
    st["consecutive_restarts"] = 0 if ok else st.get("consecutive_restarts", 0) + 1
    st["last_restart_epoch"] = now
    st["incidents"] = st.get("incidents", 0) + 1
    save_state(st)
    return ("IDLE", "recovered: worker restarted and heartbeat verified") if ok \
        else ("ERROR", "recovery restart failed — see doctor log")


# ------------------------------------------------------------------ main

def check(recover=False, as_json=False):
    st = load_state()
    p = probe_all()
    state, detail = derive(p)
    hb = p.get("heartbeat") or {}

    acted = False
    if recover and p.get("reachable"):
        new_state, new_detail = maybe_recover(st, state, detail)
        if new_state != state:
            acted = True
            state, detail = new_state, new_detail
            p2 = probe_all()
            hb = p2.get("heartbeat") or hb
            state2, detail2 = derive(p2)
            log(f"post-recovery recheck: {state2} ({detail2})")

    # idle tracking for optional auto-stop (opt-in; never default)
    if state == "IDLE":
        st["idle_since"] = st.get("idle_since") or p["epoch"]
    else:
        st["idle_since"] = None
    st["last_state"], st["last_state_epoch"] = state, p["epoch"]
    st["history"] = (st.get("history", []) +
                     [{"t": p["checked_at"], "state": state, "detail": detail}])[-30:]
    save_state(st)

    result = {
        "state": state, "detail": detail, "recovery_action": acted,
        "studio": {"state": p.get("studio_state"), "machine": p.get("machine"),
                   "phase": p.get("phase"), "balance": p.get("balance")},
        "tmux_session": p.get("tmux_session"), "tmux_windows": p.get("tmux_windows"),
        "worker_pid": (p.get("worker_pid") or "").strip() or None,
        "heartbeat_age_s": (int(p["heartbeat_age_s"]) if p.get("heartbeat_age_s") is not None else None),
        "worker_phase": hb.get("phase"),
        "worker_job": ((hb.get("job") or {}).get("id")),
        "comfy_http": p.get("comfy_http"), "gpu": p.get("gpu"),
        "h3_ready": hb.get("h3_ready"),
        "last_delivered": hb.get("last_delivered"),
        "last_error": hb.get("last_error"),
        "log_tail": p.get("log_tail"),
        "incidents": st.get("incidents", 0),
        "consecutive_restarts": st.get("consecutive_restarts", 0),
    }
    if as_json:
        print(json.dumps(result, indent=1))
    else:
        print(f"STATE: {state}  —  {detail}")
        print(f"  studio: {result['studio']}")
        print(f"  tmux: session={result['tmux_session']} windows={result['tmux_windows']}")
        print(f"  worker: pid={result['worker_pid']} phase={result['worker_phase']} "
              f"hb_age={result['heartbeat_age_s']}s job={result['worker_job']}")
        print(f"  renderer: comfy={result['comfy_http']} gpu={result['gpu']} h3_ready={result['h3_ready']}")
        print(f"  incidents={result['incidents']} consecutive_restarts={result['consecutive_restarts']}")
        if result["log_tail"]:
            print(f"  log: {result['log_tail'][:220]}")
    return result


def main():
    ap = argparse.ArgumentParser(description="DeYoung H3 worker doctor (orchestrator side)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--loop", type=int, metavar="SEC", help="supervise forever, check every SEC")
    ap.add_argument("--recover", action="store_true", help="allow automatic worker restarts (with backoff)")
    ap.add_argument("--deploy", action="store_true", help="push worker files + env into the studio")
    ap.add_argument("--ensure", action="store_true", help="run ensure_h3_tmux.sh inside the studio")
    ap.add_argument("--stop-worker", action="store_true")
    ap.add_argument("--stop-studio", action="store_true")
    ap.add_argument("--auto-stop-idle", type=int, metavar="MIN", default=0,
                    help="in --loop mode: stop the studio after MIN minutes idle (credit guard)")
    ap.add_argument("--reset-incident", action="store_true")
    args = ap.parse_args()

    if args.reset_incident:
        st = load_state()
        st.update({"consecutive_restarts": 0, "cooldown_until": 0})
        save_state(st)
        log("incident counters reset")
        print("incident counters reset")

    if args.deploy:
        if not deploy_worker_files():
            sys.exit("deploy had failures — check doctor log")
        print("deploy: OK")
    if args.ensure:
        out = ensure_worker()
        print(out.strip()[-500:])
        if "OK: worker alive" not in out:
            sys.exit(14)
    if args.stop_worker:
        stop_worker()
    if args.stop_studio:
        stop_studio()
    if args.deploy or args.ensure or args.stop_worker or args.stop_studio or args.reset_incident:
        return

    if args.loop:
        log(f"doctor loop up (every {args.loop}s, recover={args.recover}, "
            f"auto-stop-idle={args.auto_stop_idle or 'off'})")
        while True:
            try:
                r = check(recover=args.recover, as_json=args.json)
                if args.auto_stop_idle and r["state"] == "OFFLINE":
                    log("loop: studio already offline — nothing to guard")
                elif args.auto_stop_idle and r["state"] == "IDLE":
                    st = load_state()
                    idle_min = (time.time() - (st.get("idle_since") or time.time())) / 60
                    if idle_min >= args.auto_stop_idle:
                        log(f"credit guard: IDLE for {idle_min:.0f}min — stopping studio")
                        stop_studio()
            except Exception as e:
                log(f"loop cycle error: {e!r}")
            time.sleep(args.loop)
    else:
        check(recover=args.recover, as_json=args.json)


if __name__ == "__main__":
    main()
