# OPEN_SOURCE_POLICY — Working in the Open

PATI is open source from commit one. This document defines what "open" means
here: what is public, how contributions work, how decisions are recorded, and
what the project will never do.

## 1. What is public

| Artifact | Status |
|----------|--------|
| All source (`pati_api/`, `pati/`, `pati_agent/`, `pati_workers/`, `pati_connectors/`, `pati_mcp/`) | Public, MIT |
| All 40+ docs in `docs/` | Public — specs are the product |
| JSON Schemas (`schemas/`) | Public — the contract is normative |
| Tests (`tests/`, 46 tests) | Public — CI is public; green in public or it doesn't merge |
| Research report (`docs/RESEARCH_REPORT.md`) | Public — every dependency's license/cost verification |
| Roadmap, implementation plan | Public |

The research report being public is deliberate: license and cost research is
the most boring, most valuable, most perishable part of a free-first stack.
Publishing it lets others audit the $0 claim and reuse the homework.

## 2. What is (deliberately) not in the repo

- **Secrets.** Tokens live in your OS user profile (`~/.kaggle`,
  `credentials.json` with 0600 perms). `.gitignore` covers them; there is no
  "sample token" to accidentally deploy.
- **Personal data.** Examples use `~/PATIWorkspace`-style paths; no real
  folders, no real artifacts, no telemetry endpoints.
- **Paid-service glue.** There is nothing to hide — adapters for paid
  providers are simply out of scope per FREE_FIRST_POLICY.

## 3. Contribution workflow

1. **Issue first** for anything non-trivial: behavior change, new
   capability, new model registration. Include the *why* and the free-status
   impact.
2. **Research before code** for dependencies/models: add the row to the
   research report in the same PR as the code. A PR that adds a dependency
   without a verified research row is rejected mechanically.
3. **Tests are the contract.** Every PR touching behavior updates
   `tests/`; the suite must stay green (`python -m pytest tests -q`).
4. **Schema discipline.** Entity changes update `schemas/` and re-run
   `scripts/gen_schemas.py` if applicable. Schemas are normative; docs follow
   schemas, not vice versa.
5. **Docs in the same PR.** A behavior change without its doc edit is an
   incomplete change. The doc map in README must stay accurate.
6. **No CLA.** Contributions land under MIT like everything else.

## 4. Decision records

Architecture decisions are recorded where the decision lives:

- Registry/policy decisions → the policy doc itself (FREE_FIRST_POLICY,
  LICENSE_POLICY) — these docs are append-mostly; changes are justified in
  the PR description.
- Component behavior → the component spec (`docs/*.md`).
- The **MASTER_PRD** is the arbiter when specs disagree; the $0 policy is the
  arbiter when the PRD disagrees with reality.

## 5. Code of conduct

Technical disagreement is welcome; be concrete (repros, tests, benchmarks).
Assume good faith, optimize for the person debugging at 2 a.m. (docs, error
messages), and treat "it costs $0" claims as adversarially reviewable.

## 6. Release policy

- **Versioning:** SemVer. The API is versioned at the path level
  (`/v1/...`); breaking control-plane changes bump the path version rather
  than breaking old clients.
- **Release notes** list: features, fixed bugs, security notes, and any
  registry additions (with their license/cost rows).
- **Tagged commits** correspond to tested states; the 46-test suite passing
  at the tag is a release requirement, not an aspiration.

## 7. Forking and derivatives

Explicitly welcome. If you fork:

- Keep the FREE_FIRST_POLICY if you keep the name; rename it if you add paid
  paths (PATI is a *free-first* trademark of intent, not just code).
- The MIT license requires preserving notices; the registries and schemas
  make it easy for forks to audit their own license/cost posture too.

## 8. Anti-goals for the open project

- No "open core" split where useful parts go proprietary.
- No telemetry, crash reporting, or analytics baked into the source.
- No contributor tiers, no paid priority, no "sponsors get features."
- No marketing-driven roadmap inversions (paid-adjacent features never sneak
  ahead of free ones — there are no paid features to sneak ahead).
