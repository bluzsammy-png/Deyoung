# CODEX.md

OpenAI Codex (CLI or cloud agent) working in this repository: your
instructions are in **`docs/AGENTS.md`**. Read it before touching code.

Fast orientation for you specifically:

1. Non-negotiables: `docs/FREE_FIRST_POLICY.md` (cost pins are
   schema-enforced; never "fix" them) and `pati_agent/policy_engine.py`
   (the path guard is the security kernel; never weaken it).
2. Contract order: `schemas/*.json` are normative → `docs/*.md` → code.
3. Sandbox notes: the full test suite is offline by design — it binds
   ephemeral ports and uses a temp SQLite DB, so it runs fine in restricted
   sandboxes. Do not add network-dependent tests.
4. Gates before you claim done:
   `python -m pytest tests -q` (46 pass) and
   `python examples/e2e_demo.py` (smoke).
5. The exec sandbox (`pati_agent/execops.py`) uses rlimits + a command
   allowlist. If your environment lacks POSIX rlimits (e.g., Windows),
   respect the existing platform guards — do not delete them to make tests
   pass; mark and skip exactly as the current tests do.

Personal-AI runtime note: when Codex acts as the *Personal AI* talking to a
running PATI, use the SDK (`pati.PatiClient`) or the generic adapter
(`docs/ADAPTER_SPEC.md`) — never raw disk access.
