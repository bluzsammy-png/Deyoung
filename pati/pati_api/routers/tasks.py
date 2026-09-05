"""Task endpoints: submit, inspect, cancel, logs, artifacts."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request

from .. import config, db, orchestrator, security

router = APIRouter()


@router.post("/tasks", status_code=202)
async def create_task(body: dict, request: Request,
                      ctx: security.AuthCtx = Depends(security.require("tasks:write"))):
    objective = str(body.get("objective") or "").strip()
    task_type = str(body.get("type") or "auto")
    params = body.get("params") or {}
    constraints = body.get("constraints") or {}
    title = body.get("title")
    if not objective and not params:
        raise HTTPException(422, "objective is required")
    # allow the api client to dispatch pending stages promptly
    try:
        task = orchestrator.create_task(
            objective=objective, task_type=task_type, params=params,
            constraints=constraints, title=title, tenant_id=ctx.tenant_id,
            user_id=ctx.user_id, parent_task_id=body.get("parent_task_id"),
            priority=str(body.get("priority") or "normal"))
    except RuntimeError as e:
        code = str(e).split(":")[-1]
        raise HTTPException(429, f"quota exceeded: {code}")
    asyncio.get_running_loop().run_in_executor(None, orchestrator.dispatch_scan)
    return task


@router.get("/tasks")
def list_tasks(status: str = "", limit: int = 50,
               ctx: security.AuthCtx = Depends(security.require("tasks:read"))):
    if status:
        rows = db.query("SELECT id, title, type, status, created_at, completed_at FROM tasks "
                        "WHERE tenant_id=? AND status=? ORDER BY created_at DESC LIMIT ?",
                        (ctx.tenant_id, status, min(limit, 200)))
    else:
        rows = db.query("SELECT id, title, type, status, created_at, completed_at FROM tasks "
                        "WHERE tenant_id=? ORDER BY created_at DESC LIMIT ?", (ctx.tenant_id, min(limit, 200)))
    return {"tasks": rows}


@router.get("/tasks/{task_id}")
def get_task(task_id: str, ctx: security.AuthCtx = Depends(security.require("tasks:read"))):
    t = orchestrator.get_task(task_id)
    if not t or t["tenant_id"] != ctx.tenant_id:
        raise HTTPException(404, "task not found")
    return t


@router.post("/tasks/{task_id}/cancel")
def cancel_task(task_id: str, ctx: security.AuthCtx = Depends(security.require("tasks:write"))):
    t = orchestrator.get_task(task_id)
    if not t or t["tenant_id"] != ctx.tenant_id:
        raise HTTPException(404, "task not found")
    return orchestrator.cancel_task(task_id)


@router.get("/tasks/{task_id}/logs")
def task_logs(task_id: str, since: int = 0,
              ctx: security.AuthCtx = Depends(security.require("tasks:read"))):
    t = orchestrator.get_task(task_id)
    if not t or t["tenant_id"] != ctx.tenant_id:
        raise HTTPException(404, "task not found")
    return orchestrator.task_logs(task_id, since)


@router.get("/tasks/{task_id}/artifacts")
def task_artifacts(task_id: str, ctx: security.AuthCtx = Depends(security.require("tasks:read"))):
    t = orchestrator.get_task(task_id)
    if not t or t["tenant_id"] != ctx.tenant_id:
        raise HTTPException(404, "task not found")
    rows = db.query("SELECT id, name, type, mime_type, size, checksum, storage, location, "
                    "created_at FROM artifacts WHERE task_id=?", (task_id,))
    return {"artifacts": rows}
