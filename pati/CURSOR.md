# CURSOR.md

Cursor working in this repository: your instructions are in
**`docs/AGENTS.md`** (add `docs/AGENTS.md` to Cursor Rules / include it in
context). Read it before touching code.

Fast orientation for you specifically:

1. Non-negotiables: `docs/FREE_FIRST_POLICY.md` (cost pins are
   schema-enforced; never "fix" them) and `pati_agent/policy_engine.py`
   (the path guard is the security kernel; never weaken it).
2. Contract order: `schemas/*.json` are normative → `docs/*.md` → code.
   When suggesting edits to registry entries, validate against the schema
   first — paid cost values are rejected at the registry boundary, and your
   suggestion will fail CI if it carries a nonzero cost.
3. The composer/multi-file rules that matter here:
   - Docs change in the same PR as behavior (`docs/AGENTS.md` §2.5).
   - No new pip dependencies without a research row
     (`docs/RESEARCH_ENGINE.md`).
4. Gates before you claim done:
   `python -m pytest tests -q` (46 pass) and
   `python examples/e2e_demo.py` (smoke).
5. Tab-completion caution: do not accept autocomplete suggestions that
   re-import threading primitives inside `pati_api/` (async-only rule) or
   that add `try/except: pass` around security checks.

Personal-AI runtime note: when the IDE's assistant acts as the *Personal
AI* talking to a running PATI, use the MCP server (`pati_mcp`, stdio) —
it exposes only safe tools by design.
