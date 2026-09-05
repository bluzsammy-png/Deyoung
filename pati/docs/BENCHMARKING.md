# BENCHMARKING — Measuring PATI Without Lying to Yourself

PATI is a *system*, so its benchmarks are end-to-end and practical, not
model-league clickbait. This document defines what we measure, how, and how
results are recorded (locally, in-repo, no external services).

## 1. What we measure (and why)

| Dimension | Metric | Where it comes from | Why it matters |
|-----------|--------|--------------------|----------------|
| **Dispatch latency** | submit → first claim | orchestrator timestamps | the "feels alive" number |
| **End-to-end job time** | submit → artifact saved | job record | the only number users feel |
| **Pipeline overhead** | E2E time − Σ stage time | stage records | what PATI itself costs (target: single-digit %) |
| **Retry efficiency** | failed → recovered jobs, extra minutes | watchdog + retry records | resilience without waste |
| **Quota discipline** | GPU-minutes requested vs used | quota manager | budget adherence |
| **Agent op latency** | per-fs-op, per-exec | agent audit log | local plane responsiveness |
| **Path guard cost** | guard decision time | policy engine | security must be free enough to always-on |
| **Suite time** | pytest wall time | CI/local | stays under a minute as tests grow |

Explicitly **not** benchmarked: model quality league tables (that's
EVALUATION.md's job, task-based), tokens/sec bragging (meaningless across
free tiers), anything requiring paid APIs.

## 2. Method

1. **Environment row first.** Every result table starts with: host CPU/RAM,
   OS, Python, network (for Kaggle jobs: queue time is *reported* but
   flagged as external — PATI can't control Kaggle's scheduler).
2. **N runs, medians.** Local ops: N=20 medians. Pipeline E2E: N=5 (Kaggle
   queue variance is real). Outliers > 3σ noted, not silently dropped.
3. **Mock vs real.** Two columns where relevant: in-process mock worker
   (pure PATI overhead) vs real Kaggle (includes external reality). Never
   mix them in one number.
4. **Timestamps come from the system**, not from wrapping demos in timers —
   the orchestrator already records `created_at/claimed_at/completed_at`;
   the benchmark script just aggregates.

## 3. Baseline results (recorded 2026-09-02, dev machine)

Numbers below are the shipped baselines from the E2E examples and test
suite; treat them as *order-of-magnitude anchors*, not SLAs:

| Measurement | Baseline |
|-------------|----------|
| Test suite (46 tests) | ~14 s |
| Dispatch latency, local worker (mock) | tens of ms |
| Flow 1 (disk organize, E2E) | < 1 s |
| Flow 2 (15-stage video pipeline, mock GPU worker) | seconds |
| Flow 2 (real Kaggle) | minutes, dominated by queue + kernel runtime |
| Path guard decision | sub-millisecond class |
| Control plane cold boot | ~1 s (SQLite migrations included) |

## 4. Benchmark scripts & storage

```
scripts/bench_local.py     # agent ops + dispatch latency (in-process)
scripts/bench_pipeline.py  # 15-stage pipeline on mock worker, N runs
docs/BENCHMARKS.md         # results log: newest table on top, env row first
```

Rules for the results log:

- One table per run batch, dated, environment row mandatory.
- Regressions > 25% vs the previous entry need a sentence of "why" (usually:
  a security check got stricter — acceptable; note it and move on).
- No external links-as-results (services die); paste the numbers.

## 5. Regression policy

- Release gate: suite time < 60 s, Flow 1 < 2 s, mock Flow 2 < 30 s,
  pipeline overhead < 10% of stage sum.
- Path guard additions (new deny rules) may add microseconds — always fine;
  anything measurable in *milliseconds* needs a look at the implementation.
- Watchdog tick changes must show in retry-efficiency numbers (fewer wasted
  minutes, not more).

## 6. Honest caveats (standing)

1. Kaggle timing is a distribution, not a number: queue minutes vary by
   hour/week. Benchmarks include the queue but label it external.
2. SQLite is not a high-concurrency DB; PATI is single-operator, and
   benchmarks reflect *that* reality, not 10k-QPS fantasies.
3. All baselines are dev-machine class hardware. Reproduce with your env
   row before comparing.
4. Benchmarks measure PATI's overhead and discipline; they do not measure
   model capability (EVALUATION.md owns that question).
