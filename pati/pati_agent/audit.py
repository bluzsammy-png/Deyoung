"""Hash-chained audit log (tamper-evident JSONL) on the Local Agent.

Each record: {ts, actor, action, resource, detail, prev_hash, hash}
hash = sha256(prev_hash + canonical_json(record_without_hash_fields))
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from pathlib import Path


class AuditLog:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._prev_hash = self._load_last_hash()

    def _load_last_hash(self) -> str:
        if not self.path.exists():
            return "0" * 64
        last = "0" * 64
        with open(self.path, "rb") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    last = rec.get("hash", last)
                except json.JSONDecodeError:
                    continue
        return last

    def append(self, action: str, resource: str, detail: dict | None = None,
               actor: str = "local-agent") -> dict:
        with self._lock:
            record = {
                "ts": time.time(), "actor": actor, "action": action,
                "resource": resource, "detail": detail or {},
            }
            payload = json.dumps(record, sort_keys=True, default=str)
            h = hashlib.sha256((self._prev_hash + payload).encode()).hexdigest()
            record["prev_hash"] = self._prev_hash
            record["hash"] = h
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, default=str) + "\n")
                try:
                    fh.flush()
                    os.fsync(fh.fileno())
                except OSError:
                    pass
            self._prev_hash = h
            return record

    def tail(self, n: int = 50) -> list[dict]:
        if not self.path.exists():
            return []
        with open(self.path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()[-n:]
        out = []
        for line in lines:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def verify(self) -> tuple[bool, int]:
        """Recompute the chain; returns (ok, records_checked)."""
        prev = "0" * 64
        checked = 0
        for rec in self.tail(10_000_000):
            expected = {k: rec[k] for k in ("ts", "actor", "action", "resource", "detail")}
            payload = json.dumps(expected, sort_keys=True, default=str)
            h = hashlib.sha256((prev + payload).encode()).hexdigest()
            if rec.get("prev_hash") != prev or rec.get("hash") != h:
                return False, checked
            prev = rec["hash"]
            checked += 1
        return True, checked
