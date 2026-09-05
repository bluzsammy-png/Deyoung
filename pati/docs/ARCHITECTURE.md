# ARCHITECTURE.md

## Control plane vs compute plane

PATI separates **CONTROL PLANE** (API, authentication, authorization,
orchestration, routing, registries, database, observability, policy) from
**COMPUTE PLANE** (local worker, Kaggle worker, container worker, future
workers). The control plane is one FastAPI process plus SQLite; the compute
plane is any number of independent worker processes that dial IN to the
control plane (outbound-only) or receive pushed batch jobs (Kaggle).

## Component map

```
pati_api/                CONTROL PLANE
  config.py              $0 policy, limits, data dirs
  db.py                  SQLite + ordered migrations (schema_version table)
  security.py            tokens, scopes, pairing codes, rate limiter
  registries.py          capability / model / tool catalogs (+DB overrides)
  planner.py             objective -> stage graph (rule-based)
  orchestrator.py        task/stage state machines, pull-dispatch, watchdog
  quota.py               per-tenant per-day usage counters and budgets
  artifacts_store.py     content-addressed blob store (sha256)
  routers/               core, tasks, workers, artifacts, research,
                         connectors, admin
  status_page.py         public GET / dashboard (non-sensitive counts)

pati/                    SDK + CLIENTS
  client.py              PatiClient (typed high-level ops, wait_for_task)
  cli.py                 `pati` command line
  adapters/              PersonalAIAdapter base + ZAIAdapter + GenericAdapter

pati_agent/              LOCAL AGENT (compute plane, pull worker)
  policy.py              permissions + folder allowlist + path guard
  fsops.py               authorized filesystem ops (incl. organize)
  execops.py             sandboxed commands/scripts (rlimits, allowlist)
  sysinfo.py             CPU/RAM/disk/GPU reports
  audit.py               hash-chained JSONL audit log
  api_client.py          outbound-only control-plane client
  agent.py               worker loop: heartbeat + long-poll + job dispatch
  wizard.py / doctor.py / updater.py

pati_workers/            WORKER LAYER
  interface.py           UniversalWorkerInterface (11 ops) + pull base
  kaggle_worker.py       free-GPU push worker (kernels, quota budgeting)
  (container_worker inline)  optional Docker worker

pati_connectors/         CONNECTOR LAYER (external services, least privilege)
  base.py                ConnectorSpec + ConnectorAdapter contract
  manifest.py            catalog incl. honestly-planned entries
  registry.py            install/authorize/health/dispatch (DB-backed)
  github_connector.py    GitHub REST adapter
  gdrive_connector.py    Drive OAuth scaffold (drive.file least privilege)

pati_mcp/                MCP server (safe tools only)
schemas/                 15 JSON Schema files
installer/               Windows-first installer + tunnel + services
examples/                runnable proofs (flows 1 and 2)
tests/                   46 tests including both E2E flows
```

## Data flow (execution)

1. **Submit** — `POST /api/v1/tasks` authenticates, applies quotas, plans the
   objective into a stage graph (each stage: capability, op, params,
   depends_on, parallel group), stores it, returns 202.
2. **Dispatch** — workers long-poll `GET /workers/{id}/jobs/next`. The
   orchestrator assigns a stage **to the polling worker only** if the
   capability matches, dependencies are satisfied, and quota remains
   (`_claim_one` holds the dispatch lock only per attempt — a slow poller can
   never starve others). No capable free worker → task parks in
   `WAITING_FOR_RESOURCE`.
3. **Execute** — the worker enforces ITS OWN local policy (agent) or runs the
   job (Kaggle push adapter), streams logs, uploads artifacts (multipart) or
   registers local references.
4. **Complete** — `complete_job` updates the stage; retries happen on
   transient failures (`MAX_STAGE_RETRIES`); security violations quarantine
   instead of retrying. Task status advances through
   QUEUED → PLANNING → ROUTING → RUNNING → COMPLETED (or FAILED /
   CANCELLED / QUARANTINED / WAITING_FOR_RESOURCE).
5. **Watchdog** — a background loop refreshes statuses, requeues stages past
   deadline, marks silent workers offline and requeues their stages.

## Key invariants

- **FREE_ONLY is structural**: registries reject any entry with cost > 0 or
  paid free_status (`registries.enforce_free_only`); the router has no paid
  fallback path at all.
- **Pull-dispatch invariant**: a long-poll response is always a job bound to
  the requesting worker (prevents cross-worker job leakage).
- **Policy enforcement is local**: the control plane never touches the disk;
  the Local Agent validates every operation against the allowlist before any
  syscall and records a hash-chained audit event.
- **Replaceability**: Personal AI, model, worker and connector are all
  adapter seams; none is hard-wired into orchestration.

## State machines

Task: QUEUED, PLANNING, ROUTING, WAITING_FOR_RESOURCE, RUNNING, PAUSED,
VALIDATING, COMPLETED, FAILED, CANCELLED, QUARANTINED.
Stage: PENDING, DISPATCHED, RUNNING, SUCCEEDED, FAILED, SKIPPED.
Tool lifecycle: DISCOVERED → RESEARCHING → CANDIDATE → APPROVED → INSTALLING
→ INSTALLED → TESTING → BENCHMARKING → ACTIVE → (DEGRADED/STALE/
QUARANTINED/DEPRECATED/REMOVED/FAILED).
