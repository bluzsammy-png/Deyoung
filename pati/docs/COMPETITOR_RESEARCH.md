# COMPETITOR_RESEARCH — The Landscape Around PATI (2026-09)

**Scope note:** per the research engine's source rules, this survey records
*what PATI is relative to*, not a verdict on other products. Categories and
archetypes matter more than brand-by-brand scoring; where brands are named,
they illustrate an archetype. Verified facts (pricing pages, license text)
live in `docs/RESEARCH_REPORT.md`; this document is analysis.

## 1. The archetypes

| Archetype | What it is | Examples of the pattern | Why PATI is different |
|-----------|------------|--------------------------|------------------------|
| **A. Hosted agent platforms** | Cloud service where the vendor runs the agent, tools, and storage; you configure via web UI | commercial "AI employee" SaaS platforms | PATI runs on *your* PC; your disk, your tokens, $0; no account |
| **B. Local agent frameworks** | Open-source frameworks for building agents locally | several OSS agent frameworks | they give you a *framework*; PATI ships an *installed system* (control plane + agent + workers + policies + installer) with the $0 policy pinned in schemas |
| **C. Model runtimes** | Serve local models with an API | llama.cpp-based servers, Ollama-style tools | model serving is one capability plane of PATI (via free Kaggle GPUs), not the whole; PATI adds orchestration, auth, artifacts, quotas, disk ops |
| **D. Automation suites** | Node-based workflow automation (self-host or cloud) | n8n-style tools, IFTTT-style services | workflows are hand-wired graphs; PATI takes *natural language* and plans/routes; automation tools integrate services, PATI integrates *capabilities* |
| **E. Cloud GPU marketplaces** | Pay-per-second rented GPUs | commercial GPU clouds | PATI's GPU plane is Kaggle's free tier with a local budget; the architecture *could* attach rented GPUs as workers (COMMERCIALIZATION §2) but the product never requires it |
| **F. Big-assistant ecosystems** | Vendor assistants with plugin stores | commercial AI assistant ecosystems | plugins live inside the vendor's cloud and trust model; PATI's adapter layer (Z.ai today, generic tomorrow) keeps the Personal AI **replaceable** — PATI is the stable infrastructure, not the assistant |

## 2. Where PATI's design is genuinely uncommon

1. **$0 as a schema-enforced invariant.** Most "free" offerings mean free
   *tier* with upsell; PATI pins `max_spend=0` and `cost<=0` where the
   system physically can't register a paid dependency.
2. **Personal AI is a swappable client.** The assistant (Z.ai, or any tool-
   calling AI) is an adapter away; the *infrastructure* (auth, policy,
   orchestration, artifacts) is the durable asset. Most competitors fuse
   the assistant and the infra and lock both.
3. **Fail-parked, never fail-paid.** `RESOURCE_UNAVAILABLE` +
   `WAITING_FOR_RESOURCE` is a feature, not a limitation — competitors
   monetize the fallback; PATI makes the fallback structurally impossible.
4. **Security kernel posture for a home machine.** Path guard (traversal,
   symlink escape, null bytes, root-delete), hash-chained audit, rlimits,
   allowlists, worker-id-bound tokens — industrial discipline applied to a
   personal, $0 system.
5. **Research ledger as a public artifact.** The verified license/cost rows
   (RESEARCH_REPORT, RESEARCH_ENGINE) are as much a deliverable as the
   code; competitors treat dependency posture as private hygiene.

## 3. Honest trade-offs (what competitors do better today)

- **Polish:** commercial SaaS platforms have onboarding, mobile apps,
  support SLAs. PATI has an installer, a wizard, and docs.
- **Managed reliability:** hosted platforms own uptime. PATI's uptime is
  your PC's uptime (mitigated: pull-based workers, watchdogs, easy
  recovery — but it's *your* machine).
- **Model quality:** paid frontier APIs outperform free open-weights on
  hard tasks. PATI's answer is task decomposition + best free models, and
  honest `RESOURCE_UNAVAILABLE` rather than a worse-but-paid shortcut.
- **Ecosystem breadth:** automation suites have hundreds of connectors.
  PATI starts with the contract + GitHub + Drive scaffold; the connector
  SDK is the roadmap path to breadth without violating ToS/free-first.

## 4. Positioning statement (one paragraph)

PATI is not competing to be a better hosted assistant or a bigger
automation marketplace. It occupies the intersection the market skips:
**single-person, self-hosted, capability-complete AI infrastructure whose
cost is structurally $0 and whose assistant is replaceable.** If you want
the gloss of a vendor platform, archetype A wins. If you want your disk,
your tokens, your GPU budget, an auditable security kernel, and a hard
promise that nothing will ever ask for a credit card, PATI is built for
you.

## 5. Update policy

This document is re-checked quarterly by the research engine (same cadence
as license re-verification). Archetype movements (e.g., a hosted platform
adding self-hosted mode, an OSS framework adding a $0-pinning policy) get a
dated note here; factual claims about specific products require a research
report row before appearing in this file.
