# AUTH.md

## Tokens

- Format `pati_<kind>_<secret>`; sha256-hashed at rest; revocable
  (`POST /admin/tokens/{id}/revoke`); tenant-bound.
- Kinds and scope sets (`pati_api/security.py`):
  - **admin**: every scope. Bootstrap token auto-created once at first boot,
    written 0600 to `<data>/bootstrap_admin_token.txt`, creation audited.
  - **client**: tasks:read/write, artifacts:read, research:submit,
    tools:read, system:read, quotas:read, workers:read, events:read.
  - **worker**: workers:register, artifacts:write/read, system:read — plus
    a hard binding to one worker_id enforced by `require_worker_self`.

## Worker pairing flow (no admin secret on the new machine)

```
owner (any client):  pati admin-pair          -> 6-digit code, 15 min TTL
new computer:        pati-agent setup --code <code>
                     POST /workers/register {pairing_code, name, type, capabilities}
                     <- {worker_id, token}    (code burned, single use)
```

Expired/reused codes are rejected 401. Registration is audited.

## Scope enforcement

- `security.require(scope)` dependency on every protected route.
- `require_worker_self(ctx, worker_id)` on every worker route: worker-kind
  tokens must match their own id; admin/manage tokens bypass (for ops).
- Artifact content endpoint re-checks tenant ownership on every read.

## Rate limiting

Sliding window per token id (default 240/min, env `PATI_RATE_LIMIT_PER_MIN`);
exceeded → 429 RATE_LIMITED with Retry semantics. Quota rejections are a
different error (QUOTA_EXCEEDED) so clients can distinguish policy from
abuse controls.

## Personal AI clients

Z.ai (or any AI) uses a **client** token via the SDK/CLI/Z.ai adapter or
MCP. Least privilege: a leaked client token cannot manage workers, cannot
read the audit trail, cannot touch the filesystem (it has no filesystem
power at all — only the Local Agent does, inside its allowlist).
