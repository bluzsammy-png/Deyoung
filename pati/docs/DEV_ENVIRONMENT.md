# DEV_ENVIRONMENT — Developer Setup & Workflows

Everything a contributor needs to go from clone to green tests in under ten
minutes. No paid tools anywhere in the loop.

## 1. Toolchain

| Tool | Version | Why |
|------|---------|-----|
| Python | 3.11+ | match statements, modern typing |
| pip / venv | bundled | isolated env |
| Git | any recent | obviously |
| Docker (optional) | any recent | container worker testing |
| Editor | any | the repo is editor-agnostic (see AGENTS.md for AI editors) |

## 2. First-time setup

```bash
git clone <repo> pati && cd pati
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -e .
pip install -e ".[dev]"            # pytest, httpx test client, ruff if declared
python -m pytest tests -q          # expect: 46 passed in well under a minute
```

If the full suite passes immediately, your environment is correct — that is
the definition here. Tests bind to ephemeral local ports and use a temp
SQLite DB; they do not touch your real `~/.pati`, `~/.kaggle`, or network.

## 3. Repo map for developers

```
pati_api/        control plane (app, orchestrator, planner, registries…)
pati/            SDK (PatiClient), CLI, adapters (Z.ai tool-spec, generic)
pati_agent/      local agent (policy engine, fsops, execops, wizard, doctor)
pati_workers/    worker interface, Kaggle worker, container worker
pati_connectors/ connector contract, GitHub, Drive scaffold
pati_mcp/        stdio MCP server
schemas/         JSON Schemas (normative contracts)
installer/       install.ps1 / install.sh / services / tunnel helper
examples/        e2e_demo, e2e_remote_gpu, multipurpose, zai tool-spec
tests/           46 tests incl. both E2E flows
scripts/         gen_schemas.py
docs/            40+ specs & policies
```

## 4. Day-to-day commands

```bash
# run the control plane (dev)
pati-server                       # 127.0.0.1:8000, auto-reload not enabled — restart on change

# run an agent against it
pati admin-pair                   # print pairing code
pati-agent setup                  # wizard (use --non-interactive in CI)
pati-agent run

# tests
python -m pytest tests -q         # whole suite (~14 s)
python -m pytest tests/test_security_path_guard.py -q   # one file
python -m pytest tests -q -k e2e  # both E2E flows only

# examples against a local server
python examples/e2e_demo.py
python examples/e2e_remote_gpu.py # needs ~/.kaggle/kaggle.json for real GPU;
                                  # without it, asserts RESOURCE_UNAVAILABLE path
python examples/multipurpose_demo.py
```

## 5. Conventions

- **Language:** Python 3.11+; stdlib-first; no dependency without a research
  report row (LICENSE_POLICY §6 procedure).
- **Types:** type-hint public functions; the registries and SDK are the API
  surface and should be fully annotated.
- **Async discipline:** inside `pati_api`, never block the event loop — use
  `asyncio` primitives (the dispatch-loop lesson, IMPLEMENTATION_PLAN §2).
- **Errors:** stable string codes in the API envelope; SDK raises
  `PATIError` with `code` — new error codes get a row in API_SPEC.
- **Security-sensitive code** (`policy_engine.py`, `execops.py`,
  `security.py`) requires tests for both allow and deny paths, including the
  adversarial cases (see `tests/test_security_path_guard.py` for the
  pattern: traversal, symlink escape, null bytes, root deletion).
- **Docs:** behavior change ⇒ doc edit in the same PR (OPEN_SOURCE_POLICY
  §3.5); schemas are normative over prose.

## 6. Adding things (the three common PRs)

### A new model
1. Research row → `docs/RESEARCH_REPORT.md` (license, cost, source URL).
2. Registry entry in `pati_api/registries.py` (cost fields must be ≤ 0 or
   validation rejects you).
3. Test pinning the entry; update `docs/MODEL_REGISTRY.md`.

### A new capability/tool
1. Registry entry (capability → model/tool mapping).
2. Worker or agent support (`pati_agent/tools.py` or worker interface op).
3. Planner pattern if it's NL-triggerable; E2E touch if it's a flow.

### A new connector
1. Implement the connector contract in `pati_connectors/` (see GitHub for
   the reference implementation).
2. Free-tier ToS check recorded in the PR (LICENSE_POLICY §4).
3. Tests with a stubbed transport; no network in CI.

## 7. Debugging tips

- Set `PATI_LOG_LEVEL=DEBUG` for verbose server logs.
- `curl -s http://127.0.0.1:8000/health | jq` is always step one.
- The agent's audit log (`~/.pati/agent/audit.log`) shows every guard
  decision with reason codes — if an operation was rejected, the *why* is in
  there.
- For dispatch weirdness, `GET /jobs?limit=5` + `GET /workers` together tell
  you whether the job is parked (no capable worker), running (deadline
  pending), or stuck (watchdog next tick reaps).

## 8. What "done" means for a change

1. Tests green (suite + your new tests).
2. Schemas updated if entities changed.
3. Docs updated.
4. Both E2E examples still pass (they are the smoke gate).
5. Research report row for anything new (dependency/model/service).
