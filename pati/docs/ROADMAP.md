# ROADMAP — Where PATI Goes Next

The roadmap is capability-first (MASTER_PRD): each milestone adds
**abilities** you can exercise from your Personal AI, never paid services.
Every item below is $0-compatible by construction; items that can't be done
free are recorded as declined, not deferred.

## Milestones

### M0 — Foundation ✅ (shipped in this repo)

- Control plane: auth, scopes, registries, planner, orchestrator, quotas,
  artifacts, rate limits — 7 routers, SQLite with migrations.
- Local Agent: 12-step wizard, path guard (traversal/symlink/null-byte/
  root-delete protection), sandboxed exec with rlimits + command allowlist,
  hash-chained audit, doctor.
- Kaggle free-GPU worker: kernel push pipeline, per-worker dispatch,
  watchdog, cancellation, 240 GPU-min/day local budget.
- SDK + `pati` CLI + Z.ai tool-spec adapter + Generic adapter.
- MCP server (stdio) exposing safe tools.
- Connectors: GitHub implemented; Drive scaffold (`drive.file` scope).
- **Proven E2E:** disk flow + 15-stage free-GPU video pipeline. 46 tests.

### M1 — Daily-driver hardening (near term)

- **Windows service polish:** silent restart, crash-loop backoff, log
  rotation (LOGGING.md already specifies the shape).
- **Artifact retention policies:** age/size-based GC with pinned "keep"
  tags; disk usage report in `pati-agent doctor`.
- **Better planner coverage:** more natural-language patterns for fs
  organization and media pipelines; planner self-tests from real transcripts.
- **Quota UX:** `pati quota` showing remaining GPU minutes today/this week,
  per capability; job estimates before submission.

### M2 — More free compute & capabilities (medium term)

- **Container worker GA:** polished Docker worker for isolated exec
  (SANDBOX_SPEC already defines the interface).
- **Open-weights model expansion:** registry-driven additions as new free
  licenses appear (research report row first — the process is the feature).
- **Music:** open-weights music generation (e.g., freely licensed
  melodic-conditioning models) as a new capability row.
- **Batch video:** scene-parallel rendering already proven in the E2E
  pipeline; add per-scene retry budgeting and storyboard → video diff QA.

### M3 — Federation-lite & ecosystem (longer term)

- **Connector SDK:** formalize the connector contract (already drafted in
  `pati_connectors/declarations.py`) with a template repo + tests kit.
- **More connectors, same discipline:** GitHub ✅, Drive scaffold →
  completion; candidates that fit the free-first rule (public APIs only).
- **MCP growth:** expose read-only job inspection and quota to MCP clients.
- **Model router learning:** usage-informed model selection (success rates,
  latency) recorded locally; still zero-cost, zero-telemetry (data stays on
  disk).

### M4 — Politeness at scale (ongoing)

- **Research engine formalization** (RESEARCH_ENGINE.md): scheduled re-
  verification of the research report rows (license/cost drift detection).
- **Benchmark regression tracking** (BENCHMARKING.md): local baselines
  recorded per release, trended in-repo (no external services).
- **Evaluation harness** (EVALUATION.md): golden-task suites per capability
  so planner/router changes are judged on outcomes, not vibes.

## Declined (permanent list)

- Paid GPU/API fallbacks (any price) — FREE_FIRST_POLICY.
- Cloud accounts requiring a payment method for core features.
- Telemetry / analytics phone-home.
- Multi-tenant SaaS in core (MULTI_TENANT_SAAS.md explains; forks may).
- Circumventing Kaggle/GitHub/Drive free-tier terms (quota pooling,
  multi-accounting, scraping).

## How roadmap items get in

1. Research row (license + cost verified) in RESEARCH_REPORT.
2. Capability/model/tool registry entries (schema-validated, cost ≤ 0).
3. Tests: unit + at least one E2E touch.
4. Docs in the same PR (OPEN_SOURCE_POLICY §3).

The roadmap version of the product promise: **every milestone adds what you
can do for $0; nothing ever adds what you must pay for.**
