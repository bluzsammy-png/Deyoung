# PART F — TRUST PLANE (SECURITY · PRIVACY · ACCESSIBILITY)

## F.1 Authentication & sessions

1. **Rotate + purge the two committed secrets (C-1, C-2) before anything else** — §I.4 W0 has the exact runbook. This is the precondition for every other security fix: purged history + rotated keys.
2. Session cookie: `secure: true` (the site is HTTPS-only), `httpOnly` stays, `sameSite: lax` stays, add `__Host-` prefix if feasible; 7-day TTL stays.
3. Signing secret: Railway env var `AUTH_SECRET` (48+ random bytes generated once); delete the `db/.auth-secret` file path and **delete the deterministic fallback constant** (`auth.ts:25`) — if env is missing the server must fail to boot, not forge with a public constant (fixes H-3).
4. Admin bootstrap: credentials from env (`ADMIN_EMAIL`/`ADMIN_PASSWORD`) on first boot; **remove the creds hint from the login screen** (`admin-app.tsx:215–218`); keep the `usingDefaultPassword` warning banner + a forced change flow (fixes C-3).
5. Customer auth: passwordless one-time codes (10-minute expiry, 5-attempt lock, rate-limited) via `LoginCode` — no password DB to protect, no reset flows to abuse; profile created on first successful login; email verification = proof-of-login.
6. `AuthSecret` rotation procedure documented (rotate → all sessions invalidated → acceptable).
7. `WORKER_TOKEN`: Bearer header only (drop `?token=`, H-log risk); rotate now (C-2) and quarterly; per-kernel `workerKey` registration for attribution.

## F.2 Authorization, rate limiting & abuse control

- **Rate limiting**: Postgres-backed fixed-window counters (`RateLimit` table or in-`Settings` JSON) — no Redis needed at current scale. Limits (per IP + per route class): login 5/15min; one-time-code 3/10min; booking/subscription/contact 5/h; video-request 10/h; verify endpoints 10/h; file streaming 120/min. 429 with `Retry-After`. Rationale: kills brute force (H-1), spam, and quota-burn loops (H-5) with one mechanism.
- **IDOR closure (H-4/H-5)**: `GET /api/requests/[id]` requires the **full request ID + verified email token** (issued once at submit, stored hashed); render downloads move behind signed, expiring URLs bound to the requesting profile/email (§D.1); submission against a subscription requires an active session profile match (not a bare email string).
- **CSRF**: SameSite=lax covers POSTs for now; add double-submit token on all mutating browser routes when customer sessions land.
- **Security headers** (next.config or middleware): `Strict-Transport-Security` (1y, preload), `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy: camera=(), microphone=(), geolocation=()` (nothing on the site needs them — prompt §53), CSP starting `report-only` then enforcing (`self` + payment SDK hosts + inline-style nonce work).
- **Audit trail**: every admin mutation writes `AuditLog` (§B.1); login attempts (success/fail) logged; webhook signature failures logged + surfaced in admin Security panel.

## F.3 Secrets management (project-wide policy, aligned with the vault discipline)

- Production secrets live **only** in Railway env vars: `DATABASE_URL`, `AUTH_SECRET`, `WORKER_TOKEN`, `AGENTMAIL_API_KEY`, payment provider secrets, storage credentials. Nothing secret in the DB `Settings` row (H-8), nothing secret in tracked files (C-1/C-2 lesson), nothing secret in the public repo.
- Worker fleet credentials: local vault `workers/secrets/` (gitignored, 0600) + durable off-site backup = **private Kaggle dataset `deyoungsltd/deyoung-worker-vault`** (verified private 2026-09-06: foreign token → 403); recovery runbook in `BRAIN.md` §3. Rotation after any suspected exposure; `scripts/vault_backup.py` re-pushes after every vault edit.
- Secret scanning in CI (§H.2) prevents regression — it would have caught both leaks.

## F.4 Privacy program (Nigeria-first, honest)

- **Governing law**: Nigeria Data Protection Act 2023 (NDPA) + NDPC implementation. Registration: NDPC operates a Data Controller/Processor registration regime; entities classified as "data controllers of major importance" (DCPMI) must register (NDPC portal; law-firm summaries in this pass agree). **Whether DeYoung qualifies as DCPMI at current scale: LEGAL REVIEW REQUIRED** (§I.3) — register anyway if review is inconclusive; the portal process is lightweight.
- **Privacy Policy (replace the hash-route page)** — must describe the *actual* processors, which today are: Supabase (DB + storage, EU region), Railway (hosting/logs), AgentMail/Resend (notification transport), payment providers (Paystack/Flutterwave/PayPal/Stripe — receive payment data), the AI render providers (video models receive prompts/reference images — **name them per model registry**), error monitoring if adopted (§E.5). Never claim "we never share your data" (a processor list exists); never claim "zero retention" that providers don't offer.
- **Data minimisation (prompt §32)**: collect name/email/phone (booking only), prompt text, uploaded references, payment metadata (no card data — providers hold it). Do **not** add IP-based analytics, fingerprinting, session recording, or camera/mic permissions (nothing uses them — codify in `Permissions-Policy`).
- **Retention (prompt §57)**: accounts while active + 90d; productions/renders until user deletion + 30d grace (storage lifecycle); worker temp artifacts 3d; logs 30d; payment records 6y (fiscal retention norm — **LEGAL REVIEW REQUIRED** for exact Nigerian bookkeeping requirement); analytics events 12m.
- **Rights (NDPA)**: access/correction/deletion/complaint channel → `privacy@deyoungltd.site` route (new inbox), with a documented 30-day handling runbook in the ops docs; deletion job clears profile + assets (ledger rows retained in anonymized form for financial audit — stated in the policy).
- **International (prompt §56)**: if EU/UK/US customers are intentionally served → GDPR/UK-GDPR/state-law assessments **LEGAL REVIEW REQUIRED**; until then, geo-availability statement stays in Terms, no GDPR claims anywhere.

## F.5 Cookies & consent

Today the site sets exactly one cookie (the admin session) and runs **zero trackers** — say so truthfully: a short Cookie Policy listing `dy_admin` (necessary, admin login) is the *entire* honest requirement right now. If analytics/anti-bot (PostHog/Turnstile) are ever enabled, add a consent banner **before** they load: equal-prominence accept/reject, no pre-ticked boxes, reject as easy as accept, granular analytics vs marketing, consent logged with timestamp+policy version. No dark patterns (prompt §34), no silently activated trackers (§37), no cookie walls.

## F.6 Logging hygiene (prompt §59)

- `db.ts`: drop production query logging (H-9) — `log: NODE_ENV === 'development' ? ['query'] : []`.
- Never log: passwords, tokens, provider secrets, raw payment payloads beyond refs/amounts, private media URLs (they're capability URLs).
- Sentry (if adopted) scrubs `DATABASE_URL`-adjacent fields; add `beforeSend` denylist test in §H.1.

## F.7 Accessibility remediation list (WCAG 2.2 AA — audit-verified items)

| # | Issue (evidence) | Fix |
|---|---|---|
| A-1 | Showreel dot buttons 6px (`showreel.tsx:297`), arrows 32px | ≥24×24 CSS px hit areas (WCAG 2.2 SC 2.5.8 AA minimum; 44px recommended for primary controls) |
| A-2 | Low-contrast text: `text-white/40` copyright, `text-white/60` hero bullets, `text-white/55` ticket stars, StatsStrip white-on-red ≈4.0:1 at small-bold | Raise to white/70+ on dark, ≥4.5:1 for body text, ≥3:1 for large/bold ≥18.66px; test both themes with a contrast checker in CI (§H.2) |
| A-3 | Gallery lightbox: no focus trap, no Escape (`sections.tsx:126–148`) | Use a real dialog primitive (the repo already ships shadcn `dialog.tsx`): focus trap, Escape close, restore focus, `aria-modal` |
| A-4 | Hash views `#book/#subscribe/#request/#privacy` have no `h1` (`sections.tsx:504` renders h2) | Add visually-styled h1 per view; verify heading order h1→h2→h3 |
| A-5 | Hero film: no `<track kind="captions">` (`hero.tsx:194–203`) | Ship a WebVTT sidecar alongside the master (assembly already has caption text — emit .vtt); keep burned captions for visuals, VTT for AT |
| A-6 | Keyboard: mobile menu lacks containment; header links rely on default outline | Keep visible focus (`focus-visible:ring` exists in shadcn), add focus containment to the open menu, tab order check in E2E |
| A-7 | Forms are already well-labeled (`htmlFor` everywhere — keep); error messages must be `aria-live` | Add `aria-live="polite"` to form error/success regions |
| A-8 | `prefers-reduced-motion` is handled in 3 layers (globals.css 256–268, 392–408; JS checks in motion.tsx/showreel.tsx) | Preserve during any motion refactor; add a reduced-motion E2E snapshot |
| A-9 | New /studio view (§D.5) | Build to the same standard from day one: all live regions `aria-live="polite"`, canvas has text alternative (scene list IS the alternative), crew/log are real text |
| A-10 | Android app | **No Android app exists in this repo** (manifest is a PWA). Prompt §52 requirements are recorded as **build-time requirements** (TalkBack labels, text scaling, touch targets, permission justifications) should a native app ever be produced — the PWA manifest should be updated (M-12) meanwhile |

---
