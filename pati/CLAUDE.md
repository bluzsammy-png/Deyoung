# CLAUDE.md

Claude Code / Claude Desktop working in this repository: your instructions
are in **`docs/AGENTS.md`**. Read it before touching code.

Fast orientation for you specifically:

1. Non-negotiables: `docs/FREE_FIRST_POLICY.md` (cost pins are
   schema-enforced; never "fix" them) and `pati_agent/policy_engine.py`
   (the path guard is the security kernel; only adversarial tests may touch
   its test file).
2. Contract order: `schemas/*.json` are normative → `docs/*.md` → code.
3. Change workflow, commands, and the list of common agent mistakes are in
   `docs/AGENTS.md` §2–§4. The "never block the event loop" rule in
   `pati_api/` exists because of a real deadlock incident — do not
   reintroduce threading primitives into the dispatch loop.
4. Gates before you claim done:
   `python -m pytest tests -q` (46 pass) and
   `python examples/e2e_demo.py` (smoke).
5. If a task seems to need a paid API: stop, read `docs/AGENTS.md` §5.
   The answer is always "free equivalent or honest degradation."

Personal-AI runtime note: when Claude acts as the *Personal AI* talking to a
running PATI (rather than editing it), use the SDK (`pati.PatiClient`) or
the MCP server (`pati_mcp`, stdio) — never raw disk access; the Local Agent
is the only thing that touches the disk, by design.
