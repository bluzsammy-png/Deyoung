# API_SPEC.md

Base URL: `http://127.0.0.1:8000`. Versioned prefix: `/api/v1`
(response header `X-PATI-Version`). Interactive docs: `/docs`.
All request bodies are strict-validated (422 on schema failure with
`error.code = SCHEMA_VALIDATION`). Errors: `{"error": {"code", "message"}}`.

Authentication: `Authorization: Bearer <token>` on everything except
`GET /health`, `GET /version`, `GET /`, and pairing-code registration.
Scopes: admin | tasks:read/write | workers:read/register/manage |
artifacts:read/write | research:submit | tools:read/manage |
connectors:manage | system:read | quotas:read | events:read | admin:tokens.

## Core

| Method | Path | Scope | Notes |
|---|---|---|---|
| GET | /health | - | status, version, FREE_ONLY flags |
| GET | /version | - | API version tag |
| GET | /capabilities | system:read | capability registry (cost=0 enforced) |
| GET | /models | system:read | model registry (free-only enforced) |
| GET | /tools | system:read | tool registry |
| GET | /tools/discover?q= | tools:read | discovery over registry |
| POST | /tools/install {tool_id} | tools:manage | lifecycle install |
| GET | /workers | workers:read | worker fleet + health |
| GET | /quotas | quotas:read | quotas + today's usage + policy |
| GET | /system/status | system:read | uptime, worker/task counts, policy |
| GET | /system/events | events:read | event stream (observability) |
| GET | /system/updates | system:read | free-channel update manifest |

(Canonical root-level aliases exist for the master-prompt names: /health,
/capabilities, /models, /tools, /workers, /quotas, /system/status.)

## Tasks

| Method | Path | Scope | Notes |
|---|---|---|---|
| POST | /tasks | tasks:write | {objective, type=auto, params, constraints, title} → 202 + plan |
| GET | /tasks?status=&limit= | tasks:read | list |
| GET | /tasks/{id} | tasks:read | task + stages + artifact ids |
| POST | /tasks/{id}/cancel | tasks:write | cancel; pending stages skipped |
| GET | /tasks/{id}/logs?since= | tasks:read | cursor-paginated logs |
| GET | /tasks/{id}/artifacts | tasks:read | artifacts for the task |

Task statuses: QUEUED PLANNING ROUTING WAITING_FOR_RESOURCE RUNNING PAUSED
VALIDATING COMPLETED FAILED CANCELLED QUARANTINED.

## Workers (pull protocol)

| Method | Path | Notes |
|---|---|---|
| POST | /workers/register | pairing_code (no token) OR admin/client token; returns worker token |
| POST | /workers/{id}/heartbeat | worker-self; resources + optional capability sync |
| GET | /workers/{id}/jobs/next?wait= | long-poll ≤30 s; returns {job: null} or a job bound to THIS worker |
| POST | /workers/{id}/jobs/{job}/status | RUNNING + streamed logs |
| POST | /workers/{id}/jobs/{job}/logs | log batch |
| POST | /workers/{id}/jobs/{job}/complete | multipart: status/result/error/error_code/artifacts_meta + files; or path_ref local references |
| POST | /workers/{id}/shutdown | mark offline |
| POST | /workers/{id}/audit | push hash-chained audit events |

Job payload: {job_id, task_id, stage_id, stage_name, op, tool, capability,
params (with `inputs` injected from dependencies; `artifact_id` resolved
from `artifact_ref`), deadline_at, trace_id}.

## Artifacts

POST /artifacts (client upload, multipart) · GET /artifacts ·
GET /artifacts/{id} (metadata + provenance) ·
GET /artifacts/{id}/content (bytes, or 409 LOCAL_REFERENCE with location) ·
DELETE /artifacts/{id} (admin).

## Research

POST /research {query, mode=local_corpus|web, save_to, root} → 202 task.
GET /research/{task_id}.

## Connectors

GET /connectors (catalog + status) · POST /connectors/{name}/install ·
POST /connectors/{name}/authorize · GET /connectors/{name}/health ·
POST /connectors/{name}/operations/{op} · DELETE /connectors/{name}.

## Admin (admin scope)

GET/POST /admin/tokens · POST /admin/tokens/{id}/revoke ·
POST /admin/pairing-codes · GET /admin/audit · GET/PUT /admin/policies ·
POST /admin/quotas/{key} · GET/POST /admin/tenants.

## Error codes

SCHEMA_VALIDATION (422) · quota exceeded (429 QUOTA_EXCEEDED) · rate limit
(429 RATE_LIMITED) · SECURITY_VIOLATION (stage error code → task
QUARANTINED) · RESOURCE_UNAVAILABLE semantics (task parked in
WAITING_FOR_RESOURCE; model/tool availability fields; never a paid fallback).
