# PART G — LEGAL PLANE (NIGERIA-FIRST)

> Standing rule: this section reduces foreseeable risk; it does not claim legal certainty. Items marked **LEGAL REVIEW REQUIRED** are collected in §I.3 with the specific question to put to a Nigerian-qualified lawyer.

## G.1 Content honesty (zero-fabrication program — prompt §39/§40/§62)

Current violations to fix (evidence in §A.2 M-1/M-2):
1. **Testimonials**: the three seeded quotes are fabricated personas presented under "Real clients" (`seed.ts:234–263`). Fix: either (a) remove entirely, or (b) relabel the section "Sample scenes & demo reactions — illustrative, not customer reviews" with visible labeling. Never present AI personas as customers; never invent press logos, ratings, or user counts (none exist today — keep it that way).
2. **Capability claims** must match the renderer: remove "4K" until a 4K path exists (plans cap 1080p; worker renders 768×512 upscaled); "60 seconds single pass" is false as written — the truth is *stronger and honest*: "60-second films built scene-by-scene — we assemble up to 60s from real generated shots; single passes are up to ~10s on current models." The hero chips ("60S / 5 STYLES / 4K") become "60S FILMS / 5 STYLES / 1080P". The `assemble`-computed duration rule (§D.8) is what makes every published duration claim self-verifying.
3. **Urgency copy** ("Founding prices… will go up", "rate locked forever") is allowed marketing, but (a) the rate-lock must be implemented (`Subscription.lockedPriceMinor`, §E.1) before the promise is made, and (b) a price increase must eventually happen or the claim ages into a deception — owner decision, calendar it.
4. **No invented business facts**: no CAC/RC number exists → the footer says "DeYoung — AI film studio, Nigeria" with **no registration number** until the owner supplies one (prompt §41: mark NOT VERIFIED, never invent). StructuredData: remove the hardcoded 24/7 opening-hours claim or make it true and editable (`Settings` field).
5. **AI disclosure**: keep "Made with DeYoung" badges on gallery works; add model attribution from the asset graph ("Generated with [model], edited and dubbed by DeYoung") on work pages — accurate, and it doubles as license-attribution hygiene (§G.2).

## G.2 Copyright & asset licensing audit (prompt §42)

| Asset class | Current status | Action |
|---|---|---|
| Brand marks (logo.svg, icons, og-image) | Generated in-house (Task 24) — owned | Record in an ASSETS.md ledger (owner, source, date) |
| Gallery/character imagery | AI-generated in-house (z-ai image gen, Tasks 28/31) | Ledger entry + "AI-generated" label; **check the image provider's ToS for commercial use** — NOT VERIFIED this pass, verify before paid commercial-client deliverables |
| Film footage | Generated (LTX/H3/z-ai video) + in-house assembly | Same; model license gate (§C.3) already covers the model side |
| Music | `aevalsrc` synthesized drone (in-house) + `music.wav` slices (origin recorded in worklog as in-house) | Keep origin record; if any stock music is ever added → license file + URL in the ledger, else remove |
| Fonts | Archivo (OFL — SIL Open Font License), JetBrains Mono (OFL), Geist (MIT) | OFL/MIT are commercial-safe; ship license texts in `public/fonts/LICENSES.md` |
| Seeded photos/services copy | In-house seeds | Ledger |
| Third-party embeds | none (verified) | — |

Rule going forward: **unknown license = do not ship** (prompt §42); the ASSETS.md ledger is a launch-checklist item (§I.1). Generated-output ownership: Nigerian Copyright Act 2022 does not clearly define authorship for AI-generated works (commentaries reviewed in this pass agree); **what DeYoung can promise customers contractually: see §G.6 — do not promise "copyright-free" or "you own copyright" as a legal conclusion (prompt §44). LEGAL REVIEW REQUIRED** for the exact IP-assignment clause wording.

## G.3 Model license register (prompt §43) — see §C.3 table

`ModelRegistry` is the operational register; the license-verification gate (commercial renders only when verified) is the enforcement. The single most important open verification: **MiniMax H3's license territory list** (reported US exclusion; operator and customers are Nigeria/ROW — scope must be read from the actual license file at the official repo before any H3-rendered paid output).

## G.4 User uploads & takedown (prompt §44)

Upload attestation checkbox at every upload surface ("I have the rights to this material") — stored as `Upload.attestedAt`; repeat offenders (DMCA-style strikes, even without US law applying, is the operational pattern) blocked. **Complaint mechanism**: `copyright@deyoungltd.site` + a /report page capturing URL + description + contact; SLA: acknowledged 48h, actioned 7d; documented in the ops runbook. Never promise outputs are automatically copyright-free (prompt §44).

## G.5 Likeness / voice / deepfake policy (prompt §45)

Hard policy (Terms + upload attestation + content filter on prompts):
- Forbidden: impersonation of real identifiable persons without documented consent; non-consensual intimate imagery; deceptive political/fraud content; unauthorized voice cloning; harassment targets.
- Voice cloning of a **customer's own voice** only with in-product consent attestation; celebrity/character voices never.
- Enforcement ladder: prompt-time blocklist + worker-side refusal + post-hoc takedown + account termination; every enforcement event → `AuditLog`.
- This policy is a **business requirement for premium lip-sync/voice features** — enable the `lipsync_premium` capability flag only after the policy ships.

## G.6 Terms & Conditions (prompt §37) — required sections skeleton

Eligibility (18+, Nigeria-primary service; minors only via guardian — prompt §55: state minimum age, no child-directed features); accounts (accurate info, credential custody); acceptable use (incl. §G.5 policy, no abuse of free quotas); uploads & rights (attestation, license grant to process only); **AI-generated content disclaimer** (outputs may contain errors/artifacts; QC reduces but does not eliminate; no guarantee of specific artistic result; model behavior may change); **IP** (customer content remains customer's; generated outputs: contractual license/assignment clause — wording **LEGAL REVIEW REQUIRED**, §I.3); credits & subscriptions (ledger is authoritative; expiry if any stated here); payments (provider list, currency NGN-first, no card storage); **cancellation & refunds → §G.7**; suspension/termination (abuse, chargebacks); third parties (processor list per §F.4); disclaimers & liability (limitation drafted to be enforceable — no blanket waiver of non-excludable consumer rights, prompt §37); disputes (good-faith resolution first; governing law Nigeria; venue **LEGAL REVIEW REQUIRED**); changes (versioned, notice of material changes); contact (real email).

## G.7 Refund & cancellation policy (prompt §38; FCCPC-aware)

FCCPC publicly warns against blanket "no refund" practices (fccpc.gov.ng + 2024-2025 press). Policy must therefore be specific, not absolute:
- **Subscriptions**: cancel anytime (self-serve); access until period end; pro-rata refunds only where work has not started on queued renders; no refund for consumed renders (that's the consumption model, stated clearly).
- **Failed generations**: automatic credit reversal (§E.1) — this IS the refund path for renders; customer-visible copy: "If a render fails, your credits come back automatically."
- **Duplicate payments**: auto-detected (same providerRef) → auto-refund path.
- **Accidental purchases**: 48h window if no render consumed.
- **Service failures** (site cannot render for >72h while subscription active): pro-rata credit extension.
- Manual/bank payments: owner-confirmed refunds via original channel; processing time stated (5–10 business days).
- Replace the single seeded FAQ refund sentence (`seed.ts:291`) with this policy as its own hash view + link in footer; the FAQ line remains consistent with it.

## G.8 Business information (prompt §41)

Publish exactly what is true: brand name "DeYoung", contact emails (owner's real inboxes), support hours (real ones), location "Nigeria" (city-level only if the owner consents), **no CAC number until real** (field marked "Registration: pending" or omitted entirely), no fabricated certifications/partnerships/regulator approvals — ever. Owner action item: decide whether to register a business name at CAC (cost/time **NOT VERIFIED** — check cac.gov.ng) before scaling paid volume; the Terms' "operator" language must match whichever legal identity exists.

## G.9 Consumer-protection & advertising compliance (FCCPA 2018)

Practical requirements drawn from FCCPC public materials (rightify/fccpc sources in this pass): accurate descriptions (§G.1 fixes), transparent pricing (already strong: slashed-price copy shows real before/after), functional complaint channel (new /report + support email), honest refund handling (§G.7), no deceptive urgency beyond a real deadline. **LEGAL REVIEW REQUIRED** items: whether DeYoung's subscription model triggers any FCCPC sectoral registration or consumer-data reporting duties at current scale.

## G.10 International-law assessment (prompt §56)

Today: Nigeria-primary; EU/UK/US users can technically reach the site. Recommended posture: state availability honestly in Terms ("available worldwide where lawful"), **do not claim GDPR compliance**, and trigger a jurisdictional review before any of: EU/UK marketing spend, EU entity customers, or cookie-bearing analytics (GDPR/UK consent applies then). US: the MiniMax H3 license territory question (§C.3) makes US-customer renders a **model-registry enforcement issue, not just a legal one** — the scheduler must be able to deny H3 for US-geolocated orders if the license requires it (**LEGAL REVIEW REQUIRED** on geofencing duty-of-care).

---
