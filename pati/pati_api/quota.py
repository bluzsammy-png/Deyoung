"""Quota manager: GPU minutes, task rates, artifact storage, concurrency.

Usage counters are per tenant per day. Quota exhaustion routes tasks to
WAITING_FOR_RESOURCE instead of failing, and never triggers paid fallbacks.
"""
from __future__ import annotations

import json
import time
from typing import Optional

from . import config, db

_DAY = time.strftime("%Y-%m-%d", time.gmtime())


def _day() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime())


def get_quotas(tenant_id: str) -> dict:
    rows = db.query("SELECT key, value FROM quotas WHERE tenant_id=?", (tenant_id,))
    quotas = dict(config.QUOTA_DEFAULTS)
    for r in rows:
        quotas[r["key"]] = json.loads(r["value"])
    usage = {}
    for r in db.query("SELECT key, value FROM usage_counters WHERE tenant_id=? AND day=?",
                      (tenant_id, _day())):
        usage[r["key"]] = r["value"]
    return {"tenant_id": tenant_id, "quotas": quotas, "usage_today": usage,
            "policy": {k: v for k, v in config.POLICY.items()}}


def set_quota(tenant_id: str, key: str, value) -> None:
    db.execute(
        "INSERT INTO quotas(tenant_id, key, value, updated_at) VALUES (?,?,?,?) "
        "ON CONFLICT(tenant_id, key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
        (tenant_id, key, json.dumps(value), time.time()),
    )


def consume(tenant_id: str, key: str, amount: float = 1) -> None:
    db.execute(
        "INSERT INTO usage_counters(tenant_id, key, day, value) VALUES (?,?,?,?) "
        "ON CONFLICT(tenant_id, key, day) DO UPDATE SET value=value+?",
        (tenant_id, key, _day(), amount, amount),
    )


def usage(tenant_id: str, key: str) -> float:
    row = db.query_one(
        "SELECT value FROM usage_counters WHERE tenant_id=? AND key=? AND day=?",
        (tenant_id, key, _day()),
    )
    return float(row["value"]) if row else 0.0


def check(tenant_id: str, key: str, amount: float = 1) -> bool:
    q = get_quotas(tenant_id)["quotas"]
    limit = q.get(key)
    if limit is None:
        return True
    return usage(tenant_id, key) + amount <= float(limit)


def gpu_minutes_remaining(tenant_id: str) -> float:
    q = get_quotas(tenant_id)["quotas"]
    limit = float(q.get("gpu_minutes_per_day", 0))
    return max(0.0, limit - usage(tenant_id, "gpu_minutes"))
