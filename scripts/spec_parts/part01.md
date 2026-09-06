# markdown.md.txt — DEYOUNGLTD.SITE MASTER UPGRADE SPECIFICATION
## AI Film Production Studio — Deep Research · Existing-Site Audit · Target Architecture · Legal/Safety Program

**Deliverable of the master upgrade prompt** (`upload/Pasted Content_1788739243620.txt`, 79 requirements).
**Audience**: the AI/developer who will safely upgrade the existing site. **Date of research**: 2026-09-06 (UTC).
**Verification discipline** (binding on every reader of this file):
- Numbers appear only where an authoritative source was checked during this research pass; anything else is marked **NOT VERIFIED** with a "how to verify" instruction.
- Legal interpretation is never asserted as certainty; uncertain items are marked **LEGAL REVIEW REQUIRED** and collected in §I.3.
- No fabrication anywhere: no invented limits, no invented law, no invented licenses. "UNKNOWN" is a valid finding.

> Reading order for the implementing AI: §A (what exists, what's broken) → §I.4 (14-day plan, do these first) → §B–§E (build the core) → §F–§G (trust & legal) → §H (engineering discipline) → §I (tables & checklists). Upgrade, do not rebuild: every design below reuses a working subsystem that exists today. The 56 required specification items (prompt §70) are mapped 1:1 in §I.6.

---

# PART A — CURRENT STATE

## A.1 Current architecture (what is actually deployed, 2026-09-06)

**Stack (verified by direct code inspection):**

| Layer | Today | Evidence |
|---|---|---|
| Frontend | Next.js `^16.1.1`, React `^19`, Tailwind v4 (CSS-config), shadcn/ui (new-york), single client page with hash router (`#home #book #subscribe #request #privacy #thanks #admin`) | `package.json:60–67`; `src/components/site/hash.ts:15–41`; `src/app/page.tsx` |
| Backend | Next.js Route Handlers, ~30 routes under `src/app/api/**`, all manual validation (`str()/num()` in `src/lib/api.ts`) — **zod is installed but imported 0 times** | `src/lib/api.ts`; grep `from "zod"` → 0 |
| Database | Supabase Postgres (prod) via transaction pooler `:6543` (rewritten at boot by `deploy/start.sh:34–48`); SQLite dev (`db/custom.db`); **two hand-synced Prisma schemas** | `prisma/schema.prisma` vs `prisma/schema.postgres.prisma` (diff = datasource only) |
| ORM | Prisma `^6.11.1`; **zero `relations` declared** — all FKs are stringly-typed `planCode`/`subscriptionId` with manual cascade deletes | schema files; `subscriptions/[id]/route.ts:57` |
| Auth | Bespoke: scrypt password hashes (good), HMAC-SHA256 stateless cookie `dy_admin`, 7-day TTL, `secure:false` (bad), signing secret persisted to `db/.auth-secret` on ephemeral disk → falls back to a **deterministic public constant** `sha256("deyoung-fallback-secret")` | `src/lib/auth.ts:10–35, 57–88` |
| Admin | Single hardcoded-bootstrapped admin (`admin@deyoung.site` / `deyoung123`), default creds **printed on the login screen** | `auth.ts:114–115`; `admin-app.tsx:215–218` |
| Payments | Client-side SDKs (Paystack inline.js, PayPal SDK, Stripe hosted link) + server-side verify endpoints for Paystack/Flutterwave only; **no webhooks**; `manual` provider = owner confirms by hand; PayPal auto-path is dead code; Flutterwave client launcher never loads its script (silent no-op) | `book-view.tsx:218–255`; `bookings/[id]/verify/route.ts:30–52` |
| Worker plane | `/api/worker/claim` (atomic `updateMany` claim — genuinely safe), `/api/worker/jobs/[id]` (multipart ≤200MB → `public/uploads/req-<id>.mp4`), `/api/worker/status`, `/api/worker/file/[name]` (Range/206, regex whitelist, **public, unauthenticated**); `WORKER_TOKEN` Bearer (or `?token=` — leaks into logs) | `worker/claim/route.ts:23–54`; `src/lib/worker.ts:20–35` |
| Render workers | `workers/deyoung_worker.py`: `stub` (ffmpeg gradient) + `ltx` (LTX-Video 0.9.x via diffusers on CUDA; 768×512 internal, ≤161 frames ≈ 6.7s @24fps even for 60s jobs; auto-fallback to stub) | `deyoung_worker.py:178–248` |
| GPU fleet | Kaggle T4/P100 kernels launched by `scripts/kaggle_launch.py` (~30 free GPU-h/week/account, 8 accounts in vault); MiniMax-H3 film fleet kernels running 2026-09-06; monitor: `scripts/fleet_brain.py` → `brain/state.json` | vault `workers/secrets/kaggle_tokens.json`; `brain/state.json` |
| Storage | **Ephemeral container FS**: every render/upload is wiped on the next Railway deploy; DB rows outlive files → dead download links | `docs/WORKERS.md:100–104`; `worker/jobs/[id]/route.ts:53–56` |
| Email | AgentMail → **owner-only** notifications (booking/contact). Customers never receive any email | `src/lib/agentmail.ts`; `contact/route.ts:16–30` |
| Deploy | GitHub `bluzsammy-png/Deyoung` (public repo) → Railway Railpack; healthcheck `/api/health`; `typescript.ignoreBuildErrors: true` (TS errors ship silently); **no CI, no `.github/`** | `railway.toml:4–13`; `next.config.ts:6–8` |
| Live URL | https://deyoungltd.site (custom domain on Railway edge) + https://deeyoung-production-72ef.up.railway.app | Railway; DNS verified 2026-09-06 |
| Trackers | **None** (no GA/Pixel/PostHog/Sentry/Clarity — grep 0). Fonts self-hosted (next/font/local Archivo). Only outbound third parties: Supabase, AgentMail, payment SDKs, wa.me link | §7 audit grep results |

**Prisma models today (11):** `Admin`, `Settings` (site copy + contact + currency + **`paymentSecretKey` stored plaintext in DB** + `gpuMinutesDaily=240`), `Photo`, `Service` (+`compareAtPrice`), `Booking`, `Message`, `Testimonial`, `Faq`, `Plan` (beginner/pro/elite limits incl. `maxSecondsVideo`, `queuePriority`), `Subscription` (period-based), `VideoRequest` (status `queued|rendering|done|failed|cancelled`, `dedupKey` cache, `gpuMinutes` worker-self-reported).

**What genuinely works and must NOT be rebuilt:** the hash-router single-page storefront; server-side-enforced plan limits + queue position/ETA; the dedup render cache (`dedupKey` checked *before* concurrency limits); the atomic worker claim; the scrypt login; the Railway deploy chain with `:6543` pooler rewrite; the v5 talking-film pipeline (TTS post-dub, ASR-verified 8/8 — the free video model cannot follow scripted dialogue, hallucinated lines; post-dub is the honest fix, proven working); the Kaggle fleet toolchain + secrets vault.

## A.2 Current-code audit — findings register

Severity: **C = critical (fix before any feature work)** · H = high · M = medium · L = low. Every finding is reproducible at the cited path.

### CRITICAL (5)
| ID | Finding | Evidence | Immediate fix |
|---|---|---|---|
| C-1 | **Live AgentMail API key committed in a tracked file** (`am_us_3c12…` in cleartext) | `scripts/agentmail_setup.py:6`; `git ls-files` confirms tracked | Rotate key at AgentMail → move to Railway env var → purge file+history (git filter-repo) → force-push |
| C-2 | **Production `WORKER_TOKEN` committed in tracked worklog** (`dyw_a71c9…` + Railway service ID) | `worklog.md:355` | Rotate `WORKER_TOKEN` on Railway → re-launch workers with new token → purge history |
| C-3 | **Default admin creds printed on the public login screen** (`admin@deyoung.site / deyoung123`) | `admin-app.tsx:215–218`; also `seed.ts:23`, `smoke_subs.py:9` | Owner changes password now; remove hint from UI; keep `/api/auth/me` `usingDefaultPassword` banner; bootstrap creds from env |
| C-4 | **Ephemeral storage destroys paid deliverables**: renders in `public/uploads/` vanish on every deploy; customers holding download links get 404s | `worker/jobs/[id]/route.ts:53–56`; `docs/WORKERS.md:100–104` | Object storage (R2/Supabase Storage) behind signed URLs — §D.1 |
| C-5 | **`/api/upload` does not exist but the admin UI calls it** — every admin image upload and manual video delivery 404s; admin pastes URLs instead, which then break `next/image` (no `remotePatterns` configured) | callers: `admin-content.tsx:174`, `admin-subs.tsx:334`; route glob has no `/api/upload` | Implement or remove; see §E.6 |

### HIGH (10)
- **H-1 No rate limiting anywhere** — login brute-force, contact/book/request spam all unbounded (grep `rate|throttle` → 0). → §F.2
- **H-2 Session cookie `secure:false`** on an HTTPS site (`auth.ts:88`). → §F.1
- **H-3 Auth-secret fallback to a public constant** when the ephemeral disk write fails (`auth.ts:25`) — session forgery becomes feasible. → §F.1
- **H-4 Unauthenticated render download**: `GET /api/worker/file/req-<id>.mp4` needs only the request ID (no email check); combined with `GET /api/requests/[id]?email=` IDOR (email guess = prompt/status/resultUrl disclosure) | `worker/file/[name]/route.ts`; `requests/[id]/route.ts:11–33`. → §F.2
- **H-5 Quota-burn IDOR**: anyone can submit renders against another person's subscription by claiming their email (`requests/route.ts:27–33`). → §F.2
- **H-6 No payment webhooks** — verification only works if the buyer's browser returns; closed tab = paid-but-pending forever. No webhook signature verification anywhere. → §E.2
- **H-7 Verify endpoints don't bind currency or payer identity** — amount-only match (`bookings/[id]/verify/route.ts:30–39`). → §E.2
- **H-8 Payment secret key stored plaintext in the Settings DB row** (`schema.prisma:39`), single point of compromise; should be env + least exposure. → §E.2
- **H-9 Prisma query logging on in production** (`db.ts:10` `log:['query']`) — performance + PII-in-logs. → §F.6
- **H-10 `typescript.ignoreBuildErrors:true` + neutered ESLint (28 disabled rules) + zero CI** — type errors and regressions ship silently. → §H.2

### MEDIUM (12)
- **M-1 Fake testimonials presented as real clients** — seeded quotes rendered under "Real clients / Word on the Street" (`seed.ts:234–263`, `sections.tsx:195`). Violates zero-fabrication charter; consumer-protection exposure. → §G.1
- **M-2 "4K" claims contradict the renderer** (hero chip "★ 4K", request copy "up to 60 seconds… 4K"; plans cap 1080p; worker renders 768×512 upscaled; LTX caps ~6.7s/pass) — `hero.tsx:70`, `sections.tsx:409,473`, `schema.prisma:123`, `deyoung_worker.py:235`. → §G.1
- **M-3 "Rate stays locked forever" promise not implemented in the data model** (`plans.tsx:126`; `pricePaid` overwritten by admin PATCH). → §E.1
- **M-4 PayPal capture is client-side and never verified; Flutterwave client launcher dead** (`book-view.tsx:239–286`; verify route returns `provider-does-not-need-verification`). → §E.2
- **M-5 Worker `resultUrl` JSON delivery accepts any URL** (≤500 chars, no allowlist) — compromised worker could aim customers anywhere. → §C.2
- **M-6 No heartbeat/staleness/reaper**: a crashed worker leaves jobs `rendering` forever; only manual admin recovery. → §C.1
- **M-7 No job attempt counter / poison-job policy / transition validation** on admin status changes. → §B.4
- **M-8 `Float` money** in schema (Booking.amount, Plan.price, Service.price, VideoRequest.gpuMinutes). → §B.1
- **M-9 GPU-minutes accounting is worker-self-reported** (`max(0.1, round(elapsed))`), used only for dashboard. → §E.1 cost engine
- **M-10 Legal surface = one hash-route privacy page**; no Terms, no Refund page, no Cookies, no Accessibility statement; privacy page asserts "Visitors of the site cannot see your booking or message details" which H-4/H-5 contradict. → §G.4–G.6
- **M-11 `deploy/start.sh` runs `node scripts/seed.ts` on every boot; Node <22.6 cannot execute TS → seed silently skipped (`|| echo WARNING`)**; also `prisma db push --accept-data-loss` on every boot. → §H.5
- **M-12 SEO defects**: `sitemap.xml` uses relative `<loc>` (invalid); `robots.txt` contains a non-standard `Noindex:` directive; manifest description is pre-pivot copy; `metadataBase` falls back to localhost. → §H.5

### LOW (6)
- L-1 Unused heavy deps ship in node_modules (`next-auth`, `framer-motion`, `@mdxeditor/editor`, `@tanstack/*`, `zustand`, `recharts`, `react-syntax-highlighter`, `z-ai-web-dev-sdk`) — slow installs, larger attack surface. → §H.5
- L-2 Vestigial `tailwind.config.ts` (v3-style globs don't match `src/`); live theme is `globals.css` `@theme`. → §H.5
- L-3 `next/font/google` Geist Mono = build-time Google fetch; fine today, self-host for air-gapped reproducibility. → §F.5
- L-4 Header admin link `#admin` visible in footer; harmless but consider owner-only reveal. → §F.1
- L-5 StructuredData hardcodes "Mo-Su 00:00-23:59" opening hours (false claim if untrue). → §G.1
- L-6 `/api` root route returns `{"Hello, world!"}` stub; `examples/` scaffolding; 3 duplicate Archivo copies. → §H.5

### Accessibility findings (full list in §F.7; summary)
Showreel dot buttons 6px (WCAG 2.2 target-size fail); arrows 32px; `text-white/40–60` low-contrast text in footer/hero/ticket (AA fail at small sizes); gallery lightbox has no focus trap/Escape (dialog pattern fail); hash views (`#book`, `#subscribe`, `#request`, `#privacy`) have **no h1**; hero film has no `<track kind="captions">` (reduced-motion is, by contrast, handled well in 3 layers — keep it).

## A.3 Gap analysis — today vs the AI-film-studio target

| Capability (target) | Status today | Gap size |
|---|---|---|
| Multi-user accounts, customer login, email verification | None — customers are email strings on Booking/Subscription rows | Large (§B.1 profiles) |
| Production manifest / script / scenes / character bible / storyboards | One `prompt` string per VideoRequest; Elite sells "multi-scene" but no scene model exists | Large (§B.2–B.3) |
| Job state machine (11 states, attempts, leases, DLQ) | 5 flat statuses, no attempts/lease/reaper | Medium (§B.4) |
| Realtime production events (SSE), live studio UI | None (polling with `?email=`; 0 EventSource/WebSocket) | Medium (§D.4–D.5) |
| Object storage + signed URLs + lifecycle cleanup | Ephemeral FS; per-deploy data loss | Medium (§D.1) |
| Credit ledger + cost engine | Row-count quota; self-reported gpuMinutes | Medium (§E.1) |
| Payments hardened (webhooks, currency binding, server capture) | Callback-only verify, amount-only | Medium (§E.2) |
| Model registry w/ license gates + fallback chain | Hardcoded LTX/MiniMax-H3 kernels | Medium (§C.3–C.4) |
| QC automation (ffprobe/ASR gates) | Manual eyeballing (film_verify.mjs exists as a script, not wired to the platform) | Small (§D.8) |
| Feature flags / audit logs / rate limiting / backups | All absent | Small each (§F.2, §E.5, §H.4) |
| Legal pages (Terms, Refunds, Cookies, A11y statement) | Privacy-only | Small but blocking (§G) |
| Testing / CI | None (sandbox shell scripts only) | Medium (§H.1–H.2) |

## A.4 Target architecture (one screen)

```
Browser (Next.js 16 single page + /studio + /admin)
   │  fetch + SSE (/api/events/stream)
   ▼
CONTROL PLANE (same Next.js app + Supabase Postgres)      ← owns all state
   ├─ auth/users/profiles (RLS)        ├─ productions/manifests/scenes
   ├─ job queue (state machine+leases) ├─ production_events (source of truth)
   ├─ credit_ledger (immutable)        ├─ payments + webhooks (server-verified)
   └─ model_registry (license gates)   └─ feature_flags / audit_logs
   │                                      │
   │ signed URLs (never raw keys)         ▼
   ▼                                 EXECUTION PLANE (stateless, replaceable)
OBJECT STORAGE (R2 / Supabase Storage)   Kaggle T4 workers (deyoung_worker.py v2)
   private buckets, lifecycle rules       claim → download inputs → render →
   renders/refs/audio/thumbnails          checkpoint → upload → deliver → heartbeat
   ├─ FREE: Supabase Storage 1GB          ├─ FREE: Kaggle ~30 GPU-h/wk × N accounts
   └─ PAID: R2 (zero egress)              └─ PAID: Atlas/Evolink premium APIs (Kling/Veo)
```
**Invariants (the whole document in five lines):**
1. The browser never talks to Kaggle, storage keys, or payment APIs directly — only to the control plane.
2. The control plane owns every state transition; workers are stateless and disposable.
3. Every expensive operation carries an idempotency key; every balance change is a ledger row; every render is an asset-graph node.
4. Real events only: if the backend didn't emit it, the UI doesn't show it. Unknown → honest state, never a fake progress bar.
5. Free-first with a documented paid exit at every layer (§E.3–E.4).

## A.5 Why this architecture (prompt §14/§78 rationale, grounded in this codebase's history)

- **A film compiler beats "prompt → video API"** because the work we actually shipped proves it: our own model hallucinated every scripted line (Task 30, worklog) — recovered only because the pipeline separated script, voices, visuals, and assembly, so we could post-dub with TTS and ASR-verify all 8 lines. That is a compiler property: stages are independently inspectable, retryable, and replaceable. A monolithic prompt-to-API call gives one unrecoverable output.
- **Multiple shots beat one long generation** for the same reason: a 60s film = 8–10 scene jobs of 5–10s each (matching §3 of the prompt); any scene can fail and be re-queued without destroying the production. Our first live film (v3.5) shipped exactly this way when the provider failed 6/8 scenes — Ken Burns fallback for missing scenes, real clips where we had them. Duration must always be computed from actual rendered assets (`ffprobe`), never claimed from a model spec (§D.8).
- **Workers are disposable; state is not** — Kaggle kills sessions (our 4 film kernels run ~10h toward a ~9–12h cap); therefore leases + heartbeats + checkpointing (§C.1) are not optional. Losing a free GPU session must cost one scene, never a production.
- **The ledger exists because credits are money.** Row-count quotas cannot express refunds, reversals, promotions, or expirations, and cannot be audited when a customer disputes a charge (§E.1).
- **Legal/compliance surfaces exist because this is a paid Nigerian consumer service**, not a demo: fabricated testimonials and unverifiable capability claims are the two things regulators and payment providers actually act on (§G).

---
