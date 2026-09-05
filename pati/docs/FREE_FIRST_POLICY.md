# FREE_FIRST_POLICY — The $0 Guarantee

This is PATI's constitutional document. Every other spec, module and decision
is subordinate to it. If an implementation detail conflicts with this policy,
**this policy wins.**

## 1. The hard constants

```
FREE_ONLY   = true
MAX_SPEND   = 0
```

These are not configuration defaults — they are **pinned invariants**:

- `schemas/health.schema.json` pins `max_spend` to the constant `0`.
- `schemas/model.schema.json` rejects any model whose `cost_per_1k` or
  equivalent cost fields exceed `0`. A paid model literally cannot be
  registered; validation fails at the registry boundary.
- The registries (`CAPABILITY_REGISTRY`, `MODEL_REGISTRY`, `TOOL_REGISTRY`)
  run `FREE_ONLY` hard validation on every insert.
- `docs/RESEARCH_REPORT.md` records license and cost verification for every
  dependency and model as of 2026-09-02.

## 2. What "$0" means, precisely

1. **No paid API is ever called.** Not as primary, not as fallback, not
   behind a flag, not "just this once."
2. **No account that requires a payment method is required** for any feature
   PATI ships.
3. **No trial-dependent path.** Features must work on genuinely free tiers
   (Kaggle, Cloudflare Tunnel, GitHub API) or not ship.
4. **No cost shimming.** PATI does not pay in attention, data selling,
   referral capture, or "free for now, paid later" services. Free tier today
   with a hard free ceiling forever (like Kaggle's GPU quota) is acceptable;
   "free credits that expire" is not.
5. **Electricity, hardware you own, and internet you already pay for** are
   out of scope — the policy governs software and services.

## 3. Enforcement mechanism

| Layer | Mechanism |
|-------|-----------|
| Schema | Cost fields constrained to `<= 0`; health pins `max_spend: 0` |
| Registry | Insert-time validation rejects paid entries (`FREE_ONLY`) |
| Router | Resource selector only considers workers/models with free capability + active quota |
| Quota | Local budgets (e.g., 240 GPU-min/day) gate submission *before* any external call |
| Runtime | When no free resource exists, the API returns `RESOURCE_UNAVAILABLE` and the job parks in `WAITING_FOR_RESOURCE` — it waits, it never pays |
| Tests | Suite asserts the constant, schema rejection of paid entries, and park-not-pay behavior |

The behavioral contract in one sentence: **PATI would rather tell you "not
now" than spend one cent.** `RESOURCE_UNAVAILABLE` is a *successful,
honest* response, not an error to route around.

## 4. The free resource palette

| Resource | Role | Free ceiling | Payment method required |
|----------|------|--------------|--------------------------|
| Local CPU/disk | fs ops, exec, planning, artifacts | your hardware | No |
| Kaggle GPU | images, video, TTS, STT, open-weights LLMs | ~30 GPU-h/week (official) | No |
| Cloudflare Tunnel | remote access | free tier | No |
| GitHub API | connector | authenticated free tier | No |
| Open-weights models | Qwen2.5, Llama 3.2, SDXL, Whisper, Piper… | license terms (see LICENSE_POLICY) | No |
| Google Drive API | connector scaffold | free with Google account | No |

## 5. Decision procedure for adding anything new

Before any new model, tool, connector or service enters PATI:

1. **Is it free forever** (not just free credits)? If no → reject.
2. **Does it require a payment method** at signup? If yes → reject.
3. **Is its license compatible** with personal + redistribution use (see
   LICENSE_POLICY)? If no → reject.
4. **Record it** in the research report: name, license, cost verification
   date, free-tier ceiling.
5. Only then implement, register, and add a test asserting its free status.

The research-before-implementation order is itself part of this policy: no
dependency enters the tree on vibes; it enters with a verified row in the
research report.

## 6. Known anti-patterns (explicitly forbidden)

- Fallback chains that end at a paid API "for reliability."
- Env vars like `ALLOW_PAID=true` — they will never exist in PATI.
- Wrapping a paid SaaS and calling it "free because you have credits."
- Advertising-funded or data-sharing-based "free" services.
- Deprecating a free path because a paid path is more convenient.

## 7. Upgrading beyond free (out of scope, by design)

If you someday *want* to spend money on compute, do it outside PATI: run a
container worker on rented hardware and PATI will happily talk to it as just
another worker with free capabilities (you paid the provider directly; PATI
still spent $0 and has no billing code). The architecture supports arbitrary
workers; the product policy is simply that PATI itself never transacts.
