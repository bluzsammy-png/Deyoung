# AGENTS.md — Instructions for AI Coding Assistants Working on PATI

This file is the entry point for AI coding agents (Claude Code, Gemini CLI,
Codex, Cursor, GitHub Copilot, …) working **inside this repository**. The
per-tool entry files (`CLAUDE.md`, `GEMINI.md`, `CODEX.md`, `CURSOR.md`,
`COPILOT.md`) all defer to this one.

## 0. Non-negotiable rules (read first, violate never)

1. **FREE_FIRST_POLICY.md is constitutional.** Never add a dependency,
   model, service, or code path that costs money, requires a payment
   method, or relies on expiring credits. Cost fields in schemas/registries
   are pinned `≤ 0`; `max_spend` is pinned `0`. Do not "fix" these pins.
2. **The path guard is sacred** (`pati_agent/policy_engine.py`). Never
   weaken, bypass, or add an override to: traversal checks, symlink escape
   checks, null-byte rejection, root-deletion refusal. Tests in
   `tests/test_security_path_guard.py` are adversarial on purpose.
3. **Research before dependencies.** No `pip install` of anything new
   without a verified row in `docs/RESEARCH_REPORT.md` (procedure:
   `docs/RESEARCH_ENGINE.md`).
4. **Never block the event loop** in `pati_api/` — asyncio primitives only
   (the dispatch-loop incident is documented in IMPLEMENTATION_PLAN §2).
5. **Fail-parked, not fail-paid:** when a resource is missing, jobs go
   `WAITING_FOR_RESOURCE` and the API returns `RESOURCE_UNAVAILABLE`.
   Never implement a paid fallback "for convenience."

## 1. Repository orientation (2-minute tour)

```
pati_api/        FastAPI control plane. Heart: orchestrator.py (pull-based
                 dispatch, watchdog), registries.py (capability/model/tool),
                 security.py (tokens/scopes), quota.py, planner.py.
pati/            SDK (PatiClient), CLI, Personal-AI adapters (Z.ai tool spec,
                 generic).
pati_agent/      Local agent. policy_engine.py = security kernel; fsops,
                 execops (rlimits+allowlist), wizard, doctor, audit chain.
pati_workers/    worker interface (11 ops), Kaggle free-GPU worker, container.
pati_connectors/ connector contract, GitHub impl, Drive scaffold.
pati_mcp/        stdio JSON-RPC MCP server (safe tools only).
schemas/         JSON Schemas — NORMATIVE. Code follows schemas.
installer/       install.ps1 (Windows-first), services, tunnel helper.
examples/        e2e_demo (Flow 1), e2e_remote_gpu (Flow 2), multipurpose.
tests/           46 tests incl. both E2E flows.
docs/            40+ docs. Start: RESEARCH_REPORT → ARCHITECTURE → MASTER_PRD.
```

## 2. The change workflow (always this order)

1. **Locate the contract first:** the relevant schema in `schemas/` and the
   relevant doc in `docs/`. Docs and schemas precede code.
2. **Plan minimally:** smallest change that satisfies the contract.
3. **Implement** with type hints; stdlib-first; no new deps.
4. **Test:** add/adjust tests. Security-sensitive files need allow AND deny
   path tests. Run `python -m pytest tests -q` — all 46 must pass.
5. **Docs in the same change:** update the doc(s) the change touches; the
   README doc map must keep resolving.
6. **Registry changes:** registry edit + schema validation + report row +
   pinning test (see DEV_ENVIRONMENT §6 for the three common PR shapes).

## 3. Commands you'll need

```bash
python -m pytest tests -q                  # full suite (~14 s)
python -m pytest tests -q -k path_guard    # security tests only
python examples/e2e_demo.py                # Flow 1 (disk) — smoke gate
python examples/e2e_remote_gpu.py          # Flow 2 (GPU; without kaggle.json
                                           #  asserts RESOURCE_UNAVAILABLE path)
python scripts/gen_schemas.py --check      # schema drift check
pati-server                                # control plane (dev)
```

## 4. Things agents commonly get wrong (learn from your siblings)

- **Importing heavy modules at module scope** in `pati_api` — keep startup
  fast; lazy-import optional pieces.
- **Holding locks while waiting** (dispatch, long-poll) — per-attempt lock
  scope only; never sleep/wait inside a critical section.
- **Treating `RESOURCE_UNAVAILABLE` as an error to retry around** — it is a
  terminal, honest state for that moment. Retry policies live in job
  records, not in client workarounds.
- **Renaming stable API error codes** — codes are part of the contract
  (`QUOTA_EXCEEDED` ≠ `RATE_LIMITED`; the SDK distinguishes them).
- **"Improving" the path guard with permissive defaults** — e.g., resolving
  symlinks *then* allowing, or allowlisting globs that match outside roots.
  If in doubt, fail closed.
- **Writing docs that contradict schemas** — schemas win; fix the doc.
- **Adding `# type: ignore` to silence real issues** in `security.py`,
  `policy_engine.py`, `execops.py` — forbidden.

## 5. What to do when a task seems to require money

1. Stop. Re-read FREE_FIRST_POLICY §5 (decision procedure).
2. Search the registries/research report for a free equivalent.
3. If none exists: implement the capability to the point of honest
   degradation (`RESOURCE_UNAVAILABLE`), document the gap in ROADMAP's
   research-needed section, and stop. Do not stub a paid call.

## 6. Commit/message discipline

- Imperative, specific, one logical change per commit.
- Security or $0-policy changes say so explicitly in the message body.
- Never commit: `credentials.json`, tokens, `~/.kaggle` files, real user
  paths in examples (use `~/PATIWorkspace`-style placeholders).

## 7. When documentation is the deliverable

Docs live in `docs/`, Markdown, sentence-per-line is fine, no marketing
superlatives, no artificial "End of document" markers. Match the existing
tone: engineering-honest, tables over prose when comparing, every "$0"
claim traceable to a research report row.
