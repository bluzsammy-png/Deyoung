# DATABASE.md

Engine: **SQLite** (public domain) in WAL mode — $0, zero-ops, single file
at `<data>/pati.db`. The RLock-serialized connection layer (`pati_api/db.py`)
makes concurrent access safe within one control-plane process, which is the
supported deployment (see `docs/DEPLOYMENT.md` for the multi-process swap
path: Postgres adapter behind the same helper API).

## Migrations

Ordered, idempotent scripts in `db.MIGRATIONS` with a `schema_version`
table. Adding a schema change = append a new script; existing databases
upgrade on boot. Fresh installs run all of them.

## Entities (all carry tenant_id where multi-tenancy applies)

- **Identity**: tenants, users, tokens (hashed, scoped, kind, worker
  binding), pairing_codes (single-use, TTL).
- **Registries**: registered_capabilities / registered_models /
  registered_tools (DB overrides merged over code catalogs),
  installed_tools (tool lifecycle).
- **Execution**: workers (capabilities JSON, status, health, resources,
  failure_count), tasks (plan, status, trace_id, priority, cost=0),
  stages (op, params, depends_on, group, job_id, retry_count, deadline),
  artifacts (sha256 checksum, storage=control_plane|local_reference,
  provenance, visibility), logs (cursor-friendly autoincrement).
- **Observability**: events, audit, health_checks, benchmarks.
- **Policy/ops**: policies (key/value, FREE_ONLY keys immutable),
  quotas + usage_counters (per tenant per day), connectors,
  deployments, secrets_metadata (metadata only — never secrets), kv.

## Integrity notes

- Token plaintext never stored; sha256 hashes only.
- Artifact bytes live outside the DB (content-addressed files), DB stores
  checksum + location.
- JSON columns are TEXT; readers parse defensively (tests cover both).

## Replacement path

`db.query/execute/kv_*` is the only surface orchestration uses; a Postgres
implementation of that surface (asyncpg or psycopg) is a drop-in upgrade
for SaaS scale — no orchestration code changes.
