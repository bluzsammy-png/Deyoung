# TROUBLESHOOTING — Symptom → Cause → Fix

Every entry lists the observable symptom, the most common root cause, and the
exact fix. Run `pati-agent doctor` first — it checks environment, policy file,
disk space and server reachability in one shot.

## 1. Control plane

### `pati-server` does not start

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Address already in use` | Port 8000 occupied | `PATI_PORT=8001 pati-server` or stop the other process |
| `ModuleNotFoundError: fastapi` | Wrong Python / venv not active | Re-run `pip install -e .` inside `.venv` |
| `sqlite3.OperationalError` on boot | Corrupt DB from a hard crash | Restore `pati.db.bak` or delete `pati.db` (see FAILURE_RECOVERY.md) |

### Health endpoint anomalies

- `GET /health` returns `max_spend: 0` and `free_only: true` **always** — that
  is by design and schema-pinned. If you see anything else, the deployment is
  not PATI or the code was modified; reinstall.
- `status: degraded` means one or more workers are offline. Check
  `GET /workers` for per-worker `last_seen` and `capabilities`.

## 2. Authentication & pairing

| Symptom | Cause | Fix |
|---------|-------|-----|
| `401 INVALID_TOKEN` | Token revoked or typo | Mint a new token: `pati admin token-create --role client` |
| `403 SCOPE_MISSING` | Token lacks the scope for that route | Compare required scope (API_SPEC.md §Auth) with `pati admin token-show` |
| Pairing code rejected | Codes are single-use and expire in 10 min | Run `pati admin-pair` again and redo wizard step 2 within the TTL |
| Agent registers then 401s | Worker token bound to another worker id | Never copy `credentials.json` between machines; re-run `pati-agent setup` per machine |

## 3. Local Agent

### Agent never claims jobs

1. Is it running? `pati-agent run` keeps a foreground loop; check the console.
2. Wrong server URL in `credentials.json` → re-run setup or edit manually.
3. Token scopes missing (`jobs:claim`) → re-pair the agent.
4. Windows Defender / firewall blocking outbound localhost? Allow Python.

### Disk operations rejected (`PATH_FORBIDDEN`)

- The path is outside the **authorized folders** chosen in wizard step 6.
  Add the folder: edit `policy.json → allowed_roots` (absolute paths), then
  restart the agent.
- Path contains `..`, a symlink escaping a root, a null byte, or targets the
  root itself for deletion — the path guard rejects these **by design**
  (docs/POLICY_ENGINE.md). There is no override; that is the point.
- `DELETE_FILES` permission is off → enable it in `policy.json → permissions`
  if you truly want deletes, then restart.

### `EXEC_BLOCKED`

- Command not in the allowlist (`policy.json → allowed_commands`).
- Command tried to write outside authorized folders or exceeded CPU/RAM/time
  rlimits. Widen the allowlist consciously; never paste a raw shell string
  from an AI into the allowlist — add the specific binary.

## 4. Workers & GPU

| Symptom | Cause | Fix |
|---------|-------|-----|
| Jobs park in `WAITING_FOR_RESOURCE` | No worker offers the capability | Register the Kaggle worker (INSTALL §6) or a container worker |
| Kaggle worker `unavailable` | Missing `~/.kaggle/kaggle.json` | Create + place the token, restart the worker |
| `QUOTA_EXCEEDED` on submit | Daily GPU-minute budget spent (default 240 min/day) | Wait for the daily window or raise the budget in quota config — never by paying |
| Kaggle `403` from kernel push | Kaggle account unverified / new GPU rules | Verify phone on Kaggle; accept GPU usage terms |
| Long-poll returns no jobs | Job's required capability not in this worker's set | This is correct behavior (per-worker dispatch); check `GET /jobs/{id}` capabilities |
| Job stuck `RUNNING` past deadline | Worker died mid-job | Watchdog reaps it automatically (next tick) or `pati admin job-cancel` |

## 5. SDK / CLI

| Symptom | Cause | Fix |
|---------|-------|-----|
| `PATIError: QUOTA_EXCEEDED` (code) | Budget, not rate limit | See §4 above |
| `PATIError: RATE_LIMITED` (code) | Per-token rate limit | Backoff; the SDK already retries with jitter |
| 429 with `RETRY-AT` | Same | Honor the header |
| `connection refused` behind tunnel | Tunnel down / URL stale | Restart `cloudflared`; Quick Tunnel URLs change on restart |

## 6. Artifacts

| Symptom | Cause | Fix |
|---------|-------|-----|
| `artifact_ref` unresolvable | Artifact GC'd or wrong store | Artifact ids are content-addressed; re-run the producing job |
| Agent can't save artifact locally | Target path outside allowed_roots | Add the destination folder to the policy and restart |
| Large artifact upload 413 | Store size cap | Raise `max_artifact_bytes` in store config or split the artifact |

## 7. MCP

| Symptom | Cause | Fix |
|---------|-------|-----|
| AI client sees no tools | Wrong stdio command | Configure client to run `python -m pati_mcp.server` (stdio JSON-RPC) |
| `TOOL_FORBIDDEN` | Client asked for admin/shell tool | MCP exposes safe tools only by design (docs/MCP_SPEC.md) |

## 8. Diagnostics checklist (copy-paste)

```bash
curl -s http://127.0.0.1:8000/health | jq
curl -s -H "Authorization: Bearer $PATI_TOKEN" http://127.0.0.1:8000/workers | jq
curl -s -H "Authorization: Bearer $PATI_TOKEN" http://127.0.0.1:8000/jobs?limit=5 | jq
pati-agent doctor
tail -n 50 ~/.pati/agent/audit.log   # hash-chained; a broken chain = tampering
```

If a test in `python -m pytest tests -q` fails after an upgrade, run it with
`-x` and open the trace; the suite is the fastest way to localize a regression
(46 tests cover both E2E flows, auth, quotas, routing and the path guard).
