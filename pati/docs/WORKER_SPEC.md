# WORKER_SPEC.md

## Universal worker interface (11 ops)

`pati_workers/interface.py::UniversalWorkerInterface`:

REGISTER, HEALTH, CAPABILITIES, RESOURCES, SUBMIT, STATUS, CANCEL, LOGS,
ARTIFACTS, HEARTBEAT, SHUTDOWN.

Two styles implement the same contract:

1. **Pull workers** (`BasePullWorker`): dial the control plane, heartbeat,
   long-poll `GET /workers/{id}/jobs/next` (up to 30 s), execute, stream
   logs, complete with artifacts. Outbound-only — works behind home NAT.
   Used by the Local Agent and any remote free worker (the E2E test double
   is a real HTTP pull worker).
2. **Push workers** (`KaggleWorker`): the adapter submits batch jobs to an
   external free service and polls status/artifacts. Ephemeral by design.

## Worker types

LOCAL_WORKER, KAGGLE_WORKER, CONTAINER_WORKER, BATCH_WORKER,
REMOTE_FREE_WORKER, OPTIONAL_CLOUD_WORKER, BROWSER_WORKER, CPU_WORKER,
GPU_WORKER, VIDEO_WORKER, AUDIO_WORKER, IMAGE_WORKER, CODING_WORKER,
RESEARCH_WORKER, DEPLOYMENT_WORKER.

A worker's `type` is identity; its `capabilities` (declared at registration,
synced on heartbeat) drive routing. Kaggle/Colab are compute workers —
never the control plane.

## Registration & lifecycle

1. Pairing code → `POST /workers/register` → worker token (bound).
2. Heartbeat every ~15 s: resources (CPU/RAM/disk/GPU), optional capability
   sync, health (healthy/degraded via circuit breaker).
3. Jobs: claim → RUNNING → complete(SUCCEEDED/FAILED/CANCELLED) with
   result JSON, logs, artifacts (uploaded files or path_ref references).
4. Watchdog: no heartbeat for `PATI_WORKER_OFFLINE_AFTER_S` (60 s) → offline
   + stage requeue. Circuit breaker: `PATI_CIRCUIT_FAILURES` (3) consecutive
   failures → health=degraded → router deprioritizes.
5. Shutdown: explicit offline + audit entry.

## Security

Worker tokens are bound to one worker id; a worker can only see, run and
complete its own jobs; artifact uploads are size-capped; audit events are
pushed with tamper-evident chains from the agent.
