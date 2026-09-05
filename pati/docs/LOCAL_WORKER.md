# LOCAL_WORKER.md

The Local Agent (`pati_agent/`) is the secure bridge between PATI and your
computer. A browser Personal AI cannot touch your disk; the agent can —
only inside the folders you authorize, only with the permissions you grant.

## Install experience (12 steps)

`pati-agent setup` walks through: (1) PATI server URL, (2) one-time pairing
code from `pati admin-pair`, (3) name this computer, (4) authorize folders
(create-if-missing supported), (5) permissions (dangerous ones OFF),
(6) hardware detection, (7) capability registration, (8) connection test,
(9) filesystem write/read/delete self-test, (10) task-execution check,
(11) autostart (Task Scheduler / launchd / systemd), (12) finish — writing
`config.json` (0600) and starting the audit chain.

The Windows installer (`installer/install.ps1`) automates prerequisite
checks, venv, PATI install, control plane start, pairing code and the
wizard. Uninstall: `installer/uninstall.ps1` (data kept with `--keep-data`).

## Runtime

- Outbound-only: heartbeats (CPU/RAM/disk/GPU + capability sync every 15 s)
  and a long-poll job loop. Never listens on a port.
- Job handling: fetch job → check task not cancelled → enforce policy →
  execute op → stream logs → upload artifacts (small files multipart; big
  files as local references) → complete. Policy violations return
  SECURITY_VIOLATION and quarantine the task instead of retrying.

## Operations supported

fs.list, fs.read, fs.mkdir, fs.create_file, fs.copy, fs.move, fs.delete,
fs.organize (compound: create project folder + classify/move media by type
+ manifest), artifact.save (download or local copy), report.markdown,
research.local_search, sys.report, script.run / command.run (sandboxed,
permission-gated), plus simulated text/image/video/audio generators
(clearly labeled; identical protocol to real model workers).

## Folder authorization management

```bash
pati-agent authorize-folder list
pati-agent authorize-folder add "D:\Projects\Video"
pati-agent authorize-folder remove "D:\Projects\Old"
pati-agent permissions list            # * = granted
pati-agent permissions grant RUN_SCRIPTS
pati-agent allow-command add ffmpeg    # EXECUTE_COMMANDS allowlist
```

Capability changes sync to the control plane on the next heartbeat, so
routing reflects policy immediately.

## Diagnostics and updates

- `pati-agent doctor`: config, reachability, token, folder existence +
  writability, dangerous-permission warning, audit-chain integrity — each
  with an actionable fix line.
- `pati-agent update`: checks `/system/updates` (free channels only) and
  applies `pip install --upgrade pati` with `--yes`.
- `pati-agent status`: config summary without secrets.

## Files

Windows: `%USERPROFILE%\PATI\agent\config.json`, `audit.jsonl`;
POSIX: `~/.pati/agent/`. The agent data dir holds config + audit only —
no credentials beyond its own worker token.
