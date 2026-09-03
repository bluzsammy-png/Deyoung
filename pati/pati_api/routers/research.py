"""Research endpoints: submit research objectives as first-class tasks."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from .. import db, orchestrator, security

router = APIRouter()


@router.post("/research", status_code=202)
def submit_research(body: dict, ctx: security.AuthCtx = Depends(security.require("research:submit"))):
    query = str(body.get("query") or "").strip()
    if not query:
        raise HTTPException(422, "query is required")
    params = {
        "mode": body.get("mode", "local_corpus"),   # web|local_corpus
        "save_to": body.get("save_to"),
        "root": body.get("root"),
    }
    task = orchestrator.create_task(
        objective=query, task_type="research", params=params,
        constraints=body.get("constraints") or {}, title=f"Research: {query[:60]}",
        tenant_id=ctx.tenant_id, user_id=ctx.user_id)
    return task


@router.get("/research/{task_id}")
def get_research(task_id: str, ctx: security.AuthCtx = Depends(security.require("tasks:read"))):
    t = orchestrator.get_task(task_id)
    if not t or t["tenant_id"] != ctx.tenant_id or t["type"] != "research":
        raise HTTPException(404, "research task not found")
    return t
