# LOGGING.md

## Server

- uvicorn access/error logs to stdout/stderr; the installer starts the
  server with nohup into `~/.pati/server.log` (POSIX) or a Hidden window +
  Task Scheduler (Windows — redirect via `pati-server > log 2>&1` if
  desired).
- Orchestrator writes task-scoped log lines into the `logs` table (level,
  task, stage, worker, message, ts) — these are what `GET /tasks/{id}/logs`
  streams; workers push batches of the same shape.
- Security-relevant actions additionally land in `audit`.

## Local Agent

- Job logs: streamed to the control plane AND printed to stdout (service
  templates capture to files on macOS/Windows).
- Audit JSONL (`audit.jsonl`): hash-chained records for every filesystem
  operation, permission change, policy violation, wizard completion,
  heartbeat registration. `pati-agent doctor` verifies the chain.

## Rules

- Never log token plaintext, connector secrets, artifact bytes, or full
  file contents (paths + sizes only).
- Log levels: info (normal), warn (requeues, quota parks), error (failures).
- Rotation is left to the OS (logrotate/journald) by design — no extra
  dependencies.
