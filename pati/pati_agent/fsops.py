"""Authorized filesystem operations with policy checks and audit trail."""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

from .policy import (CREATE_FILES, COPY_FILES, DELETE_FILES, MOVE_FILES,
                     READ_FILES, SAVE_ARTIFACTS, PolicyViolation)

CATEGORY_EXTENSIONS = {
    "scripts": [".txt", ".md", ".docx", ".doc", ".rtf", ".pdf"],
    "images": [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"],
    "audio": [".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"],
    "video": [".mp4", ".mov", ".mkv", ".avi", ".webm"],
    "data": [".json", ".csv", ".xlsx", ".parquet", ".db"],
}


class FSOperations:
    """Every method: 1) check permission  2) validate path  3) audit  4) execute."""

    def __init__(self, engine, audit_log):
        self.engine = engine
        self.audit = audit_log

    def _pre(self, action: str, permission, **detail) -> None:
        self.engine.require(permission)
        self.audit.append(action, resource=detail.get("path", ""), detail=detail)

    # ------------------------------------------------------------------ ops
    def list_dir(self, params: dict) -> dict:
        path = self.engine.validate_path(params["path"] or ".", params.get("root"))
        self._pre("fs.list", READ_FILES, path=str(path))
        if not path.exists():
            return {"exists": False, "entries": []}
        entries = []
        for p in sorted(path.iterdir()):
            entries.append({"name": p.name, "dir": p.is_dir(), "size": p.stat().st_size if p.is_file() else 0})
        return {"exists": True, "path": str(path), "entries": entries[:2000]}

    def read_file(self, params: dict) -> dict:
        path = self.engine.validate_path(params["path"], params.get("root"), must_exist=True)
        self._pre("fs.read", READ_FILES, path=str(path))
        limit = int(params.get("max_bytes", 1_000_000))
        data = path.read_bytes()[:limit]
        try:
            return {"path": str(path), "size": path.stat().st_size, "text": data.decode("utf-8", "replace")}
        except OSError as e:
            raise PolicyViolation(f"cannot read: {e}")

    def mkdir(self, params: dict) -> dict:
        path = self.engine.validate_path(params["path"], params.get("root"))
        self._pre("fs.mkdir", CREATE_FILES, path=str(path))
        path.mkdir(parents=True, exist_ok=params.get("exist_ok", True))
        self.audit.append("fs.mkdir.done", resource=str(path))
        return {"path": str(path), "created": True}

    def create_file(self, params: dict) -> dict:
        path = self.engine.validate_path(params["path"], params.get("root"))
        self._pre("fs.create_file", CREATE_FILES, path=str(path))
        content = params.get("content", "")
        mode = params.get("mode", "overwrite")
        if mode == "append" and path.exists():
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(str(content))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(str(content), encoding="utf-8")
        self.audit.append("fs.create_file.done", resource=str(path), detail={"bytes": len(str(content))})
        return {"path": str(path), "bytes": len(str(content))}

    def copy_file(self, params: dict) -> dict:
        src = self.engine.validate_path(params["src"], params.get("root"), must_exist=True)
        dst = self.engine.validate_path(params["dst"], params.get("root_dst", params.get("root")))
        self._pre("fs.copy", COPY_FILES, src=str(src), dst=str(dst))
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return {"src": str(src), "dst": str(dst), "bytes": dst.stat().st_size}

    def move_file(self, params: dict) -> dict:
        src = self.engine.validate_path(params["src"], params.get("root"), must_exist=True)
        dst = self.engine.validate_path(params["dst"], params.get("root_dst", params.get("root")))
        self._pre("fs.move", MOVE_FILES, src=str(src), dst=str(dst))
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return {"src": str(src), "dst": str(dst)}

    def delete_path(self, params: dict) -> dict:
        path = self.engine.validate_path(params["path"], params.get("root"), must_exist=True)
        root = self.engine.resolve_root(params.get("root"))
        if Path(str(path)) == Path(str(root.resolve())):
            raise PolicyViolation("refusing to delete an authorized root itself")
        self._pre("fs.delete", DELETE_FILES, path=str(path))
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        return {"path": str(path), "deleted": True}

    # ------------------------------------------------------------- compound
    def organize(self, params: dict) -> dict:
        """Create a project folder under the workspace and organize files by type.

        This powers: 'Create a folder called YouTube Project 01 in my Video
        Projects directory and organize today's script, images, audio and
        final video there.'
        """
        self.engine.require([CREATE_FILES, MOVE_FILES, READ_FILES])
        root = self.engine.resolve_root(params.get("workspace") or params.get("root"))
        target_name = params.get("target_folder") or "New Project"
        safe_name = "".join(ch for ch in target_name if ch not in '\\/:*?"<>|').strip() or "New Project"
        target = self.engine.validate_path(str(root / safe_name), str(root))
        self._pre("fs.organize", [CREATE_FILES, MOVE_FILES], target=str(target))
        target.mkdir(parents=True, exist_ok=True)

        folders = {k: target / k for k in ("scripts", "images", "audio", "video", "data")}
        for d in folders.values():
            d.mkdir(exist_ok=True)

        moved, skipped = [], []
        search_root = root
        for p in sorted(search_root.rglob("*")):
            if not p.is_file():
                continue
            resolved = p.resolve()
            if str(resolved).startswith(str(target.resolve())):
                continue  # never reorganize files already in the target
            ext = p.suffix.lower()
            dest_dir = next((d for k, d in folders.items() if ext in CATEGORY_EXTENSIONS[k]), None)
            if dest_dir is None:
                skipped.append(p.name)
                continue
            dst = dest_dir / p.name
            if dst.exists():
                dst = dest_dir / f"{p.stem}_{int(time.time())}{p.suffix}"
            self.audit.append("fs.organize.move", resource=str(p), detail={"to": str(dst)})
            shutil.move(str(p), str(dst))
            moved.append({"from": str(p), "to": str(dst)})

        manifest = {
            "project": safe_name, "created_at": time.time(),
            "target": str(target), "files_moved": moved, "skipped": skipped,
            "categories": {k: str(v) for k, v in folders.items()},
        }
        manifest_path = target / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        self.audit.append("fs.organize.done", resource=str(target), detail={"moved": len(moved)})
        import hashlib
        manifest_bytes = manifest_path.read_bytes()
        artifacts = [{
            "name": "manifest.json", "type": "json", "mime": "application/json",
            "path_ref": str(manifest_path), "size": len(manifest_bytes),
            "checksum": hashlib.sha256(manifest_bytes).hexdigest(),
            "metadata": {"project": safe_name, "files_moved": len(moved)},
        }]
        return {"target": str(target), "moved": len(moved), "skipped": len(skipped),
                "manifest": str(manifest_path), "artifacts": artifacts}

    def save_artifact(self, params: dict, api) -> dict:
        """Persist a PATI artifact into an authorized folder.

        - control_plane artifacts: downloaded over the authenticated API.
        - local_reference artifacts whose bytes already live in an authorized
          folder on THIS machine: copied locally (no round trip).
        """
        self.engine.require([CREATE_FILES, SAVE_ARTIFACTS])
        artifact_id = params.get("artifact_id")
        if not artifact_id:
            raise PolicyViolation("artifact.save requires artifact_id")
        dest = self.engine.validate_path(params["path"], params.get("root"))
        self._pre("artifact.save", SAVE_ARTIFACTS, artifact_id=artifact_id, path=str(dest))
        import shutil
        import hashlib as _hashlib

        meta = api.get_artifact(artifact_id)
        copied = False
        if meta.get("storage") == "local_reference" and meta.get("location"):
            # try each authorized root as a hint for the source path
            src = None
            for root in self.engine.roots():
                try:
                    candidate = self.engine.validate_path(meta["location"], str(root),
                                                          must_exist=True)
                    src = candidate
                    break
                except PolicyViolation:
                    continue
            if src is not None:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(src), str(dest))
                copied = True
        if not copied:
            api.download_artifact(artifact_id, dest)
        return {"path": str(dest), "bytes": dest.stat().st_size,
                "artifact_id": artifact_id, "mode": "local-copy" if copied else "download"}

    def local_search(self, params: dict) -> dict:
        """Search text files under authorized roots (document_research)."""
        self.engine.require(READ_FILES)
        root = self.engine.resolve_root(params.get("root"))
        needle = str(params.get("objective") or params.get("query") or "").lower()
        terms = [t for t in needle.replace("?", " ").replace(".", " ").split() if len(t) > 2][:8]
        hits = []
        for p in root.rglob("*.md"):
            hits.append(p)
        for p in root.rglob("*.txt"):
            hits.append(p)
        results = []
        for p in hits[:400]:
            try:
                text = p.read_text(encoding="utf-8", errors="ignore").lower()
            except OSError:
                continue
            score = sum(text.count(t) for t in terms)
            if score:
                snippet_at = text.find(terms[0]) if terms else 0
                results.append({"path": str(p), "score": score,
                                "snippet": text[max(0, snippet_at - 80):snippet_at + 160]})
        results.sort(key=lambda r: -r["score"])
        return {"query": needle, "matches": results[:20]}

    def report_markdown(self, params: dict, inputs: dict) -> dict:
        self.engine.require(CREATE_FILES)
        root = self.engine.resolve_root(params.get("root"))
        title = params.get("title") or "Report"
        sections = []
        for stage_name, output in (inputs or {}).items():
            if isinstance(output, dict):
                text = output.get("text") or output.get("summary") or json.dumps(output)[:400]
            else:
                text = str(output)[:400]
            sections.append(f"## {stage_name}\n\n{text}\n")
        content = f"# {title}\n\nGenerated by PATI (free infrastructure) at {time.ctime()}\n\n" + "\n".join(sections)
        fname = "".join(ch if ch.isalnum() or ch in "-_ " else "_" for ch in title)[:60].strip() or "report"
        path = self.engine.validate_path(str(root / f"{fname}.md"), str(root))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self.audit.append("report.markdown", resource=str(path))
        import hashlib
        data = path.read_bytes()
        artifacts = [{
            "name": path.name, "type": "markdown", "mime": "text/markdown",
            "path_ref": str(path), "size": len(data),
            "checksum": hashlib.sha256(data).hexdigest(),
            "metadata": {"title": title},
        }]
        return {"path": str(path), "bytes": len(content), "title": title,
                "artifacts": artifacts}

    # ---------------------------------------------------------------- router
    def handle(self, op: str, params: dict, inputs: dict | None = None, api=None) -> dict:
        inputs = inputs or {}
        if op == "fs.list":
            return self.list_dir(params)
        if op == "fs.read":
            return self.read_file(params)
        if op == "fs.mkdir":
            return self.mkdir(params)
        if op == "fs.create_file":
            return self.create_file(params)
        if op == "fs.copy":
            return self.copy_file(params)
        if op == "fs.move":
            return self.move_file(params)
        if op == "fs.delete":
            return self.delete_path(params)
        if op == "fs.organize":
            return self.organize(params)
        if op == "artifact.save":
            if api is None:
                raise PolicyViolation("artifact.save requires API access")
            return self.save_artifact(params, api)
        if op == "research.local_search":
            return self.local_search(params)
        if op == "report.markdown":
            return self.report_markdown(params, inputs)
        raise PolicyViolation(f"unsupported filesystem op: {op}")
