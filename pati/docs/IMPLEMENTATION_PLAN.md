# IMPLEMENTATION_PLAN — How PATI Was Built (and How to Re-Trace It)

This is the build plan as executed, written so a new contributor (or a
future you) can re-derive the system in the same order and see *why* each
step exists. The ordering principle from MASTER_PRD: **research → contracts →
control plane → execution plane → proof → polish.**

## Phase 0 — Research before a line of code

- Output: `docs/RESEARCH_REPORT.md` (verified 2026-09-02) — every candidate
  dependency, model and service with license + cost row.
- Decisions locked: Windows-first host, no local GPU; Kaggle as the free GPU
  plane; Cloudflare Tunnel as free remote access; open-weights models
  (Qwen2.5, Llama 3.2, SDXL, Whisper, Piper) as engines.
- Rule established: anything not in the report doesn't ship (FREE_FIRST
  §5).

## Phase 1 — Contracts

1. **Schemas first** (`schemas/`, draft 2020-12): capability, model (cost
   pinned ≤ 0), tool, worker, job, task, artifact, token, health
   (`max_spend: 0` constant), event, quota, policy, pairing, connector,
   manifest.
2. **API surface** (`docs/API_SPEC.md`): resource-oriented routes,
   scope-per-route table, error envelope with stable codes
   (`RESOURCE_UNAVAILABLE`, `QUOTA_EXCEEDED`, `RATE_LIMITED`, …).
3. **Why first:** code written against schemas catches drift at the
   boundary; the E2E tests later reuse the same entities.

## Phase 2 — Control plane (`pati_api/`)

1. **App skeleton + SQLite with migrations** (versioned, idempotent).
2. **Security core:** token minting (hashed at rest), scopes, roles,
   worker-id binding, pairing codes (single-use, TTL), rate limiting.
3. **Registries:** capabilities (94), models (13), tools (24) with
   FREE_ONLY insert-time validation.
4. **Planner:** NL task → task graph (fs patterns, media pipeline patterns).
5. **Orchestrator:** pull-based dispatch (workers long-poll), per-worker
   dispatch (only the poller gets that job's stages), watchdog deadlines,
   cancellation, circuit-breaking, `WAITING_FOR_RESOURCE` parking.
6. **Quota manager:** per-token local budgets (GPU-min/day) pre-checked
   before any external call.
7. **Artifact store:** content-addressed, provenance metadata.
8. **Routers:** jobs, workers, artifacts, tokens, quotas, connectors,
   status.

**Phase 2 lesson learned (recorded for posterity):** the first dispatch loop
used a threading event inside the async loop and froze all HTTP traffic; the
fix (asyncio primitives, per-attempt locks) is why DISPATCH docs emphasize
"never hold the dispatch lock while waiting."

## Phase 3 — Execution plane

1. **Local Agent (`pati_agent/`)**: PolicyEngine path guard first (it is the
   security kernel), then fs ops (incl. `fs.organize`), then exec sandbox
   (rlimits + command allowlist), sysinfo, wizard (12 steps), doctor,
   updater, hash-chained audit.
2. **Workers (`pati_workers/`)**: universal worker interface (11 ops),
   Kaggle worker (kernel push, pull results), container worker.
3. **SDK + CLI (`pati/`)**: `PatiClient` with correct 429 semantics
   (QUOTA_EXCEEDED vs RATE_LIMITED), `pati` commands, Z.ai tool-spec adapter
   + generic adapter.
4. **Connectors (`pati_connectors/`)**: contract, registry, GitHub;
   Drive scaffold with honest `planned` status.
5. **MCP (`pati_mcp/`)**: stdio JSON-RPC; safe tools only.

## Phase 4 — Proof (the gate to "done")

- `examples/e2e_demo.py` — **Flow 1:** client → PATI → Local Agent →
  authorized folder created + artifact + audit chain → client.
- `examples/e2e_remote_gpu.py` — **Flow 2:** client → PATI → Kaggle worker →
  15-stage video pipeline (story → script → storyboard → parallel scenes →
  voice+music → edit → QA → final) with failure/retry and cancellation
  paths exercised → final artifact saved locally by the agent.
- `examples/multipurpose_demo.py` — one API, many capabilities.
- `python -m pytest tests -q` — **46 tests** including both flows, auth,
  quotas, routing, path-guard attacks, MCP, schemas.

## Phase 5 — Docs & packaging

- 40+ docs (you are reading the tail end), README map, installer
  (Windows-first), service templates, uninstallers.

## Re-tracing checklist (new contributor path)

1. Read RESEARCH_REPORT → ARCHITECTURE → MASTER_PRD (order matters).
2. Skim `schemas/` — the nouns; then `API_SPEC` — the verbs.
3. Run `pip install -e .`, run both examples, run the test suite.
4. Read `orchestrator.py` with TROUBLESHOOTING §4 open — the watchdog and
   dispatch semantics are the heart of the system.
5. Read `policy_engine.py` — the security kernel; do not propose changes
   that weaken it.
6. Pick a roadmap item (ROADMAP.md) and follow the §"How roadmap items get
   in" procedure.

## Estimation notes (for planners)

- The whole system is ~a few thousand lines of honest Python + docs; the
  risky time went into concurrency semantics and the security kernel, not
  CRUD. If you rebuild or fork: budget accordingly (concurrency bugs don't
  show in happy-path tests; the two E2E examples exist to catch them).
