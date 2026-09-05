# EVENT_SYSTEM.md

Events are the observable history of PATI's decisions and transitions.

## What is emitted (pati_api/orchestrator.py)

- task.planned {stages, type}
- stage.dispatched {worker, job}
- stage.completed {status}
- task.completed / task.failed / task.cancelled
- worker.offline {worker_id}

Stored in `events(id, tenant_id, type, resource, detail JSON, trace_id, ts)`
and exposed at `GET /api/v1/system/events?limit=` (events:read scope).
Every event carries the task's trace_id so a whole pipeline can be
reconstructed.

## Related streams

- **Task logs** (`GET /tasks/{id}/logs?since=`): worker + orchestrator
  messages, cursor-paginated for live tailing.
- **Audit** (`GET /admin/audit`): security-relevant actions (tokens,
  pairing, connectors, policy, tool installs, worker registration,
  agent-pushed hash-chained records).

## Design rules

- Events are append-only; no consumer can mutate history.
- Detail payloads are small and reference resources by id (no blobs).
- Emission failures never break execution (best-effort insert inside the
  same transaction where safe, ignored at the edges).
