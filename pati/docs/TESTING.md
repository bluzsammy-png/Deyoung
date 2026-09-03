# TESTING.md

Run: `python -m pytest tests/ -q --timeout=90` — **46 tests, ~14 s**.

## Structure

- `tests/conftest.py`: boots a REAL uvicorn control plane on 127.0.0.1
  (random port) with a throwaway data dir; `admin` SDK client;
  `agent_factory` (real Local Agent runners against the live server);
  `MockGPUWorker` (real HTTP pull-worker with deterministic inference).
- No API mocks: everything goes over live HTTP.

## Coverage by area

| File | What it proves |
|---|---|
| test_core_api.py | health, version header, registries (94 caps / 13 free models / 24 tools), FREE_ONLY policy surface, status page, discovery |
| test_auth_scopes.py | 401s, scope enforcement, worker token binding (cannot act as another worker), revocation, pairing-code single-use flow, rate limiter |
| test_planner_router.py | objective classification, folder-name extraction, parallel scene groups + dependency sanity, WAITING_FOR_RESOURCE with no free worker, concurrency quota 429 |
| test_pathguard.py | traversal/absolute/symlink-escape/null-byte/wildcard rejection, dangerous permissions default-off, root-deletion refusal, command allowlist, audit chain tamper detection |
| test_agent_e2e.py | **Flow 1**: hard-drive organize with real agent + artifacts + audit + logs; unauthorized-path attempt → SECURITY_VIOLATION quarantine |
| test_remote_worker_e2e.py | **Flow 2**: text via free GPU worker; full 15-stage video pipeline with parallel scenes + artifact hand-off to the Local Agent's disk; failure recovery with retry; cancellation |
| test_mcp.py | initialize, tools/list (safe tools only), tool calls round-trip, unknown-tool error |
| test_connectors.py | full metadata contract, least-privilege install, planned connectors refuse install, Drive scope least-privilege |
| test_schemas.py | all 15 schema files valid; FREE_ONLY pinned in schema; registry entries validate (model/tool/capability) |

## Adapter test contract (per docs/ADAPTER_SPEC.md)

Health test, minimal execution test, error test, timeout test, cleanup
test, metadata test — the pull-worker and connector tests follow it; the
Kaggle push adapter is covered for its non-network logic (availability
gating, kernel generation, quota budgeting) with honest TODO markers for
live-credential smoke tests.

## Adding tests

Fixture `server` is session-scoped (one DB per run); use `admin` for
bootstrap actions, `client_factory` for fresh tokens, `agent_factory` for
agents with a temp workspace.
