# MULTI_TENANT_SAAS — Multi-Tenancy & the SaaS Question

PATI is single-user by design. This document states the exact multi-user
boundaries already built in (`docs/MULTI_TENANCY.md` is the technical spec),
what a SaaS fork would need, and why the default answer is "don't."

## 1. What PATI supports today (single operator, several identities)

The control plane already has the primitives a tenant boundary needs:

| Primitive | Where | Notes |
|-----------|-------|-------|
| Scoped bearer tokens | `pati_api/security.py` | Roles: admin / client / worker; scopes per route |
| Worker identity binding | tokens bound to `worker_id` | A worker can only claim/report its own jobs |
| Rate limiting per token | middleware | Per-identity abuse control |
| Per-token quotas | `pati_api/quota.py` | GPU-minute budgets are token-scoped |
| Audit trail | central + hash-chained agent log | Per-actor provenance |

This means one person (or one family/team **trusted with one admin token**)
can run several client devices and several worker machines safely. That is
the supported envelope: **one operator of record.**

## 2. The SaaS fork: what you'd actually have to build

Turning PATI into "PATI Cloud" is less an extension than a second product:

1. **Tenant model.** `users`/`tenants` tables, tenant-scoped every row of
   jobs/tasks/artifacts/audit; the current schema assumes one world.
2. **Per-tenant crypto and storage.** Content-addressed artifact store
   becomes per-tenant namespaced; artifact IDs stop being global hashes.
3. **Per-tenant compute isolation.** Workers are *trusted* machines in PATI
   (they receive jobs and disk roots). In a SaaS, workers become hostile
   multi-tenant sandboxes: gVisor/Firecracker-class isolation, per-tenant
   GPU partitions, egress control.
4. **AuthN upgrade.** Bearer tokens → full accounts: registration, MFA,
   password reset, session lifecycle, OAuth SSO.
5. **Billing.** The one thing the core forbids (FREE_FIRST_POLICY) — a SaaS
   fork must add metering/invoicing, which is fine *in the fork* because the
   fork renamed itself (OPEN_SOURCE_POLICY §7).
6. **Abuse/ToS machinery.** Content scanning, DMCA, bans, jurisdiction.

Items 1–5 are roughly the size of PATI itself. That is the honest cost.

## 3. Why the default answer is "don't"

- **The value proposition inverts.** PATI's promise is *your* disk, *your*
  tokens, *your* GPU budget, no account. A SaaS reintroduces the account,
  the vendor, the data gravity — the exact things PATI exists to remove.
- **Free-tier economics break at tenant scale.** Kaggle quota is per human
  account; a SaaS cannot honestly pool 10,000 users onto N volunteer
  accounts. Either it becomes paid (violates fork naming honesty) or it
  throttles into uselessness.
- **Security posture changes class.** PATI's worker tokens are safe because
  workers are *your* machines. Hosting strangers' code execution needs
  isolation engineering far beyond PATI's threat model (SECURITY.md).

## 4. Legitimate middle grounds

If you want *some* shared-ness without a SaaS:

| Pattern | How PATI supports it today |
|---------|----------------------------|
| **Family/team on one admin** | Topology: shared control plane, per-device client tokens, per-token quotas. Works now. |
| **Federated jobs** | Submit to *another person's* PATI as an external worker? Not built. The worker pull model would support a relay, but identity/trust for strangers' workers is unsolved and deliberately out of scope. |
| **Community model hosting** | Use Kaggle datasets/kernels or HF hub directly — the free commons already exists; PATI just consumes official APIs. |
| **Read-only public status** | Expose `/health` and the status page through the tunnel; keep all data routes token-gated. Works now. |

## 5. Decision rule (for anyone forking)

Proceed toward multi-tenant only if **all** of these are true:

1. You accept building accounts, isolation and billing as a second product.
2. You can fund compute without violating the free-tier terms of Kaggle et
   al. (i.e., you pay for your own GPUs — see COMMERCIALIZATION §2).
3. You rename the fork (it is no longer free-first personal infrastructure).
4. You keep the core MIT and upstream your non-billing improvements — the
   registries and schemas make that easy, and the project is better for it.

## 6. Summary

- **Built in:** one operator, many devices, many workers, scoped tokens,
  per-token quotas, full audit — safely.
- **Not built, by choice:** stranger-to-stranger multi-tenancy. The single-
  user posture is what lets PATI be simultaneously powerful and trivially
  auditable; MULTI_TENANCY.md documents the seams for those who push further.
