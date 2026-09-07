# PART H — ENGINEERING PLANE

## H.1 Testing (prompt §66)

Framework: **Vitest** (unit/integration) + **Playwright** (E2E, already proven via agent-browser patterns) + contract tests for webhooks. The `pati/` subtree has 46 passing pytest tests — that pattern (tests live next to the code, run in CI) is the house style to copy, not the current ad-hoc `scripts/qa_*.py` situation.

| Suite | Covers | Non-negotiable cases |
|---|---|---|
| Unit | money math (ledger balances, kobo conversions), plan-limit enforcement, queue position math, manifest schema validation, capability scheduling | a ledger replay test: random sequence of purchase/consume/reverse/expire → balance always matches sum of deltas |
| Integration | DB (both schemas — the sync test), storage adapter (signed URL round-trip), worker claim/deliver (the existing `qa_worker_plane.sh` flow becomes a test), webhook parsers (Paystack sig HMAC, Flutterwave hash, duplicate events, tampered signature → 403) | duplicate webhook = exactly one ledger row |
| E2E | signup→project→production→generation→completion→export (happy path), subscribe→pay(mock)→request→deliver→download, admin flows | no console/page errors (existing qa_site.mjs standard) |
| Failure injection | worker crash mid-render (lease expiry → requeue), provider timeout, OOM, duplicate webhook, duplicate claim, storage outage, payment failure | the state machine table (§B.4) is literally asserted row by row |
| A11y | Playwright axe-core on all views; contrast assertions on the theme | WCAG 2.2 AA on every shipped view |
| Security | rate-limit behavior, IDOR attempts (request-status with wrong email token, file access without signed URL), RLS if direct DB ever exposed | per §F.2 |

## H.2 CI/CD (prompt §67) — GitHub Actions free tier (public repo = free minutes; verify concurrency limits at docs.github.com — **NOT VERIFIED this pass**)

Pipeline (blocks merge AND blocks the push-to-deploy branch):
1. install (bun, cached) → 2. `tsc --noEmit` (**first task: delete `ignoreBuildErrors: true`** — expect a cleanup wave, do it in W0) → 3. eslint with the 28 disabled rules re-enabled progressively (start with `no-unused-vars`, `no-explicit-any`) → 4. unit + integration (Postgres service container; run against **both** schema files + a drift test `schema.prisma ⇄ schema.postgres.prisma`) → 5. build → 6. E2E smoke against the standalone build → 7. **gitleaks/secret scan** (would have caught C-1/C-2) → 8. axe a11y → 9. dependency audit (`bun audit`) → 10. legal-page check (footer must link Terms/Privacy/Refunds; privacy page must list every processor found in `src/lib/*` — a simple grep-based test).
Deploy: merge to main → Railway auto-deploy (existing) → post-deploy healthcheck assert (`/api/health` 200) → smoke E2E against the live URL from CI. Do not deploy when any critical check fails (prompt §67).

## H.3 Backups (prompt §68)

- **DB**: Supabase built-in snapshots on Pro; on free tier, a daily `pg_dump` cron to object storage (worker-cron on Kaggle CPU is fine) — 7-day rotation. Restore drill quarterly.
- **Storage**: R2/Supabase bucket versioning on `renders/` + `masters/` (expensive classes only); lifecycle cleanup for `tmp/`.
- **Config**: Railway env export + `railway.toml` + DNS records documented in the private ops doc (never in the public repo).
- **Secrets**: the vault + private Kaggle dataset (already durable, verified) — the only approved secret backup channel.
- **The film masters**: final masters additionally copied to the owner's storage (e.g. Google Drive via the existing rclone-ish flows) — a paid customer's film must survive any single-vendor incident.

## H.4 Disaster recovery (prompt §53)

Scenarios with runbooks (write as `docs/DR.md`): Railway outage (status page + customer notice template); Supabase outage (read-only mode banner; queue writes buffer to local disk on workers); storage loss (re-render from manifest — the asset graph makes re-rendering deterministic; ledger preserves what was paid); secret compromise (rotation runbooks per secret; the C-1/C-2 incident IS the template); bad deploy (Railway rollback + `db push` is additive-only so rollbacks are safe); data-deletion request mid-production (cancel jobs first, then purge).

## H.5 Deployment hardening (prompt §54 + audit M-11/M-12/L-1)

1. `deploy/start.sh`: seed only when `SEED_ON_BOOT=true` (default false in prod); run migrations (`prisma migrate deploy`) instead of `db push --accept-data-loss` once W1 migrations exist (keep push for dev only); guard `node scripts/seed.ts` behind a Node-version check or precompile seed to JS.
2. Kill dead weight deps (L-1); delete vestigial `tailwind.config.ts` (L-2); self-host Geist Mono (L-3); delete `/api` stub (L-6).
3. Fix SEO defects (M-12): absolute-URL sitemap generated from `NEXT_PUBLIC_SITE_URL` (which must be set in Railway to the custom domain), standard robots.txt, refreshed manifest description.
4. Two-stage rollout for the new control-plane: feature flags (`film_compiler_v1`, `storage_v2`, `customer_auth_v1`, `h3_film`, `payments_webhooks`) — every flag has an emergency-off (§B.1 FeatureFlag).

## H.6 Migration strategy — implementation waves (each independently shippable)

| Wave | Scope | Exit criteria |
|---|---|---|
| **W0 — security emergencies** (days 1–3) | Rotate + purge C-1/C-2 secrets (incl. git history filter + force-push + Railway env updates); C-3 login-screen fix; F.1 cookie/secret fixes; rate limiting (F.2); delete query logging (F.6); implement or remove /api/upload (C-5) | audit C-items closed; secrets scan green; live site unaffected |
| **W1 — data foundation** (week 1–2) | New tables (§B.1) + Profile/LoginCode + relations + Decimal money + Job mapping from VideoRequest; storage_v2 (object storage behind signed URLs) replaces /api/worker/file | dual-run: old and new queue both work; no deploy data loss (the C-4 class is dead) |
| **W2 — jobs & workers** (week 2–3) | State machine + leases + reaper + attempts + checkpoints; worker v2 (register/heartbeat/capabilities); model registry + license gate; QC gate promoted to blocking | a killed worker self-heals in <lease+poll seconds; QC blocks a deliberately corrupted render (test) |
| **W3 — studio & events** (week 3–4) | ProductionEvent + SSE + /studio control room; manifest compiler v1 behind flag; character bible seeded from film-v5 cast | a customer can watch a real production assemble in real time; refresh-safe |
| **W4 — money** (week 4–5) | CreditLedger + transactional debit + CostRecords; payment webhooks + hardening (§E.2); locked pricing column; refund policy live (§G.7) | duplicate-webhook test = single ledger row; a forced render failure auto-reverses credits |
| **W5 — legal & launch** (week 5–6) | All §G pages live (Terms/Refunds/Cookies/A11y/Privacy rewrite), testimonial relabel, claim fixes (4K→1080P), consent flow if any tracker adopted, compliance dashboard populated, launch checklist §I.1 signed | §75 self-audit answers all-green or explicitly LEGAL REVIEW REQUIRED |

Ordering rationale: W0 first because leaked credentials make every other control moot; W1 before W2 because the state machine needs the Job table; money (W4) after jobs (W2) because debits hook into claims; legal (W5) last-but-blocking because it must describe the system that actually exists (prompt §31: the policy reflects the implementation, not aspirations).

---
