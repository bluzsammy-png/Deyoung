# EVALUATION — Task-Based Quality Assessment

BENCHMARKING.md measures the *system* (speed, overhead, discipline). This
document measures **outcomes**: does PATI, using its free models and tools,
actually accomplish the tasks you give it? The unit of evaluation is the
**golden task** — a concrete input with a checkable output.

## 1. Golden task format

```json
{
  "id": "fs.organize.youtube-01",
  "capability": "fs.organize",
  "utterance": "Create a folder called YouTube Project 01 in my workspace,
                then make subfolders: scripts, b-roll, thumbnails, exports",
  "setup": ["workspace/ exists"],
  "checks": [
    {"type": "path_exists", "path": "workspace/YouTube Project 01"},
    {"type": "path_exists", "path": "workspace/YouTube Project 01/scripts"},
    {"type": "audit_event", "event": "fs.mkdir", "min": 5}
  ],
  "weight": 1.0
}
```

Checks are structural (paths exist, artifact exists, audit events fired) or
content (regex/keyword for text, dimensions/duration for media). LLM-as-
judge is allowed only *locally* (open-weights model via PATI itself) and
only for open-ended text quality — with the judge model recorded in the
result row.

## 2. Suite composition (per capability)

| Capability | Golden tasks (seed set) | Check style |
|------------|--------------------------|-------------|
| fs.mkdir / fs.write / fs.organize | 15 | structural + audit |
| exec.run (allowlisted) | 8 | stdout match + rlimits held |
| text.generate | 10 | keyword/length + local judge |
| image.generate | 6 | dimensions + CLIP-less heuristic (filesize/palette sanity) + manual spot row |
| tts / stt | 6 | duration sanity; WER on a tiny fixed corpus |
| video.pipeline | 3 | full 15-stage run: artifacts at every stage, final duration/size sane |
| research.collect | 5 | source count + dedup + all sources free-tier |
| connectors.github | 5 | fixture repo: create/update/read round-trip |
| mcp tools | 5 | JSON-RPC round-trips |

Seed set lives at `tests/evaluation/golden/*.json` (extensible; the runner
is `scripts/eval_run.py`).

## 3. Scoring

- **Task score:** 1.0 if every check passes, else fraction passed × weight;
  security violations (path guard denial where the task *should* succeed) are
  automatic 0 with a `guard_blocked` tag — a task that fights the guard is a
  bug in the task or the planner, never a reason to weaken the guard.
- **Suite score:** weighted mean, plus three health metrics that matter more
  than the mean:
  1. **`RESOURCE_UNAVAILABLE` rate** — how often free resources were simply
     absent (informational; parking is correct behavior, not failure).
  2. **Quota overrun** — must be 0. Always.
  3. **Guard bypass attempts** — must be 0. Always.
- **Per-model attribution:** every result row records the model id used, so
  model swaps show up as before/after columns, not mysterious drift.

## 4. When evaluation runs

1. **Before planner/router changes** (they change *which* tool gets the
   task — outcome-sensitive).
2. **Before model registry additions/removals** (swap impact).
3. **Before releases** (full suite).
4. **After "why is this worse now" incidents** (targeted capability suite).

It does not run on every commit — the 46-test suite remains the fast gate;
evaluation is the deep check.

## 5. Recording results

`docs/EVALUATIONS.md` (results log, newest on top):

```
2026-09-02  suite=v1  n=68  score=0.87  unavailable=6  quota_overrun=0
            guard_bypass=0  models: qwen2.5-7b, sdxl-base, whisper-small
            notes: video.pipeline task 3 failed on stage 12 QA (duration
            mismatch) — planner produced wrong concat order; fixed in <PR>
```

Rules: environment row, model ids, raw score + the three health metrics,
and a notes line for every failure. A result without its failure notes is
considered marketing, not engineering.

## 6. The evaluation philosophy

- **Tasks, not vibes:** "make a 30s video" with a checkable duration beats
  "rate the video 1-10."
- **Free stack, judged honestly:** if the free model can't pass a task, the
  row says so; the fix is a better free model (research row → registry) or a
  better planner decomposition — never a paid API.
- **Security is a check, not a tradeoff:** no task score can buy back a
  guard bypass; those rows are red lines.
- **Small and honest beats big and fake:** 68 structural, reproducible tasks
  are worth more than a 10k-task benchmark nobody reruns.
