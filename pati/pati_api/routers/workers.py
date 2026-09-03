"""Worker endpoints: register (pairing), heartbeat, job pull (long-poll),
status/logs/complete, shutdown, audit reporting.

Security model:
- Workers authenticate with a worker token bound to their worker_id.
- A worker can only see and complete its own jobs.
- The Local Agent is just one worker type; remote free workers (e.g. Kaggle)
  use the same interface. PATI remains the controller.
"""
from __future__ import annotations

import asyncio
import json
import time

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from .. import config, db, ids, orchestrator, security

router = APIRouter()


def _new_worker(tenant_id: str, name: str, wtype: str, capabilities: list[str],
                machine: dict = None) -> dict:
    wid = ids.worker_id()
    db.execute(
        "INSERT INTO workers(id, tenant_id, name, type, capabilities, status, machine, "
        "last_heartbeat, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (wid, tenant_id, name, wtype, json.dumps(capabilities), "online",
         json.dumps(machine or {}), time.time(), time.time()))
    orchestrator.audit("api", "worker.register", wid, {"name": name, "type": wtype})
    return db.query_one("SELECT * FROM workers WHERE id=?", (wid,))


@router.post("/workers/register")
def register_worker(body: dict, request: Request):
    """Register a worker.

    Two paths:
    - pairing_code: NO prior token needed. A one-time code (issued by the
      admin via `pati admin-pair`) is exchanged for a worker token.
    - authenticated admin/client token: direct registration.
    """
    name = str(body.get("name") or "").strip() or "unnamed-worker"
    wtype = str(body.get("type") or "LOCAL_WORKER")
    capabilities = list(body.get("capabilities") or [])
    machine = body.get("machine") or {}

    if body.get("pairing_code"):
        tenant_id = security.redeem_pairing_code(str(body["pairing_code"]))
        if not tenant_id:
            raise HTTPException(401, "invalid or expired pairing code")
        worker = _new_worker(tenant_id, name, wtype, capabilities, machine)
        _, token = security.create_token(f"worker:{name}", security.WORKER, tenant_id,
                                         worker_id=worker["id"])
        return {"worker_id": worker["id"], "token": token,
                "heartbeat_interval_s": config.HEARTBEAT_INTERVAL_S}

    # non-pairing registration requires an authenticated caller
    from fastapi import Request as _Req
    header = (request.headers if request else {}).get("Authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(401, "missing bearer token (or provide pairing_code)")
    ctx = security.auth(request)
    if not (ctx.has("workers:manage") or ctx.has("workers:register") or ctx.kind == "worker"):
        raise HTTPException(403, "not allowed to register workers")

    worker = _new_worker(ctx.tenant_id, name, wtype, capabilities, machine)
    _, token = security.create_token(f"worker:{name}", security.WORKER, ctx.tenant_id,
                                     worker_id=worker["id"])
    return {"worker_id": worker["id"], "token": token,
            "heartbeat_interval_s": config.HEARTBEAT_INTERVAL_S}


def _get_worker(worker_id: str) -> dict:
    w = db.query_one("SELECT * FROM workers WHERE id=?", (worker_id,))
    if not w:
        raise HTTPException(404, "worker not found")
    return w


@router.post("/workers/{worker_id}/heartbeat")
def heartbeat(worker_id: str, body: dict,
              ctx: security.AuthCtx = Depends(security.require())):
    security.require_worker_self(ctx, worker_id)
    _get_worker(worker_id)
    caps = body.get("capabilities")
    if caps is not None:
        db.execute("UPDATE workers SET capabilities=? WHERE id=?",
                   (json.dumps(list(caps)), worker_id))
    db.execute("UPDATE workers SET status='online', last_heartbeat=?, resources=?, health=COALESCE(?, health) WHERE id=?",
               (time.time(), json.dumps(body.get("resources") or {}),
                body.get("health"), worker_id))
    return {"ok": True, "server_time": time.time()}


@router.get("/workers/{worker_id}/jobs/next")
async def next_job(worker_id: str, wait: float = 0,
                   ctx: security.AuthCtx = Depends(security.require())):
    security.require_worker_self(ctx, worker_id)
    _get_worker(worker_id)
    wait = min(max(0.0, wait), float(config.LONGPOLL_MAX_S))
    job = await asyncio.to_thread(orchestrator.claim_job, {"id": worker_id}, wait)
    if job is None:
        return {"job": None}
    return {"job": job}


@router.post("/workers/{worker_id}/jobs/{job_id}/status")
def job_status(worker_id: str, job_id: str, body: dict,
               ctx: security.AuthCtx = Depends(security.require())):
    security.require_worker_self(ctx, worker_id)
    stage = db.query_one("SELECT * FROM stages WHERE job_id=? AND worker_id=?", (job_id, worker_id))
    if not stage:
        raise HTTPException(404, "unknown job for this worker")
    status = str(body.get("status") or "RUNNING")
    if status not in ("RUNNING",):
        raise HTTPException(400, "use /complete for terminal states")
    db.execute("UPDATE stages SET status='RUNNING' WHERE id=?", (stage["id"],))
    for entry in body.get("logs") or []:
        orchestrator.log_line(stage["task_id"], str(entry.get("message", "")),
                              level=str(entry.get("level", "info")), stage_id=stage["id"],
                              worker_id=worker_id)
    return {"ok": True}


@router.post("/workers/{worker_id}/jobs/{job_id}/logs")
def job_logs(worker_id: str, job_id: str, body: dict,
             ctx: security.AuthCtx = Depends(security.require())):
    security.require_worker_self(ctx, worker_id)
    stage = db.query_one("SELECT * FROM stages WHERE job_id=? AND worker_id=?", (job_id, worker_id))
    if not stage:
        raise HTTPException(404, "unknown job for this worker")
    for entry in body.get("logs") or []:
        orchestrator.log_line(stage["task_id"], str(entry.get("message", "")),
                              level=str(entry.get("level", "info")), stage_id=stage["id"],
                              worker_id=worker_id)
    return {"ok": True}


@router.post("/workers/{worker_id}/jobs/{job_id}/complete")
async def complete_job(worker_id: str, job_id: str,
                       status: str = Form(...),
                       result: str = Form("{}"),
                       error: str = Form(""),
                       error_code: str = Form(""),
                       artifacts_meta: str = Form("[]"),
                       files: list[UploadFile] = File([]),
                       ctx: security.AuthCtx = Depends(security.require("artifacts:write"))):
    """Complete a job. Artifacts can be uploaded inline (multipart files) or
    declared as local references (Local Agent keeps the bytes on-disk)."""
    security.require_worker_self(ctx, worker_id)
    stage = db.query_one("SELECT * FROM stages WHERE job_id=? AND worker_id=?", (job_id, worker_id))
    if not stage:
        raise HTTPException(404, "unknown job for this worker")
    task = db.query_one("SELECT tenant_id FROM tasks WHERE id=?", (stage["task_id"],))
    tenant_id = task["tenant_id"]
    meta = json.loads(artifacts_meta or "[]")
    try:
        result_obj = json.loads(result or "{}")
    except json.JSONDecodeError:
        result_obj = {"raw": result}

    uploaded_by_name = {f.filename: f for f in files or []}
    from .. import orchestrator as orch
    for m in meta:
        fname = m.get("file")
        if fname and fname in uploaded_by_name:
            uf = uploaded_by_name[fname]
            data = await uf.read()
            if len(data) > config.MAX_UPLOAD_MB * 1024 * 1024:
                raise HTTPException(413, "artifact exceeds max upload size")
            import hashlib
            checksum = hashlib.sha256(data).hexdigest()
            from ..artifacts_store import save_bytes  # local helper
            path = save_bytes(data, checksum)
            aid = orch.add_worker_artifact(
                tenant_id, stage["task_id"], stage["id"], worker_id,
                m.get("name") or fname, m.get("type") or "file",
                m.get("mime") or uf.content_type or "application/octet-stream",
                len(data), checksum, "control_plane", str(path),
                provenance={"worker_id": worker_id, "job_id": job_id},
                metadata=m.get("metadata") or {})
            result_obj.setdefault("artifact_ids", []).append(aid)
        elif m.get("path_ref"):
            import hashlib
            aid = orch.add_worker_artifact(
                tenant_id, stage["task_id"], stage["id"], worker_id,
                m.get("name") or "local-file", m.get("type") or "file",
                m.get("mime") or "application/octet-stream",
                int(m.get("size") or 0), m.get("checksum") or "",
                "local_reference", m["path_ref"],
                provenance={"worker_id": worker_id, "job_id": job_id},
                metadata=m.get("metadata") or {})
            result_obj.setdefault("artifact_ids", []).append(aid)

    orch.complete_job(worker_id, job_id, status, result_obj, error, error_code)
    return {"ok": True}


@router.post("/workers/{worker_id}/shutdown")
def shutdown_worker(worker_id: str, ctx: security.AuthCtx = Depends(security.require())):
    security.require_worker_self(ctx, worker_id)
    db.execute("UPDATE workers SET status='offline' WHERE id=?", (worker_id,))
    orchestrator.audit(ctx.id, "worker.shutdown", worker_id, {})
    return {"ok": True}


@router.post("/workers/{worker_id}/audit")
def worker_audit(worker_id: str, body: dict,
                 ctx: security.AuthCtx = Depends(security.require())):
    """Local Agent pushes hash-chained audit events for the central trail."""
    security.require_worker_self(ctx, worker_id)
    for entry in (body.get("events") or [])[:100]:
        db.execute("INSERT INTO audit(ts, actor, action, resource, detail) VALUES (?,?,?,?,?)",
                   (entry.get("ts") or time.time(), f"worker:{worker_id}",
                    str(entry.get("action", "")), str(entry.get("resource", "")),
                    json.dumps(entry.get("detail") or {})))
    return {"ok": True}
