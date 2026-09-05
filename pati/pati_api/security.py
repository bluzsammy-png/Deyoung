"""Authentication, authorization (RBAC-style scopes), rate limiting.

- Bearer tokens, stored hashed (sha256), scoped, revocable, tenant-bound.
- Token kinds: admin, client, worker (bound to one worker id).
- Pairing codes allow a Local Agent / remote worker to obtain a worker token
  without exposing an admin token to the machine.
- Sliding-window rate limiter per token.
"""
from __future__ import annotations

import hashlib
import secrets
import threading
import time
from collections import defaultdict, deque
from typing import Optional

from fastapi import Depends, HTTPException, Request

from . import config, db, ids

ADMIN = "admin"
CLIENT = "client"
WORKER = "worker"

SCOPES = {
    "admin", "tasks:read", "tasks:write", "workers:read", "workers:register",
    "workers:manage", "artifacts:read", "artifacts:write", "research:submit",
    "tools:read", "tools:manage", "connectors:manage", "system:read",
    "quotas:read", "events:read", "admin:tokens",
}

ROLE_SCOPES = {
    ADMIN: sorted(SCOPES),
    CLIENT: ["tasks:read", "tasks:write", "artifacts:read", "research:submit",
             "tools:read", "system:read", "quotas:read", "workers:read", "events:read"],
    # Workers upload/download artifacts and report on their own jobs only
    WORKER: ["workers:register", "artifacts:write", "artifacts:read", "system:read"],
}

_rate_lock = threading.Lock()
_rate_buckets: dict[str, deque] = defaultdict(deque)


class PATIError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        self.code, self.message, self.status = code, message, status
        super().__init__(message)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def generate_token(kind: str) -> str:
    return f"pati_{kind}_{secrets.token_urlsafe(24)}"


def create_token(name: str, kind: str, tenant_id: str, scopes: Optional[list[str]] = None,
                 user_id: Optional[str] = None, worker_id: Optional[str] = None) -> tuple[dict, str]:
    token = generate_token(kind)
    tid = ids.token_id()
    scope_list = scopes if scopes is not None else ROLE_SCOPES.get(kind, ["system:read"])
    db.execute(
        "INSERT INTO tokens(id, tenant_id, user_id, name, kind, scopes, token_hash, worker_id, created_at)"
        " VALUES (?,?,?,?,?,?,?,?,?)",
        (tid, tenant_id, user_id, name, kind, " ".join(scope_list), hash_token(token), worker_id, time.time()),
    )
    row = db.query_one("SELECT * FROM tokens WHERE id=?", (tid,))
    return row, token


def bootstrap_admin_token() -> str:
    """Create (once) the initial admin token and store it file-protected."""
    existing = db.query_one("SELECT * FROM tokens WHERE kind='admin' AND revoked=0")
    if existing:
        return ""
    _, token = create_token("bootstrap-admin", ADMIN, config.DEFAULT_TENANT, user_id="usr_owner")
    config.ensure_dirs()
    p = config.BOOTSTRAP_TOKEN_FILE
    p.write_text(token)
    try:
        p.chmod(0o600)
    except OSError:
        pass
    db.execute(
        "INSERT INTO audit(ts, actor, action, resource, detail) VALUES (?,?,?,?,?)",
        (time.time(), "system", "bootstrap_admin_token", str(p), "initial admin token created"),
    )
    return token


def issue_pairing_code(tenant_id: str, ttl_s: int = 900) -> dict:
    code = f"{secrets.randbelow(1_000_000):06d}"
    expires = time.time() + ttl_s
    db.execute(
        "INSERT INTO pairing_codes(code, tenant_id, expires_at, used) VALUES (?,?,?,0)",
        (code, tenant_id, expires),
    )
    return {"code": code, "expires_at": expires}


def redeem_pairing_code(code: str) -> Optional[str]:
    row = db.query_one("SELECT * FROM pairing_codes WHERE code=?", (code,))
    if not row or row["used"] or row["expires_at"] < time.time():
        return None
    db.execute("UPDATE pairing_codes SET used=1 WHERE code=?", (code,))
    return row["tenant_id"]


class AuthCtx:
    def __init__(self, token_row: dict):
        self.id = token_row["id"]
        self.kind = token_row["kind"]
        self.tenant_id = token_row["tenant_id"]
        self.user_id = token_row["user_id"]
        self.worker_id = token_row["worker_id"]
        self.scopes = set((token_row["scopes"] or "").split())

    def has(self, scope: str) -> bool:
        return "admin" in self.scopes or scope in self.scopes


def _load_token(bearer: str) -> AuthCtx:
    row = db.query_one("SELECT * FROM tokens WHERE token_hash=? AND revoked=0", (hash_token(bearer),))
    if not row:
        raise HTTPException(status_code=401, detail="invalid or revoked token")
    return AuthCtx(row)


def auth(request: Request, scope: Optional[str] = None) -> AuthCtx:
    """FastAPI dependency. Also enforces per-token rate limits."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    ctx = _load_token(header[7:].strip())

    now = time.time()
    with _rate_lock:
        bucket = _rate_buckets[ctx.id]
        while bucket and now - bucket[0] > 60:
            bucket.popleft()
        if len(bucket) >= config.RATE_LIMIT_PER_MIN:
            raise HTTPException(status_code=429, detail="rate limit exceeded")
        bucket.append(now)

    if scope and not ctx.has(scope):
        raise HTTPException(status_code=403, detail=f"missing required scope: {scope}")
    return ctx


def require(scope: Optional[str] = None):
    def dep(request: Request) -> AuthCtx:
        return auth(request, scope)
    return dep


def require_worker_self(ctx: AuthCtx, worker_id: str) -> None:
    if ctx.kind != WORKER and not ctx.has("workers:manage"):
        raise HTTPException(status_code=403, detail="worker token required")
    if ctx.kind == WORKER and ctx.worker_id != worker_id:
        raise HTTPException(status_code=403, detail="token not bound to this worker")
