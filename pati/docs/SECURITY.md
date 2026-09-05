# SECURITY.md

## Threat model

PATI runs on the owner's PC and talks to free external services. Adversaries
considered: (a) a compromised or curious Personal AI client, (b) a malicious
task objective (prompt injection via web content), (c) network attackers on
the tunnel path, (d) a stolen token, (e) supply-chain compromise of
dependencies.

## Authentication

- Bearer tokens only. Stored as sha256 hashes; plaintext shown once at
  creation. Bootstrap admin token is written to the data dir with 0600 and
  its creation is audited.
- Token kinds: **admin** (all scopes), **client** (task/artifact/research
  scopes), **worker** (bound to exactly one worker id; job + artifact scopes
  for itself only).
- Worker pairing: a 6-digit one-time code (15-minute TTL, single use)
  exchanges for a worker token — no admin secret ever touches the new
  machine. See `docs/AUTH.md`.

## Authorization

- Every endpoint declares a required scope (`security.require(scope)`).
- Worker endpoints double-check worker binding (`require_worker_self`): a
  worker token cannot act as another worker, cannot complete foreign jobs,
  cannot read foreign artifacts (artifact reads are tenant-scoped and the
  content endpoint re-checks ownership).
- Rate limiting: sliding window per token (default 240 req/min; a 429 is
  explicit, never silent).

## Filesystem authorization (Local Agent)

- Explicit allowlist of absolute folders. The user adds/removes roots via
  `pati-agent authorize-folder add|remove|list` or the wizard.
- `PolicyEngine.validate_path` (pati_agent/policy.py) rejects, before any
  syscall: null bytes, wildcards, relative escapes (`..`), absolute paths
  outside every root, symlinks resolving outside a root (both file and
  intermediate-component symlinks), and deleting an authorized root itself.
- Windows/POSIX normalization: `Path.resolve()` + case-insensitive
  comparison via `os.path.normcase` (paths are compared post-resolution, so
  `..`, duplicate separators and 8.3-style tricks cannot smuggle escapes).
- Operations map to permissions (READ/CREATE/MODIFY/COPY/MOVE/DELETE,
  SAVE_ARTIFACTS). Dangerous ones (DELETE_FILES, EXECUTE_COMMANDS,
  RUN_SCRIPTS, RUN_LOCAL_MODELS) are **disabled by default** and are granted
  only through explicit user action; every grant/revocation is audited.

## Sandboxing and resource limits

- Commands: exact argv allowlist (basenames, e.g. `python3`, `ffmpeg`); no
  shell interpolation; environment scrubbed of credential-prefixed vars.
- POSIX: rlimits for CPU, address space, file size and process count inside
  a detached process group; hard timeout with process-group kill.
- Windows: timeout + allowlist enforced; Job Objects documented as the
  hardening path (`docs/SANDBOX_SPEC.md`).
- Control plane: upload size cap (MAX_UPLOAD_MB), stage deadlines,
  per-tenant quotas (concurrency, daily tasks, GPU minutes, artifact MB).

## Audit and tamper evidence

- Local Agent: JSONL, hash-chained (`hash = sha256(prev_hash + record)`);
  `verify()` recomputes the chain; `pati-agent doctor` reports integrity.
  Chain events are pushed best-effort to the central audit table.
- Control plane: `audit` table records token issuance/revocation, worker
  registration/shutdown, connector changes, policy and tool changes.
- Never logged: token plaintext, connector secrets, artifact bytes.

## Secrets and dangerous data

PATI never reads or exposes: SSH keys, wallet credentials, browser profiles/
cookies, password stores, production secrets — they are simply not in the
allowlist, and the wizard explicitly warns against authorizing those
locations. Connector tokens live in the control-plane data dir with 0600
(POSIX); the agent never sees them.

## Network posture

- The Local Agent makes outbound connections only; it never listens.
- The control plane binds 127.0.0.1 by default; `--public` + the Cloudflare
  tunnel option still require bearer tokens for every call.
- SSRF surface is minimal: the control plane calls only configured connector
  endpoints; the agent downloads only artifact content from its own control
  plane over the authenticated client.

## Supply chain

Dependencies are few and pinned loosely in `pyproject.toml`; licenses and
free status are recorded in `docs/LICENSE_POLICY.md`. Dependency scanning is
on the roadmap (`docs/ROADMAP.md`, CI_CD).

## Known limitations (honest)

- Single-process control plane (SQLite) is not hardened for hostile
  multi-tenant load yet — see `docs/MULTI_TENANCY.md`.
- Windows sandboxing uses timeout+allowlist, not Job Objects yet.
- TOCTOU on the agent path validation is mitigated but not elimination-proof
  on all filesystems; dangerous permissions stay off by default for this
  reason.
