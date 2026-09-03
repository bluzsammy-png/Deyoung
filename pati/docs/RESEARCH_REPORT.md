# RESEARCH_REPORT.md

Research performed 2026-09-02 (UTC+8) with live web verification. Every entry
records: technology, purpose, free status, license, limits, PATI role,
decision (USE / OPTIONAL / DEFER / REJECT), confidence, last verified.
Free-status classes follow `docs/FREE_FIRST_POLICY.md`.

## Summary of decisions

| # | Technology | Purpose | Free status | License | Decision | Confidence |
|---|-----------|---------|-------------|---------|----------|------------|
| 1 | Python 3.10+ | Core runtime | FREE_FOREVER | PSF | USE | high |
| 2 | FastAPI | Control plane API | FREE_FOREVER | MIT | USE | high |
| 3 | Uvicorn | ASGI server | FREE_FOREVER | BSD-3 | USE | high |
| 4 | SQLite | Database | FREE_FOREVER | Public domain | USE | high |
| 5 | Pydantic v2 | Schemas/validation | FREE_FOREVER | MIT | USE | high |
| 6 | httpx | HTTP client (SDK/agent) | FREE_FOREVER | BSD-3 | USE | high |
| 7 | psutil | Hardware/resource reporting | FREE_FOREVER | BSD-3 | USE | high |
| 8 | Kaggle API + CLI | Free GPU batch compute | FREE_WITH_LIMITS | Apache-2.0 (client) | USE | high |
| 9 | Kaggle-hosted open-weights models | Inference (text/image/audio) | FREE_WITH_LIMITS | per model | USE | high |
| 10 | Ollama / llama.cpp | Optional local inference | OPEN_SOURCE_SELF_HOSTED | MIT | OPTIONAL | high |
| 11 | Cloudflared tunnel | Free remote access to local API | FREE_FOREVER (no card) | Apache-2.0 | OPTIONAL | high |
| 12 | systemd / launchd / Task Scheduler | Autostart | FREE_FOREVER (OS feature) | n/a | USE | high |
| 13 | PyInstaller | Single-file agent packaging | FREE_FOREVER | GPL v2 + bundling exception | OPTIONAL | high |
| 14 | MCP (Model Context Protocol) | AI-client integration standard | FREE_FOREVER, open standard, Linux Foundation | MIT | USE | high |
| 15 | Google Drive API v3 | External storage connector | FREE_WITH_LIMITS | Google APIs ToS | USE (scaffold) | medium-high |
| 16 | GitHub REST API | Code/repo connector | FREE_FOREVER (free tier) | GitHub ToS | USE | high |
| 17 | Docker | Container worker | FREE_FOREVER (desktop personal use) | Apache-2.0 | OPTIONAL | high |
| 18 | Playwright | Future browser automation | FREE_FOREVER | Apache-2.0 | DEFER | medium |
| 19 | vLLM | Optional model-serving adapter | OPEN_SOURCE_SELF_HOSTED | Apache-2.0 | DEFER | medium |
| 20 | Paid AI APIs (any) | — | PAID | — | REJECT | high |

## Verified details

### 1-7. Core stack (Python, FastAPI, Uvicorn, SQLite, Pydantic, httpx, psutil)
- **Purpose:** control plane, API, persistence, validation, agent HTTP, hardware reports.
- **Free status:** all FREE_FOREVER open source; no credit card, no metered billing anywhere.
- **Limits:** SQLite single-file (adequate for personal/small-tenant scale; swap
  path documented in `docs/DATABASE.md`); FastAPI/uvicorn single-process
  orchestration assumption documented in `docs/DEPLOYMENT.md`.
- **PATI role:** the entire control plane + agent runtime.
- **Confidence:** high. **Last verified:** 2026-09-02.

### 8-9. Kaggle as free GPU compute
- **Official API:** https://www.kaggle.com/docs/api — `kaggle kernels push|status|output`,
  dynamic rate limiting on the public API (verified on official docs).
- **GPU quota:** weekly GPU limit ~30 hours/week per user (Kaggle announcement
  "Weekly Maximum GPU Usage", official forum/docs); sessions capped (≈12 h);
  kernels run in ephemeral sandboxes with /kaggle/working output.
- **Models:** Kaggle Models hosts official open-weights models (Qwen2.5,
  Llama 3.2, Gemma 2, SDXL, Whisper, MusicGen...). Weights run inside
  Kaggle's infrastructure — no redistribution by PATI, respecting each
  model's license. XTTS-v2 and MusicGen weights carry NON-COMMERCIAL
  licenses; flagged in the model registry (`license_restrictions`); Piper
  (MIT) is the commercial-safe TTS path.
- **Classification:** FREE_WITH_LIMITS. **Never treat as a permanent server**
  — PATI models it as ephemeral batch compute with local GPU-minute budgeting
  (`docs/QUOTA_MANAGER.md`).
- **ToS caution:** automation must use the official API within its rate
  limits; PATI never scrapes the website and never parallelizes beyond
  quota. **Decision:** USE. **Confidence:** high. **Verified:** 2026-09-02.

### 10. Ollama / llama.cpp (local inference)
- Optional local text generation on CPU. Not required for MVP (the owner's
  PC has no GPU; simulated engines cover demos and tests, clearly labeled).
- **Decision:** OPTIONAL (adapter slot reserved in the model registry).

### 11. Cloudflare Tunnel
- Free plan, no credit card; outbound-only connector — the control plane
  never opens ports. Bearer-token auth still mandatory.
- **Decision:** OPTIONAL (documented in installer/enable-tunnel.ps1).

### 13. PyInstaller
- Dual licensing: GPL-2.0 **with a bundling exception** that permits
  distributing binaries built with it under any terms (verified on
  pyinstaller.org license page). Optional single-file packaging of the agent.

### 14. MCP
- Open standard for connecting AI applications to tools/data; donated to the
  Linux Foundation (Dec 2025); spec at modelcontextprotocol.io. PATI ships a
  dependency-free stdio MCP server (`pati_mcp/`) exposing only safe,
  read/task tools — no admin, no shell, no credentials.
- **Decision:** USE. **Confidence:** high. **Verified:** 2026-09-02.

### 15. Google Drive API
- Free tier with published quotas; OAuth2; **least privilege via
  `drive.file` scope** (per Google's own guidance — app sees only files it
  created or the user opened with it). Consent in the owner's browser;
  revocable from Google Account at any time. PATI ships a scaffold adapter
  that requires the free `pip install pati[gdrive]` extras and a user
  consent flow — never full-drive scope. **Decision:** USE (scaffold).

### 16. GitHub API
- Free tier, 5000 req/h authenticated. Fine-grained PATs allow repo-scoped,
  read-mostly tokens. Connector stores tokens with restrictive permissions;
  read-only by default. **Decision:** USE.

### 20. Paid services — blanket rejection
Every paid AI API, paid GPU cloud, paid hosting tier and "free trial that
requires a card" is classified PAID and rejected as a core dependency. If no
free resource can serve a request, PATI returns `RESOURCE_UNAVAILABLE`
(`docs/FREE_FIRST_POLICY.md`).

## Source quality note
Primary sources were preferred (official docs, official license pages,
official announcements). Community sources were used only for quota context
and marked medium confidence. Nothing in this report was assumed from
memory without a verification pointer; where limits change over time (Kaggle
quota, Drive quotas), the registry entries carry `last_verified` dates and
PATI treats them as advisory budgets, never as guarantees.
