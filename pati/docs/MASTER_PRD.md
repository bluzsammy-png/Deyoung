# MASTER_PRD.md

## Product vision

PATI is the owner's own AI infrastructure and API: a zero-cost, capability-
first execution layer that any Personal AI can call. The owner's Personal AI
(Z.ai today) handles conversation; PATI determines **what** needs to happen,
**which** free resources can do it, **where** it runs, **whether** quota and
licensing allow it, and returns validated artifacts. Over time PATI is
exposed to other users as an API/SaaS without ever acquiring a paid core
dependency.

## Goals (v1 — delivered in this repository)

1. Hard $0 guarantee, enforced structurally (registry validation, no paid
   fallback code path anywhere).
2. Versioned API with strict schemas (`/api/v1`, JSON Schemas in `schemas/`).
3. Capability-first registries: 90+ capabilities across text, coding,
   research, vision, image, video, audio, automation, app-building,
   infrastructure and local-filesystem domains.
4. Orchestration: rule-based planner, intelligent router (free-first,
   health- and failure-aware scoring), parallel groups, retries,
   cancellation, quarantine, watchdog.
5. Local Agent with hardened filesystem authorization + hash-chained audit.
6. Kaggle free-GPU worker with local GPU-minute budgeting.
7. Connector layer with least-privilege declarations (GitHub installed;
   Drive scaffold; planned entries marked honestly).
8. SDK + CLI + Personal AI adapters (Z.ai tool spec; MCP server).
9. Windows-first installer with 12-step wizard, autostart, tunnel helper.
10. Tests proving both mandated end-to-end flows.

## Non-goals for v1

Multi-node clustering; GPU-accelerated local inference on the owner's PC
(no GPU); real model serving baked into the core; paid anything.

## Users and roles

- **Owner** (admin): full control, token issuance, quotas, policies.
- **Clients** (Personal AIs, scripts): submit objectives, read results.
- **Workers** (local agent, Kaggle, containers): execute, report, upload.
- **Future tenants**: the data model carries tenant_id everywhere
  (`docs/MULTI_TENANCY.md`).

## Success metrics

- `pytest` green (46 tests) including both E2E flows.
- `examples/e2e_demo.py` and `examples/e2e_remote_gpu.py` complete on a
  clean machine with zero cost and zero credit-card touchpoints.
- `pati-agent doctor` passes on a fresh Windows install.
- Every registry entry has cost=0 and a recorded license + verification date.

## MVP definition of done — status

| Requirement | Status |
|---|---|
| API starts, health works | DONE (`/health`, status page) |
| Capability/model/tool/worker registries | DONE (94 caps, 13 models, 24 tools) |
| Task submission + routing + execution | DONE (pull-dispatch, tested) |
| Validation + artifacts + logs + quotas | DONE |
| Failure handling (retry/timeout/quarantine) | DONE (tested) |
| Safe MCP | DONE (tools/list + calls tested) |
| Personal AI integration | DONE (Z.ai adapter + MCP + generic) |
| Schemas validate | DONE (15 schemas, registry validation test) |
| Security controls | DONE (scopes, binding, path guard, sandbox, audit) |
| No paid AI API required | DONE (structural) |

## Milestones after v1

See `docs/ROADMAP.md` (real model serving via Ollama adapter, web research
connectors, Playwright browser worker, multi-tenant packaging, benchmarking
harness).
