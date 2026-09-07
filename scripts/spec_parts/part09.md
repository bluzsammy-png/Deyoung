# PART I — TABLES, DASHBOARDS, REGISTERS, ACTION PLAN

## I.1 Final launch checklist (prompt §70 item 56 + §75 self-audit)

**Technical**
- [x] Can a worker disappear without destroying a production? — Yes: leases + reaper + requeue (§C.1); failure-injection test asserts it (§H.1)
- [x] Can another provider replace Kaggle? — Yes: `Worker.provider` + provider-agnostic worker binary + paid-API adapters (§E.4)
- [x] Can another video model replace H3? — Yes: ModelRegistry + `modelPolicy.fallbacks` + QC-neutral asset graph (§C.3–C.4)
- [x] Can the system generate a 60-second film from multiple shots? — Yes: manifest scenes → scene jobs → measured assembly (§B.2/D.7); duration always measured (§D.8)
- [x] Can users see real production activity? — Yes: DB events + SSE + studio (§D.4–D.5); fake progress is forbidden and untestable-by-absence
- [x] Can failed jobs be retried? — Yes: attempts + taxonomy (§B.4) | Can jobs be resumed? — Yes: segment checkpoints (§C.5)
- [x] Can credits be audited? — Yes: immutable ledger + idempotency keys (§E.1)
- [x] Can final videos be traced to source assets? — Yes: asset graph joins (§D.2)

**Security** — cross-user access: closed by signed URLs + email-token status + profile binding (§F.2) · credits manipulation: impossible without a ledger row; ledger writes are server-transactional (§E.1) · fake payment success: requires provider signature (§E.2) · admin escalation: single-admin + rate-limited + no public hint (§F.1) · worker secret exposure: Bearer-only, rotation runbook, scoped uploads (§C.2) · signed-URL abuse: 10-min TTL + bound to asset + audited (§D.1)
**Legal** — fake reviews: removed/relabelled (§G.1) · unsupported claims: fixed to renderer truth (§G.1) · unknown image licenses: none shipped without ledger entry (§G.2) · model licenses verified: gate enforced (§C.3) · privacy accurately described: processor list from code, not wishes (§F.4) · cookies/tracking disclosed: §F.5 · consent where required: §F.5 · refunds explained: §G.7 · terms accessible: footer links + hash views · real business details: §G.8 (registration number explicitly absent until real)
**Accessibility** — keyboard, alt text, contrast, labels, forms: §F.7 remediation list; TalkBack/Android: build-time requirements recorded (§F.7 A-10)
**Operations** — replaceable free infra: §E.4 table · GPU scaling: fleet + registry (§C.1) · worker drain: §C.2 · job recovery: §B.4 · costs measured: CostRecords (§E.1) · monitoring: §E.5

**Ship blockers before scaling paid volume**: W0 closed; Terms/Privacy/Refunds live; storage_v2 (no ephemeral deliverables); payment webhooks; ledger; testimonial relabel; model-license gate on for paid renders.

## I.2 Compliance dashboard (prompt §61) — current honest status

| Area | Status | Evidence / gap | Required action |
|---|---|---|---|
| PRIVACY | **FAIL** | hash-route only; contradicted by IDOR reality (H-4/H-5); processor list missing | F.4 rewrite post-W1 |
| COOKIES | PASS (trivially) | exactly one first-party admin cookie; honest single-cookie policy suffices | §F.5 page |
| TRACKING | PASS (zero trackers) | grep-verified | keep zero unless consented (§F.5) |
| CONSUMER PROTECTION | **FAIL** | no complaint channel; urgency claims without implemented price-lock | §G.1/§G.9 + lockedPriceMinor |
| REFUNDS | **FAIL** | one FAQ sentence; no policy page; no auto-reversal | §G.7 + §E.1 |
| COPYRIGHT | PARTIAL | assets in-house; ledger missing; "Made with" labels exist | ASSETS.md ledger (§G.2) |
| MODEL LICENSES | **FAIL (blocking paid use)** | H3 territory + LTX commercial terms unread | §C.3 verification tasks |
| ACCESSIBILITY | **FAIL** | §F.7 list (targets, contrast, dialog, headings, captions) | §F.7 fixes |
| SECURITY | **FAIL** | C-1..C-5 + H-1..H-10 open | W0 + F.1–F.3 |
| PAYMENTS | PARTIAL | server verify exists (good); webhooks/currency/binding missing | §E.2 |
| BUSINESS INFORMATION | PARTIAL | real brand/contact; no entity number (honestly absent) | owner CAC decision (§G.8) |

## I.3 LEGAL REVIEW REQUIRED register (for a Nigerian-qualified lawyer)

1. NDPC/DCPMI registration duty & threshold for this service at current scale (NDPA 2023 + NDPC guidance) — §F.4.
2. IP clause: what can be contractually promised about ownership/licensing of AI-generated outputs under the Copyright Act 2022 (AI authorship is unsettled) — §G.2/§G.6.
3. Retention period for payment/financial records (6-year assumption unverified) — §F.4.
4. Refund policy wording vs FCCPC expectations for prepaid subscription services — §G.7.
5. Terms: governing law/venue + enforceable limitation-of-liability that preserves non-excludable consumer rights — §G.6.
6. Geofencing duty-of-care for model-territory license restrictions (H3) — §G.10.
7. Whether any FCCPC sectoral registration/reporting applies at launch scale — §G.9.

## I.4 Immediate 14-day action plan (operator + implementing AI)

**Days 1–3 (W0, security)** — do these in order, same day if possible:
1. Rotate AgentMail key (owner, agentmail.to) → set `AGENTMAIL_API_KEY` in Railway → delete the key from `scripts/agentmail_setup.py` → `git filter-repo` purge + force-push → old key revoked.
2. Rotate `WORKER_TOKEN` on Railway → update worker launcher → purge `worklog.md:355` + history the same way.
3. Owner changes admin password; remove creds hint from login UI; `AUTH_SECRET` env; cookie `secure:true`.
4. Rate limiting shipped (§F.2 numbers); query logging off; `/api/upload` implemented or removed (C-5).
5. Enable secret scanning (gitleaks in CI) so this class of incident is impossible to reintroduce.
**Days 4–7**: storage_v2 (object storage + signed URLs + /api/files) → kills C-4; start W1 tables; verify model licenses (read H3 + LTX license files at their official repos — 1 hour, unblocks §C.3); verify Supabase/R2/Resend/PostHog/Sentry current limits (§E.3 NOT VERIFIED cells).
**Days 8–11**: W2 state machine + reaper + QC gate; wire film_verify ASR as blocking check.
**Days 12–14**: W3 events + /studio skeleton; legal pages drafts (§G) to owner for review; compliance dashboard v0 in admin.
**Parallel operator track**: film v10 fleet outputs land → fetch via `scripts/fleet_brain.py` → rebuild the v10 assembly toolchain (lost in sandbox reset — inventory + assemble + refs chain) → publish with honest claims only.

## I.5 Research source register (this pass, 2026-09-06)

Saved under `download/research/` (t01–t21 JSON): MiniMax H3 official announcement (minimax.io) + HF model hub (MiniMaxAI/MiniMax-H3) + territory-exclusion analyses (we0.ai, explainx.ai 2026-08) · LTX-2 open-source release (globenewswire) + ltx.io commercial licensing · Kaggle official posts: "Weekly Maximum GPU Usage" (30h/wk), T4 options, session-runtime increases, concurrent-session limits · Supabase pricing page + 2026 secondary analyses (5GB egress free tier) · Paystack pricing pages (NGN 1.5%+₦100, waived <₦2,500, cap ₦2,000) · Flutterwave help center (NGN 2.0% local after Apr-2025 increase) · NDPC portal (registration regime; DCPMI categorization via Aluko & Oyebode analysis) · FCCPC site (rights, refund-practice warnings) · Copyright Act 2022 AI commentaries (Dentons ACAS, SSRN) · WCAG 2.2 (w3.org, What's New in WCAG 2.2) · Sentry/PostHog/Resend/R2 pricing pages located, numbers pending verification (§E.3). Every NOT VERIFIED cell in this document maps to one of these follow-up reads.

---

*End of specification. This document is the operating contract between the current codebase and the target AI Film Production Studio; every claim is either verified, marked NOT VERIFIED, or marked LEGAL REVIEW REQUIRED. Change it through versioned revisions, never by silent edits.*
