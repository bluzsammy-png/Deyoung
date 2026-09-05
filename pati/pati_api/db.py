"""SQLite persistence layer with ordered migrations (no paid database).

Single-file SQLite (public domain) keeps PATI $0 and portable. WAL mode is used
for concurrent readers. All JSON columns are stored as TEXT.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Optional

from . import config

_LOCK = threading.RLock()
_CONN: Optional[sqlite3.Connection] = None

MIGRATIONS: list[str] = [
    # 1 - core identity / tenancy
    """
    CREATE TABLE IF NOT EXISTS tenants(
      id TEXT PRIMARY KEY, name TEXT UNIQUE, created_at REAL
    );
    CREATE TABLE IF NOT EXISTS users(
      id TEXT PRIMARY KEY, tenant_id TEXT, name TEXT, role TEXT,
      created_at REAL, FOREIGN KEY(tenant_id) REFERENCES tenants(id)
    );
    CREATE TABLE IF NOT EXISTS tokens(
      id TEXT PRIMARY KEY, tenant_id TEXT, user_id TEXT, name TEXT,
      kind TEXT, scopes TEXT, token_hash TEXT UNIQUE, worker_id TEXT,
      created_at REAL, revoked INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS pairing_codes(
      code TEXT PRIMARY KEY, tenant_id TEXT, expires_at REAL, used INTEGER DEFAULT 0
    );
    """,
    # 2 - registries (DB overrides over code catalogs)
    """
    CREATE TABLE IF NOT EXISTS registered_capabilities(
      id TEXT PRIMARY KEY, category TEXT, description TEXT, risky INTEGER,
      min_level INTEGER, registered_at REAL
    );
    CREATE TABLE IF NOT EXISTS registered_models(
      model_id TEXT PRIMARY KEY, doc TEXT, registered_at REAL
    );
    CREATE TABLE IF NOT EXISTS registered_tools(
      tool_id TEXT PRIMARY KEY, doc TEXT, registered_at REAL
    );
    CREATE TABLE IF NOT EXISTS installed_tools(
      tool_id TEXT PRIMARY KEY, version TEXT, status TEXT, installed_at REAL
    );
    """,
    # 3 - workers / tasks / jobs / artifacts
    """
    CREATE TABLE IF NOT EXISTS workers(
      id TEXT PRIMARY KEY, tenant_id TEXT, name TEXT, type TEXT,
      capabilities TEXT, status TEXT, resources TEXT, machine TEXT,
      last_heartbeat REAL, created_at REAL, failure_count INTEGER DEFAULT 0,
      health TEXT DEFAULT 'healthy'
    );
    CREATE TABLE IF NOT EXISTS tasks(
      id TEXT PRIMARY KEY, tenant_id TEXT, user_id TEXT, parent_task_id TEXT,
      title TEXT, objective TEXT, type TEXT, capability TEXT,
      input TEXT, constraints TEXT, policy TEXT, plan TEXT,
      status TEXT, progress REAL DEFAULT 0, result TEXT, error TEXT,
      trace_id TEXT, retry_count INTEGER DEFAULT 0, cost REAL DEFAULT 0,
      priority TEXT DEFAULT 'normal',
      created_at REAL, started_at REAL, completed_at REAL, updated_at REAL
    );
    CREATE TABLE IF NOT EXISTS stages(
      id TEXT PRIMARY KEY, task_id TEXT, seq INTEGER, name TEXT,
      capability TEXT, tool TEXT, op TEXT, params TEXT,
      depends_on TEXT, group_id TEXT, status TEXT, worker_id TEXT,
      job_id TEXT, output TEXT, error TEXT, retry_count INTEGER DEFAULT 0,
      started_at REAL, finished_at REAL, deadline_at REAL
    );
    CREATE TABLE IF NOT EXISTS artifacts(
      id TEXT PRIMARY KEY, tenant_id TEXT, task_id TEXT, stage_id TEXT,
      worker_id TEXT, name TEXT, type TEXT, mime_type TEXT, location TEXT,
      storage TEXT, size INTEGER, checksum TEXT, retention TEXT,
      visibility TEXT, provenance TEXT, metadata TEXT, created_at REAL
    );
    CREATE TABLE IF NOT EXISTS logs(
      id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT, stage_id TEXT,
      worker_id TEXT, level TEXT, message TEXT, ts REAL
    );
    CREATE TABLE IF NOT EXISTS events(
      id TEXT PRIMARY KEY, tenant_id TEXT, type TEXT, resource TEXT,
      detail TEXT, trace_id TEXT, ts REAL
    );
    CREATE TABLE IF NOT EXISTS audit(
      id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, actor TEXT, action TEXT,
      resource TEXT, detail TEXT
    );
    CREATE TABLE IF NOT EXISTS policies(
      key TEXT PRIMARY KEY, value TEXT, updated_at REAL
    );
    CREATE TABLE IF NOT EXISTS quotas(
      tenant_id TEXT, key TEXT, value TEXT, updated_at REAL,
      PRIMARY KEY(tenant_id, key)
    );
    CREATE TABLE IF NOT EXISTS usage_counters(
      tenant_id TEXT, key TEXT, day TEXT, value REAL,
      PRIMARY KEY(tenant_id, key, day)
    );
    CREATE TABLE IF NOT EXISTS benchmarks(
      id TEXT PRIMARY KEY, target_kind TEXT, target_id TEXT, metrics TEXT,
      worker_id TEXT, created_at REAL
    );
    CREATE TABLE IF NOT EXISTS connectors(
      name TEXT PRIMARY KEY, tenant_id TEXT, version TEXT, status TEXT,
      config TEXT, installed_at REAL
    );
    CREATE TABLE IF NOT EXISTS health_checks(
      id INTEGER PRIMARY KEY AUTOINCREMENT, target TEXT, status TEXT,
      detail TEXT, ts REAL
    );
    CREATE TABLE IF NOT EXISTS deployments(
      id TEXT PRIMARY KEY, target TEXT, status TEXT, detail TEXT, ts REAL
    );
    CREATE TABLE IF NOT EXISTS secrets_metadata(
      id TEXT PRIMARY KEY, name TEXT, kind TEXT, scope TEXT, created_at REAL,
      note TEXT
    );
    CREATE TABLE IF NOT EXISTS kv(key TEXT PRIMARY KEY, value TEXT);
    CREATE INDEX IF NOT EXISTS idx_stages_task ON stages(task_id, seq);
    CREATE INDEX IF NOT EXISTS idx_logs_task ON logs(task_id, id);
    CREATE INDEX IF NOT EXISTS idx_artifacts_task ON artifacts(task_id);
    """,
]


def _connect() -> sqlite3.Connection:
    config.ensure_dirs()
    conn = sqlite3.connect(str(config.DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db() -> None:
    global _CONN
    with _LOCK:
        if _CONN is None:
            _CONN = _connect()
        cur = _CONN.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
        )
        version = 0
        if cur.fetchone() is not None:
            version = _CONN.execute("SELECT MAX(version) v FROM schema_version").fetchone()["v"] or 0
        for i, script in enumerate(MIGRATIONS, start=1):
            if i > version:
                _CONN.executescript(script)
                _CONN.execute("CREATE TABLE IF NOT EXISTS schema_version(version INTEGER PRIMARY KEY)")
                _CONN.execute("INSERT OR REPLACE INTO schema_version(version) VALUES (?)", (i,))
        _CONN.commit()
        _bootstrap(_CONN)


def _bootstrap(conn: sqlite3.Connection) -> None:
    now = time.time()
    if conn.execute("SELECT COUNT(*) c FROM tenants").fetchone()["c"] == 0:
        conn.execute(
            "INSERT INTO tenants(id, name, created_at) VALUES (?,?,?)",
            (config.DEFAULT_TENANT, "local", now),
        )
        conn.execute(
            "INSERT INTO users(id, tenant_id, name, role, created_at) VALUES (?,?,?,?,?)",
            ("usr_owner", config.DEFAULT_TENANT, config.DEFAULT_ADMIN_USER, "admin", now),
        )
    conn.commit()


def reset_db() -> None:
    """Test helper: wipe database file."""
    global _CONN
    with _LOCK:
        if _CONN is not None:
            _CONN.close()
            _CONN = None
        if config.DB_PATH.exists():
            config.DB_PATH.unlink()
        for suffix in ("-wal", "-shm"):
            p = Path(str(config.DB_PATH) + suffix)
            if p.exists():
                p.unlink()


@contextmanager
def tx():
    """Yield the shared connection inside a transaction lock."""
    with _LOCK:
        assert _CONN is not None, "init_db() not called"
        try:
            yield _CONN
            _CONN.commit()
        except Exception:
            _CONN.rollback()
            raise


def execute(sql: str, params: Iterable[Any] = ()) -> None:
    with tx() as conn:
        conn.execute(sql, tuple(params))


def executemany(sql: str, seq: Iterable[Iterable[Any]]) -> None:
    with tx() as conn:
        conn.executemany(sql, [tuple(p) for p in seq])


def query(sql: str, params: Iterable[Any] = ()) -> list[dict]:
    with _LOCK:
        assert _CONN is not None, "init_db() not called"
        rows = _CONN.execute(sql, tuple(params)).fetchall()
    return [dict(r) for r in rows]


def query_one(sql: str, params: Iterable[Any] = ()) -> Optional[dict]:
    rows = query(sql, params)
    return rows[0] if rows else None


def kv_get(key: str, default: Any = None) -> Any:
    row = query_one("SELECT value FROM kv WHERE key=?", (key,))
    if row is None:
        return default
    return json.loads(row["value"])


def kv_set(key: str, value: Any) -> None:
    execute(
        "INSERT INTO kv(key, value) VALUES (?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, json.dumps(value)),
    )
