"""Task orchestrator + intelligent capability router.

State machines:
  task:  QUEUED -> PLANNING -> ROUTING -> RUNNING -> VALIDATING -> COMPLETED
                       |              |               > FAILED / CANCELLED / QUARANTINED
                       +-> WAITING_FOR_RESOURCE (no free worker/quota available yet)

  stage: PENDING -> DISPATCHED -> RUNNING -> SUCCEEDED | FAILED(retry) | SKIPPED

Router scoring (per master prompt): capability match (required), then
free_status priority, worker health, failure rate, latency history, quota.
PAID resources are blocked by FREE_ONLY enforcement. If no free worker can
take a stage the task parks in WAITING_FOR_RESOURCE (never a paid fallback).
"""
from __future__ import annotations

import json
import threading
import time
from typing import Optional

from . import config, db, ids, planner, quota, registries

_wd_lock = threading.Lock()


def log_line(task_id: str, message: str, level: str = "info", stage_id: str = None, worker_id: str = None):
    db.execute("INSERT INTO logs(task_id, stage_id, worker_id, level, message, ts) VALUES (?,?,?,?,?,?)",
               (task_id, stage_id, worker_id, level, message, time.time()))


def emit_event(tenant_id: str, type_: str, resource: str, detail: dict, trace_id: str = None):
    db.execute("INSERT INTO events(id, tenant_id, type, resource, detail, trace_id, ts) VALUES (?,?,?,?,?,?,?)",
               (ids.event_id(), tenant_id, type_, resource, json.dumps(detail), trace_id, time.time()))


def audit(actor: str, action: str, resource: str, detail: dict):
    db.execute("INSERT INTO audit(ts, actor, action, resource, detail) VALUES (?,?,?,?,?)",
               (time.time(), actor, action, resource, json.dumps(detail)))


# ---------------------------------------------------------------------------
# Task creation
# ---------------------------------------------------------------------------
def create_task(objective: str, task_type: str = "auto", params: dict = None,
                constraints: dict = None, title: str = None, tenant_id: str = None,
                user_id: str = None, parent_task_id: str = None, priority: str = "normal") -> dict:
    tenant_id = tenant_id or config.DEFAULT_TENANT
    params = params or {}
    constraints = constraints or {}
    tid = ids.task_id()
    trace = ids.trace_id()

    if not quota.check(tenant_id, "max_tasks_per_day", 1):
        raise RuntimeError("QUOTA_EXCEEDED:max_tasks_per_day")
    active = db.query_one(
        "SELECT COUNT(*) c FROM tasks WHERE tenant_id=? AND status IN ('QUEUED','PLANNING','ROUTING','RUNNING','VALIDATING')",
        (tenant_id,))["c"]
    if active >= quota.get_quotas(tenant_id)["quotas"]["max_concurrent_tasks"]:
        raise RuntimeError("QUOTA_EXCEEDED:max_concurrent_tasks")

    db.execute(
        "INSERT INTO tasks(id, tenant_id, user_id, parent_task_id, title, objective, type, "
        "input, constraints, status, trace_id, priority, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (tid, tenant_id, user_id, parent_task_id, title or (objective[:60] or task_type),
         objective, task_type, json.dumps({"objective": objective, "params": params}),
         json.dumps(constraints), "PLANNING", trace, priority, time.time(), time.time()))
    quota.consume(tenant_id, "tasks")
    log_line(tid, f"task accepted (type={task_type})")

    plan = planner.plan_task(task_type, objective, params, constraints)
    db.execute("UPDATE tasks SET plan=?, status='ROUTING', updated_at=? WHERE id=?",
               (json.dumps(plan), time.time(), tid))
    for st in plan["stages"]:
        db.execute(
            "INSERT INTO stages(id, task_id, seq, name, capability, tool, op, params, depends_on, "
            "group_id, status) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (ids.stage_id(), tid, st["seq"], st["name"], st["capability"], st.get("tool"),
             st["op"], json.dumps(st["params"]), json.dumps(st["depends_on"]), st.get("group"),
             "PENDING"))
    emit_event(tenant_id, "task.planned", tid, {"stages": len(plan["stages"]), "type": task_type}, trace)
    return get_task(tid)


def get_task(task_id: str) -> Optional[dict]:
    t = db.query_one("SELECT * FROM tasks WHERE id=?", (task_id,))
    if not t:
        return None
    stages = db.query("SELECT * FROM stages WHERE task_id=? ORDER BY seq", (task_id,))
    arts = db.query("SELECT id, name, type, size, checksum, storage FROM artifacts WHERE task_id=?", (task_id,))
    t["stages"] = stages
    t["artifact_ids"] = [a["id"] for a in arts]
    return t


def task_logs(task_id: str, since: int = 0, limit: int = 500) -> dict:
    rows = db.query("SELECT id, ts, level, stage_id, worker_id, message FROM logs "
                    "WHERE task_id=? AND id>? ORDER BY id LIMIT ?", (task_id, since, limit))
    nxt = rows[-1]["id"] if rows else since
    return {"logs": rows, "next_since": nxt}


# ---------------------------------------------------------------------------
# Intelligent router: pick the best free worker for a stage
# ---------------------------------------------------------------------------
def _score_worker(worker: dict, stage: dict) -> float:
    caps = set(json.loads(worker["capabilities"] or "[]"))
    if stage["capability"] not in caps:
        return -1.0
    score = 100.0
    score -= worker.get("failure_count", 0) * 10
    if worker.get("health") == "degraded":
        score -= 40
    # Workers that heartbeat recently are preferred (freshness proxy)
    hb_age = time.time() - (worker.get("last_heartbeat") or 0)
    score -= min(20.0, hb_age / 60.0)
    return score


def pick_worker(tenant_id: str, stage: dict) -> Optional[dict]:
    workers = db.query("SELECT * FROM workers WHERE tenant_id=? AND status='online'", (tenant_id,))
    best, best_score = None, -1.0
    for w in workers:
        s = _score_worker(w, stage)
        if s > best_score:
            best, best_score = w, s
    return best


def _deps_satisfied(stage: dict) -> bool:
    deps = json.loads(stage["depends_on"] or "[]")
    if not deps:
        return True
    rows = db.query("SELECT name, status FROM stages WHERE task_id=?", (stage["task_id"],))
    by_name = {r["name"]: r["status"] for r in rows}
    return all(by_name.get(d) in ("SUCCEEDED",) for d in deps)


def _try_dispatch_stage(stage: dict, worker: dict) -> Optional[dict]:
    """Assign one stage to a specific worker (the caller of the pull endpoint)."""
    tenant = db.query_one("SELECT tenant_id FROM tasks WHERE id=?", (stage["task_id"],))["tenant_id"]
    jid = ids.job_id()
    now = time.time()
    deadline = now + config.STAGE_DEADLINE_S
    params = json.loads(stage["params"] or "{}")

    # Resolve artifact references: {"artifact_ref": "<stage-name>"} -> artifact_id
    if params.get("artifact_ref"):
        ref = params.pop("artifact_ref")
        row = db.query_one(
            "SELECT a.id FROM artifacts a JOIN stages s ON s.id=a.stage_id "
            "WHERE s.task_id=? AND s.name=? ORDER BY a.created_at DESC LIMIT 1",
            (stage["task_id"], ref))
        if row:
            params["artifact_id"] = row["id"]

    # Inject upstream outputs so dependent stages can consume results.
    deps = json.loads(stage["depends_on"] or "[]")
    if deps:
        siblings = db.query("SELECT name, output FROM stages WHERE task_id=?", (stage["task_id"],))
        by_name = {s["name"]: s["output"] for s in siblings}
        params["inputs"] = {d: json.loads(by_name[d]) if by_name.get(d) else {} for d in deps}

    db.execute("UPDATE stages SET status='DISPATCHED', worker_id=?, job_id=?, started_at=?, deadline_at=? WHERE id=?",
               (worker["id"], jid, now, deadline, stage["id"]))
    log_line(stage["task_id"], f"stage '{stage['name']}' dispatched to worker {worker['name']} ({worker['type']})",
             stage_id=stage["id"], worker_id=worker["id"])
    emit_event(tenant, "stage.dispatched", stage["id"], {"worker": worker["id"], "job": jid})
    return {
        "job_id": jid, "task_id": stage["task_id"], "stage_id": stage["id"],
        "stage_name": stage["name"], "op": stage["op"], "tool": stage["tool"],
        "capability": stage["capability"], "params": params,
        "deadline_at": deadline, "trace_id": _trace_of(stage["task_id"]),
    }


def _trace_of(task_id: str) -> str:
    t = db.query_one("SELECT trace_id FROM tasks WHERE id=?", (task_id,))
    return t["trace_id"] if t else ""


def _refresh_task_status(task_id: str):
    t = db.query_one("SELECT status FROM tasks WHERE id=?", (task_id,))
    if not t or t["status"] in ("COMPLETED", "FAILED", "CANCELLED", "QUARANTINED"):
        return
    stages = db.query("SELECT * FROM stages WHERE task_id=? ORDER BY seq", (task_id,))
    statuses = [s["status"] for s in stages]
    if any(s in ("DISPATCHED", "RUNNING") for s in statuses):
        db.execute("UPDATE tasks SET status='RUNNING', started_at=COALESCE(started_at,?), updated_at=? WHERE id=?",
                   (time.time(), time.time(), task_id))
        return
    if all(s == "SUCCEEDED" for s in statuses):
        db.execute("UPDATE tasks SET status='COMPLETED', completed_at=?, updated_at=?, progress=100 WHERE id=?",
                   (time.time(), time.time(), task_id))
        log_line(task_id, "task completed")
        emit_event(_tenant_of(task_id), "task.completed", task_id, {})
        return
    if any(s == "FAILED" for s in statuses):
        db.execute("UPDATE tasks SET status='FAILED', completed_at=?, updated_at=? WHERE id=?",
                   (time.time(), time.time(), task_id))
        emit_event(_tenant_of(task_id), "task.failed", task_id, {})
        return
    if all(s in ("PENDING", "SKIPPED") for s in statuses):
        db.execute("UPDATE tasks SET status='ROUTING', updated_at=? WHERE id=?", (time.time(), task_id))


def _tenant_of(task_id: str) -> str:
    return db.query_one("SELECT tenant_id FROM tasks WHERE id=?", (task_id,))["tenant_id"]


def dispatch_scan() -> int:
    """Refresh statuses for all active tasks; mark WAITING_FOR_RESOURCE when
    ready stages have no free worker. Actual assignment happens when a worker
    pulls a job (claim), so multi-stage pipelines flow stage-by-stage and
    multiple workers parallelize independent stages naturally."""
    waiting = 0
    active = db.query("SELECT id, tenant_id, status FROM tasks "
                      "WHERE status IN ('QUEUED','PLANNING','ROUTING','RUNNING','VALIDATING','WAITING_FOR_RESOURCE')")
    for t in active:
        stages = db.query("SELECT * FROM stages WHERE task_id=? ORDER BY seq", (t["id"],))
        any_waiting = False
        for st in stages:
            if st["status"] != "PENDING" or not _deps_satisfied(st):
                continue
            if pick_worker(t["tenant_id"], st) is None:
                any_waiting = True
        if any_waiting:
            waiting += 1
            db.execute("UPDATE tasks SET status='WAITING_FOR_RESOURCE', updated_at=? WHERE id=? "
                       "AND status NOT IN ('COMPLETED','FAILED','CANCELLED')",
                       (time.time(), t["id"]))
        else:
            _refresh_task_status(t["id"])
    return waiting


def claim_job(worker: dict, wait_s: float = 0) -> Optional[dict]:
    """Worker pulls its next job (long-poll handled in router layer).

    The dispatch lock is held ONLY around each single claim attempt - never
    across the long-poll wait - so one slow-polling worker can never starve
    the others."""
    end = time.time() + max(0.0, wait_s)
    while True:
        with _wd_lock:
            job = _claim_one(worker)
        if job is not None:
            return job
        if time.time() >= end:
            return None
        time.sleep(0.3)


class tx_guard:
    """No-op context kept for symmetry; db layer serializes internally."""
    def __enter__(self): return self
    def __exit__(self, *a): return False


def _claim_one(worker_row: dict) -> Optional[dict]:
    """Assign the next eligible stage TO THE POLLING WORKER ONLY.

    Pull-dispatch invariant: a long-poll response is always a job bound to
    the worker that made the request (prevents cross-worker job leakage)."""
    worker = db.query_one("SELECT * FROM workers WHERE id=?", (worker_row["id"],))
    if not worker or worker["status"] != "online":
        return None
    caps = set(json.loads(worker["capabilities"] or "[]"))
    stages = db.query(
        "SELECT s.* FROM stages s JOIN tasks t ON t.id = s.task_id "
        "WHERE t.status IN ('QUEUED','PLANNING','ROUTING','RUNNING','VALIDATING','WAITING_FOR_RESOURCE') "
        "AND s.status='PENDING' ORDER BY t.created_at, s.seq")
    for st in stages:
        if st["capability"] not in caps:
            continue
        if not _deps_satisfied(st):
            continue
        tenant = _tenant_of(st["task_id"])
        if st["capability"] in ("image_generation", "text_to_video", "image_to_video",
                                "text_generation", "text_to_speech", "music_generation",
                                "GPU_execution"):
            est = 2.0
            if not quota.check(tenant, "gpu_minutes", est):
                log_line(st["task_id"], "GPU quota exhausted for today; task parked "
                         "(RESOURCE_UNAVAILABLE until quota resets)",
                         level="warn", stage_id=st["id"])
                continue
        job = _try_dispatch_stage(st, worker)
        if job:
            quota.consume(tenant, "gpu_minutes", 2.0)
            return job
    return None


# ---------------------------------------------------------------------------
# Job completion / failure
# ---------------------------------------------------------------------------
def complete_job(worker_id: str, job_id: str, status: str, result: dict = None,
                 error: str = None, error_code: str = None) -> dict:
    stage = db.query_one("SELECT * FROM stages WHERE job_id=? AND worker_id=?", (job_id, worker_id))
    if not stage:
        return {"ok": False, "detail": "unknown job for worker"}
    task_id = stage["task_id"]
    now = time.time()
    if status == "SUCCEEDED":
        db.execute("UPDATE stages SET status='SUCCEEDED', output=?, finished_at=?, error=NULL WHERE id=?",
                   (json.dumps(result or {}), now, stage["id"]))
        log_line(task_id, f"stage '{stage['name']}' succeeded", stage_id=stage["id"], worker_id=worker_id)
    elif status == "CANCELLED":
        db.execute("UPDATE stages SET status='SKIPPED', finished_at=?, error='cancelled' WHERE id=?",
                   (now, stage["id"]))
    else:
        w = db.query_one("SELECT failure_count, health FROM workers WHERE id=?", (worker_id,))
        if w:
            fc = (w["failure_count"] or 0) + 1
            health = "degraded" if fc >= config.CIRCUIT_BREAKER_FAILURES else "healthy"
            db.execute("UPDATE workers SET failure_count=?, health=? WHERE id=?", (fc, health, worker_id))
        retries = stage["retry_count"] or 0
        if retries < config.MAX_STAGE_RETRIES and (error_code or "") != "SECURITY_VIOLATION":
            db.execute("UPDATE stages SET status='PENDING', worker_id=NULL, job_id=NULL, retry_count=?, error=? WHERE id=?",
                       (retries + 1, error, stage["id"]))
            log_line(task_id, f"stage '{stage['name']}' failed ({error}); requeued (retry {retries+1})",
                     level="warn", stage_id=stage["id"], worker_id=worker_id)
        else:
            final = "QUARANTINED" if (error_code or "") == "SECURITY_VIOLATION" else "FAILED"
            db.execute("UPDATE stages SET status='FAILED', finished_at=?, error=? WHERE id=?",
                       (now, error, stage["id"]))
            db.execute("UPDATE tasks SET status=?, updated_at=?, error=? WHERE id=? AND status NOT IN ('COMPLETED','CANCELLED')",
                       (final, now, error, task_id))
            log_line(task_id, f"stage '{stage['name']}' failed permanently: {error}", level="error",
                     stage_id=stage["id"], worker_id=worker_id)
    _refresh_task_status(task_id)
    emit_event(_tenant_of(task_id), "stage.completed", stage["id"], {"status": status})
    return {"ok": True}


def cancel_task(task_id: str) -> dict:
    t = db.query_one("SELECT * FROM tasks WHERE id=?", (task_id,))
    if not t:
        return {"ok": False, "detail": "not found"}
    if t["status"] in ("COMPLETED", "CANCELLED"):
        return {"ok": True, "status": t["status"]}
    db.execute("UPDATE stages SET status='SKIPPED', finished_at=?, error='task cancelled' "
               "WHERE task_id=? AND status IN ('PENDING','DISPATCHED')", (time.time(), task_id))
    db.execute("UPDATE tasks SET status='CANCELLED', completed_at=?, updated_at=? WHERE id=?",
               (time.time(), time.time(), task_id))
    log_line(task_id, "task cancelled by user")
    emit_event(_tenant_of(task_id), "task.cancelled", task_id, {})
    return {"ok": True, "status": "CANCELLED"}


def watchdog() -> int:
    """Requeue stages past deadline once, then fail them. Fail tasks whose worker died."""
    now = time.time()
    n = 0
    stale = db.query("SELECT * FROM stages WHERE status IN ('DISPATCHED','RUNNING') AND deadline_at < ?", (now,))
    for st in stale:
        retries = st["retry_count"] or 0
        if retries < config.MAX_STAGE_RETRIES:
            db.execute("UPDATE stages SET status='PENDING', worker_id=NULL, job_id=NULL, retry_count=?, "
                       "deadline_at=NULL, error='deadline exceeded; requeued' WHERE id=?",
                       (retries + 1, st["id"]))
        else:
            db.execute("UPDATE stages SET status='FAILED', finished_at=?, error='deadline exceeded' WHERE id=?",
                       (now, st["id"]))
        log_line(st["task_id"], f"stage '{st['name']}' deadline exceeded", level="warn", stage_id=st["id"])
        n += 1
    # workers silent too long -> offline; their dispatched stages requeue
    cutoff = now - config.WORKER_OFFLINE_AFTER_S
    off = db.query("SELECT id FROM workers WHERE status='online' AND last_heartbeat < ?", (cutoff,))
    for w in off:
        db.execute("UPDATE workers SET status='offline' WHERE id=?", (w["id"],))
        requeued = db.query("SELECT id, task_id, name FROM stages WHERE worker_id=? AND status IN ('DISPATCHED','RUNNING')", (w["id"],))
        for st in requeued:
            db.execute("UPDATE stages SET status='PENDING', worker_id=NULL, job_id=NULL, deadline_at=NULL WHERE id=?", (st["id"],))
            log_line(st["task_id"], f"stage '{st['name']}' requeued (worker offline)",
                     level="warn", stage_id=st["id"])
        emit_event(config.DEFAULT_TENANT, "worker.offline", w["id"], {})
        n += 1
    return n


def add_worker_artifact(tenant_id: str, task_id: str, stage_id: str, worker_id: str,
                        name: str, kind: str, mime: str, size: int, checksum: str,
                        storage: str, location: str, provenance: dict = None,
                        metadata: dict = None, visibility: str = "tenant") -> str:
    aid = ids.artifact_id()
    db.execute(
        "INSERT INTO artifacts(id, tenant_id, task_id, stage_id, worker_id, name, type, mime_type, "
        "location, storage, size, checksum, retention, visibility, provenance, metadata, created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (aid, tenant_id, task_id, stage_id, worker_id, name, kind, mime, location, storage,
         size, checksum, "default", visibility,
         json.dumps(provenance or {}), json.dumps(metadata or {}), time.time()))
    return aid
