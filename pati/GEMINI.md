# GEMINI.md

Gemini CLI / Gemini Code Assist working in this repository: your
instructions are in **`docs/AGENTS.md`**. Read it before touching code.

Fast orientation for you specifically:

1. Non-negotiables: `docs/FREE_FIRST_POLICY.md` (cost pins are
   schema-enforced; never "fix" them) and `pati_agent/policy_engine.py`
   (the path guard is the security kernel; never weaken it).
2. Contract order: `schemas/*.json` are normative → `docs/*.md` → code.
3. The repo's docs are the spec set (40+ files in `docs/`); prefer citing
   the exact doc file in explanations over paraphrasing from memory.
4. Gates before you claim done:
   `python -m pytest tests -q` (46 pass) and
   `python examples/e2e_demo.py` (smoke).
5. When generating **media-capable** suggestions (image/video/TTS), route
   through PATI capabilities backed by the Kaggle worker
   (`docs/KAGGLE_WORKER.md`); when no free resource exists the correct
   behavior is `RESOURCE_UNAVAILABLE` — do not propose paid APIs.
6. Async rule: inside `pati_api/`, asyncio only — no blocking calls in the
   event loop (`docs/AGENTS.md` §0 rule 4).

Personal-AI runtime note: when Gemini acts as the *Personal AI* talking to
a running PATI, use the generic adapter pattern (`docs/ADAPTER_SPEC.md`)
or the MCP server (`pati_mcp`) — never raw disk access.
