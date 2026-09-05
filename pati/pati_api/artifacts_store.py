"""Artifact storage: content-addressed files under the control plane data dir.

$0: the artifact store is the local filesystem. Remote free workers upload
bytes; the Local Agent may register local references instead (bytes stay on
the owner's disk). Checksums (sha256) enable dedup and integrity checks.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from . import config


def _blob_path(checksum: str) -> Path:
    return config.ARTIFACT_DIR / checksum[:2] / checksum


def save_bytes(data: bytes, checksum: str) -> Path:
    path = _blob_path(checksum)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(data)
        tmp.replace(path)
    return path


def save_file(src: Path, checksum: str) -> Path:
    path = _blob_path(checksum)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        shutil.copy2(src, path)
    return path


def open_blob(checksum: str) -> Path | None:
    p = _blob_path(checksum)
    return p if p.exists() else None
