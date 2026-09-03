"""Google Drive connector - permission-scoped, revocable, free API.

Verified 2026-09-02 (docs/RESEARCH_REPORT.md):
- Drive API v3 is free; standard quotas; no billing for personal use.
- LEAST PRIVILEGE: request only https://www.googleapis.com/auth/drive.file
  (per-file consent, per Google's own guidance) or drive.readonly for reads.
- OAuth consent happens in the OWNER'S browser; refresh tokens live in the
  control plane data dir with 0600. Access is revocable at any time from
  Google Account -> Security -> Third-party access.

This module is an honest scaffold: it requires `pip install pati[gdrive]`
(free Apache-2.0 libraries) and a Cloud Console project the user creates
for free. It never invents endpoints and never stores credentials in logs.
"""
from __future__ import annotations

from .base import ConnectorAdapter, ConnectorSpec

SPEC = ConnectorSpec(
    name="gdrive",
    version="1.0.0",
    description="Search/download/upload files in the owner's Google Drive via OAuth2 (drive.file least-privilege).",
    capabilities=["web_scraping", "document_research", "artifact_storage"],
    auth="oauth2",
    scopes=["https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive.readonly (optional, reads)"],
    rate_limits="12,000 queries/min/project (Google published quota)",
    security=["user consent in browser", "revocable from Google Account",
              "refresh token stored 0600 in control-plane data dir",
              "no full-drive scope requested"],
    free_status="FREE_WITH_LIMITS",
    license="Google APIs Terms of Service (free tier)",
    supported_operations=["search_files", "download_file", "upload_file"],
    config_schema={"client_secret_file": "string (path)"},
)


class DriveConnector(ConnectorAdapter):
    spec = SPEC

    def install(self, config: dict) -> dict:
        secret = str(config.get("client_secret_file") or "")
        if not secret:
            raise ValueError(
                "config.client_secret_file required: create a free Google Cloud project, "
                "enable Drive API, download OAuth client secret JSON. See docs/KAGGLE_WORKER.md "
                "sibling: docs/ADAPTER_SPEC.md#gdrive")
        return {"client_secret_file": secret, "installed_at_note": "authorization not yet granted"}

    def authorize(self, config: dict) -> dict:
        return {
            "instructions": [
                "1. pip install 'pati[gdrive]' (free Apache-2.0 libraries)",
                "2. Ensure the Drive API is enabled in your free Google Cloud project",
                "3. Run: pati connector-authorize gdrive  (opens your browser for consent)",
                "4. Scope granted: drive.file - PATI sees ONLY files it creates or you open with it",
                "5. Revoke anytime: myaccount.google.com/permissions",
            ],
            "flow": "oauth2 installed-app loopback; runs locally; no PATI cloud involved",
        }

    def health_check(self) -> dict:
        try:
            import googleapiclient  # noqa: F401
            return {"ok": True, "library": "installed", "authorized": "check via operations"}
        except ImportError:
            return {"ok": True, "library": "not installed (pip install 'pati[gdrive]')",
                    "authorized": False}

    def call(self, op: str, payload: dict, config: dict) -> dict:
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
        except ImportError:
            raise ValueError("RESOURCE_UNAVAILABLE: install free extra with pip install 'pati[gdrive]'")
        token_file = payload.get("_token_file") or config.get("_token_file")
        if not token_file:
            raise ValueError("not authorized yet; run the authorize flow first")
        creds = Credentials.from_authorized_user_file(token_file)
        service = build("drive", "v3", credentials=creds)
        if op == "search_files":
            q = payload.get("query", "")
            res = service.files().list(q=f"name contains '{q}'", pageSize=payload.get("limit", 20),
                                       fields="files(id,name,mimeType,size)").execute()
            return {"files": res.get("files", [])}
        if op == "download_file":
            from googleapiclient.http import MediaIoBaseDownload
            import io
            request = service.files().get_media(fileId=payload["file_id"])
            buf = io.BytesIO()
            downloader = MediaIoBaseDownload(buf, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            return {"bytes": buf.getvalue(), "size": len(buf.getvalue())}
        if op == "upload_file":
            from googleapiclient.http import MediaInMemoryUpload
            media = MediaInMemoryUpload(payload["content"], mimetype=payload.get("mime", "text/markdown"))
            f = service.files().create(body={"name": payload["name"]}, media_body=media).execute()
            return {"file_id": f.get("id"), "name": f.get("name")}
        raise ValueError(f"unsupported operation: {op}")
