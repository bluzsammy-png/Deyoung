"""Connector endpoints: catalog, install, authorize, health, delete, dispatch ops."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException

from .. import db, orchestrator, security

router = APIRouter()


def _registry():
    from pati_connectors import registry as creg
    return creg


@router.get("/connectors")
def list_connectors(ctx: security.AuthCtx = Depends(security.require("system:read"))):
    reg = _registry()
    installed = {r["name"]: r for r in db.query(
        "SELECT * FROM connectors WHERE tenant_id=?", (ctx.tenant_id,))}
    out = []
    for spec in reg.catalog():
        row = installed.get(spec["name"])
        out.append({
            "name": spec["name"], "version": spec["version"],
            "capabilities": spec["capabilities"], "auth": spec["auth"],
            "scopes": spec["scopes"], "rate_limits": spec["rate_limits"],
            "security": spec["security"], "free_status": spec["free_status"],
            "license": spec["license"], "supported_operations": spec["supported_operations"],
            "status": row["status"] if row else spec.get("default_status", "available_for_install"),
            "installed_at": row["installed_at"] if row else None,
        })
    return {"connectors": out}


@router.post("/connectors/{name}/install")
def install_connector(name: str, body: dict,
                      ctx: security.AuthCtx = Depends(security.require("connectors:manage"))):
    reg = _registry()
    try:
        config_ = reg.install(ctx.tenant_id, name, body.get("config") or {})
    except KeyError:
        raise HTTPException(404, "connector not found")
    except ValueError as e:
        raise HTTPException(400, str(e))
    orchestrator.audit(ctx.id, "connector.install", name, {})
    return {"ok": True, "name": name, "status": "installed", "health": reg.health_check(name)}


@router.post("/connectors/{name}/authorize")
def authorize_connector(name: str, body: dict,
                        ctx: security.AuthCtx = Depends(security.require("connectors:manage"))):
    reg = _registry()
    try:
        return reg.authorize(ctx.tenant_id, name, body or {})
    except KeyError:
        raise HTTPException(404, "connector not found")
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/connectors/{name}/health")
def connector_health(name: str, ctx: security.AuthCtx = Depends(security.require("system:read"))):
    reg = _registry()
    try:
        return reg.health_check(name)
    except KeyError:
        raise HTTPException(404, "connector not found")


@router.post("/connectors/{name}/operations/{op}")
def connector_op(name: str, op: str, body: dict,
                 ctx: security.AuthCtx = Depends(security.require("connectors:manage"))):
    reg = _registry()
    try:
        return reg.call_op(ctx.tenant_id, name, op, body or {})
    except KeyError:
        raise HTTPException(404, "connector or operation not found")
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/connectors/{name}")
def remove_connector(name: str, ctx: security.AuthCtx = Depends(security.require("connectors:manage"))):
    reg = _registry()
    reg.uninstall(ctx.tenant_id, name)
    orchestrator.audit(ctx.id, "connector.remove", name, {})
    return {"ok": True}
