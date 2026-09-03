# RESEARCH_ENGINE — The Research-Before-Build Loop, Formalized

PATI's most important rule is "research before implementation"
(MASTER_PRD). This document turns that rule into a repeatable engine: how
research requests are raised, verified, recorded, and re-verified over time.

## 1. The core loop

```
  need detected                    (new capability, model, service, or doubt
        │                           about an existing one)
        ▼
  research request                 one row in the research queue:
        │                          question, constraints, deadline
        ▼
  candidate scan                   sources: official docs, license text,
        │                          pricing pages, ToS — primary sources only
        ▼
  verification                     license OSI check, cost check ($0 forever?),
        │                          ToS read, fallback plan check
        ▼
  decision                         ACCEPT / REJECT / TRIAL (local sandbox only)
        │
        ▼
  record                           row in docs/RESEARCH_REPORT.md:
                                   name, license, cost, source URL,
                                   verification date, decision + reason
        │
        ▼
  implementation only if ACCEPT    registry entry → tests → docs
```

## 2. Source hierarchy (what counts as evidence)

1. **License text** — the file itself (GitHub LICENSE, HF model card tag).
   Blog posts about licenses are not licenses.
2. **Official pricing page** — archived/quoted with date. "Free" claims
   need the ceiling in writing (rate limits, quota, account requirements).
3. **Official API/model cards** — for capability claims (context length,
   output formats).
4. **Community signals** (issue trackers, forums) — for *reliability*
   hints only, never as license/cost evidence.

Secondary sources (news, rankings, "top 10" posts) may *find* candidates
but cannot *verify* them.

## 3. The verdict rubric

A candidate is ACCEPT-able only with every box checked:

| # | Question | Evidence |
|---|----------|----------|
| 1 | Free forever (not expiring credits)? | pricing page quote + date |
| 2 | No payment method required? | signup flow tested or documented |
| 3 | License compatible (personal + intended use)? | license text name + bucket (LICENSE_POLICY §3) |
| 4 | ToS compatible with automated use? | ToS section quoted |
| 5 | Graceful degradation exists when the resource is absent? | design note (RESOURCE_UNAVAILABLE path) |
| 6 | Official source for downloads/API? | URL in the row |

TRIAL status: sandboxed local testing allowed (never on the real control
plane); the trial gets a deadline and either converts to ACCEPT with a row,
or dies. Nothing lives in TRIAL indefinitely — that's how paid dependencies
sneak in.

## 4. Artifact: the research report

`docs/RESEARCH_REPORT.md` is the engine's output ledger. Its row format:

```
| Name | Kind | License | Cost | Source URL | Verified | Decision |
```

- **Append-only by hand;** corrections get a new dated row (never silent
  edits) — license/cost drift is thus visible in the ledger itself.
- Registries reference report rows: a registry entry whose row is missing
  fails the registry-audit test (CI_CD §1 stage 5).

## 5. Scheduled re-verification (drift detection)

Licenses change; free tiers shrink. The engine therefore re-verifies:

| Cadence | Scope | Trigger |
|---------|-------|---------|
| Quarterly | all model rows + paid-adjacent services (Kaggle ToS, tunnel terms) | calendar |
| Per release | every registry entry has a report row | CI test |
| On suspicion | any row, immediately | issue/PR flags drift |

Re-verification = re-open the primary source, confirm license/cost, add a
dated row. A failed re-verification starts a deprecation: registry entry
flagged → EVALUATION runs the swap test (better free replacement?) → removal
PR with a migration note.

## 6. Research request template (copy into an issue)

```
Question:        (what must be true/false?)
Candidates:      (names you already suspect)
Constraints:     (free-first, license bucket, Windows-first)
Primary sources: (links you plan to verify)
Deadline:        (date)
Decision owner:  (who records the row)
```

## 7. Why this engine exists (the honest reason)

Free-first stacks rot *silently*: a license changes, a free tier closes,
and six months later the project is accidentally violating ToS or built on
a dead service. The research engine's only job is to make that rot **loud**
— dated rows, scheduled re-checks, CI-enforced linkage — so that PATI's $0
claim stays a verified fact, not a launching assumption.
