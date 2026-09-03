# SANDBOX_SPEC.md

## Local command/script execution (pati_agent/execops.py)

Preconditions (all required): RUN_SCRIPTS or EXECUTE_COMMANDS granted,
command basename in the explicit allowlist (`pati-agent allow-command`),
scripts located inside an authorized folder.

Controls applied to every execution:

- argv array only — no shell interpolation, no string concatenation.
- Environment scrubbed: credential-prefixed variables (PATI_TOKEN, AWS_,
  GOOGLE_, KAGGLE_, GITHUB_TOKEN...) removed; PATH preserved.
- Working directory must validate against the allowlist.
- POSIX: preexec hook sets RLIMIT_CPU, RLIMIT_AS, RLIMIT_FSIZE, RLIMIT_NPROC
  and starts a new session (setsid) so the whole tree can be killed.
- Hard timeout (default 120 s, cap 1800 s) with process-group SIGKILL.
- Output captured and truncated (20 KB streams) into job logs.

## Windows hardening path

v1 enforces allowlist + timeout + env scrub. Documented next step: a Job
Object with JOB_OBJECT_LIMIT_PROCESS_MEMORY / JOB_OBJECT_LIMIT_CPU_RATE and
CREATE_BREAKAWAY_FROM_JOB for nested processes; plus optional restricted
tokens. Tracked in docs/ROADMAP.md.

## Control-plane sandboxing

- python-multipart upload caps (MAX_UPLOAD_MB).
- Stage deadlines (STAGE_DEADLINE_S) as the outer time box for workers.
- Container worker (optional) executes jobs inside Docker with resource
  flags when Docker is present — the strongest isolation option.

## What is never sandboxed-but-allowed

- No raw shell access to any AI client, ever.
- No secrets in job environments (scrub + never injected).
- Deletion requires DELETE_FILES and refuses to remove an authorized root.
