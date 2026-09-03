"""Prefixed ID helpers for PATI entities."""
from __future__ import annotations

import uuid

def _pid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:20]}"

def task_id() -> str: return _pid("task")
def stage_id() -> str: return _pid("stg")
def job_id() -> str: return _pid("job")
def worker_id() -> str: return _pid("wrk")
def artifact_id() -> str: return _pid("art")
def token_id() -> str: return _pid("tok")
def tenant_id() -> str: return _pid("ten")
def user_id() -> str: return _pid("usr")
def event_id() -> str: return _pid("evt")
def benchmark_id() -> str: return _pid("bm")
def trace_id() -> str: return uuid.uuid4().hex
