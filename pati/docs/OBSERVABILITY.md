# OBSERVABILITY.md

## Correlation IDs

Every task gets a `trace_id` at creation. It appears in: task rows, job
payloads (workers echo it), stage events, and log lines. The HTTP layer
adds `X-PATI-Version` and `X-PATI-Trace-Time-ms` (request latency) headers
via pure-ASGI middleware.

## Endpoints

- `GET /health` — liveness + FREE_ONLY flags (public).
- `GET /system/status` — uptime, worker/task counts by status, policy,
  platform (system:read).
- `GET /system/events` — decision/transition stream (events:read).
- `GET /tasks/{id}` + `/logs` — per-task drill-down.
- `GET /workers` — fleet health incl. failure_count, last_heartbeat.
- `GET /admin/audit` — security trail (admin).
- `GET /` — zero-auth status page: version, policy banner, worker/task
  summaries, last 8 tasks. No sensitive data.

## What to watch in production

1. Tasks stuck in WAITING_FOR_RESOURCE → missing free worker or exhausted
   GPU budget (`GET /quotas`).
2. worker.offline events → machine asleep? agent service stopped?
3. Rising failure_count / degraded health → circuit breaker will
   deprioritize; fix the worker or re-register it.
4. Audit chain verification failures on the agent (`pati-agent doctor`) →
   investigate immediately.

Local file logs: server stdout + `~/.pati/server.log` when started by the
installer; agent prints job logs to stdout (captured by the service
templates).
