# PART D — MEDIA PLANE

## D.1 Storage architecture (fixes C-4, the worst operational bug)

**Object storage, private by default, signed URLs for delivery.** Provider abstraction (`src/lib/storage.ts`, interface: `put(key, stream) / signedUrl(key, ttl) / delete(key) / lifecycle()`):

| Path | Free tier (verified where marked) | Paid exit |
|---|---|---|
| **Supabase Storage** (same project as DB — zero new vendor) | 1 GB storage, 2 GB egress/month free tier per Supabase docs — **current exact limits: NOT VERIFIED in this pass (search returned docs page only); verify at supabase.com/docs/guides/storage before relying on numbers** | Supabase Pro (volume pricing; Pro includes 100GB storage / 250GB bandwidth per pricing page snippet, re-verify) |
| **Cloudflare R2** (recommended at first scale-up) | 10 GB storage, zero egress fees, Class A/B ops free allowances — **current numbers: NOT VERIFIED in this pass; verify at developers.cloudflare.com/r2/pricing** | Per-GB beyond free; no egress charge is the reason it beats S3 for video delivery |
| Worker artifacts | R2 lifecycle rule: delete `tmp/` prefix after 3 days | — |

Keys: `productions/{id}/scenes/{index}/v{version}.mp4`, `refs/…`, `audio/…`, `renders/…`, `tmp/…`. **Delivery**: `GET /api/files/:assetId` → authz (owner, or admin, or unlisted-with-signed-token) → 302 to a 10-minute signed URL. This replaces both the unauthenticated `/api/worker/file/:name` route (H-4) and the fragile static `/uploads/` path, and survives deploys forever (fixes C-4). Migration for existing rows: current `public/uploads` files are ephemeral anyway; new deliveries go to storage from W1.

## D.2 Asset graph & traceability (prompt §17)

Every file is an `Asset`; every `Asset` knows its producer (`createdByJobId`); every `Job` knows its scene; every scene knows its manifest version; every render knows its manifest. Traceability query = 4 joins. Practical rule: **no file is ever written outside the graph** (workers upload via control-plane-issued scoped URLs that stamp lineage), which is what makes "trace this final video to source assets + model versions" a query, not an investigation.

## D.3 Character system (prompt §15–§16)

`Character` rows are the single source of truth; scenes reference `characterIds`; prompts are compiled at job time by injecting the character's `consistencyInstructions` + reference image URLs (signed, expiring) — never by re-describing the character per scene. Versioning: a character edit creates a new version; scenes pin the version they were generated against (`Scene.characterVersionIds`), so a costume change never silently mutates already-planned scenes. Voice: `Voice` rows bind character → TTS engine + voiceKey (the 7-voice cast from film v5 becomes seed data).

## D.4 Realtime events — real ones only (prompt §19)

`ProductionEvent` rows are **the** source of truth (prompt: "Realtime is for delivery; database history is the source of truth"). Event taxonomy: `production.started/completed/failed`, `manifest.created`, `script.completed`, `character.created`, `scene.started`, `worker.claimed`, `scene.progress {pct?}` (only when the worker reports a real number — the LTX renderer's tqdm percentage is real; there is no other), `scene.completed`, `audio.started/completed`, `qc.started/passed/failed`, `render.started/completed`. **Forbidden**: any UI-generated percentage, any simulated crew chatter, any "Generating… 72%" without a backend event carrying 72.

Delivery: `GET /api/events/stream?productionId=…` — Server-Sent Events (SSE) via a `ReadableStream` route handler polling the event table (Postgres LISTEN/NOTIFY upgrade later; SSE over polling is honest and works on Railway). The customer studio view renders event history on load (replay from DB) then appends live — refreshing the page never loses the story.

## D.5 Live Studio UI (`/studio` — the "control room", prompt §18/§78)

One new hash view (keep the single-page pattern): **CANVAS** (latest selected frame per scene), **STORYBOARD** (scene cards appear as scene.completed fires; rejected versions dimmed but visible), **TIMELINE** (measured durations; shots slot in automatically), **AI CREW** (roles derived from real events: Director = compile stage, Character AI = bible stage, Scene Workers = per-worker rows with real GPU/status from `Worker` table, Voice/Sound = audio jobs, Editor = assembly job, QC = qc events — each shows "working / waiting / done" driven by events, nothing else), **PRODUCTION LOG** (the event stream verbatim, timestamped), **WORKER STATUS** (human strings: "Scene 4 is rendering on a T4 worker — started 2 min ago"). Empty state = "No production running — start one" not a fake film set. Admin/advanced details (leases, attempts, seeds) collapse into an "advanced" drawer.

## D.6 Audio pipeline (what already works, formalized)

The v5 film proved the honest path: generated video cannot follow scripted dialogue → **dialogue is TTS post-dub, always** (until premium lip-sync APIs are enabled). Pipeline: TTS per line (`film_voices.mjs` logic → `tts` jobs) → speed-fit per segment (`atempo`) → loudnorm per clip → placement timeline (adelay) → voice bus amix → music bed with sidechain ducking → limiter → measured duration (`ffprobe`), never assumed. All of this moves into `audio`/`assemble` jobs on the same queue (currently `film_mix.py` runs on the operator's machine — formalize as a worker capability `ffmpeg`, runnable on CPU workers).

## D.7 Editing pipeline

Assembly = the proven chain (`v3_assemble.py`/`v5_assemble.py` lineage): normalize → per-scene trim/grade → captions burn (Archivo) → Ken Burns for still-fallback scenes → end card → loudness master → web encode (crf 26–27, hqdn3d, faststart, moov-first). Encode as an `assemble` job with `editPlan` from the manifest. Cache-busting (`?v=N` on the hero video) becomes automatic (asset checksum suffix).

## D.8 QC gates (prompt §65) — automatic, blocking, honest

`QcResult.checksJson` per render/asset; **a job cannot reach COMPLETED without QC pass** (or an explicit admin override recorded in `AuditLog`):
1. container/codec sanity (ffprobe: exists, h264, faststart);
2. duration within manifest tolerance (planned ±0.8s) — **the delivered duration is the measured duration; the "60-second film" is always the sum of measured scenes**;
3. black-frame / frozen-frame ratio check (ffmpeg blackdetect/freezedetect thresholds);
4. silence check for audio jobs; loudness within −16 to −12 LUFS band for masters;
5. **dialogue match** for voiced scenes: ASR the clip (whisper on worker, capability `whisper_asr`) and require the scripted line to match above a threshold — this is `film_verify.mjs`'s proven ASR gate promoted to a platform check (it caught 8/8 hallucinated lines; it would have caught them before shipping if it had been a gate instead of a script);
6. subject-presence (frame-difference heuristic; flagged "review", not auto-fail).
QC failure → job `FAILED (model_failure)` → retry/fallback path (§C.4) → if terminal, the customer sees "This scene didn't pass our quality check — regenerating / credits preserved" (§E.1). Never deliver obviously broken output silently.

---
