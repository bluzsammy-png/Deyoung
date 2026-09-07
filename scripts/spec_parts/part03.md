# PART C — EXECUTION PLANE

## C.1 Worker architecture & registry

**Worker lifecycle** (prompt §7, all 13 steps mapped): start → authenticate (`WORKER_TOKEN`, Bearer header only — **drop the `?token=` query variant**, `src/lib/worker.ts:27`, tokens in URLs leak into access logs) → register (`POST /api/worker/register` new: GPU model/VRAM/RAM/capabilities/workerVersion → upserts `Worker`) → heartbeat every 60s (`POST /api/worker/heartbeat`: gpu util, current step, progress) → request work → claim (existing atomic route) → download inputs via short-lived signed URLs → process → report progress → upload result to storage (worker gets a **scoped upload URL**, no storage credentials) → complete job → loop or terminate.

**Registry**: the `Worker` table (§B.1) is populated at register time. The scheduler (inside `POST /api/worker/claim`) filters jobs by required capability (e.g. `scene_render` needs capability `video_generation_small` + gpuClass ≥ T4; `tts` jobs can run on CPU workers; `assemble` needs `ffmpeg`), then applies priority-desc → FIFO — preserving the exact customer-facing queue math that exists today (`subs.ts:54–79`). Capability examples: `video_generation_small`, `video_generation_h3`, `image_generation`, `ffmpeg`, `whisper_asr`, `tts`, `lipsync_premium`, `upscale`.

**Heartbeat & reaper (fixes M-6)**: control-plane reaper runs on every `GET /api/worker/status` + a cron tick: any job with `leaseUntil < now()` and state ∈ {CLAIMED, RUNNING, UPLOADING} → `STALE`; its worker is marked `offline` if `lastHeartbeatAt < now() − 3 min`. STALE jobs requeue automatically with attempts++ (§B.4). Lease = 10 min, renewed by each heartbeat and each progress call. Effect: a Kaggle session dying mid-scene costs exactly one scene requeue — the production continues (prompt §9–§10).

## C.2 Worker trust boundaries

- Workers can: claim, heartbeat, deliver to their own job, fail their own job with a reason.
- Workers cannot: read other jobs, set `resultUrl` to arbitrary hosts (JSON deliver restricted to `{storage: true}` — the control plane uploads/validates; if raw URL delivery is ever needed, scheme+host allowlist, fixing M-5), touch payments/users/settings, or exceed `MAX_UPLOAD` 200MB (unchanged).
- Worker code version is reported at register; admin can `drain` a worker (no new claims, finish current job) or disable it — per prompt §27 worker controls.
- The render fleet today is one shared token; keep it but **rotate quarterly** (and now, per C-2), and give each launched kernel a distinct `workerKey` so the registry can attribute failures per account.

## C.3 Model registry & license gates (prompt §5/§43)

`ModelRegistry` rows are **facts with sources**, not vibes. Seeded from this research pass (verification status honest):

| Model | Task | GPU class | Max duration | License (verified 2026-09-06) | Commercial use | Restrictions |
|---|---|---|---|---|---|---|
| **MiniMax H3** (Hailuo 3, open weights) | text/image→video | T4-class reported by community; **exact VRAM/resolution: NOT VERIFIED — verify from the official model card before enabling on T4 fleet** | NOT VERIFIED (community reports ~10s/pass) | Open-weight license; **reported to exclude certain territories (US; scope of exclusion NOT VERIFIED)**; prohibits using outputs to improve other models (reported) | **CONDITIONAL — verify the license text at the official repo before commercial enablement: huggingface.co/MiniMaxAI/MiniMax-H3 (license file) + minimax.io announcement** | Territory list must be checked against Nigeria (operator) and customer location; outputs-must-not-train-competitors clause affects fine-tuning plans |
| **LTX-Video 0.9.x** (already running in `deyoung_worker.py`) | text/image→video, small | T4 (proven: it runs today at 768×512, 161 frames) | ~6.7s/pass @24fps | Lightricks open-weights license (community "Open-Weights License" files exist on HF; **exact commercial terms NOT VERIFIED — read the license file shipped with the weights**) | UNKNOWN until license text read — mark `commercialUse: unknown` in registry | LTX-2 announced open-source ("production-ready", globenewswire 2026); commercial licenses offered via ltx.io |
| **ffmpeg stub renderer** | placeholder/fallback | CPU | any | N/A (we authored it) | YES | Label output as placeholder |
| **TTS engines (current voice cast)** | speech | CPU | — | Per-provider ToS; **verify each voice's commercial/redistribution terms in the provider dashboard before paid use** | UNKNOWN per voice | Voice cloning of real persons forbidden (§G.5) |
| Premium APIs (Kling via Atlas, Veo 3.1 via Evolink) | premium render/lipsync | API | per API docs | Provider ToS; **keys valid but currently EMPTY (402)** — worklog Task 30/31 | YES (paid) | Cost ~$0.153/s Kling v3-std i2v (quoted 2026-09-05, re-verify) |

**Gate rule (enforced in the scheduler)**: a model serves paid renders only if `enabled && commercialUse == true && verifiedAt < 90 days`. Free-tier/demo renders may use `unknown`-license models **with output labeling** ("Made with DeYoung" + model name on the work page), never on paid orders. This single rule prevents the most expensive mistake in AI products: building revenue on a license you never read.

## C.4 H3 integration plan (honest version)

- **Feasibility**: the fleet's `minimax-h3-on-kaggle-t4-2-one-click-notebook` kernel exists (deyoungsltd, 2026-08-30) — H3 on T4 is at least runnable. It is **not yet proven at production quality/duration**; the 4 film kernels in flight (2026-09-06) are the actual proof. Do not promise H3-powered tiers until those outputs pass QC (§D.8).
- **Integration shape**: H3 is just another entry in `ModelRegistry` + a renderer in `deyoung_worker.py v2` (`--renderer h3`) behind feature flag `h3_film`. Scene-level outputs feed the same asset graph as LTX — nothing downstream changes. That is the provider-abstraction payoff (prompt §5).
- **T4 reality check**: T4 = 16GB VRAM; expect quantized/low-res internal renders + upscale steps, 5–10s clips per pass. 60-second films are produced by **scene chaining + last-frame conditioning** (first/last-frame pinning pattern documented in research R-1: OpenMontage uses it; clean-room implement, do not copy AGPL code).
- **Fallback chain (prompt §64)**: `minimax-h3 → ltx-2 → kenburns(stills) → stub(placeholder, flagged honestly)`. On any fallback that materially changes quality, the customer sees it (event + status line), and credits follow §E.1 policy. Never fake a model result (prompt §64/§77).

## C.5 Checkpointing (prompt §10)

`JobAttempt.checkpointJson` (§B.1) stores: rendered segment files already uploaded (asset IDs), current frame/step, seed in use. A requeued job resumes from the last uploaded segment (`payload.resumeFrom` = asset ID) instead of from zero. Implementation order: (1) segment-based resume (scene jobs produce 5–10s segments; each completed segment is uploaded immediately — the H3 fleet already does this), (2) frame-level resume for LTX (skip if it complicates the renderer — segment-level is enough), (3) assembly jobs are naturally idempotent (re-run re-encodes from assets).

---
