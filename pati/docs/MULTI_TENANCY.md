# MULTI_TENANCY.md

PATI is designed single-user-first but multi-tenant-ready: every
tenant-scoped table (tasks, artifacts, workers, tokens, connectors, quotas,
events) carries `tenant_id`, and every authenticated query filters by the
token's tenant.

## What exists today

- `tenants` + `users` tables; default tenant `tenant_local` bootstrapped.
- `POST /admin/tenants {name}` creates a tenant + its admin user + admin
  token in one call (audited).
- Tokens, quotas, usage counters, artifacts (with visibility), events and
  audit rows are tenant-scoped.
- Artifact `visibility` field (default "tenant") anticipates future
  public/shareable artifacts.

## What is deliberately NOT multi-tenant yet

- One control-plane process shares one SQLite file; there is no per-tenant
  encryption, per-tenant rate fairness beyond per-token limits, or admin UI.
- Registration/pairing issues tokens into the issuing admin's tenant —
  cross-tenant worker pools are not exposed.

## SaaS path

See `docs/MULTI_TENANT_SAAS.md`: swap SQLite → Postgres behind the db
helper, add per-tenant API keys with plan-based quotas (the quota manager
already keys everything by tenant), keep the compute plane exactly as is.
No orchestration code changes are required because the tenant filter lives
in the data layer's call sites, already parameterized.
