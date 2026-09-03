# AUTONOMY.md

Autonomy levels gate what PATI may do without fresh human approval.
`ZERO_APPROVAL` (pre-authorized safe operations) never implies unrestricted
or destructive access.

| Level | Meaning | Examples in PATI |
|---|---|---|
| 0 | READ ONLY | fs.list, fs.read, sys.report, GET endpoints |
| 1 | SAFE LOCAL | fs.create/move/copy inside allowlist, report.markdown |
| 2 | SANDBOXED INSTALL | tools/install (registry-gated) |
| 3 | SANDBOXED EXECUTION | script.run, command.run (allowlist + rlimits), coding_agent |
| 4 | EXTERNAL SERVICE | connectors, web_research, browser_automation (planned) |
| 5 | PRODUCTION | deployment, CI_CD (future, explicit approval) |
| 6 | DESTRUCTIVE | fs.delete — dangerous, default OFF, per-op audited |

## Enforcement

- Each capability declares `min_autonomy_level`; risky capabilities are
  flagged in the registry.
- The Local Agent's permission model is the hard gate for local_fs
  capabilities: DELETE_FILES / EXECUTE_COMMANDS / RUN_SCRIPTS /
  RUN_LOCAL_MODELS are granted only by explicit owner action, and the
  doctor flags when they are on.
- The control plane's autonomy comes from quotas + deadlines + circuit
  breakers; it cannot escalate itself.

## Automatic-but-safe (ZERO_APPROVAL)

Heartbeats, capability sync, watchdog requeues, log/artifact bookkeeping,
task status transitions, quota consumption — all Level 0-1 and fully
automatic. Anything touching external services or destructive operations
stays behind explicit configuration or approval.
