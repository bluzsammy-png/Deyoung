# COPILOT.md

GitHub Copilot (IDE + Copilot Workspace/coding agent) working in this
repository: your instructions are in **`docs/AGENTS.md`**. Read it before
touching code.

Fast orientation for you specifically:

1. Non-negotiables: `docs/FREE_FIRST_POLICY.md` (cost pins are
   schema-enforced; never "fix" them) and `pati_agent/policy_engine.py`
   (the path guard is the security kernel; never weaken it).
2. Contract order: `schemas/*.json` are normative → `docs/*.md` → code.
3. PR discipline: this repo has no CLA (MIT, same as everything else), but
   PRs must carry tests + doc edits together (`docs/OPEN_SOURCE_POLICY.md`
   §3). A PR adding a dependency without a `docs/RESEARCH_REPORT.md` row is
   rejected mechanically — don't generate one.
4. Gates before you claim done:
   `python -m pytest tests -q` (46 pass) and
   `python examples/e2e_demo.py` (smoke).
5. Suggestion hygiene: Copilot's training data loves paid-API snippets
   (openai.api_key, stripe, paid GPU clouds). None of that belongs here;
   when the pattern sneaks into a suggestion, decline it and use the free
   path (`docs/AGENTS.md` §5).
6. CI: the reference workflow is documented in `docs/CI_CD.md` — keep
   `.github/workflows/ci.yml` in sync with it if you edit either.

Personal-AI runtime note: when Copilot acts as the *Personal AI* talking to
a running PATI, use the SDK (`pati.PatiClient`) — never raw disk access.
