# FAILURE_RECOVERY — Failure Modes & Recovery Procedures

PATI is a local-first system: the worst case is always "reinstall the control
plane, keep your data." This document enumerates the failure modes the system
anticipates, what the software does automatically, and what a human does
manually.

## 1. Design principles

1. **Local-first state.** The SQLite database, artifact store and audit logs
   live on your disk. No cloud account holds the only copy of anything.
2. **Content-addressed artifacts.** Artifact ids are content hashes, so
   recovery = re-copying files; there is no referential "magic" to rebuild.
3. **Pull-based workers.** Workers recover by simply reconnecting and
   long-polling; there is no push socket state to lose.
4. **Fail-parked, never fail-paid.** Jobs that cannot get a resource park in
   `WAITING_FOR_RESOURCE`. Recovery is "resource appears," not "spend money."
5. **Tamper-evident audit.** The agent's audit log is hash-chained; a broken
   chain proves tampering, which recovery must treat as an incident.

## 2. Failure matrix

| # | Failure | Detected by | Automatic response | Manual response |
|---|---------|-------------|--------------------|-----------------|
| 1 | Worker dies mid-job | Watchdog deadline tick | Job reaped → status `FAILED(reason=worker_timeout)` → retry per job policy | Inspect agent logs; restart `pati-agent run` |
| 2 | Worker offline at dispatch | Long-poll absence | Job parks `WAITING_FOR_RESOURCE` | Start the worker; job resumes automatically |
| 3 | Control plane crash | OS / user | — | Restart `pati-server`; SQLite WAL recovers committed state |
| 4 | SQLite corruption on boot | `sqlite3.DatabaseError` | Boot aborts (no silent half-state) | Restore `pati.db.bak` or rebuild (§4) |
| 5 | Artifact file missing on read | Store lookup miss | `ARTIFACT_NOT_FOUND` error to caller | Re-run the producing job; ids are content hashes so re-creation is deterministic |
| 6 | Disk full during artifact save | OS error | Save fails cleanly; job fails, nothing partial | Free space; the job is re-runnable |
| 7 | Kaggle quota exhausted | Quota manager precheck | `QUOTA_EXCEEDED` before any submission | Wait for the daily window or raise the local budget |
| 8 | Kaggle token invalid | Worker registration/403 | Worker reports `unavailable`; jobs park | Replace `~/.kaggle/kaggle.json`; restart worker |
| 9 | Tunnel drops | Client connection error | Clients retry with backoff | Restart `cloudflared`; Quick Tunnel URL changes — update `PATI_SERVER` |
| 10 | Token leaked | Audit anomaly / user report | `pati admin token-revoke` | Revoke, re-mint, update clients; check audit trail for foreign calls |
| 11 | Path guard violation attempt | PolicyEngine | Operation rejected + audit event | No action needed; if unexpected, investigate who submitted the task |
| 12 | Agent policy file corrupt | JSON parse error at boot | Agent refuses to start (fails closed) | Restore from backup or re-run `pati-agent setup` |
| 13 | DB migration interrupted | Version check at boot | Boot aborts with clear message | Re-run `pati-server`; migrations are idempotent |
| 14 | Clock skew (watchdog false positives) | Deadline math | Watchdog grace period absorbs small skew | Sync OS clock if skew is large |

## 3. Job recovery semantics

- **Idempotency.** Job ids are unique; re-submitting a failed job's payload is
  always safe. Stage results that already succeeded are reused when the
  pipeline planner can match stage signatures; otherwise the pipeline re-runs
  from the failed stage (per-stage artifacts make this cheap).
- **Retry policy.** Transient failures (network, worker timeout) retry with
  exponential backoff up to the job's `max_retries` (default 2). Validation
  failures do not retry — they fail immediately with the validator's reason.
- **Cancellation.** `POST /jobs/{id}/cancel` flips the job to `CANCELLING`;
  the next claim/report transition lands it in `CANCELLED`. In-flight GPU
  work on Kaggle is best-effort abandoned (kernel deletion attempted).
- **Orphans.** If a worker reports a result for a job the orchestrator no
  longer tracks (e.g., after a DB restore), the report is logged and
  discarded — the artifact is still stored, since artifacts are
  content-addressed and harmless.

## 4. Manual recovery procedures

### 4.1 Restore the database

```bash
pati-server stop        # or Ctrl+C
cp data/pati.db.bak data/pati.db   # if a backup exists
pati-server             # boots, runs idempotent migrations if needed
```

If no backup exists: delete `pati.db` and let PATI rebuild an empty control
plane. Your tokens, workers and history are lost; **artifacts survive**
(content-addressed files) and agents re-pair in minutes:

```bash
pati admin-pair         # new code per machine
pati-agent setup        # per machine
```

### 4.2 Rebuild the artifact index

Artifacts are files named by their content hash. If the DB is fresh but the
artifact folder still has files, they remain valid: submit jobs that reference
them by recomputing the hash, or simply treat them as loose outputs. PATI
never *requires* old artifacts to accept new work.

### 4.3 Verify the audit chain after an incident

```bash
pati-agent doctor --verify-audit
```

A broken chain means someone edited the log. Preserve the file (copy, do not
truncate), then investigate which event broke the chain — everything before
the break is still trustworthy (each entry's hash covers only prior history).

### 4.4 Full clean reinstall (nuclear option)

1. `installer/uninstall.ps1|sh` — removes services, venv, (optionally) data.
2. Reinstall per `docs/INSTALL.md`.
3. Re-pair agents, re-add authorized folders (wizard step 6).
4. Re-create Kaggle token file.
5. Re-run `python examples/e2e_demo.py` to confirm the disk flow, and
   `python examples/e2e_remote_gpu.py` to confirm GPU availability.

Total expected downtime: under 15 minutes. Expected cost: $0, by definition.

## 5. What recovery deliberately does NOT do

- **No paid fallback.** If recovery needs a resource you don't have (GPU
  minutes, tunnel), PATI says `RESOURCE_UNAVAILABLE` and waits with you.
- **No silent data migration.** Version mismatches abort at boot with a
  message rather than improvising schema changes on a suspect database.
- **No auto-elevation.** Recovery never widens permissions; if the wizard
  granted DELETE and the policy now blocks it, the human re-enables it.
