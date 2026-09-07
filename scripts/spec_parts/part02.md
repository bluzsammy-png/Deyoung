# PART B — DATA & JOB CORE

## B.1 Database architecture (target)

Same engine (Supabase Postgres) — **upgrade, don't migrate away**. Prisma stays as the ORM; the two hand-synced schema files are consolidated by making `prisma/schema.prisma` the single source and generating the postgres variant (`sed` transform already exists in `deploy` flow) — with a CI check that the two never drift (§H.2).

**Money**: replace every `Float` amount with `Int` minor units (kobo) or Prisma `Decimal` — this includes `Booking.amount`, `Plan.priceMonthly/compareAtPrice`, `Service.price/compareAtPrice`, `Subscription.pricePaid`, and the new ledger (§E.1). Rounding rules live in code, not in float arithmetic.

**Relations**: declare real Prisma `relations` for every existing stringly-typed FK (`Subscription.planCode → Plan.code` as a unique FK, `VideoRequest.subscriptionId → Subscription.id` with `onDelete: Cascade`), eliminating manual cascade deletes (`subscriptions/[id]/route.ts:57` becomes automatic).

**New tables (26 — full target set per the master prompt §20).** Existing tables keep their names; new columns are additive so `prisma db push` never destroys data:

| Table | Purpose / key fields (beyond today's) |
|---|---|
| `Profile` | Customer identity: `id`, `email` (unique), `name`, `phone?`, `emailVerifiedAt?`, `marketingConsent?`, `createdAt`. Customers log in with email + one-time code (no passwords to store — see §F.1). Subscriptions/Bookings/Requests gain `profileId` (nullable during migration, backfilled by email match) |
| `LoginCode` | `email`, `codeHash` (scrypt), `expiresAt` (10 min), `attempts`, `consumedAt` — powers passwordless customer auth |
| `Project` | A customer's creative container: `profileId`, `title`, `description` |
| `ProjectMember` | `projectId`, `profileId`, `role` (owner/editor/viewer) — RLS anchor |
| `Production` | One film run: `projectId`, `targetDurationSec`, `style`, `status` (draft/manifested/running/completed/failed/cancelled), `manifestId` (selected version), `createdAt` |
| `Script` | Versioned screenplay: `productionId`, `version`, `content`, `selectedAt?` |
| `Character` | Character-bible row: `projectId`, `name`, `appearance`, `face`, `hair`, `clothing`, `accessories`, `voiceId`, `personality`, `movement`, `negativeTraits`, `consistencyInstructions`, `version` — scenes reference by ID, never re-describe (prompt §15) |
| `CharacterReference` | `characterId`, `kind` (image/video/audio), `assetId`, `weight` |
| `Voice` | `name`, `provider` (tts-engine), `voiceKey`, `sampleAssetId?`, `licenseNote` |
| `Scene` | `productionId`, `index`, `plannedDurationSec`, `characterIds[]`, `locationId`, `camera`, `lighting`, `movement`, `prompt`, `audioPlanJson`, `modelPolicyJson`, `qcPlanJson` |
| `SceneVersion` | Every generation attempt is preserved: `sceneId`, `version`, `jobId`, `assetId`, `status` (rejected/selected/pending) — the "v1 rejected, v3 selected" lineage (prompt §16) |
| `Location` | `projectId`, `name`, `description`, `referenceAssetIds[]`, `consistencyInstructions` |
| `ProductionManifest` | Immutable versioned JSON of the whole film (§B.2): `productionId`, `version`, `schemaVersion`, `contentJson`, `createdBy`, `createdAt` |
| `Job` | The unified queue (§B.4): `type` (scene_render/audio/tts/qc/upscale/assemble), `sceneId?`, `productionId?`, `videoRequestId?` (legacy), `state`, `attempts`, `maxAttempts`, `leaseUntil`, `claimedByWorkerId`, `idempotencyKey` (unique), `priority`, `payloadJson`, `lastError` |
| `JobAttempt` | Append-only: `jobId`, `workerId`, `startedAt`, `endedAt?`, `outcome`, `errorSummary`, `checkpointJson?` |
| `Worker` | Registry (§C.1): `workerKey` (unique), `provider` (kaggle/local/paid-api), `gpuModel`, `gpuCount`, `vramGb`, `ramGb`, `capabilities` (text[]), `modelVersionsJson`, `workerVersion`, `status` (online/busy/offline/drained), `lastHeartbeatAt`, `currentJobId?`, `jobsCompleted`, `jobsFailed`, `lastError` |
| `WorkerHeartbeat` | `workerId`, `at`, `gpuUtil`, `memUsedGb`, `currentStep`, `progressPct?` — time-series, pruned >7 days |
| `ProductionEvent` | Append-only event log (§D.4): `productionId?`, `jobId?`, `type` (`production.started`, `scene.completed`, `worker.claimed`, …), `payloadJson`, `at` |
| `Asset` | Every file with lineage (§D.2): `kind` (reference/render/audio/caption/thumbnail/master/upload), `storageKey`, `bytes`, `mimeType`, `checksumSha256`, `metaJson` (ffprobe results), `createdByJobId?`, `expiresAt?` |
| `Render` | Final outputs: `productionId?`, `videoRequestId?`, `assetId`, `durationSec` (measured), `resolution`, `qcStatus` |
| `ModelRegistry` | `name`, `version`, `provider`, `task`, `licenseName`, `licenseUrl`, `commercialUse` (bool/unknown), `territoryLimits`, `attributionRequired`, `hostedServiceRestrictions`, `outputRestrictions`, `gpuClass`, `maxDurationSec`, `resolutions`, `verifiedAt`, `verifiedBy`, `enabled`, `notes` — **a model cannot serve paid users unless `commercialUse=true` and `verifiedAt` < 90 days** (prompt §43) |
| `CreditLedger` | Immutable (§E.1): `profileId`, `delta` (Int, signed, kobo-denominated or credit-denominated — choose credits), `type` (purchase/consumption/refund/promo/reversal/adjustment/expiration), `reason`, `refType?`, `refId?`, `idempotencyKey` (unique), `balanceAfter` |
| `Payment` | `profileId?`, `bookingId?`, `subscriptionId?`, `provider` (paystack/flutterwave/paypal/stripe/manual), `providerRef` (unique per provider), `amountMinor`, `currency`, `status` (pending/verified/failed/refunded), `webhookEventId?` (unique — replay guard), `verifiedAt`, `rawJson` |
| `QcResult` | `assetId`/`renderId`, `checksJson` (duration/codec/black-frames/silence/loudness/asr-dialogue), `passed`, `failureReason` |
| `CostRecord` | `jobId?`, `model?`, `gpuMinutes` (measured server-side: lease end − start, not self-reported), `gpuClass`, `theoreticalCostMinor` (theoretical cost even when free — prompt §22), `provider` |
| `FeatureFlag` | `key` (unique), `enabled`, `rolloutJson`, `note` — flags for `h3_film`, `paid_apis`, `new_providers` (prompt §69) |
| `AuditLog` | `actorType` (admin/worker/system), `actorId`, `action`, `entityType`, `entityId`, `beforeJson?`, `afterJson?`, `ip?`, `at` — every admin mutation lands here |

**RLS posture**: with Supabase, enable RLS on all tables; the app connects with the service role via Prisma (server-only), and **no Supabase client key ships to the browser** (today's architecture already has no client-side DB access — keep it that way; RLS is defense-in-depth for direct DB access, not a substitute for the API layer). `ProjectMember` + `profileId` columns make per-user isolation enforceable if direct Supabase access is ever introduced.

**Migration order** (no destructive steps): add tables → backfill (`Profile` from distinct emails; `Job` from `VideoRequest`) → add FKs with `onDelete` → move money columns to `Decimal` → drop nothing until W4 (§H.6).

## B.2 Production Manifest (versioned, §13 of prompt)

One immutable JSON per production version, stored in `ProductionManifest.contentJson` and **validated by zod at write time** (first real use of the installed dependency). Schema v1:

```jsonc
{
  "schemaVersion": 1,
  "productionId": "cuid",
  "targetDurationSec": 60,          // planned; delivered duration is measured later
  "style": "anime | realistic | cartoon | stickman | kids | custom:…",
  "language": "en",
  "characters": [{ "id": "char_amara", "name": "Amara", "voiceId": "…",
                   "appearance": "…", "consistencyInstructions": "…", "negativeTraits": ["…"] }],
  "locations":  [{ "id": "loc_lagos_rooftop", "description": "…", "references": ["asset:…"] }],
  "scenes": [{
    "index": 1, "plannedDurationSec": 6,
    "characterIds": ["char_amara"], "locationId": "loc_lagos_rooftop",
    "camera": "slow push-in, 35mm", "lighting": "golden hour rim", "movement": "gentle dolly",
    "prompt": "…", "negativePrompt": "…",
    "references": ["asset:plate_001.png"],
    "audio": { "dialogue": [{ "characterId": "char_amara", "line": "One sentence. Sixty seconds. Done.",
                               "voiceId": "voice_tongtong", "maxSec": 5.5 }],
               "music": { "bed": "asset:music_drone", "duckUnderDialogue": true } },
    "modelPolicy": { "preferred": "minimax-h3", "fallbacks": ["ltx-2", "kenburns"], "seed": 99 },
    "qc": { "minDurationSec": 5.2, "requireSubjectPresence": true, "requireDialogueMatch": true }
  }],
  "audioPlan": { "musicBed": "…", "loudnessTargetLufs": -14, "ducking": true },
  "editPlan":  { "transitions": "hard cut + 0.4s dip-to-black at scene 5",
                 "captions": "burned-in, Archivo, bottom-center",
                 "endCard": { "assetId": "asset:endcard", "durationSec": 5 } },
  "qcPlan":    { "perScene": true, "finalAsr": true, "blackFrameCheck": true }
}
```
Rules: manifests are never edited in place — a change creates `version+1`; the execution graph is derived deterministically from the selected manifest version; the final render stores `manifestId` so any film can be traced to the exact plan that produced it (prompt §70/§17 traceability).

## B.3 Film compiler (§14 of prompt) — pipeline stages and where they run

```
idea → understanding → script (LLM, versioned) → character bible → storyboard text
     → production manifest (validated JSON) → execution graph (jobs w/ deps)
     → [execution plane renders scene jobs] → asset graph fills in
     → edit graph (assembly ffmpeg chain) → audio (TTS + mix) → QC gates → master
```
- Stage outputs are **rows, not memories**: each arrow above writes a table (Script/Character/Scene/Job/Asset/QcResult), which is what makes every stage resumable and auditable.
- The compile step is an API route (`POST /api/productions/:id/compile`) executed by the control plane using the configured LLM provider — behind a feature flag (`film_compiler_v1`) until it beats the manual pipeline in QA.
- Failure isolation: a script revision or character change invalidates only downstream jobs of affected scenes (dependency edges stored in `Job.payloadJson.deps`).

## B.4 Job system — explicit state machine

States (prompt §11): `QUEUED → CLAIMED → RUNNING → CHECKPOINTED → UPLOADING → COMPLETED`, plus `FAILED → RETRYING`, `STALE`, `CANCELLED`.

**Transition table (enforced in code, not by convention):**

| From | Event | To | Guard |
|---|---|---|---|
| QUEUED | worker claim (atomic) | CLAIMED | `updateMany({where:{id,state:QUEUED}, …})` = 1 row (existing pattern kept) |
| CLAIMED | worker first heartbeat/progress | RUNNING | lease extended |
| RUNNING | periodic checkpoint | CHECKPOINTED→RUNNING | checkpoint blob stored on attempt |
| RUNNING | upload start | UPLOADING | — |
| UPLOADING | deliver OK + QC passed | COMPLETED | QC gate mandatory (§D.8) |
| any of CLAIMED/RUNNING/UPLOADING | lease expired | STALE | reaper (§C.1) |
| STALE | reaper | QUEUED (RETRYING implied) | if attempts < maxAttempts else FAILED |
| RUNNING | worker fail (transient) | FAILED→RETRYING | attempts++ |
| any | worker fail (permanent/moderation/invalid) | FAILED (terminal) | no requeue; reason recorded |
| QUEUED/CLAIMED/RUNNING | admin/user cancel | CANCELLED | worker notified on next poll |

**Failure taxonomy** (each maps to a distinct retry/credit policy): `transient` (network, provider 5xx) → retry ×3 with backoff; `model_failure` (generation garbage) → retry once with different seed, then fallback model (§C.4); `worker_failure` (crash/OOM) → STALE path, never counts against scene attempts beyond requeue limit; `moderation` → terminal, user-visible honest reason, credit reversal if charged (§E.1); `invalid_input` → terminal + validation fix requested; `storage_failure` → retry with different key prefix; `payment_failure` → no render started at all (pre-paid check).

**Idempotency (prompt §12)**: every `Job` carries a unique `idempotencyKey` (e.g. `scene:{sceneId}:v{attempt}:seed`); a re-delivered result for a COMPLETED job is acknowledged and discarded; payment webhooks are deduped on `webhookEventId`; ledger writes carry `idempotencyKey` so a retried webhook can never double-credit (§E.1–E.2).

**Legacy path**: the existing `VideoRequest` flow keeps working unchanged (single-scene productions under the hood): W1 maps `VideoRequest` → one `Production` + one `Scene` + one `Job` so both UIs ride the same queue (§H.6 W1).

---
