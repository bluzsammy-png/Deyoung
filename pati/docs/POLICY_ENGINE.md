# POLICY_ENGINE.md

Two layers of policy, both enforced in code (not convention):

## 1. System policy (control plane)

`pati_api/config.py::POLICY` — the hard $0 guarantees:

FREE_ONLY=true, PAID_SERVICES/APIS/MODELS/COMPUTE/HOSTING/STORAGE/DATABASES/
FALLBACKS=false, AUTO_BILLING=false, CREDIT_CARD_REQUIRED=false,
MAX_SPEND=0, MAX_AUTOMATIC_SPEND=0.

- Surfaced publicly at /health, /system/status and the status page.
- Enforced by `registries.enforce_free_only` (rejects cost>0 or paid
  free_status entries; rejection is audited).
- `PUT /admin/policies/{key}` refuses to disable any hard-true key — the
  owner cannot accidentally (or an attacker with the admin token cannot
  easily) flip the $0 guarantee; the policy schema also pins FREE_ONLY=true
  and MAX_SPEND=0 as consts.
- Custom policies live in the `policies` table (key/value + updated_at).

## 2. Local policy (Local Agent)

`pati_agent/policy.py::PolicyEngine` — the folder allowlist + permission
model:

- `allowed_roots`: absolute authorized folders only.
- `permissions`: READ/CREATE/MODIFY/COPY/MOVE/DELETE_FILES,
  EXECUTE_COMMANDS, RUN_SCRIPTS, RUN_LOCAL_MODELS, SAVE_ARTIFACTS —
  dangerous ones OFF by default.
- `allowed_commands`: exact basenames for EXECUTE_COMMANDS.
- `validate_path`: the last line of defense before any syscall
  (traversal/symlink/escape defense — details in docs/SECURITY.md).
- `capabilities()`: derives the worker capability set from granted
  permissions, synced to the router via heartbeat — policy changes remap
  routing without restarts.

## Violations

`PolicyViolation` → job fails with error_code SECURITY_VIOLATION → the
orchestrator **quarantines** the task (no retry), records the event, and
the attempt lands in both audit trails. Security failures are never
retried blindly.
