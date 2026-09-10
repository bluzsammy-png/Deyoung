# BRAIN.md — DeYoung Studio Operating Brain

> **READ THIS FILE FIRST, EVERY SESSION.** This is the single always-current memory of the
> DeYoung AI Film Studio operation. It never contains secrets — those live only in the vault
> (see below). Append-only history lives in `worklog.md`; this file is the **current state**.
> Any AI or human taking over: follow the Session Protocol at the bottom, then continue the
> highest-priority open item in the tracker. Update this file before ending a session.

Last updated: 2026-09-10 (Task 62 MASTER UPGRADE AUDIT pushed + deployed: **DEYOUNGLTD_DEYO_MASTER_ARCHITECTURE.md** (repo root) = synchronized architecture record + 6-wave migration plan (W3.0→W3.6). W3.0 honesty pack LIVE on prod (4K claims gone, fake testimonials removed from seed, flyer prices aligned, robots fixed — verified via prod fetch). **S-1 cookie leak PURGED from all git history** (filter-repo, fsck clean, force-push; CI + Railway SUCCESS on rewritten tip) — **AUTH_SECRET rotation still REQUIRED** (purge ≠ invalidation; orphaned-commit/fork caveat) and is BLOCKED on the vault passphrase: rebuild #7 sealed the vault AND the passphrase text did not survive session compaction — filesystem sweep = zero traces (by design), owner must re-paste it. PAT push path works (one-shot URL + scripts/ci_watch_62.py commit-status watcher). H3 commercial license NOT VERIFIED = gate before scale-up)

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
  (verified 2026-09-06; RE-VERIFIED 2026-09-07 — w1 proven by downloading the private offsite
  vault dataset with it). `w3`–`w8` = reserve, account names unknown (Kaggle v1 has no
  /me endpoint — account is discoverable at next kernel launch; record it in vault + state
  when that happens).
- **2026-09-07 vault recovery**: sandbox restore wiped all gitignored files incl. the vault;
  owner re-provided all 8 KGAT tokens in chat → vaulted, identities reconciled 1:1 against
  the offsite backup (downloaded with w1 → exact match, 8/8). Offsite backup refreshed →
  VERIFY PASS. Brain loop REVIVED. Campaign dir (incl. h3-kernel-src copy) still lost —
  re-pull kernel source from Kaggle when relaunching (`kaggle kernels pull <ref>`).
- **Monitor/fetch (idempotent, one pass)**: `python3 scripts/fleet_brain.py`
  (loop mode: `python3 scripts/fleet_brain.py --loop 60`). Writes `brain/state.json`
  (loop-owned `fleet` section) + appends `brain/events.log`.
- **Always-on loop (the brain pulse)**: `bash scripts/brain_boot.sh` — idempotent:
  starts `fleet_brain.py --loop 60` with nohup if not already running, records PID in
  `brain/loop.pid`, logs to `brain/loop.out`. Run it EVERY session (sandbox resets kill
  processes but not files). Check alive: `kill -0 $(cat brain/loop.pid)`.
- **v2 RELAUNCH PLAN (2026-09-07, "go" executed)**: root cause of the 12h/empty failure = 158f@1376x768 jobs exceed any sane T4 budget + v1's 90-min per-job abort killed every render before it could finish. v2 kernel (`scripts/h3v2_make.py`): shrunk jobs (native 768p band 1376x768, len=80, 4-step turbo), NO mid-render abort (6h watchdog instead), 11h hard-cap skip-guard with adaptive rate calibration, status.json heartbeat to /kaggle/working every 30s poll. CANARY: `deyoungsltd/deyoung-v2-s01` (s01 @960x544x121 — pushed 2026-09-07 ~23:07Z, RUNNING) proves the render->output->harvest chain before wave 2. THE GATE IS AUTONOMOUS: `fleet_brain.py relaunch_step()` polls the canary every 60s — on COMPLETE it harvests via the normal fleet pass, verifies (mp4 ≥1MB + result.json ok=true, 5-poll grace), then pushes wave 2 with per-account vault tokens (state saved after EACH push; failures retry up to 3x then abandon that slug; ERROR/CANCEL/failed-verify = GROUND STOP recorded in state). WAVE 2 STAGED (dirs built, NOT pushed; the gate fires them): v2-jc-a(jimcreat)=s02+s03, v2-bx-a(bittrexminingltd)=g09+g10, v2-yw-a(youngwilly)=g11+g12, v2-wk-a(wikeyoung5)=g13+g14, v2-tp-a(teslaprime)=s07, v2-bx-b(bittrexminingltd)=s08. Account names DISCOVERED 2026-09-07 (kernels list --mine): w3=jimcreat, w4/w6=bittrexminingltd, w5=teslaprime(2nd token), w7=youngwilly, w8=wikeyoung5. Quota model — deyoungsltd + teslaprime ~24 GPU-h burned this week (~6h left) -> wave 2 leans on the 4 fresh accounts; teslaprime gets 1 job only. KNOWN GAPS: v10 prompts for s04-s06, s09-s10, g01-g08 are LOST (only 11 jobs survived in kernel sources; master spec has no scene list) -> regeneration task needed. Tradeoff: all wave-2 jobs 4-step (8-step quality deferred to fresh-quota re-renders).
- **⚠️ Fleet state 2026-09-07 ~17:51Z**: ALL FOUR film kernels → `cancelAcknowledged` at 12h01m after push (= Kaggle 12h GPU session cap), outputs EMPTY — the v10 renders were lost, not completed. Recovery: `kaggle kernels pull <ref>` → `kaggle kernels push` re-runs the identical kernel source (source survives on Kaggle; the local kernel dir was lost in the sandbox reset). Kernel source RECOVERED from Kaggle to campaign/v10/h3-kernel-src/ (ComfyUI + H3 GGUF; deyoung-h3-e embedded jobs s01-s03 at 1376x768 len=158 steps=4-8 — only a 90-min PER-JOB timeout, no self-cancel; 3 scenes did NOT finish in 12h on T4). RELAUNCH DECISION NEEDED (owner or next session): a blind re-push likely loses another 12h; the render plan must shrink per kernel (fewer steps / fewer frames per job / split scenes across more kernels within the 30 GPU-h weekly quota) — classify: INFRASTRUCTURE BLOCKER (Kaggle 12h cap) + plan redesign (spec C.4/C.5 checkpointing).
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

- **Deploy**: commit → push to GitHub → Railway auto-builds (`railway.toml`: prisma generate
  postgres schema → next build → standalone; `deploy/start.sh`: db push + seed + :6543 switch + serve).
  Push mechanics (Task 41 verified): `git push [force] "https://x-access-token:$PAT@github.com/bluzsammy-png/Deyoung.git" main:main`
  — PAT lives in `workers/secrets/github.json` (0600; chat-exposed → owner rotates at github.com/settings/tokens);
  token used one-shot in the URL, never saved to remotes/credential helpers. Pre-push gate:
  `python3 scripts/prepush_secret_scan.py` (vault-literal + pattern sweep over full history, exit 1 = do not push).
  Every push fires: gitleaks CI (secret-scan.yml) + Railway auto-deploy (commit status written back to GitHub).
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
| 5 | Implementation waves (control plane, manifests, worker registry, credit ledger, legal pages, a11y, tests/CI) | **W0 EXECUTED 2026-09-07** (see below) — **W1 storage_v2 + RateLimit EXECUTED 2026-09-07** (see below) — **2026-09-10 SUPERSEDED by the Master Upgrade Instruction (Task 62)**: canonical plan = `DEYOUNGLTD_DEYO_MASTER_ARCHITECTURE.md` §16 (waves W3.0→W3.6 + W4); that doc also supersedes this tracker for status (§20 §-by-§ table) |

**W1 state (2026-09-07, Task 35):**
- ✅ Supabase credentials vaulted (`workers/secrets/supabase.json`, 0600) + offline backup VERDICT PASS; vault_backup.py now backs up the WHOLE vault dir (fixed latent PATH bug).
- ✅ **CRITICAL: the Supabase project is SHARED with another app** (33 trading tables in `public`). All DeYoung tables live in the dedicated **`deyoung` schema** (pushed, E2E-verified; `public` untouched). Any DeYoung Postgres URL MUST carry `?schema=deyoung` — `deploy/start.sh` auto-injects it (guard prevents `--accept-data-loss` from dropping the other app's tables on a bare URL).
- ✅ storage_v2 E2E ALL PASS (11/11) against real Supabase via the real adapter: put/sign/round-trip/private-reject/stat/delete + local fallback + RateLimit + :6543 pgbouncer. Private bucket `deyoung-media`. Known artifact: GET may serve deleted bytes for a short CDN window — authoritative deletion proof = 2nd DELETE returns `NoSuchKey`.
- ✅ RateLimit table (both schemas) + Postgres-backed limiter with in-memory fallback; `guard()` async, 8 route call sites converted. C-5 /api/upload + /api/files/:id delivery (signed URLs, Range) were already in place pre-reset; now proven end-to-end.
- ✅ **C-6 leak found + purged**: OLD Supabase project ref + DB password (reused on the new project!) hardcoded in 4 diag scripts + worklog → rewritten env-driven, full-history filter-repo purge, triple-verified (pickaxe 0 / per-commit grep 0 / markers only).
- ⚠️ **OWNER ACTION (new)**: check whether the OLD Supabase project (aws-0-eu-central-1) still exists — if yes, rotate its DB password or delete the project (password reuse).
- ⚠️ **OWNER NOTE**: gitleaks CI has never actually run — the repo has no `origin` remote yet; it fires on first push (along with the W0 force-push).
- ⏳ Remaining W1 week-1–2 items (spec §I.5): Profile/LoginCode tables + relations + Decimal money + Job mapping from VideoRequest; fixing the 21 pre-existing tsc errors (still exactly 21, 0 new).


**W2 state (2026-09-07, Task 42):**
- ✅ User platform LIVE: User/StudioProject models (both schemas), dy_user cookie sessions (separate from dy_admin — owner can hold both), fail-closed status gates (banned/deactivated w/ reason), Google OAuth manual flow w/ ADMIN_EMAILS auto-promotion (owner seat deyoungsltd@gmail.com, also seeded as Admin row w/ bootstrap password), rate-limit classes signup+ai.
- ✅ Subscription-with-registration: signup → #subscribe funnel; Subscription.userId bound server-side when session email matches.
- ✅ Dashboard + AI Film Studio: GPU-life ring (plan budget vs gpuMinutesUsed, 15s live), studio pipeline Brief→Script→Scenes→Render→Delivery; /api/studio/enhance + /script (z-ai LLM, JSON-shaped) + /render (tier limits; admin = synthetic admin-free sub, priority 100, unlimited, no watermark). Renders land in the REAL queue → Kaggle worker plane claims them (/api/worker/claim) — supply depends on wave-2 fleet.
- ✅ Admin: Users tab (ban w/ reason / activate / deactivate / make-admin / revoke-admin; owner seat protected 403) + AI Studio (Free) tab.
- ✅ Gallery: 20 works, category chips (AI Film / Style Lab / Studio Work), seeded idempotently at prod boot.
- ⏳ OWNER: GOOGLE_CLIENT_ID + GOOGLE_CLIENT_SECRET on Railway (redirect URI https://deyoungltd.site/api/auth/google/callback) → Google buttons go live for users AND owner login.

**W0 state (2026-09-07, Task 34):**
- ✅ C-1/C-2 secrets purged from ALL 33 commits (git filter-repo; verified 0 hits, full-history blob scan). Working tree de-leaked (agentmail_setup.py env-only, qa_worker_plane.sh env-based, worklog redacted, tool-results/ untracked).
- ✅ **GITHUB FORCE-PUSH DONE 2026-09-07 (Task 41)**: owner provided a PAT (vaulted `workers/secrets/github.json`, 0600). Pre-push scan `scripts/prepush_secret_scan.py` = CLEAN; junk pycache/brain-runtime blobs untracked + gitignored (UUID auto-snapshot commits stripped from tip); purged history force-pushed (`1545df1 → 9c6a105 forced`) then allowlist fix `a932791`. gitleaks CI: first run FAILED on a `generic-api-key` FALSE POSITIVE ("wikeyoung5" account name contains "key" + colon in prose) → allowlisted account-name stopwords in `.gitleaks.toml` + reworded BRAIN quota line → **CI SUCCESS on a932791**. Railway auto-deployed BOTH pushes (deployments b44723fe→removed, 52c13f7f→SUCCESS): **W0/W1 code now LIVE** (rate-limit v2, storage_v2, paymentKey fix, secret-scan.yml). Railway writes commit status back: a932791 = success → 52c13f7f. Old key revocation at agentmail.to still required.
- ✅ WORKER_TOKEN CUTOVER **DONE 2026-09-07** (Task 40): owner re-provided a Railway project token (vaulted `workers/secrets/railway.json`; the 8cb7de14-… predecessor died with the sandbox wipe — no git leak, only a truncated prefix ever committed). Applied ALL 8 prod vars via GraphQL API (`scripts/railway_apply.py` — the v4 CLI rejects project tokens) to service 1a50a560… (project "QuantEdge Terminal" 99f9348d, production env a3f81c18…): `DATABASE_URL` (:5432 session +schema=deyoung), `DIRECT_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `STORAGE_DRIVER=supabase`, `AUTH_SECRET`, `ADMIN_BOOTSTRAP_PASSWORD`, `WORKER_TOKEN`=dyw_62bf… — now LIVE on green deployment dc6d060a. **Contract learned the hard way**: `deploy/start.sh` requires DATABASE_URL = SESSION :5432 (it rewrites runtime to :6543 itself) — setting :6543 directly hangs db push on pgbouncer advisory locks and fails the deploy (attempt 1; Railway kept the old release serving). Vault `_meta.railway_boot_contract` records this. Untouched: AGENTMAIL_API_KEY, NEXT_PUBLIC_SITE_URL. ~~⚠️ Railway still runs the stale Sep-6 BUILD~~ → **superseded by Task 41**: the GitHub force-push shipped W0/W1; current green build = 52c13f7f (a932791).
- ✅ Login: public creds hint removed; bootstrap password = `ADMIN_BOOTSTRAP_PASSWORD` env or random-once-in-deploy-log; session secret = `AUTH_SECRET` env → file → **fail closed** (no public fallback); cookie `secure` in production.
- ✅ Rate limiting v2 (`src/lib/ratelimit.ts`, Postgres `RateLimit` table in `deyoung` schema, §F.2 numbers, async guard() at all 8 sites, opportunistic 24h prune, in-memory fallback when DB unreachable).
- ✅ Prod Prisma query logging OFF (F.6). ✅ gitleaks CI (`.github/workflows/secret-scan.yml`; fires on first push — repo has no origin remote yet).
- ✅ C-5 /api/upload: SHIPPED (W1 storage_v2 — supabase driver + signed URLs + `/api/files/:id` authz delivery; E2E 11/11 vs real Supabase).
- ✅ Pre-existing tsc errors: **0** (was 21). W1 fixed the root causes: `publicSettings()` now carries `paymentPublicKey`+`paymentLinkUrl` (public-by-design — this was a LATENT CHECKOUT BUG: Paystack/Flutterwave/PayPal could never start), pool_check typo, skill SDK shapes; `examples/` excluded from app typecheck.
- ⚠️ 2026-09-07 SANDBOX RESTORE INCIDENT: snapshot restore wiped ALL gitignored files (vault `workers/secrets/*`, `.env.local`, `~/.kaggle`, brain loop files, kaggle CLI). Git history intact. Recovered: Supabase vault + `.env.local` re-vaulted from session context (0600, gitignored, E2E-verified), `server-only` dep re-added, WORKER_TOKEN re-staged in vault. UNRECOVERABLE without owner input: the 8 fleet KGAT tokens + old staged WORKER_TOKEN (their only other copy is the offsite Kaggle dataset, which itself needs an owner token to read).
- ✅ BRAIN LOOP UP (revived 2026-09-07 after token re-provision; pidfile `brain/loop.pid`). The canary-gated wave-2 pusher (`relaunch_step()`) lives INSIDE this loop (state machine in `brain/state.json` "relaunch", idempotent, never double-pushes). Do NOT launch `scripts/v2_wave2_watcher.py` — DEPRECATED: the sandbox reaped that long-sleeping process twice (silent kill after first poll; the 60s brain loop is the only proven-surviving host).
- **OWNER env checklist for next deploy** (values in vault `supabase.json`): `DATABASE_URL` (tx pooler, `?schema=deyoung`), `DIRECT_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `STORAGE_DRIVER=supabase`, `AUTH_SECRET` (vaulted, ≥32), `ADMIN_BOOTSTRAP_PASSWORD` (vaulted, ≥10), then WORKER_TOKEN cutover (vault runbook) + owner changes admin password in Security panel. Postgres `deyoung` schema is seeded and production-ready (admin + plans/services/photos/testimonials/faqs).

Deliverable location: `/home/z/my-project/download/markdown.md.txt` (+ repo-root copy).

## 7. Session protocol (the "AI in charge" loop)

0. **IF the sandbox was rebuilt** (vault/`.env.local`/brain missing): `bash scripts/selfheal.sh
   "<vault passphrase>"` — restores workers/secrets + .env.local from the tracked encrypted
   blob `vault/vault.enc`, installs the kaggle CLI, boots the brain. The passphrase is held
   by the OWNER and repeated in agent chat history — never stored in any tracked file.
   Nothing else may be treated as lost: the repo carries all durable state (Task 46).
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

## Task 46 — Durability model: rebuilds may never break anything again (2026-09-07)

The platform periodically REBUILDS the sandbox: tracked (committed) files are restored from
the repo; gitignored files and processes are WIPED. That is how the vault, .env.local and
the brain loop "vanished" twice on 2026-09-07. The fix — everything durable lives in the
repo:

- `vault/vault.enc` (TRACKED): AES-256-CBC / PBKDF2-600k encrypted tar of `workers/secrets/*`
  + `.env.local`. Plaintext secrets are still NEVER committed (repo is PUBLIC — verified).
- ONE passphrase unlocks it (owner + agent chat history only; generated 2026-09-07, owner
  instructed to save it out-of-band). Recovery order: (1) selfheal with passphrase, (2)
  offsite Kaggle dataset `deyoungsltd/deyoung-worker-vault` via any fleet KGAT token + the
  CLI access_token recipe (raw HTTP datasets API returns 403 datasets.get — KGAT scope).
- `scripts/selfheal.sh "<passphrase>"`: restore vault -> ensure kaggle CLI -> boot brain ->
  status. Idempotent; tested by simulating a full wipe (restore verified byte-identical).
- `campaign/v10/` TRACKED (job definitions + kernel metadata are reproducible work product).
- `brain/state.json` tracked + committed on real changes (auto-checkpoint); events.log stays
  ignored (churn). Seed the canary jobs back with `scripts/h3v2_make.py` if ever needed.
- Fleet note: Kaggle GPU quota is 30 GPU-hours/week PER ACCOUNT — deyoungsltd exhausted its
  window (v1's 12h burn); canary now lives on youngwilly (fresh quota). Push a kernel there
  only after checking status; never assume quota on a used account.

## W2.1 — Live film simulator + render notifications (Task 43, 2026-09-07)
- SSE agent trace: GET /api/studio/stream?requestId= (session auth owner-or-admin; 2s ticks; end-event on done/failed/cancelled; 30-min cap). Engine: src/lib/agenttrace.ts (deterministic; REAL queue position + REAL claim time from worker notes; pacing simulated inside phases only — UI labels it).
- UI: agent-stream.tsx connected timeline console; auto-opens on scene submit (StudioView), Watch live buttons (scene cards + dashboard rows).
- Email: src/lib/render-mail.ts — done + failure mail to request.email via AgentMail (prod key live; dev no-op). Hooks in worker/jobs PATCH deliver(multipart+JSON)/fail. Failed renders do NOT consume quota — email copy matches periodUsage.
- Bugfix: script-writer scene seconds floor 3->5 (render API rejects <5s): writer clamp + prompt rule + client clamp. Found via browser QA golden path.
- Shipped: 1a9df05 -> CI success -> Railway SUCCESS 02:38Z. QA e2e suite: scripts/qa_stream_e2e.js (14/14). NOTE: dev DB == prod DB — QA scripts mutate ONLY by-id/QA-prefixed rows.

## Task 49 — The Director's Brain + the two-schema trap
- **Studio AI now thinks in film**: `src/lib/cinema.ts` (shot grammar, camera moves, lighting, composition, color scripting, the 12 animation principles, kid-lens rules, sound design, per-niche director voices). Every script gets ONE visual bible + per-scene direction (shot/move/light/emotion/principle + director's note) — shown in the studio storyboard. Cast comes FROM the brief ("robot & firefly" star as Robot & Firefly).
- **THE TWO-SCHEMA TRAP (never again)**: prod boots `prisma db push --schema prisma/schema.postgres.prisma`; dev uses `prisma/schema.prisma`. A column added ONLY to the dev schema gets DROPPED by every prod boot (this killed `StudioProject.storyboardJson` twice). Rule: any schema change goes into BOTH files, or into `schema.postgres.prisma` at minimum.
- Fleet plane: queue is clear of site renders (owner order — campaign video first); kernels write storyboards via `deyoung_fleet` scoped grants.

## Task 62-d — W3.1 worker-plane truth + S-1 severity correction (2026-09-10)
- **S-1 CORRECTED with live evidence**: the purged `brain/admin_cookie_58.txt` was recovered from the orphaned pre-rewrite commit (GitHub still serves f4cf428 by SHA) and INSPECTED: it is a **localhost-scoped `dy_user` dev-session jar** from Task 58's local E2E — NOT a production admin cookie. Forced prod use = 401 (dev-secret HMAC rejected). Task 62's "LIVE production admin cookie" wording was wrong; purge stays correct hygiene; residual risk is far lower than reported. AUTH_SECRET rotation = recommended hygiene, not breach response.
- **ADMIN_PASS (repo secret) PROVEN stale**: server-side probe workflow (`.github/workflows/admin-data-hygiene.yml`) on a fresh GHA runner: health 200, admin login 401 — the secret predates the Task 58 password reset. No deletion attempted by design.
- **Prod fake testimonials still live** (Amara/Kwame/Tessa rows): deletion now REQUIRES an owner-side action — Admin -> Reviews & FAQ (30 s), or vault passphrase -> SQL.
- **W3.1 SHIPPED** (commit 78760e7, gitleaks CI success): F-9 DB-plane CLAIM_SQL `reserved:` parity; F-10 H3 site progress beats (throttled 60 s, real quantities only, reaper-safe); S-7 `?token=` auth fallback removed (header-only; zero consumers verified); admin Video Queue renders worker identity notes (dev E2E screenshot `brain/qa_w31_videosequeue_notes_62d.png`).
- Worker script re-push note (per architecture doc): the H3 worker changes take effect on the Lightning rig at the next `ensure_h3_tmux.sh` relaunch / kernel re-push window (needs vault).
- Gitleaks += cookie-jar rules (netscape header + #HttpOnly_ entries).
- Still blocked on vault passphrase: workers/secrets + .env.local restore, fleet brain, Railway AUTH_SECRET rotation, H3 worker live re-push.
