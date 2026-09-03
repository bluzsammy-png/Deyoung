# PATI — Personal AI Tool Infrastructure

**A zero-cost AI infrastructure layer.** PATI is the execution, orchestration,
routing, security and artifact layer that your Personal AI (Z.ai today, any
other AI tomorrow) runs on. The Personal AI is the conversation; PATI is the
infrastructure.

```
FREE_ONLY = true      PAID_SERVICES = false      MAX_SPEND = 0
```

## What PATI does

```
USER
 ↓
PERSONAL AI (Z.ai in a browser — replaceable, never a hard dependency)
 ↓
PATI API (versioned, provider-independent)
 ↓
AUTHENTICATION → AUTHORIZATION + POLICY ENGINE
 ↓
TASK ORCHESTRATOR → PLANNER → CAPABILITY ROUTER
 ↓                                   ↓
MODEL / TOOL / WORKER REGISTRIES     QUOTA MANAGER
 ↓
RESOURCE SELECTOR
 ├── LOCAL WORKER  (your PC: authorized folders, scripts, reports)
 ├── KAGGLE WORKER (free GPU: open-weights models, image/video/audio jobs)
 └── CONTAINER WORKER (optional, local Docker)
 ↓
VALIDATION + QA → ARTIFACT STORE → RESULT + LOGS + PROVENANCE
 ↓
PERSONAL AI → USER
```

## Proven end-to-end (tested in this repo, 46 passing tests)

- **Flow 1 — hard-drive automation:** client → PATI → Local Agent → authorized
  disk operation (`Create a folder called YouTube Project 01...`) → artifact +
  hash-chained audit trail → client. See `examples/e2e_demo.py`.
- **Flow 2 — free GPU pipeline:** client → PATI → remote free GPU worker →
  15-stage video pipeline (story → script → storyboard → parallel scenes →
  voice + music → edit → QA → final) → final artifact saved by the Local Agent
  into the authorized folder → client. See `examples/e2e_remote_gpu.py`.
- **Multipurpose:** text, image, voice, music, research, filesystem — one $0
  API. See `examples/multipurpose_demo.py`.

## Repository layout

| Path | Purpose |
|------|---------|
| `pati_api/` | Control plane: FastAPI app, orchestrator, planner, router, registries, quotas, artifacts |
| `pati/` | SDK (`PatiClient`), `pati` CLI, Personal AI adapters (Z.ai + generic) |
| `pati_agent/` | Local Agent: policy engine, path guard, sandboxed exec, wizard, doctor |
| `pati_workers/` | Universal worker interface + Kaggle free-GPU worker + container worker |
| `pati_connectors/` | Connector layer: declarations, registry, GitHub, Drive scaffold |
| `pati_mcp/` | MCP server (stdio JSON-RPC) exposing safe PATI tools to AI clients |
| `schemas/` | JSON Schema for every core entity (draft 2020-12) |
| `installer/` | Windows-first installer (`install.ps1`), tunnel helper, services |
| `examples/` | Runnable end-to-end proofs |
| `tests/` | 46 tests: API, auth, quotas, routing, path-guard security, both E2E flows |
| `docs/` | Architecture, specs, policies, research report |
| `adapters/` | Adapter template for new providers |

## Quickstart (your Windows PC)

```powershell
# from the repo root
Set-ExecutionPolicy -Scope Process Bypass
.\installer\install.ps1
```

The installer checks prerequisites, creates an isolated venv, installs PATI,
starts the control plane, prints a pairing code and launches the 12-step
Local Agent setup wizard (connect → authenticate → name PC → choose
authorized folders → permissions → hardware detection → tests → autostart).

Manual route:

```bash
pip install -e .
pati-server                      # control plane on http://127.0.0.1:8000
pati admin-pair                  # one-time code for a new computer
pati-agent setup                 # wizard on the target computer
pati-agent run                   # the agent loop
```

Then from any client:

```bash
export PATI_SERVER=http://127.0.0.1:8000
export PATI_TOKEN=<client token>
pati submit "Create a folder called YouTube Project 01 in my workspace" --wait
```

## Free remote access (PC + free tunnel)

```powershell
winget install --id Cloudflare.cloudflared   # free, no credit card
.\installer\enable-tunnel.ps1
```

## Free GPU

The Kaggle worker (`pati_workers/kaggle_worker.py`) runs open-weights models
(Qwen2.5, Llama 3.2, SDXL, Whisper, Piper...) as Kaggle kernel jobs — the
official free API, ~30 GPU-hours/week. PATI's quota manager budgets GPU
minutes locally. Without `~/.kaggle/kaggle.json` the worker reports
unavailable and PATI returns `RESOURCE_UNAVAILABLE` — never a paid fallback.

## Security model (short version)

- Bearer tokens, hashed at rest, scoped (admin / client / worker), revocable.
- Local Agent enforces folder allowlists ON YOUR MACHINE: traversal, symlink
  escape, absolute escapes and null-byte paths are rejected before any syscall.
- Dangerous permissions (DELETE_FILES, EXECUTE_COMMANDS, RUN_SCRIPTS,
  RUN_LOCAL_MODELS) are OFF by default.
- Hash-chained audit log (tamper-evident) on the agent + central audit trail.
- Worker tokens are bound to one worker id; job results are worker-scoped.
- Rate limiting, resource limits (CPU/RAM/time), command allowlists.

Details: `docs/SECURITY.md`, `docs/AUTH.md`, `docs/SANDBOX_SPEC.md`.

## Documentation map

**Getting started:** `docs/INSTALL.md` (setup) → `docs/TROUBLESHOOTING.md`
(symptom→cause→fix) → `docs/FAILURE_RECOVERY.md` (failure modes) →
`docs/DEPLOYMENT.md` (topologies).

**Dashboard & web app:** `docs/WEB_DASHBOARD.md` (installable PWA,
phone-first dashboard, custom domain, SEO/PWA checklist coverage).

**Architecture & specs:** start with `docs/RESEARCH_REPORT.md` (verified
free-stack research) → `docs/ARCHITECTURE.md` → `docs/MASTER_PRD.md`, then
per-component: `docs/KAGGLE_WORKER.md`, `docs/LOCAL_WORKER.md`,
`docs/API_SPEC.md`, `docs/MCP_SPEC.md`, `docs/ADAPTER_SPEC.md`,
`docs/ROUTING.md`, `docs/QUOTA_MANAGER.md`, `docs/ARTIFACT_SPEC.md`,
`docs/DATABASE.md`, `docs/WORKER_SPEC.md`, `docs/LOCAL_WORKER.md`,
`docs/POLICY_ENGINE.md`, `docs/SANDBOX_SPEC.md`, `docs/AUTH.md`,
`docs/SECURITY.md`, `docs/EVENT_SYSTEM.md`, `docs/OBSERVABILITY.md`,
`docs/LOGGING.md`, `docs/TOOL_DISCOVERY.md`, `docs/AUTONOMY.md`,
`docs/MULTI_TENANCY.md`.

**Policies:** `docs/FREE_FIRST_POLICY.md` (the $0 constitution) ·
`docs/LICENSE_POLICY.md` · `docs/OPEN_SOURCE_POLICY.md` ·
`docs/COMMERCIALIZATION.md` · `docs/MULTI_TENANT_SAAS.md`.

**Process:** `docs/ROADMAP.md` · `docs/IMPLEMENTATION_PLAN.md` ·
`docs/DEV_ENVIRONMENT.md` · `docs/CI_CD.md` · `docs/BENCHMARKING.md` ·
`docs/EVALUATION.md` · `docs/RESEARCH_ENGINE.md` ·
`docs/COMPETITOR_RESEARCH.md` · `docs/TESTING.md`.

**AI coding agents:** `AGENTS.md` (root pointer) → `docs/AGENTS.md`
(authoritative) + `CLAUDE.md` / `GEMINI.md` / `CODEX.md` / `CURSOR.md` /
`COPILOT.md`.

## License

MIT for PATI's own code. Every dependency and model is recorded with license
and free-status in `docs/RESEARCH_REPORT.md` and the registries.
