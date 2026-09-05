# COMMERCIALIZATION — How Money Could Touch PATI (and How It Doesn't)

PATI has no business model and no billing code. This document exists to
pre-answer the question "how would this ever be commercial?" honestly, and to
set the firewalls that keep any future commercial activity from corroding the
$0 guarantee.

## 1. Current state (the only committed state)

- **Revenue:** $0. **Spend:** $0. **Billing surface:** none.
- There is no license key, seat count, usage metering, or "Pro" tier in the
  codebase, and this policy forbids adding one to PATI itself.

## 2. Compatible commercial avenues (outside PATI's core)

| Avenue | What it is | Why it's compatible |
|--------|-----------|---------------------|
| **Paid deployment help** | Someone charges for installing/tuning PATI on a client's PC | Service revenue around free software; PATI stays $0 |
| **Managed hosting of a fork** | A company runs multi-tenant PATI-as-a-service (see MULTI_TENANT_SAAS.md) | The fork pays its own costs; core PATI is untouched |
| **Hardware bundles** | Selling a "PATI box" (mini-PC with PATI preinstalled) | You pay for hardware, not software |
| **Training/content** | Courses, books, workshops about running local-first AI | Knowledge revenue |
| **Enterprise support** | SLAs, security reviews, custom connectors for companies | Support revenue, MIT-licensed base |
| **First-party paid services YOU choose** | You rent a GPU elsewhere and attach it as a worker | FREE_FIRST_POLICY §7: PATI never transacts; you do, outside PATI |

All of these monetize **people's time or hardware**, never PATI's code paths,
and none require changing a single line of the $0 core.

## 3. Non-negotiable firewalls

Even if PATI ever gets an organization, funding, or a company around it:

1. **The core stays MIT and free-first.** FREE_FIRST_POLICY and the schema
   pins (`max_spend: 0`) do not get "temporary exceptions."
2. **No telemetry becomes a data business.** PATI has no telemetry; a future
   optional, auditable, local-only analytics tool would still store data on
   your disk and never phone home.
3. **No open-core amputation.** Features don't migrate from the open repo
   into a paid product. Paid products are adjacent (support, hosting,
   hardware), never carved from the core.
4. **No pay-for-priority roadmap.** Sponsors can't buy roadmap inversions;
   there are no paid features to prioritize anyway.
5. **No dark patterns in `RESOURCE_UNAVAILABLE`.** "Out of free quota" will
   never become an upsell screen; the fix is waiting or adding a free
   resource, and the message will say exactly that.
6. **Registry honesty.** A "commercial mode" (if a fork adds one) may
   *restrict* to permissive-license models (LICENSE_POLICY §3), but the
   personal free path is never degraded to upsell it.

## 4. The honest economics (why free-first is viable)

- Control plane: one Python process + SQLite → runs on a machine you own.
- Compute: Kaggle's free GPU quota (~30 h/week) covers serious hobby-scale
  media production; the local agent covers disk/exec at the cost of
  electricity.
- Transport: Cloudflare Tunnel free tier; GitHub/Drive free API tiers.
- Models: open weights (Qwen2.5, Llama 3.2, SDXL, Whisper, Piper) at $0.
- The scarce resource is **engineering attention**, which contributions
  (open source) and adjacent services (above) can fund without touching the
  user's wallet.

## 5. If you fork to commercialize

You may — MIT says so. The license obligations you take on:

- Preserve MIT notices and attribution (LICENSE_POLICY §7).
- Respect model licenses: non-commercial (NC) checkpoints must not power a
  commercial offering; Community licenses carry their brand/use terms.
- Respect external services' terms (Kaggle quota is per-account; a multi-
  tenant SaaS burning 50 accounts' quotas violates Kaggle ToS and the spirit
  of this project — see MULTI_TENANT_SAAS.md §ToS).
- Renaming guidance (OPEN_SOURCE_POLICY §7): if you add paid paths, rename;
  "PATI" denotes the free-first behavior.

## 6. Summary in one line

**PATI the software is and stays a gift; anything commercial happens around
it — in services, hardware, and forks that obey licenses — never inside its
execution path.**
