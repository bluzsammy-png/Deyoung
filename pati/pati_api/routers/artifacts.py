"""Artifact endpoints: direct upload (clients), metadata, content download."""
from __future__ import annotations

import hashlib
import json
import time

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from .. import config, db, orchestrator, security
from ..artifacts_store import open_blob, save_bytes

router = APIRouter()


@router.post("/artifacts", status_code=201)
async def upload_artifact(task_id: str = Form(""), name: str = Form(...),
                          type: str = Form("file"), mime: str = Form(""),
                          provenance: str = Form("{}"),
                          file: UploadFile = File(...),
                          ctx: security.AuthCtx = Depends(security.require("artifacts:write"))):
    data = await file.read()
    if len(data) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, "artifact exceeds max upload size")
    if task_id:
        t = db.query_one("SELECT tenant_id FROM tasks WHERE id=?", (task_id,))
        if not t:
            raise HTTPException(404, "task not found")
        tenant_id = t["tenant_id"]
    else:
        tenant_id = ctx.tenant_id
    checksum = hashlib.sha256(data).hexdigest()
    path = save_bytes(data, checksum)
    aid = orchestrator.add_worker_artifact(
        tenant_id, task_id or None, None, None, name, type,
        mime or file.content_type or "application/octet-stream", len(data),
        checksum, "control_plane", str(path),
        provenance=json.loads(provenance or "{}") | {"uploaded_by": ctx.id})
    return {"artifact_id": aid, "size": len(data), "checksum": checksum}


@router.get("/artifacts")
def list_artifacts(task_id: str = "", ctx: security.AuthCtx = Depends(security.require("artifacts:read"))):
    if task_id:
        rows = db.query("SELECT id, task_id, name, type, mime_type, size, checksum, storage, "
                        "location, created_at FROM artifacts WHERE task_id=?", (task_id,))
    else:
        rows = db.query("SELECT id, task_id, name, type, mime_type, size, checksum, storage, "
                        "location, created_at FROM artifacts WHERE tenant_id=? ORDER BY created_at DESC LIMIT 200",
                        (ctx.tenant_id,))
    return {"artifacts": rows}


@router.get("/artifacts/{artifact_id}")
def artifact_meta(artifact_id: str, ctx: security.AuthCtx = Depends(security.require("artifacts:read"))):
    a = db.query_one("SELECT * FROM artifacts WHERE id=?", (artifact_id,))
    if not a or a["tenant_id"] != ctx.tenant_id:
        raise HTTPException(404, "artifact not found")
    a = dict(a)
    a["provenance"] = json.loads(a["provenance"] or "{}")
    a["metadata"] = json.loads(a["metadata"] or "{}")
    return a


@router.get("/artifacts/{artifact_id}/content")
def artifact_content(artifact_id: str, ctx: security.AuthCtx = Depends(security.require("artifacts:read"))):
    a = db.query_one("SELECT * FROM artifacts WHERE id=?", (artifact_id,))
    if not a or a["tenant_id"] != ctx.tenant_id:
        raise HTTPException(404, "artifact not found")
    if a["storage"] == "local_reference":
        raise HTTPException(409, detail={
            "error": "LOCAL_REFERENCE",
            "message": "bytes live on the Local Agent machine; use artifact.save via a task "
                       "or read from the authorized path",
            "path": a["location"], "worker_id": a["worker_id"], "checksum": a["checksum"]})
    blob = open_blob(a["checksum"])
    if not blob:
        raise HTTPException(410, "artifact bytes missing from store")
    return FileResponse(str(blob), media_type=a["mime_type"] or "application/octet-stream",
                        filename=a["name"])


@router.delete("/artifacts/{artifact_id}")
def delete_artifact(artifact_id: str, ctx: security.AuthCtx = Depends(security.require("admin:tokens"))):
    a = db.query_one("SELECT * FROM artifacts WHERE id=?", (artifact_id,))
    if not a:
        raise HTTPException(404, "artifact not found")
    db.execute("DELETE FROM artifacts WHERE id=?", (artifact_id,))
    orchestrator.audit(ctx.id, "artifact.delete", artifact_id, {})
    return {"ok": True}
