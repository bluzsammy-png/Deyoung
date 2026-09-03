# TOOL_REGISTRY.md

Source: `pati_api/registries.py::TOOLS` + DB overrides + installed_tools
lifecycle. Exposed at `GET /api/v1/tools`; discovery at
`GET /tools/discover?q=`; validated against `schemas/tool.schema.json`.

Each tool declares: tool_id, name, description, category, capabilities,
version, source/repo/docs, license, install_method, runtime, dependencies,
hardware/network requirements, input/output schemas, health_check,
benchmark_command, security_profile, sandbox_required, worker_type,
startup/shutdown commands, status, last_verified, commercial_use,
free_status, fallback_tools, adapter, and the wire `op` workers execute.

## Local filesystem tools (Local Agent)

fs.list, fs.read, fs.mkdir, fs.create_file, fs.move, fs.copy, fs.delete
(DELETE_FILES-gated), fs.organize (compound project organizer),
artifact.save (download or local copy), report.markdown,
research.local_search, sys.report, script.run / command.run
(RUN_SCRIPTS / EXECUTE_COMMANDS + allowlist + rlimits).

## Simulated engines (clearly labeled)

sim.text_generate, sim.image_generate, sim.video_render, sim.tts,
sim.music — deterministic outputs with `simulated: true`; identical job
protocol to real model workers so swapping in Kaggle/Ollama changes
nothing for clients.

## Infrastructure / external

kaggle.kernel_run (free GPU; available_when_configured), container.run
(available_when_docker_present, sandboxed), git.commit (requires
connector), drive.read (requires connector), web.scrape (planned —
status reflects reality; never faked).

## Lifecycle

status flows: available_* → installed → active (with
DEGRADED/QUARANTINED/REMOVED states reserved by the schema). Installation
is an audited admin operation (`POST /tools/install`); fallback_tools
chains give the router substitution options (e.g., kaggle.kernel_run →
sim.* in demo mode — always free → free).
