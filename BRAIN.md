# BRAIN.md — DeYoung Studio Operating Brain

> **READ THIS FILE FIRST, EVERY SESSION.** This is the single always-current memory of the
> DeYoung AI Film Studio operation. It never contains secrets — those live only in the vault
> (see below). Append-only history lives in `worklog.md`; this file is the **current state**.
> Any AI or human taking over: follow the Session Protocol at the bottom, then continue the
> highest-priority open item in the tracker. Update this file before ending a session.

Last updated: 2026-09-07 (vault backup re-verified PASS via CLI; brain loop relaunched; fleet check 17:0xZ)

---

## 1. What this project is

**DeYoung (deyoungltd.site)** — an AI Film Production Studio: sells AI video services and
monthly video subscriptions, generates 60-second films via a free-first render fleet
(Kaggle T4 GPUs running MiniMax H3), with an owner admin panel. Built with Next.js +
Prisma + Supabase Postgres, deployed on Railway. A master upgrade prompt (uploaded
2026-09-06, canonical copy at `upload/Pasted Content_1788739243620.txt`) directs the
evolution into a full production studio (control plane, worker registry, production
manifests, credit ledger, Nigerian-law compliance, WCAG 2.2 AA). See tracker in §6.

## 2. Live infrastructure map

| Layer | What | Where / how |
|---|---|---|
| Site | Next.js app (single-page + /admin) | this repo, `src/` |
| Deploy | GitHub → Railway auto-deploy | repo `bluzsammy-png/Deyoung` (public) → Railway service "Deeyoung" |
| Live URL | https://deyoungltd.site (custom domain, live on Railway edge) | also https://deeyoung-production-72ef.up.railway.app |
| Health | `GET /api/health` → `{"ok":true,"db":true}` | healthcheck path in Railway |
| DB | Supabase Postgres | app connects via transaction pooler `:6543` (rewritten in `deploy/start.sh`); schema ops on `:5432` |
| DB schema | `prisma/schema.prisma` (sqlite dev) + `prisma/schema.postgres.prisma` (prod) | keep both in sync on every model change |
| Sandbox IP note | Railway edge 429-throttles THIS sandbox's IP ("rate limited") | verify the live site via external prober (Railway healthcheck) or web-reader, not raw curl |
| Worker plane | `/api/worker/*` (claim/deliver/status/file), `WORKER_TOKEN` env on Railway | see `docs/WORKERS.md`, `workers/deyoung_worker.py`, `scripts/kaggle_launch.py` |

## 3. Secrets vault — NEVER LOSE AGAIN

- **Local vault**: `workers/secrets/kaggle_tokens.json` (chmod 600, gitignored via `/workers/secrets/`).
- **Off-site backup (durable across sandbox resets)**: **private Kaggle dataset
  `deyoungsltd/deyoung-worker-vault`**. Re-verified 2026-09-07: owner-list found,
  round-trip sha256 content MATCH, foreign token → blocked (404).
- **⚠️ API lesson (2026-09-07)**: raw v1 REST `datasets/list?user=` and `datasets/view`
  return empty/404 **even for the owner** with Bearer KGAT auth — they give FALSE negatives.
  The official `kaggle` CLI is authoritative for dataset ops. CLI 2.2.4 auth = file
  `~/.kaggle/access_token` (KGAT), NOT `KAGGLE_KEY`. `scripts/vault_backup.py` now drives
  the CLI and self-heals the access_token file; `--verify` exits 0 only on PASS.
- **Recovery if vault file is missing** (sandbox reset):
  1. `pip install --user --break-system-packages kaggle`
  2. Put ANY valid KGAT token in `~/.kaggle/access_token` (chmod 600), then:
     `kaggle datasets download deyoungsltd/deyoung-worker-vault --unzip -p /tmp/vrec`
  3. Restore: `cp /tmp/vrec/kaggle_tokens.json workers/secrets/ && chmod 600 workers/secrets/kaggle_tokens.json`
  4. If ALL tokens are lost/rotated: owner must regenerate at kaggle.com → Settings → API → "Create New Token", then re-create vault + backup dataset.
- **Refresh the backup after any vault edit**: `python3 scripts/vault_backup.py` (CLI-based; prints VERIFY VERDICT: PASS/FAIL).
- **Rules**: never commit vault contents; never paste token values into worklog, BRAIN.md,
  spec files, or chat; reference the vault path only. Account names are NOT secret.

## 4. Render fleet (Kaggle)

- **Tokens**: 8 in vault (`w1`–`w8`). `w1` = account **deyoungsltd**, `w2` = **teslaprime**
  (both verified 2026-09-06). `w3`–`w8` = reserve, account names unknown (Kaggle v1 has no
  /me endpoint — account is discoverable at next kernel launch; record it in vault + state
  when that happens).
- **Monitor/fetch (idempotent, one pass)**: `python3 scripts/fleet_brain.py`
  (loop mode: `python3 scripts/fleet_brain.py --loop 60`). Writes `brain/state.json`
  (loop-owned `fleet` section) + appends `brain/events.log`.
- **Always-on loop (the brain pulse)**: `bash scripts/brain_boot.sh` — idempotent:
  starts `fleet_brain.py --loop 60` with nohup if not already running, records PID in
  `brain/loop.pid`, logs to `brain/loop.out`. Run it EVERY session (sandbox resets kill
  processes but not files). Check alive: `kill -0 $(cat brain/loop.pid)`.
- **Fleet state 2026-09-06 ~17:05Z**: `deyoungsltd/deyoung-h3-e`, `deyoung-h3-e2`, `teslaprime/deyoung-h3-f`, `deyoung-h3-f2` — **status RUNNING** since ~05:50Z (~11h; at/above the usual GPU session cap — completion or timeout imminent). Outputs: empty so far. `teslaprime/deyoung-worker-c` = COMPLETE (Sep 5 PATI DB-worker run; scripts archived to `campaign/v10/teslaprime__deyoung-worker-c/`). Monitor with `python3 scripts/fleet_brain.py`.
- **Film v10 plan** (from the pre-reset session, partially lost): 10 scenes `s01`–`s10`
  (MiniMax H3 on Kaggle T4, 2–9h render window) + 14 gallery clips `g01`–`g14`. When
  kernels complete: fetch outputs into `campaign/v10/<account>__<kernel>/`, inventory
  against the s/g list, assemble the film, update site refs, publish gallery works.
- **⚠️ LOST WORK WARNING**: the v10 toolchain described in the old session summary
  (`scripts/v10_inventory.py`, `v10_swap_refs.py`, `v10_finish.sh`, `film_v10_build`,
  `fleet_monitor.py`) does **NOT exist on disk** (sandbox reset). It must be REBUILT when
  the first outputs land. Do not trust the old summary's claims about files — verify on disk.

## 5. Workflow runbooks

- **Deploy**: commit → push to GitHub (needs the owner's PAT — *none stored by design*;
  ask owner when a push is required) → Railway auto-builds (`railway.toml`: prisma generate
  postgres schema → next build → standalone; `deploy/start.sh`: db push + seed + :6543 switch + serve).
- **Launch a new Kaggle GPU worker**: `KAGGLE_API_TOKEN=<token> python3 scripts/kaggle_launch.py
  --token <WORKER_TOKEN> --watch` (see `docs/WORKERS.md`). After launch, discover which
  account the token owns (kernel author) and record it in the vault.
- **Local dev**: `.env` DATABASE_URL → Supabase :6543; `bun install`; `bun run dev`.
  Schema change flow: edit BOTH prisma schemas → `prisma db push` (postgres, :5432 URL) →
  regenerate clients → test → commit.
- **QA the worker plane**: `scripts/qa_worker_plane.sh` (foreground burst).

## 6. Master upgrade tracker (the "upgrade prompt")

Canonical prompt: `upload/Pasted Content_1788739243620.txt` (79 numbered requirements; the
deliverable it demands is `markdown.md.txt` — a 56-section master upgrade specification).

| # | Phase | Status |
|---|---|---|
| 1 | Deep research (video models / MiniMax H3, free GPUs, Supabase/R2/etc. free tiers, Nigerian law, WCAG) | **DONE** (21 search result sets in `download/research/`; key finding: MiniMax H3 license reportedly excludes US/EU territories — Nigeria OK pending license-text verification) |
| 2 | Existing-code audit (stack, routes, auth, payments, worker plane, content/claims, trackers, a11y, tests) | **DONE** (5 CRITICAL + 10 HIGH + 12 MEDIUM findings, incl. leaked AgentMail key + WORKER_TOKEN in git-tracked files — see spec §A.2) |
| 3 | Write `markdown.md.txt` (56 sections incl. research tables, NOT VERIFIED / LEGAL REVIEW REQUIRED discipline) | **DONE** — deliverable at `download/markdown.md.txt` + repo-root copy; 720 lines, all 56 items mapped in §I.6 |
| 4 | Validate spec against codebase (prompt §75 checklist) | **DONE** (§I.1 self-audit) |
| 5 | Implementation waves (control plane, manifests, worker registry, credit ledger, legal pages, a11y, tests/CI) | PENDING — **start with W0 security emergencies (spec §I.4 days 1–3): rotate + purge the two leaked secrets** |

Deliverable location: `/home/z/my-project/download/markdown.md.txt` (+ repo-root copy).

## 7. Session protocol (the "AI in charge" loop)

1. Read `BRAIN.md` (this file) + last 2 worklog entries.
2. `bash scripts/brain_boot.sh` — ensure the always-on fleet loop is running (every minute).
3. Run `python3 scripts/fleet_brain.py` once — record fleet deltas into the conversation.
4. If fleet outputs landed → follow §4 film v10 chain (rebuild tooling first if missing).
5. Continue the highest **PENDING/IN PROGRESS** item in §6.
6. Before ending: update `BRAIN.md` (status + "Last updated"), append `worklog.md`, commit
   brain/spec/doc changes (never secrets, never campaign media).
7. Honesty rules: no fake progress, no unverifiable claims, mark unknowns NOT VERIFIED,
   mark legal interpretation LEGAL REVIEW REQUIRED.

## 8. Standing owner decisions / context

- Business: Nigeria-based operator; payments via Paystack/Flutterwave (+manual rails);
  founding-price urgency pricing live; no free trials.
- Film truth: the free video model cannot follow scripted dialogue (hallucinated lines) —
  v5 film uses clean TTS post-dub (ASR-verified 8/8). True lip-sync needs paid Kling/Veo
  (Atlas/Evolink keys valid but EMPTY until owner tops up).
- Owner wants: permanent memory (this brain), fleet autonomy, upgrades driven by the master
  prompt, everything free-first.
