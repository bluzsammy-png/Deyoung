# ROUTING.md

The intelligent router (`pati_api/orchestrator.py`) assigns each stage to a
worker capable of executing it.

## Matching (hard filter)

A stage is claimable by a worker iff:

1. Worker is `online` (heartbeat fresh).
2. `stage.capability` ∈ worker's declared capabilities.
3. All `depends_on` stages are SUCCEEDED.
4. Task is in an active state (QUEUED/PLANNING/ROUTING/RUNNING/VALIDATING/
   WAITING_FOR_RESOURCE).
5. GPU-budgeted capabilities require GPU-minute quota headroom.

## Scoring (soft ranking) — `pick_worker`

Among eligible workers: score = 100 − 10×failure_count − 40 (if degraded)
− min(20, heartbeat_age_minutes). Free resources are the only resources
(FREE_ONLY is structural); the score therefore ranks **free** workers by
reliability and freshness, exactly the master prompt's criteria (quality and
latency histories arrive via `benchmarks` on the roadmap).

## Pull-dispatch invariant

Stages are assigned **only to the worker whose long-poll request is being
answered** (`_claim_one`), never handed to a third worker. This prevents
cross-worker job leakage and makes multi-worker parallelism natural: two
GPU workers independently pull scene stages from the same parallel group.

## No-capacity behavior

If no free worker can serve a ready stage, `dispatch_scan` parks the task
in **WAITING_FOR_RESOURCE** — the explicit, honest RESOURCE_UNAVAILABLE
state. When a capable worker registers or comes online, the next claim
instantly resumes the task. There is no paid fallback branch anywhere in
the router.

## Cancellation and deadlines

Cancelling a task skips PENDING/DISPATCHED stages and marks the task
CANCELLED; agents check task status on job start. Stages past
`STAGE_DEADLINE_S` are requeued (up to `MAX_STAGE_RETRIES`), then failed;
workers that go silent are marked offline and their stages requeue.
