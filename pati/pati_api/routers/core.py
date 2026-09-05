"""Core read-only API: health, version, registries, quotas, system status."""
from __future__ import annotations

import platform
import time

from fastapi import APIRouter, Depends, HTTPException, Request

from .. import __version__, config, db, orchestrator, quota, registries, security

router = APIRouter()

_START_TIME = time.time()


@router.get("/health")
def health():
    return {
        "status": "ok", "service": "pati-control-plane", "version": __version__,
        "uptime_s": round(time.time() - _START_TIME, 1),
        "free_only": config.POLICY["FREE_ONLY"], "max_spend": 0,
    }


@router.get("/version")
def version():
    return {"version": __version__, "api": config.API_VERSION_TAG}


@router.get("/capabilities")
def capabilities(ctx: security.AuthCtx = Depends(security.require("system:read"))):
    return {"capabilities": registries.enforce_free_only(
        [dict(c, cost=0, free_status="FREE_FOREVER") for c in registries.merged_capabilities(ctx.tenant_id)])}


@router.get("/models")
def models(ctx: security.AuthCtx = Depends(security.require("system:read"))):
    return {"models": registries.enforce_free_only(registries.merged_models(ctx.tenant_id))}


@router.get("/tools")
def tools(ctx: security.AuthCtx = Depends(security.require("system:read"))):
    return {"tools": registries.enforce_free_only(
        [dict(t, cost=0) for t in registries.merged_tools(ctx.tenant_id)])}


@router.get("/tools/discover")
def tools_discover(q: str = "", ctx: security.AuthCtx = Depends(security.require("tools:read"))):
    """Lightweight discovery over the registry (external discovery lands in Phase 15)."""
    ql = q.lower()
    hits = [t for t in registries.merged_tools(ctx.tenant_id)
            if ql in t["tool_id"].lower() or ql in t["name"].lower()
            or any(ql in c for c in t["capabilities"])]
    return {"query": q, "results": registries.enforce_free_only([dict(t, cost=0) for t in hits])}


@router.post("/tools/install")
def tools_install(body: dict, ctx: security.AuthCtx = Depends(security.require("tools:manage"))):
    tool_id = str(body.get("tool_id", ""))
    tool = next((t for t in registries.merged_tools(ctx.tenant_id) if t["tool_id"] == tool_id), None)
    if not tool:
        raise HTTPException(404, "tool not found")
    if tool["status"] not in ("active", "available_when_configured", "available_when_docker_present"):
        raise HTTPException(400, f"tool not installable in current state: {tool['status']}")
    db.execute("INSERT INTO installed_tools(tool_id, version, status, installed_at) VALUES (?,?,?,?) "
               "ON CONFLICT(tool_id) DO UPDATE SET status=excluded.status, installed_at=excluded.installed_at",
               (tool_id, tool["version"], "installed", time.time()))
    orchestrator.audit(ctx.id, "tool.install", tool_id, {"status": "installed"})
    return {"ok": True, "tool_id": tool_id, "status": "installed"}


@router.get("/workers")
def list_workers(ctx: security.AuthCtx = Depends(security.require("workers:read"))):
    rows = db.query("SELECT id, name, type, capabilities, status, health, resources, "
                    "machine, last_heartbeat, failure_count, created_at FROM workers "
                    "WHERE tenant_id=? ORDER BY created_at", (ctx.tenant_id,))
    return {"workers": rows}


@router.get("/quotas")
def quotas(ctx: security.AuthCtx = Depends(security.require("quotas:read"))):
    return quota.get_quotas(ctx.tenant_id)


@router.get("/system/status")
def system_status(ctx: security.AuthCtx = Depends(security.require("system:read"))):
    workers = db.query("SELECT status, COUNT(*) c FROM workers WHERE tenant_id=? GROUP BY status",
                       (ctx.tenant_id,))
    tasks = db.query("SELECT status, COUNT(*) c FROM tasks WHERE tenant_id=? GROUP BY status",
                     (ctx.tenant_id,))
    return {
        "service": "pati-control-plane", "version": __version__,
        "api": config.API_VERSION_TAG, "python": platform.python_version(),
        "platform": platform.platform(),
        "uptime_s": round(time.time() - _START_TIME, 1),
        "workers": {r["status"]: r["c"] for r in workers},
        "tasks": {r["status"]: r["c"] for r in tasks},
        "policy": config.POLICY,
        "data_dir": str(config.DATA_DIR),
    }


@router.get("/system/events")
def system_events(limit: int = 100, ctx: security.AuthCtx = Depends(security.require("events:read"))):
    return {"events": db.query("SELECT * FROM events ORDER BY ts DESC LIMIT ?", (min(limit, 500),))}


@router.get("/system/updates")
def system_updates(ctx: security.AuthCtx = Depends(security.require("system:read"))):
    """Update manifest for the Local Agent updater. $0: updates ship from this
    server itself or from PyPI/GitHub releases; never paid channels."""
    return {
        "channel": "stable", "current_version": __version__,
        "latest_version": __version__,
        "method": "pip install --upgrade pati (from PyPI or local wheel)",
        "notes": "PATI updates are distributed through free channels only.",
    }
