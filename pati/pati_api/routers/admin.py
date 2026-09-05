"""Admin endpoints: tokens, pairing codes, policies, tenants/users, audit.

All admin endpoints require the 'admin' scope (bootstrap admin token).
"""
from __future__ import annotations

import json
import time

from fastapi import APIRouter, Depends, HTTPException

from .. import config, db, orchestrator, security

router = APIRouter()


def _require_admin(ctx: security.AuthCtx):
    if not ctx.has("admin"):
        raise HTTPException(403, "admin scope required")
    return ctx


@router.get("/admin/tokens")
def list_tokens(ctx: security.AuthCtx = Depends(security.require())):
    _require_admin(ctx)
    rows = db.query("SELECT id, name, kind, scopes, worker_id, created_at, revoked FROM tokens")
    return {"tokens": rows}


@router.post("/admin/tokens", status_code=201)
def create_token(body: dict, ctx: security.AuthCtx = Depends(security.require())):
    _require_admin(ctx)
    name = str(body.get("name") or "token")
    kind = str(body.get("kind") or "client")
    if kind not in (security.ADMIN, security.CLIENT, security.WORKER):
        raise HTTPException(422, "kind must be admin|client|worker")
    scopes = body.get("scopes")
    if scopes is not None:
        bad = set(scopes) - security.SCOPES
        if bad:
            raise HTTPException(422, f"unknown scopes: {sorted(bad)}")
    row, token = security.create_token(name, kind, ctx.tenant_id, scopes=scopes,
                                       worker_id=body.get("worker_id"))
    orchestrator.audit(ctx.id, "token.create", row["id"], {"kind": kind, "name": name})
    return {"token": token, "id": row["id"], "kind": kind, "scopes": row["scopes"]}


@router.post("/admin/tokens/{token_id}/revoke")
def revoke_token(token_id: str, ctx: security.AuthCtx = Depends(security.require())):
    _require_admin(ctx)
    db.execute("UPDATE tokens SET revoked=1 WHERE id=?", (token_id,))
    orchestrator.audit(ctx.id, "token.revoke", token_id, {})
    return {"ok": True}


@router.post("/admin/pairing-codes", status_code=201)
def new_pairing_code(body: dict, ctx: security.AuthCtx = Depends(security.require())):
    """Issue a one-time code so a new computer/worker can register securely."""
    _require_admin(ctx)
    return security.issue_pairing_code(ctx.tenant_id, int(body.get("ttl_s", 900)))


@router.get("/admin/audit")
def read_audit(limit: int = 200, ctx: security.AuthCtx = Depends(security.require())):
    _require_admin(ctx)
    return {"audit": db.query("SELECT * FROM audit ORDER BY id DESC LIMIT ?", (min(limit, 1000),))}


@router.get("/admin/policies")
def get_policies(ctx: security.AuthCtx = Depends(security.require())):
    _require_admin(ctx)
    rows = db.query("SELECT key, value, updated_at FROM policies")
    return {"policies": {r["key"]: {"value": json.loads(r["value"]), "updated_at": r["updated_at"]} for r in rows},
            "system_policy": config.POLICY}


@router.put("/admin/policies/{key}")
def set_policy(key: str, body: dict, ctx: security.AuthCtx = Depends(security.require())):
    _require_admin(ctx)
    if key in config.POLICY and config.POLICY[key] is True:
        raise HTTPException(400, f"policy {key} is a hard requirement and cannot be disabled")
    db.execute("INSERT INTO policies(key, value, updated_at) VALUES (?,?,?) "
               "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
               (key, json.dumps(body.get("value")), time.time()))
    orchestrator.audit(ctx.id, "policy.set", key, body)
    return {"ok": True}


@router.post("/admin/quotas/{key}")
def set_quota(key: str, body: dict, ctx: security.AuthCtx = Depends(security.require())):
    _require_admin(ctx)
    quota_mod = __import__("pati_api.quota", fromlist=["quota"])
    quota_mod.set_quota(ctx.tenant_id, key, body.get("value"))
    return {"ok": True}


@router.get("/admin/tenants")
def list_tenants(ctx: security.AuthCtx = Depends(security.require())):
    _require_admin(ctx)
    return {"tenants": db.query("SELECT * FROM tenants"),
            "users": db.query("SELECT id, tenant_id, name, role, created_at FROM users")}


@router.post("/admin/tenants", status_code=201)
def create_tenant(body: dict, ctx: security.AuthCtx = Depends(security.require())):
    _require_admin(ctx)
    name = str(body.get("name") or "").strip()
    if not name:
        raise HTTPException(422, "name required")
    tid = config.DEFAULT_TENANT if name == "local" else f"ten_{name.lower()}"
    db.execute("INSERT OR IGNORE INTO tenants(id, name, created_at) VALUES (?,?,?)",
               (tid, name, time.time()))
    uid = f"usr_{name.lower()}_admin"
    db.execute("INSERT OR IGNORE INTO users(id, tenant_id, name, role, created_at) VALUES (?,?,?,?,?)",
               (uid, tid, f"{name}-admin", "admin", time.time()))
    row, token = security.create_token(f"{name}-admin", security.ADMIN, tid, user_id=uid)
    orchestrator.audit(ctx.id, "tenant.create", tid, {"name": name})
    return {"tenant_id": tid, "admin_token": token}
