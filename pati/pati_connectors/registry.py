"""Connector registry: install/authorize/health/dispatch, persisted in DB."""
from __future__ import annotations

import json
import time

from pati_api import db
from .manifest import adapter_for, catalog


def catalog_specs() -> list[dict]:
    return catalog()


def install(tenant_id: str, name: str, config: dict) -> dict:
    adapter = adapter_for(name)
    if adapter is None:
        raise KeyError(name)
    spec = adapter.spec
    if spec.default_status == "planned":
        raise ValueError(f"connector '{name}' is planned but not implemented yet")
    clean = adapter().install(config)
    db.execute(
        "INSERT INTO connectors(name, tenant_id, version, status, config, installed_at) "
        "VALUES (?,?,?,?,?,?) ON CONFLICT(name) DO UPDATE SET status=excluded.status, "
        "config=excluded.config, installed_at=excluded.installed_at",
        (name, tenant_id, spec.version, "installed", json.dumps(clean), time.time()))
    return clean


def uninstall(tenant_id: str, name: str) -> None:
    db.execute("DELETE FROM connectors WHERE name=? AND tenant_id=?", (name, tenant_id))


def _get(tenant_id: str, name: str) -> dict:
    row = db.query_one("SELECT * FROM connectors WHERE name=? AND tenant_id=?", (name, tenant_id))
    if not row:
        raise KeyError(name)
    return row


def authorize(tenant_id: str, name: str, body: dict) -> dict:
    adapter = adapter_for(name)
    if adapter is None:
        raise KeyError(name)
    row = _get(tenant_id, name)
    return adapter().authorize(json.loads(row["config"] or "{}"))


def health_check(name: str) -> dict:
    adapter = adapter_for(name)
    if adapter is None:
        raise KeyError(name)
    return adapter().health_check()


def call_op(tenant_id: str, name: str, op: str, payload: dict) -> dict:
    adapter = adapter_for(name)
    if adapter is None:
        raise KeyError(name)
    row = _get(tenant_id, name)
    config = json.loads(row["config"] or "{}")
    return adapter().call(op, payload, config)
