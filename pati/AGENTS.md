# AGENTS.md (repository root — pointer)

Any AI coding agent working in this repository: your instructions are in
**`docs/AGENTS.md`** — start there. Tool-specific entry points that defer
to it: `CLAUDE.md`, `GEMINI.md`, `CODEX.md`, `CURSOR.md`, `COPILOT.md`.

One-paragraph summary (the full version is authoritative):

> PATI is a free-first ($0, schema-pinned) personal AI infrastructure.
> Schemas in `schemas/` are normative; the path guard in
> `pati_agent/policy_engine.py` is a security kernel you must never weaken;
> `pati_api/` is async-only inside the event loop; no dependency, model, or
> service may be added without a verified free license/cost row in
> `docs/RESEARCH_REPORT.md`; when a free resource is missing the correct
> behavior is `RESOURCE_UNAVAILABLE` + `WAITING_FOR_RESOURCE`, never a paid
> fallback. Gates before done: `python -m pytest tests -q` (46 pass) and
> `python examples/e2e_demo.py`.
