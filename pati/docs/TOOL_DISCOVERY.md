# TOOL_DISCOVERY.md

Phase-15 vision: when PATI needs a capability it cannot serve, it should
find, vet, install and benchmark a better free tool — autonomously but
inside security boundaries.

## Implemented today

- `GET /api/v1/tools/discover?q=` — discovery over the merged registry
  (id/name/capabilities matching), FREE_ONLY-filtered.
- `POST /api/v1/tools/install` — audited lifecycle transition
  (registry-gated statuses; no arbitrary downloads).
- Registry merges: code catalog + `registered_tools` DB rows → third-party
  registrations can appear without code changes.

## Pipeline (lifecycle states reserved)

DISCOVERED → RESEARCHING → CANDIDATE → APPROVED → INSTALLING → INSTALLED →
TESTING → BENCHMARKING → ACTIVE → monitor → REPLACE / QUARANTINE.

Safety rules that will NOT change:

1. Never blindly install or execute downloaded code — installation is an
   audited admin action against a declared source with a recorded license.
2. License + security check before APPROVED (see docs/LICENSE_POLICY.md).
3. New tools land in SANDBOX (sandbox_required=true) and must pass a health
   check and a benchmark before ACTIVE.
4. Replacement decisions compare benchmarks against the incumbent; failed
   tools are quarantined, not silently deleted.

## Research sources (free)

PyPI metadata, GitHub API (via the connector), official docs — fetched by
the research engine (roadmap) and recorded into `benchmarks` +
`last_verified` fields. No paid research APIs.
