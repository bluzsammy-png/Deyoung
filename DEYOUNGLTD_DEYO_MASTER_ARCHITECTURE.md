# DEYOUNGLTD DEYO MASTER ARCHITECTURE

> **Status**: AUDIT COMPLETE 2026-09-10 (Task 62). This document is the synchronized
> architecture + audit record demanded by the Master Upgrade & Implementation Instruction
> (§36). It reflects the repository and live application **as verified on 2026-09-10**.
> Honesty discipline (AGENTS.md): unknowns are marked **NOT VERIFIED**, legal
> interpretations are marked **LEGAL REVIEW REQUIRED**, simulated things are labeled
> simulated. No claim in this document outruns its evidence.
>
> Maintenance rule: any change that alters worker plane, data model, auth, or the Deyo
> product surface MUST update the corresponding section here in the same commit.

---

## 0. Executive summary (1 page)

**What DeyoungLTD is today (verified):** a live, revenue-taking Next.js 16 single-page app
(deyoungltd.site, Railway + Supabase Postgres `deyoung` schema, Supabase Storage) with
(1) a customer funnel (plans $12/$39/$99, bookings, subscriptions, video-request queue),
(2) an AI Film Studio ("W3") where a brief becomes a script, storyboard and queued renders,
(3) a 16-tab owner admin panel, (4) a free-GPU render fabric — 6 rotating Kaggle accounts
(T4/P100) plus one Lightning AI T4 studio running MiniMax **H3** through ComfyUI, managed
by sandbox-resident orchestrators ("brain") with a tmux-persistent queue worker (Task 61).

**What it already does well:** honest queue mechanics (atomic claims, orphan reaper,
dedup cache, real queue positions), two separated session planes (customer vs admin vs
worker token), provider-agnostic storage with sniffed MIME + signed URLs, rate limiting,
secret hygiene (W0 purge, gitleaks CI), and an SSE production view whose *status is real*
(only intra-phase pacing is simulated, and it is labeled).

**The five biggest gaps between today and the Master Instruction:**

| # | Gap | Instruction § | Severity |
|---|-----|--------------|----------|
| G1 | A **live production admin session cookie is committed to the public repo** (`brain/admin_cookie_58.txt`, Task 58) — valid until ~2026-09-16 (7-day TTL) unless `AUTH_SECRET` rotates | §26 | **CRITICAL** |
| G2 | Fabrications on the storefront: "4K" claims (code caps 1080p), 3 fictional testimonials headed "**Real clients**", flyer prices ($9/$29/$79) contradict real plans ($12/$39/$99) | §28, §39 | **CRITICAL** |
| G3 | No Terms of Service, no Refund Policy, no Cookie Policy (only a Privacy view); no checkout consent step | §28 | HIGH |
| G4 | No first-class **production state machine** (story/characters/scenes/shots/camera/movement as persistent typed tasks) — the studio has brief→script→scenes but generation is per-scene `VideoRequest` rows only; no event stream beyond the per-request SSE trace | §5, §8-11, §19 | HIGH |
| G5 | **Worker Registry is self-reported names** — one shared `WORKER_TOKEN`, no registration/heartbeat/capability records, so the scheduler cannot make capability-based decisions; H3 workers don't report progress to the site | §15-17 | HIGH |

**Smallest safe first implementation task** (chosen per §37 workflow): **the honesty fix
pack** — remove "4K" claims, replace fictional testimonials with an honest empty state +
seed removal, align flyer prices with real plans, fix the invalid `Noindex:` robots line.
Zero schema risk, zero worker risk, directly mandated by §28/§39, verifiable with tsc +
dev QA in one pass. (Implemented in Task 62, commit following this document.)

**Escalations that block remote work right now** (sandbox rebuild #7, 2026-09-10 ~11:08
local): the vault passphrase is not in this session's context → `workers/secrets/`
(incl. GitHub PAT, Railway token, Kaggle tokens) and `.env.local` are unrestored, so
**no push, no Railway env changes, no fleet control** until the owner repeats the
passphrase. The `AUTH_SECRET` rotation + history purge for G1 are prepared but blocked on
the same. Fleet processes are down (expected after rebuild; `scripts/selfheal.sh` +
`brain_boot.sh` resume them).

---

## 1. Existing architecture (as-built)

### 1.1 Topology

```
                       ┌──────────────────────────────────────────────┐
                       │  deyoungltd.site  (Cloudflare edge in front) │
                       │  Railway service "Deeyoung" (Next 16 standalone) │
                       └──────────┬─────────────────────┬─────────────┘
              customer/admin HTML │                     │ /api/worker/*
              (hash-routed SPA)   ▼                     ▼ (Bearer WORKER_TOKEN)
                       ┌──────────────────┐    ┌─────────────────────────┐
                       │ Supabase Postgres│    │  WORKER FABRIC          │
                       │  schema "deyoung"│◄───┤  6× Kaggle site-workers │
                       │  16 Prisma models│SQL │   (DB-plane, SKIP LOCKED)│
                       └────────┬─────────┘    │  1× Lightning T4 H3     │
                                │              │   queue worker (tmux)   │
                                ▼              │  1× universal worker    │
                       ┌──────────────────┐    │   (API-plane, any box)  │
                       │ Supabase Storage │◄───┤  campaign kernels (v2/c20)│
                       │ deyoung-media    │    └─────────────────────────┘
                       │ (private bucket) │             ▲
                       └──────────────────┘             │ supervise/launch/harvest
                                                        │
                                          ┌─────────────┴─────────────┐
                                          │ SANDBOX "BRAIN" (this box)│
                                          │ fleet_brain.py --loop 60s │
                                          │ recovery_orchestrator_51  │
                                          │ h3_doctor_61 (tmux health)│
                                          │ state: brain/*.json       │
                                          └───────────────────────────┘
```

- The site is **one route** (`src/app/page.tsx`) with a client hash router
  (`src/components/site/hash.ts`; routes `#/`, `#/studio`, `#/dashboard`, `#/admin`,
  `#/book`, `#/subscribe`, `#/request`, `#/privacy`, `#/thanks`, `#/signin`, `#/signup`).
- The API is **53 route files** under `src/app/api/` (full table in §10).
- Two Prisma schemas, field-identical: `prisma/schema.prisma` (sqlite dev) and
  `prisma/schema.postgres.prisma` (prod; pushed by `deploy/start.sh` with a
  `?schema=deyoung` tenancy guard — the Supabase project is **shared** with another app;
  its `public` schema must never be touched).
- Runtime DB access goes through the transaction pooler (`:6543`, pgbouncer,
  connection_limit 5); schema ops use the session pooler (`:5432`).

### 1.2 Process responsibilities

| Process | Host | Role | State |
|---|---|---|---|
| Next.js standalone | Railway | app + API + SSE + worker plane | Railway deployment (last verified SUCCESS: Task 60 `b2681dd1`, 2026-09-09) |
| `scripts/fleet_brain.py --loop 60` | sandbox | Kaggle kernel inventory/harvest, canary-gated wave-2 pusher, Lightning watch (idle/20h alerts), orchestrator keepalive | `brain/state.json`, `brain/lightning_watch.json`, `brain/events.log` |
| `scripts/recovery_orchestrator_51.py` | sandbox (keepalive via fleet_brain) | 3-phase ground→restore→watch; rotates all 6 Kaggle accounts pushing `deyoung-site-w` DB-plane drain kernels; quota probe (regex `weekly GPU quota`), 30-min sleep per full QUOTA round | `brain/recovery51_state.json` |
| `scripts/h3_doctor_61.py` | sandbox | Lightning H3 worker health ladder (REST→SDK L0→tmux→pid→heartbeat age→ComfyUI queue→H3 `object_info`→GPU), bounded restarts (3 max, 60-min cooldown, ≥120 s apart), optional idle auto-stop | `brain/h3worker_state.json` |
| `workers/lightning/h3_queue_worker.py` | Lightning studio `deyoung-h3`, tmux session `h3-queue` | claims site jobs via API, renders H3 in ComfyUI, uploads mp4, beats `~/h3work/status_h3q.json` | local heartbeat file + `h3q.log` |
| `workers/deyoung_worker.py` | any Kaggle kernel / box | universal API-plane worker (stub/LTX renderers), self-budget `--max-minutes 480` | stateless |

**Honest operational note:** the brain/orchestrators run on a sandbox that the platform
periodically rebuilds (wiping gitignored files and processes — 7 rebuilds to date). The
durability model (Task 46) keeps all durable state in the repo: tracked `brain/*.json`
checkpoints, `vault/vault.enc` (AES-256-CBC) for secrets, offsite Kaggle vault dataset,
and idempotent boot scripts. Rebuilds are survivable by design; they do, however, require
the vault passphrase to resume remote actions.

---

## 2. Existing technologies (verified)

| Layer | Technology | Evidence |
|---|---|---|
| Framework | Next.js 16.1.1 (App Router, standalone output), React 19, TypeScript 5 | `package.json` |
| UI | Tailwind CSS 4, shadcn/Radix suite, framer-motion 12, lucide, sonner | `package.json`, `components.json` |
| ORM/DB | Prisma 6.11 (sqlite dev / postgres prod), Supabase Postgres (shared project, `deyoung` schema) | `prisma/`, BRAIN.md §6 |
| Storage | Supabase Storage private bucket `deyoung-media` (REST, presigned 10-min URLs) + local `./media` fallback (dev-only) | `src/lib/storage.ts` |
| Auth | Custom HMAC stateless session cookies (`dy_admin`, `dy_user`), scrypt password hashing, manual Google OAuth (HMAC state cookie) | `src/lib/auth.ts`, `src/lib/users.ts` |
| Payments | Paystack/Flutterwave server-side verify w/ secret key in Settings row; PayPal/Stripe/manual paths (PayPal path trusts client — §6) | `src/app/api/bookings/[id]/verify`, `src/lib/settings.ts` |
| Email | AgentMail (owner notify + render done/fail mail) | `src/lib/agentmail.ts`, `src/lib/render-mail.ts` |
| Realtime | SSE (`/api/studio/stream`), 2 s ticks, 30-min cap | `src/app/api/studio/stream/route.ts` |
| AI | z-ai-web-dev-sdk present; studio `aiengine.ts` uses optional OpenAI-compatible env (`AI_API_KEY`) with a deterministic local cinematic engine fallback (`cinema.ts` banks) | `src/lib/aiengine.ts`, `src/lib/cinema.ts` |
| Video gen | ComfyUI + MiniMax H3 (fp8 DiT + Qwen3-VL-32B nvfp4 AWQ encoder + video VAE fp16 + audio VAE fp32; turbo LoRA 4/8-step) on T4s | §3 |
| CI/CD | GitHub Actions: gitleaks secret scan + prod-selftest; Railway auto-deploy on push to `main`; pre-push secret scan script | `.github/workflows/`, `scripts/prepush_secret_scan.py` |
| Worker runtime | Python 3.9+ stdlib; tmux as session layer (Lightning); Kaggle kernels; ffmpeg for normalize/assembly | `workers/`, `scripts/` |

**Explicit non-goals kept:** no Modal (instruction §2), no new database (§19 — Supabase
Postgres stays the single state store), no paid-GPU dependency (§2 free-first).

---

## 3. Existing H3 implementation (audited to file:line)

### 3.1 Model stack

- **HF repo `Comfy-Org/MiniMax-H3`** (ComfyUI repackaged weights). DiT:
  `minimax_h3_fl2va_pruned_fp8_scaled.safetensors` — fp8 **safetensors, not GGUF**
  (`workers/lightning/h3_queue_worker.py:232`; the `ComfyUI-GGUF` node + pip package are
  installed but the runtime graph uses `UNETLoader`).
- Text encoder: `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` via `CLIPLoader
  type:"minimax"` (`deyoung-site-w.py:88,350`).
- Video VAE fp16; **Audio VAE fp32 — audio support is real**: the graph decodes audio
  (`VAEDecodeAudio`) and muxes it (`CreateVideo audio=...`)
  (`h3_queue_worker.py:259-261`).
- Turbo LoRA: `minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors`; the queue
  worker picks 4-step or 8-step by job length (`h3_queue_worker.py:236-237`).
- Graph: `MiniMaxH3ImageToVideo` + `RandomNoise` / `KSamplerSelect(res_multistep)` /
  `BasicScheduler(simple)` / `BasicGuider` / `SamplerCustomAdvanced` → dual VAE decode →
  `CreateVideo(fps 24)` → `SaveVideo` (`h3_queue_worker.py:238-265`).
- Stack ≈ 35 GB download / ~54 GB preinstalled on the Lightning studio
  (`deyoung-site-w.py:86`; worklog Task 54).

### 3.2 Profiles and budgets (T4 economics, learned live)

| Profile | Resolution | Frames | Steps | Where used |
|---|---|---|---|---|
| Site queue band | 960×544 ("T4-safe") | `8n+1`, clamp [121, 289] (≈5–12 s @24 fps) | 8 if ≤121 frames else 4 | `h3_queue_worker.py:52-59,270-274` |
| Kaggle site-worker | 960×544 | `max(121, min(289, round(secs*24)))` | 4 | `deyoung-site-w.py:370-384` |
| v2 campaign (768p band) | 1376×768 | len 80 | 4 | BRAIN.md §4 (historical) |
| v1 (BURNED — never again) | 1376×768 | 158 | 4–8 | 12 h Kaggle cap killed all 4 kernels, 0 outputs (BRAIN.md §4:77) |

- Runtime calibration: `RATE = 0.0001293650647630262` s/pixel-frame; est-min =
  `length*width*height*RATE/60` (`h3_queue_worker.py:288`). A 121-frame 960×544 job ≈
  **13 min** GPU time; a 289-frame job ≈ **31 min** — this is why the site caps seconds
  and why 45–60 s films must be assembled from scene chunks, not generated single-pass.
- VRAM guard: ComfyUI `--reserve-vram 0.4`, `CUDA_VISIBLE_DEVICES=0`, `/free
  unload_models` after every job (`h3_queue_worker.py:194,544-549`). T4 15 360 MiB
  verified (`brain/lightning55d_gpu.json`).
- ffmpeg post: scale/crop to requested res, watermark policy, audio policy (keep H3
  soundscape if `withAudio` else silence), **tpad last-frame hold** when the H3 band is
  shorter than the requested seconds (`h3_queue_worker.py:369-400`).

### 3.3 Task 61 tmux layer (verified facts)

- Session `h3-queue`, windows `worker` + `diag`; **tmux is ONLY the session layer** —
  the worker file itself knows nothing about tmux; health truth is the heartbeat file
  (`h3_queue_worker.py:9-15`, `ensure_h3_tmux.sh:4-8`). This matches the instruction's
  rule that tmux must not become the orchestration layer.
- TERM fix forced before any tmux call (Jupyter exec ships empty `TERM`, which kills the
  tmux server — proven live 2026-09-10) (`ensure_h3_tmux.sh:29-33`).
- Secrets sourced inside the pane from `h3q.env` (0600), never on argv; every pane byte
  logged to `h3q.log` (`ensure_h3_tmux.sh:62-78`).
- Idempotent starter: alive session + alive heartbeat pid → no-op; stale session killed
  and replaced; nohup fallback; verification layer with exit codes 10–14
  (`ensure_h3_tmux.sh:36-134`).
- Doctor state machine: OFFLINE/STARTING/IDLE/BUSY/UNHEALTHY/ERROR (ONLINE = alias);
  "tmux-alive alone NEVER means healthy"; max 3 consecutive restarts → 60-min cooldown
  (`h3_doctor_61.py:11-27,58-61,319-346`).
- Credit guard: doctor never starts the machine; `--stop-studio` / opt-in
  `--auto-stop-idle MIN`; fleet_brain raises a >20 h RUNNING alert
  (`fleet_brain.py:404-415`). Balance preserved 12.75 credits as of Task 57.

### 3.4 H3 licensing (honest status)

- In-repo research verdict (2026-09-06/07): open-weight license **reported** to exclude
  certain territories (US) and **reported** to prohibit using outputs to improve other
  models; scope **NOT VERIFIED** (`scripts/spec_parts/part03.md:24`,
  `markdown.md.txt:288`). No LICENSE file exists in-repo (grep-verified).
- **The fleet is commercially rendering with H3 today while the license text remains
  unverified. This must be resolved before scaling** (owner escalation; see §18, §19).
  LEGAL REVIEW REQUIRED for: commercial use, attribution/UI disclosure, territory
  restrictions (operator is Nigeria-based; customers' territory NOT VERIFIED),
  derivative/training restrictions (Deyo Phase-2 LoRA training must not use H3 outputs
  if prohibited), service-user obligations.

---

## 4. Existing worker architecture (as-built)

### 4.1 Two claim planes (a real architectural fact the Master Instruction must respect)

1. **API plane** (provider-neutral, the one the instruction wants): workers call
   `POST /api/worker/claim` with `Bearer WORKER_TOKEN` and body `{agent}`. The route
   first runs the **45-min orphan reaper** (any `rendering` row with stale `updatedAt`
   → honest `failed`), then skips `reserved:`-noted rows, orders by
   `queuePriority desc → createdAt asc → id asc`, and claims **atomically**
   (`updateMany` guarded on `status:"queued"`, ≤5 retries → 409)
   (`src/app/api/worker/claim/route.ts:29-73`).
2. **DB plane** (Kaggle site-workers): kernels connect directly to Postgres with a
   scoped role (`deyoung_fleet` derived from the app DSN) and claim via
   `FOR UPDATE SKIP LOCKED`, then upload to Supabase Storage and update rows via SQL
   (`campaign/site-worker/deyoung-site-w.py:170-176`,
   `scripts/site_worker_make.py:36-44`). Faster (no API dependency) but bypasses API
   logic — including, today, the `reserved:` guard (a verified mismatch; see §6, F-9).

### 4.2 Job lifecycle (as implemented)

```
queued ──claim (atomic)──► rendering ──deliver multipart──► done
   ▲                          │  │ 45-min reaper               (Asset + sha256,
   │                          │  └──► failed "orphaned…"        resultUrl=/api/files/:id,
   │ requeue (admin)          └─fail──► failed (+email)        done-email)
   └───────────────────────────────────────────────► cancelled (admin only)
```

- Delivery: multipart `action=deliver` with `gpuMinutes`, `renderer` (≤40 chars), file
  1 B–200 MB, magic-byte sniff (video kind required) → storage
  `deyoung-media/renders/req-<id>.mp4` → private `Asset` → row done
  (`src/app/api/worker/jobs/[id]/route.ts:39-94`). JSON `{resultUrl}` variant supported.
- Progress: `action:"progress"` note exists and bumps `updatedAt` (reaper protection),
  but **the H3 queue worker does not use it** (only the local heartbeat file); only the
  DB-plane site worker writes progress beats. Customer-visible row notes therefore go
  stale during H3 renders (F-10, fix scheduled in W3.1).
- Dedup: `dedupKey` (sha256 of prompt+params) hit returns instant `done`,
  `fromCache:true`, `gpuMinutes:0` (`src/lib/subs.ts:14-19`, `api/requests/route.ts:68-94`).

### 4.3 Kaggle fleet management

- 8 vaulted tokens; 6 active accounts (deyoungsltd, teslaprime ×2, jimcreat,
  bittrexminingltd ×2, youngwilly, wikeyoung5). Quota ≈ 30 GPU-h/week/account; 12 h
  session cap (proven by the v10 loss). Self-exit budgets sit below the caps (480–660
  min across worker types).
- fleet_brain harvests completed kernels into `campaign/v10/<account>__<kernel>/`, writes
  `brain/state.json`, and hosts the (currently **grounded** — canary
  `cancelAcknowledged`) wave-2 relaunch gate. Recovery orchestrator re-grounds the
  site-worker fleet after quota windows.

---

## 5. Existing deployment (as-built)

- Push to GitHub `bluzsammy-png/Deyoung` `main` (one-shot PAT URL push;
  pre-push secret scan gate) → gitleaks CI + Railway auto-build
  (`railway.toml`: prisma generate (postgres schema) → next build → standalone;
  `deploy/start.sh`: db push + seed + `:6543` runtime switch + serve).
- Health: `GET /api/health` → `{"ok":true,"db":true}` (Railway healthcheck).
- Railway env contract (Task 40/58 lessons): `DATABASE_URL` must be the **session
  :5432** URL (start.sh rewrites runtime to :6543); `ADMIN_BOOTSTRAP_PASSWORD` only
  seeds **missing** rows; `AUTH_SECRET` ≥32 chars fail-closed.
- Known edge behavior: Cloudflare managed challenge fronts the site (sandbox IPs get 429
  on bare fetches; real browsers pass; static assets pass). **NOT VERIFIED** whether
  Turnstile friction has been tuned for real users (owner decision pending from Task 55).
- Deployments verified by GraphQL polling (`scripts/railway_watch_60.py`; note Railway
  schema change — `DeploymentMeta` is now a scalar, `meta{...}` selections 400).

---

## 6. Security findings (Task 62 audit)

Severity scale: CRITICAL / HIGH / MEDIUM / LOW. Every finding has file evidence.

### CRITICAL

| ID | Finding | Evidence | Required action |
|----|---------|----------|-----------------|
| S-1 | **Live production admin session cookie committed to the public repo.** `brain/admin_cookie_58.txt` (Netscape jar from Task 58 login QA) is git-tracked; `dy_admin` tokens are stateless with 7-day TTL → valid until ≈2026-09-16 unless `AUTH_SECRET` rotates. Repo is public. | `git ls-files` confirms; `src/lib/auth.ts:101-109` (cookie TTL) | (1) Rotate `AUTH_SECRET` on Railway (invalidates all sessions immediately); (2) `git rm` + full-history purge (filter-repo) + force-push; (3) gitleaks pattern for cookie jars; (4) owner rotates admin password again post-rotation. **BLOCKED on vault restore (passphrase) — owner escalation #1.** |

### HIGH

| ID | Finding | Evidence |
|----|---------|----------|
| S-2 | **No security headers anywhere**: no CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy; no `middleware.ts`; Caddyfile sets none. CSRF posture = SameSite=lax + JSON bodies only. | `next.config.ts`, repo-wide grep |
| S-3 | **Admin sessions are irrevocable**: `isAdmin()` accepts `role:"admin"` tokens with no DB check; banning/deleting the Admin row does not kill issued cookies (user sessions *are* re-checked per request). | `src/lib/auth.ts:129-136` vs `src/lib/users.ts:85-94` |
| S-4 | **Single shared `WORKER_TOKEN`** for all workers; baked into Kaggle kernel sources (`kaggle_launch.py:75-114`); agent identity is self-reported (`{agent}` string). One leaked kernel = full worker plane. No per-worker credentials, no revocation. | `src/lib/worker.ts:20-35`, `scripts/kaggle_launch.py` |
| S-5 | Weak private-render authz: `/api/files/:id` accepts `?request=<id>&email=<email>` (email is not a secret) — same trust model as `/api/requests/[id]`. Upgrade path (per-request signed tokens) documented in code but not built. | `src/app/api/files/[id]/route.ts:34-47` |

### MEDIUM

| ID | Finding | Evidence |
|----|---------|----------|
| S-6 | SSE endpoint unthrottled: `LIMITS.stream` (120/min) defined but `guard()` never called on `/api/studio/stream`; each connection hits the DB every 2 s for up to 30 min. `LIMITS.code` is dead config. | `src/lib/ratelimit.ts`, `stream/route.ts` |
| S-7 | `?token=` query-param acceptance on worker routes leaks the token into access logs/Referer. | `src/lib/worker.ts:27` |
| S-8 | Legacy public route `GET /api/worker/file/[name]` streams any `public/uploads/*.mp4` to anyone with the filename (acknowledged H-4; filenames server-generated). Should be retired once no assets reference it. | `worker/file/[name]/route.ts:5-7` |
| S-9 | Rate-limit counters are find-then-update (non-atomic; documented); IP from spoofable `x-forwarded-for` (mitigated by edge overwrites). Money columns are Float (documented since W1). | `src/lib/ratelimit.ts:18-20`, schema |
| S-10 | PayPal path trusts the client (verify endpoints return `provider-does-not-need-verification` for non-Paystack/Flutterwave). | `bookings/[id]/verify`, `subscriptions/[id]/verify` |
| S-11 | `prisma/prisma/dev.db` (dev SQLite with real rows) is git-tracked. No obvious secret material on inspect, but it does not belong in a public repo. | `git ls-files` |
| S-12 | `typescript.ignoreBuildErrors: true` in `next.config.ts` ships type errors silently (pre-existing W2 note; tsc is currently clean, but the flag defeats the gate). | `next.config.ts` |

### Positive controls already in place (verified)

- Fail-closed `AUTH_SECRET` (env → 0600 file → refuse boot), scrypt hashing, timing-safe
  compares, role-claim separation (`auth.ts:17-36,62,129`).
- Fail-closed `WORKER_TOKEN` (503 when unset/short; timing-safe compare).
- Per-request user-session reload → bans take effect immediately (`users.ts:85-94`).
- OAuth state HMAC + 10-min TTL + verified-email requirement (`users.ts`).
- Upload validation: magic-byte sniffing, size caps (8 MB img / 200 MB video / 50 MB
  audio), key sanitization, path containment (`src/lib/storage.ts`).
- Path traversal: `SAFE` regex + suffix check on legacy file route; DB-keyed storage
  paths otherwise.
- Secrets: Settings payment secret stripped from all read paths; vault + gitleaks CI +
  pre-push scan; `deyoung` schema tenancy guard against the shared Supabase project.

---

## 7. Accessibility findings (Task 62 audit; WCAG 2.2 AA orientation)

**Already good:** labeled forms throughout; landmarks + `aria-label`s on navs; admin tabs
use `aria-current`; niche picker uses `role="radiogroup"`/`aria-checked`; GPU rings carry
`role="progressbar"`; decorative art `aria-hidden`; reduced-motion handled in three CSS
blocks + JS checks (hero/tilt/showreel); gallery alt text is admin-editable.

**Gaps (all concrete, file-referenced):**

| ID | Gap | Evidence |
|----|-----|----------|
| A-1 | Low-contrast content text: `text-white/25`–`/40` on `#0A0A0A` for meaningful copy (≈2.3–4.8:1; AA needs 4.5:1). Studio descriptions, agent-stream pending rows, plan fine print. | `studio-view.tsx:433,476,590-592`; `agent-stream.tsx:34,46-48,55`; `plans.tsx:109` |
| A-2 | Pseudo-ARIA without keyboard semantics: gallery/premiere filters declare `tablist/tab/aria-selected` with no tabpanels or arrow-key handling; radiogroup lacks roving focus. | `sections.tsx:105-125`; `premiere-wall.tsx:102-125`; `studio-view.tsx:477-490` |
| A-3 | Lightboxes: premiere lightbox handles Escape; **gallery lightbox does not**; neither traps focus, restores focus to trigger, or locks body scroll. | `sections.tsx:162-184`; `premiere-wall.tsx:54-61` |
| A-4 | Touch targets below 44×44: showreel dots ≈6 px, agent-stream close ≈28 px, niche chips `py-1.5`. | `showreel.tsx:291-301`; `agent-stream.tsx:108`; `studio-view.tsx:484` |
| A-5 | No `aria-live` on status transitions that matter (scene status pills, agent-stream rows). Toasts (sonner) do announce. | `studio-view.tsx:699-767` |
| A-6 | Hash navigation never moves focus or updates `document.title` — no SR navigation cue between views. | `hash.ts:60-68` |
| A-7 | Micro-typography for meaningful UI: `text-[9px]/[10px]/[11px]` status pills, plan fine print, simulated-pacing disclosure. | `studio-view.tsx:181`; `plans.tsx:125`; `agent-stream.tsx:147` |
| A-8 | Bare `<select>`s without `focus-visible` ring styling on dark bg. | `studio-view.tsx:507-517` |

---

## 8. Legal / compliance findings (Task 62 audit)

| ID | Finding | Evidence | Severity |
|----|---------|----------|----------|
| L-1 | **"4K" claims contradict the code.** Hero ticket "★ 60S ★ 5 STYLES ★ 4K", "choose 720p or crisp 4K", "UP TO 4K CINEMATIC" — while `RESOLUTION_RANK` caps at 1080p, plans seed 1080p max, and the request form offers 720p/1080p only. Unsupported claim → must be removed/reworded. | `hero.tsx:70`; `sections.tsx:445,509` vs `src/lib/subs.ts:6`, `scripts/seed.ts:116,144`, `request-view.tsx:177-178` | CRITICAL |
| L-2 | **Fictional testimonials presented as "Real clients"** (3 seeded 5★ reviews: Amara O./Kwame B./Tessa M.). Instruction §28: remove fake reviews; do not invent testimonials. | `sections.tsx:231`; `scripts/seed.ts:274-304` | CRITICAL |
| L-3 | **Flyer prices contradict real plans**: admin flyer copy says $9/$29/$79; seeded plans are $12/$39/$99. Stale template that can ship to socials. | `admin-flyers.tsx:48` vs `seed.ts:84,112,140` | HIGH |
| L-4 | **No Terms of Service, no Refund Policy, no Cookie Policy** anywhere (grep-verified). Only a Privacy view exists (`#/privacy`, inside `thank-you-privacy.tsx:88`) — and it omits cookies the site actually sets (`dy_user`, `dy_admin`, `dy_oauth_state`), has no last-updated date, no legal entity/address. Checkout has **no consent checkbox**. | `thank-you-privacy.tsx:88-144`; `book-view.tsx:343-575` | HIGH |
| L-5 | Founding-price urgency ("they go up soon", "Your rate stays locked") with no pricing-terms page backing the promise. | `hero.tsx:132`; `plans.tsx:46-55,98-99,126` | MEDIUM |
| L-6 | SEO/meta defects: JSON-LD uses non-schema `opens`; `robots.txt` has invalid `Noindex:` directive (removed from robots spec in 2019 — admin gate must be server-side, which it is); sitemap lists hash URLs (one page to a crawler); no per-route titles (hash router cannot set them). | `layout.tsx:21-77`; `page.tsx:171-214`; `public/robots.txt`; `public/sitemap.xml` | MEDIUM |
| L-7 | H3 license unresolved for commercial rendering (territory exclusion + outputs-training clause both NOT VERIFIED). See §3.4. LEGAL REVIEW REQUIRED. | `scripts/spec_parts/part03.md:24` | HIGH |
| L-8 | Nigerian/local requirements (business registration display, consumer-protection wording): **NOT VERIFIED — needs qualified legal advice**; instruction §28 acknowledges this explicitly. | — | INFO |

---

## 9. Current database / state (as-built)

**16 models** (field-identical across both schemas; drift: NONE — verified by diff):
`Admin, Settings, Photo, Service, Booking, Message, Testimonial, Faq, Plan,
Subscription, VideoRequest, Asset, RateLimit, User, Premiere, StudioProject`.

Core production-relevant shapes:

- **VideoRequest** (the queue): `subscriptionId, email, prompt, seconds, resolution,
  withAudio, watermark, queuePriority, status(queued|rendering|done|failed|cancelled),
  resultUrl, resultAssetId→Asset, gpuMinutes, dedupKey, fromCache, notes, premiere`.
  This is a **flat job** — it has no parent project, no scene identity beyond
  `notes "studio:<projectId>:<sceneId>"` strings, no shot/camera/movement fields, no
  retry counters. §11 proposes the incremental extension.
- **StudioProject**: `userId→User, brief, scriptJson, storyboardJson?, status
  (draft|scripted|rendering|done)` — the W3 studio's container (two-schema lesson: this
  column was dropped twice by prod boots before the both-schema rule).
- **Asset**: `kind, mime(sniffed), bytes, storageKey@unique, driver(supabase|local),
  isPublic, sha256, createdBy("admin"|"worker:<id>")`.
- **Plan/Subscription**: full editable limits (maxVideosMonth, maxSecondsVideo,
  maxResolution, watermark, concurrentJobs, queuePriority, commercial, audio);
  subscriptions bind `userId` server-side on signup-match.
- **User**: `passwordHash?` (null = Google-only), `provider, googleId?, role, status
  (active|banned|deactivated), banReason, lastLoginAt`.
- **Premiere**: `requestId?@unique, assetId?@unique, status(pending|published|rejected),
  source(admin|user), requestedBy` — the public wall.

**External state stores:** Supabase Storage (`deyoung-media`); sandbox `brain/*.json`
(fleet, doctor incidents, lightning watch, relaunch gate — tracked, committed on real
changes); worker-local `~/h3work/status_h3q.json` heartbeat (Lightning studio, ephemeral
by design); Kaggle kernel sources + outputs (Kaggle-side).

**Data honesty note:** dev DB == prod DB whenever `.env.local` is present (Task 43 rule:
QA scripts mutate only by-id/QA-prefixed rows). Today (vault sealed) dev falls back to
tracked `prisma/prisma/dev.db` (sqlite).

---

## 10. Current API architecture (summary table)

53 route files. Auth planes: **admin** (`dy_admin` cookie), **user** (`dy_user`), **studio**
(admin-wins union), **worker** (`Bearer WORKER_TOKEN`), **public**. RL = rate-limit class.

| Area | Routes | Auth | Notes |
|---|---|---|---|
| Health/meta | `/api/health`, `/api`, `/api/home`, `/api/settings`, `/api/plans`, `/api/faqs[/:id]`, `/api/photos[/:id]`, `/api/services[/:id]`, `/api/testimonials[/:id]` | public reads; admin writes | `/api` is a hello-world stub (retire candidate) |
| Auth | `/api/auth/login`, `logout`, `me`, `change-password` (admin); `signup`, `user-login`, `user-logout`, `session` (user); `google`, `google/callback` | public | RL `login`/`signup`; ADMIN_EMAILS auto-promote; fail-closed status gates |
| Commerce | `/api/bookings[/:id][/verify]`, `/api/subscriptions[/:id][/verify]` | public create + admin manage | server-side Paystack/Flutterwave verify; PayPal trusts client (S-10) |
| Requests | `/api/requests[/:id]` | public create (subscription-proof email) + admin | tier limits, dedup, queue position, email-proof read |
| Studio | `/api/studio/projects`, `/enhance`, `/script`, `/render`, `/stream` | studio | RL `submit`/`ai`/`request`; admin = synthetic `admin-free` sub (priority 100, unlimited, no watermark); SSE 2 s ticks, 30-min cap |
| Admin ops | `/api/overview`, `/api/admin/users[/:id]`, `/api/admin/premieres[/:id]`, `/api/admin/full-settings`, `/api/admin/payments-meta` | admin | secret never leaves server (`payments-meta` returns `hasSecret` bool) |
| Worker plane | `/api/worker/claim`, `/api/worker/jobs/:id`, `/api/worker/status`, `/api/worker/file/:name` | worker | claim = reaper + reserved-guard + atomic claim; jobs/:id = deliver/fail/progress; file/:name = legacy public streamer (S-8) |
| Delivery | `/api/files/:id` | public-if-Asset.isPublic else admin or request+email proof | 302 presigned (10 min) or local Range stream |
| Messages | `/api/messages[/:id]`, `/api/contact` | admin / public | — |

Full route-by-route table with file:line evidence is preserved in the Task 62 audit
record (worklog entry; agent transcripts summarized in §6-§8 findings above).

---

## 11. Proposed architecture (target state)

**Principle: extend, never replace.** Every element below maps onto an existing
mechanism. No new database, no Modal, no paid-GPU dependency, no rewrite of working
planes. Additions are incremental, feature-flagged where they change customer-visible
behavior, and keep both Prisma schemas in sync (the Task 49 rule).

```
CUSTOMER APPLICATION (hash SPA, mobile-first)          ADMIN APPLICATION (16 tabs today
        │  simple: idea → Deyo model → options → Create │  + Production Control Center)
        ▼                                               ▼
                DEYO DIRECTOR  (src/lib/director/* — deterministic orchestration,
                        │       LLM-assisted where keys exist; every task = DB row)
                        ▼
        PERSISTENT PRODUCTION STATE  (Supabase Postgres "deyoung" schema — extended,
                        │           see §11.1; SSE events from a ProductionEvent table)
                        ▼
              JOB/SCHEDULER  (existing claim route + capability matching §12)
                        │
      ┌─────────────────┼──────────────────────┐
      ▼                 ▼                      ▼
  Worker 1..6       Lightning T4 H3        future workers (any provider)
  (Kaggle DB-plane) (API-plane, tmux)      (API-plane, registered)
      └─────────────────┴──────────────────────┘
                        ▼
      MEDIA PIPELINE (ffmpeg normalize → audio → captions → transitions →
                      final MP4 → final validation)   →   QA gates
                        ▼
      DELIVERY (Supabase Storage signed URLs → /api/files authz → Premiere wall)
                        ▲
   TERMUX INFRA AGENT ─┘  (outbound-only, authenticated /api/infra/* channel;
                           monitoring + SAFE SHUTDOWN state machine, §13)
```

### 11.1 Production state extension (incremental, non-destructive)

New tables (both schemas, one migration, additive only):

- **Production** — the project container the Director owns:
  `id, userId→User, title, idea, deyoModel, aspectRatio, targetSeconds, status
  (planning|running|completed|failed|cancelled), createdAt/updatedAt`.
- **ProductionTask** — every decomposed unit of work with explicit state
  (`QUEUED|PLANNING|RUNNING|VALIDATING|COMPLETED|FAILED|RETRYING|BLOCKED|CANCELLED`):
  `id, productionId→Production, kind (story|script|character|location|scene|shot|
  movement|generation_job|audio|captions|assembly|qa|export), seq, title, payloadJson,
  resultJson, state, attempts, lastError, dependsOnJson, createdAt/updatedAt`.
  Scene-level regeneration = re-run one `generation_job` task without touching siblings
  (instruction §18/§19 requirement).
- **ProductionEvent** — append-only event log (§14): `id, productionId, taskId?,
  type, dataJson, createdAt`. SSE tail = `SELECT … WHERE id > cursor ORDER BY id`
  every ~1.5 s. This makes the customer graph **real**: the UI renders events, not
  timers.
- **Worker** (registry, §12) and optional **JobLease** columns on VideoRequest
  (`workerId, leaseExpiresAt, attemptCount`) to formalize what the reaper + notes do
  informally today.

`VideoRequest` stays the GPU job primitive; `ProductionTask(kind=generation_job)`
**references** a `videoRequestId` — the existing queue, dedup, tier limits, reaper and
worker plane keep working unchanged (backward compatibility §34). `StudioProject`
remains; new projects may link `studioProjectId`.

### 11.2 Deyo Director (deterministic core, LLM-assisted edges)

`src/lib/director/` — a pure-ish orchestration module that turns a Production row into a
task tree using the already-built `cinema.ts` craft banks (shots/moves/lighting/
composition/palettes/principles) and `aiengine.ts` (LLM when `AI_API_KEY` set, local
banks otherwise — honestly labeled). The Director:

1. creates tasks (story → script → characters → locations → scenes → shots → movement →
   generation jobs → audio → captions → assembly → QA → export) with dependencies;
2. advances state only from DB-truth (task completion events), never from timers;
3. marks failures honestly (`FAILED` + reason) and supports retry with backoff;
4. never blocks customer UI on LLM availability (local banks are the fallback — same
   pattern as `aiengine.ts` today).

Honest constraint: H3 on free T4s cannot deliver a 60-s film single-pass (§3.2 math).
The Director therefore plans **scene-chunked generation + ffmpeg assembly** (the proven
Task 49/53/56 pattern) as the default production strategy. "60 s in one pass" marketing
language must be retired or re-scoped to assembly (§8 L-1 fix covers the storefront).

### 11.3 Customer experience targets

- Create flow: idea → Deyo model (4 cards) → aspect ratio → duration → voice/audio →
  Create. No GPU/worker/provider vocabulary (instruction §21).
- Production screen: live production graph rendered from `ProductionEvent` (§14);
  character lab previews; storyboard forming scene-by-scene; movement/camera plan shown
  pre-generation and the generated clip post-generation (§10/§11 of the instruction);
  assembly + QA stages visible; final film in place.
- Mobile-first: vertical production timeline (horizontally scrollable nodes, expandable
  details, optimized previews) — built against the A-4/A-7 findings (bigger targets,
  readable type).

---

## 12. Worker fabric design (provider-neutral registry)

### 12.1 Registry model (new `Worker` table, both schemas)

```
worker_id (cuid, pk)          provider (kaggle|lightning|generic)
display_name                  gpu (T4/P100/…)           vram_mb
model ("minimax-h3")          model_version/variant      software_version
capabilitiesJson  { resolutions[], maxFrames, audio, reference_i2v, steps[] }
status (REGISTERED|IDLE|BUSY|STARTING|UNHEALTHY|OFFLINE|ERROR)
queue_depth   current_job_id  heartbeat_at  last_seen
success_count/fail_count      avg_runtime_s
```

- **Registration**: `POST /api/worker/register` (worker auth) → upsert by
  `worker_id`, returns signed per-worker secret (hash-stored) → retires the shared-token
  model gradually (S-4) via dual acceptance during migration.
- **Heartbeat**: `POST /api/worker/heartbeat` `{worker_id, state, current_job,
  queue_depth, metrics}` every ≤60 s; site marks `OFFLINE` after 3 missed intervals
  (scheduler-side `heartbeatTimeout`).
- **Status discipline** (Task 61's doctor ladder, generalized): `status` is computed —
  session-manager alive (tmux/systemd) **counts for nothing by itself**; `IDLE/BUSY`
  require live heartbeat + worker process + (for H3) ComfyUI/H3 readiness probes.
  The site trusts only the heartbeat payload; the doctor pattern stays sandbox-side.
- **Scheduler**: `claim` grows an optional capabilities filter in the request body
  (`{resolution, seconds, audio, reference}`); the route matches against
  `capabilitiesJson` before the atomic claim. Capability-matched claim is a **strict
  superset** of today's behavior (no capabilities requested → current order applies), so
  the DB-plane Kaggle workers keep draining unchanged.
- Admin surfaces the registry (real provider names); customers see only generic
  "Generation Worker 1..N" labels (instruction §23).

### 12.2 Self-healing contract (formalizing what exists)

- heartbeat timeout → `OFFLINE` → lease release (45-min reaper generalizes to
  `leaseExpiresAt`) → job retry with exponential backoff + `attemptCount` cap →
  dead-letter (`FAILED` with reason) — all server-side, worker-agnostic.
- duplicate-job protection: atomic claim (already) + idempotent deliver (already
  rejects `done/cancelled` rows).
- worker quarantine: 3 consecutive failures → `UNHEALTHY`, excluded from matching
  until a fresh heartbeat with healthy probes (doctor pattern, server-side now).
- customer-facing message on reassignment: "Generation worker changed. Production
  continuing." — no CUDA/provider detail ever (instruction §16).

### 12.3 Provider rules (honest)

- Kaggle: free 30 GPU-h/wk/account, 12 h session cap, weekly quota windows → fleet stays
  a *capacity pool*, not always-on; orchestrator re-grounds on quota reset (exists).
- Lightning AI: per-minute credits (T4 ≈ 1.5 credits/h; 12.75 credits banked) → only
  runs with an active credit guard (idle auto-stop, 20 h alert — exists; wired into the
  registry heartbeat as `metrics.balance` when available).
- Red line (instruction §2/§34): **no mechanism here makes free GPUs permanent.**
  Providers can reclaim machines at any time; the fabric is designed for churn
  (reaper + retry + reassignment), not for permanence.

---

## 13. Termux infrastructure agent design

**Role (per instruction §4):** infrastructure-control/edge agent on an Android device —
monitoring, start/stop of idle services, health checks, log fetch, worker registration
support, resource/credit conservation. **Not** the customer-facing Director; **never**
exposed to the public internet.

**Design (fits existing security posture):**

- Outbound-only: the agent polls an authenticated **`/api/infra/*` plane** (new; admin
  token + per-agent credential from the Worker registry; no inbound ports, no SSH
  exposure). Commands are lease-based (agent pulls work; server never pushes).
- Agent capabilities (phase 1): `fleet status` (read brain JSONs / worker heartbeats
  via API), `doctor` (run h3_doctor_61-style checks), `stop idle studio` (credit
  guard), `restart worker` (bounded, same 3-strikes/cooldown policy), `logs --tail`.
- **Safe shutdown state machine** (instruction §4, verbatim implemented):
  `ACTIVE JOB → FINISHING → IDLE → IDLE TIMEOUT → SAFE TO STOP`. A job claimed by any
  worker the agent can see marks the fleet ACTIVE — "idle from another process's
  perspective" can never kill a claimed job (the 45-min reaper + heartbeat current_job
  are the source of truth, not process idleness).
- Device reality: **NOT VERIFIED** — no Termux device is currently enrolled; the API
  plane + protocol are buildable and testable with a sandbox agent before any device
  exists. Owner must provide the device + Termux environment for live enrollment.

---

## 14. Deyo model architecture (honest product layer)

**What the Deyo family IS (instruction §6 allows exactly this):** a proprietary
production layer — orchestration policies, prompt systems, model configurations,
generation strategies, consistency logic, QA, worker routing — over the real H3 stack.
**What it is NOT (until real weights exist):** independently trained foundation models.

| Product | Meaning (honest) | Current stack mapping |
|---|---|---|
| **Deyo 1 Flash** | Fastest production option | H3 turbo **4-step**, 960×544 band, ≤121 frames, no audio post, fastest claim matching |
| **Deyo 1 Pro** | Higher-quality standard | H3 turbo **8-step**, 960×544 band, audio kept, watermark policy per plan |
| **Deyo 2** | Advanced cinematic | 8-step + per-scene `cinema.ts` direction + reference i2v keyframes, longer multi-scene assembly |
| **Deyo 2 Max** | Flagship system | The full Director pipeline (§11.2): story→characters→storyboard→shots→movement→generation→audio→captions→assembly→QA; highest attempt budgets + priority |

**Model Registry** (new `ModelRegistry` table or settings-JSON — decided at
implementation): `name, version, base_model ("minimax-h3" today), adapter (null today),
capabilities, generation_profile, worker_requirements, prompt_policy, quality_profile,
limits, license_metadata` (license fields filled only from the verified license text —
§3.4 gate). Adding a future Deyo model = registry row + scheduler capabilities, **no
platform rewrite** (instruction §31).

**Training roadmap (honest, instruction §14):**
- Phase 1 (feasible on free fleet, CPU/light GPU): production-intelligence artifacts —
  structured shot/movement/prompt banks distilled from our own accepted renders +
  QA'd outputs (deterministic, license-clean — our own outputs are inputs to our own
  pipeline, not model training).
- Phase 2: LoRA/adapters for **legally appropriate open models only** — never trained
  on H3 outputs while the H3 license's outputs-training clause is unresolved (§3.4).
- Phase 3: registry integration of any trained components.
- Phase 4: larger proprietary models **only** when compute + properly licensed data
  exist. Dataset provenance table (`asset_id, source, license, permission,
  training_allowed, commercial_allowed, attribution_required`) is part of Phase 2
  acceptance criteria, not an afterthought.
- **No claim of a trained Deyo foundation model may appear anywhere until trained
  weights/adapters verifiably exist.**

---

## 15. Event architecture

- **Transport: SSE** (already proven in prod for the per-request trace; Railway +
  Cloudflare pass it; WebSockets would need new infra for zero customer benefit).
- **Event catalog** (instruction §8 — implemented as `ProductionEvent.type`):
  `project.created, story.started/completed, script.started/completed,
  character.started/completed, scene.created, shot.created, movement.planned,
  generation.queued, worker.claimed, generation.started, generation.progress,
  generation.completed, generation.failed, qa.started/completed, export.completed`.
- **Emitters**: Director state transitions (server-side, in the same transaction as
  task updates); worker progress beats (`action:"progress"` — H3 worker will emit these,
  fixing F-10); delivery/QA hooks.
- **Consumer**: `GET /api/production/:id/events?cursor=` SSE; the existing
  `/api/studio/stream` stays for legacy per-request views (backward compat), and gains
  the `guard(req,"stream")` throttle (S-6 fix).
- **No invented percentages**: progress events carry real quantities only (frames
  rendered from worker beats, task counts done/total). The current "pacing simulated,
  status real" label is retained wherever any deterministic pacing remains, and raised
  above the 11px footnote size (A-7).

---

## 16. Migration plan (incremental waves, each shippable + reversible)

Ground rule (instruction §34/§37): every wave is independently deployable, keeps the
site green, keeps both Prisma schemas in sync, and can be feature-flagged.

| Wave | Scope | Key changes | Risk control |
|------|-------|-------------|--------------|
| **W3.0 — Honesty & security hygiene** (smallest safe first task = the copy subset of this wave) | L-1 4K claims, L-2 fake testimonials, L-3 flyer prices, robots `Noindex` fix; S-1 cookie purge + `AUTH_SECRET` rotation; S-6 SSE throttle; S-12 remove `ignoreBuildErrors`; retire `/api` stub | Copy edits, seed edits, one middleware, one env rotation | tsc + dev QA; no schema change; no worker change |
| **W3.1 — Worker plane truth** | F-9 align DB-plane `CLAIM_SQL` with `reserved:` guard; F-10 H3 worker emits `action:"progress"` beats; S-7 drop `?token=` acceptance (header only); admin Video Queue shows worker identity | 3 small diffs + worker script re-push at next Kaggle window | Site-plane changes are backward-compatible with deployed workers (progress is optional today) |
| **W3.2 — Legal & trust pages** | Terms, Refund Policy, Cookie Policy (hash views + footer + consent checkbox at checkout); privacy policy gains cookies/entity/last-updated; JSON-LD fix | Pure additive views/copy | Owner reviews wording before deploy (legal wording = owner sign-off) |
| **W3.3 — Production state + events** | New tables (Production, ProductionTask, ProductionEvent, Worker, ModelRegistry) additive; Director lib; event SSE; studio "Create with Deyo" flow consumes it; old per-request flow untouched | One additive migration (both schemas); feature flag `deyo_director` | Flag off = current behavior; flag on = new flow for new projects only |
| **W3.4 — Deyo product surface + registry** | 4 Deyo model cards (registry-driven), capability-matched claim filter, admin Production Control Center (Overview/Production/Workers/Jobs/Models/Assets/Users/Logs/Security/System), customer/admin label separation | Scheduler superset change + admin UI | Workers without capabilities keep working; admin-only exposure |
| **W3.5 — Media pipeline + QA gates** | ffmpeg assembly service tasks (captions/audio/transitions), final validation (ffprobe: codec/res/duration/corruption) as explicit QA tasks; 9:16 45–60 s target via chunked assembly | Scripts already exist in pieces (Task 56 assembly pipeline) — productized | Validation failures → QA task FAILED honestly, never silent |
| **W3.6 — Termux infra plane** | `/api/infra/*` authenticated plane + safe-shutdown state machine + sandbox test agent | New plane, admin-only credentials | Agent is optional; nothing depends on it |
| **W4 — Deyo training roadmap** | Phase 1 artifacts; Phase 2 only after license gate (§3.4) | Per §14 | Legal gate blocks Phase 2 |

**Rollback strategy:** additive migrations only (no destructive drops — the Task 49
rule); feature flags for the Director flow; worker-plane changes are
backward-compatible so older kernels drain during rollouts; every wave ships behind a
verified local build + prod-selftest.

---

## 17. Testing plan

**Today (verified):** no app test suite (no vitest/jest); QA is scripted
(`scripts/qa_worker_plane.sh`, `qa_stream_e2e.js` 14/14, `prod_selftest` CI,
`smoke_subs.py`) + manual browser E2E + tsc. CI = gitleaks + prod-selftest only.

**Target (instruction §35), prioritized:**

1. **Unit/integration (vitest, app+db against sqlite mirror):** auth guards
   (admin/user/studio/worker planes, cross-plane rejection), rate-limit classes,
   tier limits + dedup, queue ordering + atomic claim + reaper + reserved guard,
   duplicate-deliver rejection, files authz matrix, capability matching, event cursor
   pagination.
2. **Worker fabric integration (real, staged):** register→heartbeat→claim→progress→
   deliver→validate happy path; heartbeat timeout → lease release → retry → reassign;
   3-strikes quarantine; dead-letter. Run against the real claim API from a sandbox
   worker (the existing QA-plane pattern).
3. **Media validation:** ffprobe assertions (codec/res/fps/duration/audio) on worker
   deliveries incl. malformed uploads (magic-byte lies, oversize, zero-byte).
4. **E2E (browser):** customer create→produce→watch→download on mobile viewport; admin
   control center; customer/admin isolation (a customer session must never see provider
   names or admin routes).
5. **CI gates:** extend `prod_selftest` with the vitest suite; keep gitleaks; add a
   cookie-jar/secret-artifact pattern (S-1 lesson).

Rollout rule: a wave is not "done" until its tests exist and pass against the real
stack — same discipline as Tasks 35/43/60 (evidence or it didn't happen).

---

## 18. Risks (ranked)

| # | Risk | Mitigation |
|---|------|-----------|
| R1 | Live admin cookie in public repo until rotation (S-1) | Owner repeats vault passphrase → rotate `AUTH_SECRET` first, then purge history + force-push |
| R2 | H3 commercial licensing unresolved (§3.4) | License-text verification gate before W3.4 marketing scale-up; attribution/disclosure implemented per verified terms; LEGAL REVIEW REQUIRED |
| R3 | Free-fleet churn (Kaggle quota/12 h cap; Lightning credits ≈ 1.5/h; 12.75 banked) | Fabric designed for churn (reaper/retry/reassign); credit guards; honest ETAs; never promise fleet permanence |
| R4 | Shared Supabase project (another app's tables in `public`) | Tenancy guard stays; additive-only migrations; scoped roles |
| R5 | Sandbox rebuilds interrupt long ops (7 rebuilds to date) | Durability model (Task 46): tracked state, vault.enc, idempotent boots; keep waves small |
| R6 | Hash-router ceiling (per-route SEO/meta/404) | Accepted short-term; if organic SEO matters later, migrate routes to real paths behind the same components (flagged, not urgent) |
| R7 | Single-brain sandbox (orchestrators die with rebuilds until selfheal) | brain_boot idempotence + Termux agent (W3.6) as out-of-band supervisor |
| R8 | Owner-keyed copy can silently re-falsify claims (e.g. durations) | Copy comes from DB where owner edits; add honesty lint to seed + flyers source of truth (W3.0) |

---

## 19. Unresolved questions (owner input required)

1. **Vault passphrase** — repeat in chat to unseal `workers/secrets/` (PAT push, Railway
   env rotation for S-1, fleet control). Blocks all remote actions right now.
2. **`AUTH_SECRET` rotation window** (S-1) — rotating logs out all admin/user sessions
   (7-day cookies); pick a low-traffic moment; owner then re-logs-in and sets their own
   password.
3. **H3 license text** — owner or agent (once unsealed) must fetch the actual license
   from `huggingface.co/MiniMaxAI/MiniMax-H3` (and Comfy-Org repack terms) before
   commercial scale-up; answers territory/attribution/outputs-training clauses. LEGAL
   REVIEW REQUIRED for interpretation.
4. **Testimonial policy** — remove seeded fakes entirely (recommended, mandated by §28)
   vs. re-label as placeholders until real reviews exist. W3.0 implements removal.
5. **Termux device** — which device, Android version, network constraints; needed for
   W3.6 enrollment (NOT VERIFIED until then).
6. **Cloudflare Turnstile tuning** (Task 55 leftover) — accept launch friction vs
   challenge tuning decision.
7. **Refund/price-terms wording** — owner sign-off on W3.2 legal text (Nigerian
   consumer law specifics = qualified legal advice).
8. **Kaggle wave-2 gate** — re-arm with a fresh canary or retire the grounded relaunch
   state machine (campaign v10 prompt assets for s04–s06/g01–g08 are lost and would
   need regeneration either way).

---

## 20. Implementation status vs the Master Instruction (§-by-§)

| Instruction § | Requirement | Status 2026-09-10 |
|---|---|---|
| §1 core objective / §2 rules | audit-first, preserve, no Modal, free-first, honest | **AUDIT DONE** (this doc); rules binding |
| §3 worker fleet as one logical pool | registration/capabilities/heartbeat/leasing | **PARTIAL** — atomic claim + reaper + status counts exist; registry/heartbeat/capability matching = W3.4 |
| §4 Termux agent | infra-control channel + safe shutdown | **MISSING** (design §13; device NOT VERIFIED) — W3.6 |
| §5 Director + task states | decompose, explicit state | **PARTIAL** — cinema.ts direction + scene-level flow exist; formal task tree = W3.3 |
| §6 Deyo family (honest naming) | product layer, not fake training claims | **NOT STARTED** — W3.4; no trained-weights claims anywhere (verified) |
| §7 Deyo 2 Max as full system | director→…→assembly | **W3.3/W3.4** |
| §8 real-time production events | real events, no invented % | **PARTIAL** — SSE real-status trace exists (pacing labeled); event-catalog stream = W3.3 |
| §9 Character Lab | persistent characters, honest consistency | **MISSING** — W3.3 (characters from brief exist; persistence/identity-lock honest version) |
| §10 Storyboard | visual, forming live | **PARTIAL** — studio storyboard exists (script-driven); live-forming = W3.3 |
| §11 Shots/Movement first-class | plan vs output separated | **PARTIAL** — cinema.ts plans shots/moves; persisted plan-vs-output = W3.3 |
| §12 H3 behind abstraction | audited, provider-abstracted | **AUDIT DONE** (§3); workers already speak site-API, not Kaggle internals; registry = W3.4 |
| §13 H3 licensing | verify before architecture change | **BLOCKED/NOT VERIFIED** — gate before W3.4 scale-up |
| §14 training roadmap | staged, honest, provenance | Design §14; no false claims in repo (verified) |
| §15 Worker Registry | schema + capability requests | **MISSING** — W3.4 |
| §16 lifecycle + honest customer msg | lease/retry/reassign | **PARTIAL** — reaper+atomic claim exist; leases/quarantine = W3.4 |
| §17 smart scheduler | capabilities/health/quota-aware | **PARTIAL** (priority+quota rotation today) — W3.4 |
| §18 self-healing | backoff, dedup, quarantine, dead-letter | **PARTIAL** — W3.4 formalization |
| §19 persistent state, scene regen | audit DB, no new DB | **AUDIT DONE** (§9); additive extension = W3.3 |
| §20 media pipeline + 9:16 45–60 s | validation chain | **PARTIAL** — normalize+watermark+tpad exist; full QA chain = W3.5 |
| §21 simple customer UI | no infra vocabulary | **GOOD** today (studio hides fleet); keep |
| §22 production screen | live graph, previews, audio, QA | **PARTIAL** — W3.3/W3.5 |
| §23 admin/customer separation | generic labels for customers | **GOOD** (verified: no provider names in customer UI); keep enforced in W3.4 |
| §24 admin control center | live infra state, real connections only | **PARTIAL** — 16 tabs exist; infra center = W3.4 |
| §25 mobile-first | first-class mobile | **PARTIAL** — good bones; A-4/A-7 fixes W3.0+ |
| §26 security audit | serious pass | **DONE** (§6); fixes W3.0+ |
| §27 rate limiting / resource control | protect fleet | **GOOD** (8 classes); SSE throttle W3.0; credits architecture future |
| §28 legal/compliance | pages, fake reviews out | **GAPS** (§8) — W3.0 (claims/reviews) + W3.2 (pages) |
| §29 accessibility | WCAG-oriented | **GAPS** (§7) — W3.0+ passes |
| §30 observability | structured logs, no secrets | **PARTIAL** — events.log + doctor history; admin observability = W3.4 |
| §31 model registry | abstraction for future models | **MISSING** — W3.4 |
| §32 design language | dark cinematic, restrained | **GOOD** (verified site language); extend to new surfaces |
| §33 architectural separation | app/director/state/registry/scheduler/adapter/pipeline/QA/delivery/termux | Target §11 |
| §34 backward compat | users/projects/videos keep working | **BOUND** into every wave |
| §35 testing | real integration tests | **MISSING** — §17 plan, starts W3.1 |
| §36 this document | DEYOUNGLTD_DEYO_MASTER_ARCHITECTURE.md | **DONE** (this file; keep synced) |
| §37 workflow | audit→report→…→commit→next | Followed (Task 62) |
| §38 acceptance test | phone→"Lagos 2050"→Deyo 2 Max→film | **FUTURE** — after W3.3–W3.5; honest note: scene-chunked assembly, not single-pass |
| §39 absolute honesty | never fake | Binding; current violations listed (L-1/L-2) fixed in W3.0 |
| §40 start now | audit first | **THIS DOCUMENT** |

---

### Appendix A — Audit evidence index (Task 62, 2026-09-10)

- Route-by-route API table, lib inventory, schema drift check: full-repo Explore audit
  (53 routes, 16 lib modules, 16 models, drift NONE) — findings §6/§9/§10.
- Worker fabric audit: `workers/deyoung_worker.py`, `workers/lightning/*`,
  `scripts/fleet_brain.py`, `scripts/recovery_orchestrator_51.py`,
  `scripts/site_worker_make.py`, `scripts/h3_doctor_61.py`,
  `campaign/site-worker/deyoung-site-w.py` — findings §3/§4/§12.
- Frontend/legal/a11y audit: all `src/components/site/*` + `src/app/*` +
  `scripts/seed.ts` — findings §7/§8.
- Environment verification: `git ls-files` (S-1/S-11), `workers/secrets` absent,
  processes absent (rebuild #7), `brain/state.json` relaunch grounded.
- Task 61 commits audited: `b50c491` (+1,231 lines: tmux worker/doctor/starter),
  `8e818d1` (45-min orphan reaper). Worklog entry for Task 61 reconstructed post-hoc
  (session ended before logging) — appended to `worklog.md` in the same commit as this
  document.

*End of DEYOUNGLTD_DEYO_MASTER_ARCHITECTURE.md — keep synchronized with code per §36.*
