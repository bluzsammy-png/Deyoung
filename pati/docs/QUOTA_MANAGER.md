# QUOTA_MANAGER.md

`pati_api/quota.py` — per-tenant, per-day usage counters with configurable
limits. Purpose: spend Kaggle's ~30 GPU-h/week deliberately, protect the
local machine, and make limits explicit instead of surprising.

## Quotas (defaults in config.QUOTA_DEFAULTS)

| key | default | meaning |
|---|---|---|
| max_concurrent_tasks | 4 | active tasks at once |
| max_tasks_per_day | 200 | submissions per day |
| max_artifact_mb_total | 2048 | artifact bytes stored |
| gpu_minutes_per_day | 240 | local budget inside Kaggle's free weekly allowance |
| api_requests_per_min | 240 | per-token rate limit |

## Mechanics

- Counters live in `usage_counters(tenant_id, key, day)`; consumption is an
  atomic upsert. The day key is UTC.
- `check(tenant, key, amount)` gates admission: task creation (concurrency,
  daily rate), stage claims for GPU-budgeted capabilities (2 min estimated
  per GPU-capable stage), artifact uploads (size).
- Exhaustion behavior is honest and non-destructive:
  - task submission → HTTP 429 QUOTA_EXCEEDED,
  - stage claim → the task parks in WAITING_FOR_RESOURCE (the
    RESOURCE_UNAVAILABLE semantic) and resumes automatically when the day
    rolls over or an admin raises the quota.
- Admin operations: `POST /admin/quotas/{key} {value}`, view at
  `GET /quotas` (returns quotas + today's usage + the FREE_ONLY policy).

## Why 240 GPU-min/day

Conservative daily budgeting under Kaggle's ~30 h/week free tier (~4.3 h/day
average). Owners can raise it, but PATI never silently hammers a free tier
to its limit.
