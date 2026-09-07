# PART E — MONEY & OPS

## E.1 Credit ledger & cost engine (prompt §21–§22)

**Ledger**: `CreditLedger` rows only; there is no `user.credits = 100` column anywhere. Invariant: `balanceAfter` of the newest row per profile = current balance; every row has `type`, `reason`, `idempotencyKey` (unique — replays are no-ops). Entry types: `purchase` (verified payment), `consumption` (render debit at claim time), `reversal` (failed/cancelled render), `promo`, `refund` (operator action), `adjustment` (support), `expiration`. Debits are **transactional with the claim**: the same DB transaction that flips a job to CLAIMED inserts the `consumption` row (row-locked `SELECT … FOR UPDATE` on the profile's balance); a rollback never loses both money and render.

**Policy table (consumer-facing copy mirrors this exactly):**
| Situation | Ledger action |
|---|---|
| Render fails terminally (any failure type) | `reversal` full credit back, automatic |
| QC pass but customer rejects a scene | regenerate from credits if within plan allowance; else `consumption` again (stated in Terms §G.6) |
| Duplicate payment detected (same providerRef) | second payment auto-`refund` path + audit log |
| Plan price change | existing subscriptions keep their price — implemented via `Subscription.lockedPriceMinor` (fixes M-3; "rate locked" becomes a column, not a slogan) |

**Cost engine**: every `Job` completion writes `CostRecord` with **server-measured** GPU-minutes (lease start→end, not worker self-report — fixes M-9) and `theoreticalCostMinor` computed from a per-model price table even when the GPU was free (Kaggle ≈ $0 theoretical out-of-pocket, but the table carries the replacement cost, e.g. T4 cloud ≈ $0.35–0.60/h — **current cloud pricing NOT VERIFIED; populate from provider pricing pages when cost reporting ships**). This is what makes FREE→CHEAP→PREMIUM migration a config change (§E.4), and it makes unit economics visible from day one.

## E.2 Payment architecture (fixes H-6/H-7/H-8/M-4)

**Providers**: Paystack + Flutterwave (Nigeria-first, researched fees below), PayPal + Stripe (existing manual rails), `manual` (bank transfer) — all behind one `payments` abstraction (`src/lib/payments/{provider}.ts` implementing `initiate`, `verify(ref)`, `parseWebhook(headers, body)`).

**The flow (server-authoritative, prompt §23):**
```
USER PAYS → PROVIDER → (a) webhook POST /api/webhooks/{provider}  [primary]
                     → (b) callback verify (existing endpoints)  [fallback]
both paths → parseWebhook/verify (signature + amount + currency + ref) → Payment row (idempotent)
         → Subscription activation / CreditLedger purchase → ProductionEvent → email receipt
```
- **Webhooks are primary**: `POST /api/webhooks/paystack` (verify `x-paystack-signature` HMAC-SHA512 with secret), `POST /api/webhooks/flutterwave` (verify `verif-hash` header against stored secret) — signature verification code per provider docs (hookdeck/paystack guide reviewed in this pass; **exact header algorithms: implement from the official docs pages and add contract tests, §H.1**). Both endpoints: raw-body read, 200-fast/queue-slow, duplicate `webhookEventId` ignored.
- **Verify hardening**: bind `amount` **and `currency`** and expected `ref` prefix; reject `ref`s not matching a pending row (fixes H-7); PayPal: server-side capture via Orders API (client `onApprove` sends only the order ID; server captures and records — fixes M-4); Flutterwave client launcher: either load the official inline script or remove the option until it works (silent no-op is worse than absence).
- **Secrets**: `paymentSecretKey` moves from the Settings DB row to Railway env vars (fixes H-8); admin UI keeps provider **on/off + public key** only. `Payment` rows store verified amounts in minor units.
- **Refunds**: Paystack/Flutterwave refund APIs invoked from an admin-only action, mirrored as `Payment.status=refunded` + negative ledger row + email. No client-side refund claims (§G.7 policy copy).
- **Fees (verified this pass, for the pricing model)**: Paystack Nigeria **local 1.5% + ₦100, fee waived under ₦2,500, capped ₦2,000** (paystack.com pricing, support pages, 2026 snippets agree); Flutterwave Nigeria **local 2.0% (1.4% transaction + 0.6% platform)** after the Apr-2025 increase (flutterwave.com help center). International card pricing differs — **verify exact international tiers before publishing any fee table to customers**.

## E.3 Free-first infrastructure (prompt §24/§72 research table)

| Component | Provider | Free? | No card? | Nigeria? | Current limit | Upgrade path | Source status |
|---|---|---|---|---|---|---|---|
| App hosting | **Railway** (existing) | trial credit only | no | yes (edge serving) | trial-limited | Hobby $5/mo → Pro | **NOT VERIFIED this pass — confirm current trial terms at railway.com/pricing** |
| Postgres | **Supabase** (existing) | yes | yes | yes (region eu-central today) | free tier egress **5 GB/mo** (schematichq summary of official pricing, 2026-05); storage/disk free cap: **NOT VERIFIED — check supabase.com/pricing** | Pro ($25/mo) → dedicated | verified via 2026 secondary sources; primary page exists |
| Object storage | Supabase Storage → **Cloudflare R2** | yes | yes (R2 requires CF account; card requirements NOT VERIFIED) | yes | R2 10GB/zero-egress — **NOT VERIFIED this pass; verify developers.cloudflare.com/r2/pricing** | per-GB | R2 pricing page exists; numbers to re-verify |
| Free GPU | **Kaggle** (proven, in use) | yes | yes | yes (operator uses it daily) | **~30 GPU-h/week per account** (official Kaggle "Weekly Maximum GPU Usage" post; community-verified 2026); T4 ×2 / P100 options; session cap ~9–12h (**exact current cap NOT VERIFIED — Kaggle "increased session runtimes" post; check notebook docs**) | multiple accounts (current pattern: 8 tokens) → paid GPU (§E.4) | official posts verified |
| Free GPU #2 | Lightning AI / SageMaker Studio Lab / Colab | partial | partial | partial | **NOT VERIFIED this pass** — evaluate only if Kaggle quota becomes the bottleneck; priority: email signup, Nigeria access, own-model runs (prompt §6) | per-provider | deliberately unverified → do not build on unverified platforms |
| Email | **Resend** (proposed) + existing AgentMail | free tier exists | yes | yes (API) | **NOT VERIFIED this pass — confirm resend.com/pricing (search results were noise)**; AgentMail currently used owner-side | Resend paid tier | agentmail key must rotate first (C-1) |
| Analytics | **PostHog** (proposed) | generous free tier | yes | yes | **NOT VERIFIED — confirm posthog.com/pricing**; if adopted: no prompts/media, product events only (§E.6) | usage-based | — |
| Errors | **Sentry** (proposed) | free Developer tier | yes | yes | **NOT VERIFIED — confirm sentry.io/pricing** (official page found; numbers unread) | Team tier | — |
| Payments | Paystack / Flutterwave | per-transaction | yes | **yes — Nigeria-primary** | fees §E.2 | volume tiers | verified |
| Bot protection | Cloudflare Turnstile (proposed) | free | yes | yes | **NOT VERIFIED** — confirm before adding; only with honest consent copy (§F.5) | — | — |

**Rule repeated from the prompt (§73):** every "NOT VERIFIED" above gets a verification task in §I.4 **before** the corresponding component ships; nothing builds on an unverified limit.

## E.4 Free → paid migration paths (prompt §63)

| Layer | Free today | First paid step | Dedicated step |
|---|---|---|---|
| GPU | Kaggle fleet (8 accounts ≈ 240 GPU-h/wk theoretical) | Atlas/Evolink top-up for Kling/Veo premium scenes (keys exist, empty) | dedicated T4/L4 VM (provider-agnostic worker — same binary, `provider: paid-api` or `provider: vm`) |
| DB | Supabase free | Supabase Pro | dedicated Postgres (Prisma URL swap only) |
| Storage | Supabase Storage | R2 (zero egress for video) | R2 + CDN pinning |
| Queue | Postgres tables (current) | unchanged to ~10k jobs/day | Redis/BullMQ or a workflow engine **only when** Postgres queueing measurably hurts (keep the state machine, swap the transport) |
| Email | AgentMail (owner notifications) | Resend free tier (customer receipts) | Resend paid |
| Video | local/LTX/H3 free fleet | premium APIs per scene (manifest `modelPolicy`) | dedicated inference (model registry unchanged) |

No architectural rewrite anywhere — the abstraction seams are the storage interface, the payments interface, the worker registry (`provider` field), and the model registry (`modelPolicy.fallbacks`).

## E.5 Observability (prompt §28) & Admin Mission Control (prompt §27)

- **Sentry**: frontend + route handlers + worker script (a tiny `/api/worker/telemetry` error forwarder or Sentry SDK in the kernel). Capture: render failures with job ID, webhook signature failures (security signal), deploy boot failures. **No prompt/media payloads** — IDs only.
- **PostHog** (optional, behind a flag; if the owner prefers zero third-party JS, skip — honest default is *not* to add trackers without a need): events `signup`, `project_created`, `production_started`, `production_completed`, `generation_failed`, `export`, `purchase`, `subscription_cancelled`. No PII in properties.
- **Admin Mission Control** (extend the existing /admin): Users, Projects, Active productions, Queue (exists — add lease/attempts columns), Workers (health, drain/disable), GPU health (heartbeat feed), Model usage + license status, Failures & retries, Credits (ledger viewer w/ filters), Payments/refunds, Storage usage, Estimated vs theoretical cost (`CostRecord` rollups), Security alerts (failed logins, webhook sig failures), **Compliance status panel (§I.2 dashboard)**. Every admin mutation → `AuditLog` row. Everything server-authorized (existing `guardAdmin`) and paginated.

## E.6 Notification & upload plumbing

- **/api/upload implementation (fixes C-5)**: `POST /api/upload` (admin) and `POST /api/files` (worker-scoped) → size cap per kind (image 8MB as the UI already promises; video 200MB), MIME sniffing (magic bytes, not extension), straight to object storage (§D.1), returns `assetId`. `next/image` remotePatterns: only our storage host, explicitly configured.
- **Customer emails** (new — today customers get nothing): booking confirmed, payment receipt, production completed (with download link), refund notice. Transactional only; marketing is a separate explicit-consent list (§F.5). Provider: Resend behind `email_customer_v1` flag; AgentMail keeps owner notifications until rotated (C-1).

---
