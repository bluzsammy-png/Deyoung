# Render Workers — how DeYoung renders without anyone present

DeYoung does **not** depend on a single AI vendor. The site sells videos through a
Postgres queue (`VideoRequest`), and rendering is done by a fleet of swappable
**workers** that pull from that queue. Anyone can add capacity; nothing blocks on
one provider being up, funded, or rate-limited.

```
                     ┌────────────────────────────────────────────┐
customer pays →      │  Railway app (Next.js + Supabase Postgres) │
submits prompt →     │  /api/requests  →  status queued           │
watches status →     │  /api/worker/*   ←  the worker plane       │
gets download ←      └───────────────┬────────────────────────────┘
                                     │ claim (priority → FIFO)
        ┌────────────────────────────┼─────────────────────────────┐
        ▼                            ▼                             ▼
 Kaggle GPU kernel            owner's PC (PATI agent)        paid render APIs
 (workers/deyoung_worker.py   (same worker,                  (z-ai / Atlas Cloud Kling /
  via scripts/                 RENDERER=auto)                 Evolink Veo — when funded,
  kaggle_launch.py,                                           plugged into the same
  LTX-Video, free ~30h/wk)                                    queue, premium quality)
```

## The worker plane (this repo)

| Endpoint | Auth | Purpose |
|---|---|---|
| `POST /api/worker/claim` | `Bearer WORKER_TOKEN` | Atomically claims the next queued job (priority → FIFO, double-claim safe) |
| `PATCH /api/worker/jobs/:id` | `Bearer WORKER_TOKEN` | `deliver` (multipart mp4 or JSON url), `fail` (honest failure with reason), `progress` |
| `GET /api/worker/file/:name` | public | Streams a delivered render (Range/206-capable for `<video>`) |
| `GET /api/worker/status` | `Bearer WORKER_TOKEN` | Queue depth heartbeat — lets workers decide to keep polling |

The owner's admin **Video Queue** tab still works exactly as before — workers
simply replace the manual "start render → paste URL" loop.

## The universal worker — `workers/deyoung_worker.py`

Runs anywhere with Python 3.9+ and ffmpeg (**stdlib only**, no pip installs
needed for the worker itself):

```bash
python3 workers/deyoung_worker.py \
  --site https://deeyoung-production-72ef.up.railway.app \
  --token <WORKER_TOKEN> \
  --renderer auto        # auto | stub | ltx | comma chain e.g. "ltx,stub"
  --job-budget 1.0       # scale the per-renderer wall-clock caps
  --max-minutes 480      # stop cleanly after this budget
  --exit-idle            # optional: exit when the queue drains
```

Renderers:
- **`stub`** — ffmpeg-only branded placeholder. Runs on any CPU. Used for QA
  and as the automatic fallback; proves the whole queue→render→deliver→download
  loop end-to-end without a GPU.
- **`ltx`** — **LTX-Video** (Lightricks, open weights) text-to-video on CUDA.
  Needs `pip install torch diffusers transformers accelerate imageio imageio-ffmpeg`
  (pre-installed on Kaggle GPU images except diffusers — the kernel installs it).
  Falls back to `stub` automatically if torch/CUDA/diffusers are missing.
- **`auto`** — chain `ltx,stub` when CUDA exists, else `stub`.

### Quality + cost discipline (in the worker)

- **QA gate (fail-closed).** Nothing is delivered until it passes ffprobe +
  pixel sanity: video AND audio streams present, duration within tolerance,
  resolution matches the job, sane file size; real renderers additionally get
  a black-frame scan (the stub's dark gradient is exempt by design). A failed
  render falls down the chain; only an honest `action=fail` reaches the site.
- **Fallback chain.** `--renderer "ltx,stub"` tries renderers in order; any
  renderer that crashes, blows its budget, or fails QA is skipped.
- **Cost governor.** Each renderer gets a per-job wall-clock budget
  (`ltx: 2min + 0.8min/s`, `stub: 6min`, × `--job-budget`). Over-budget
  renders are aborted so one poison prompt can't eat a whole free GPU hour.
- The QA verdict travels with the delivery and shows in the admin queue notes
  (e.g. `QA OK` / `QA FAIL: duration …`).

Failures are reported back with `action=fail` and the reason lands in the
admin queue — a poison prompt never silently clogs the fleet.

## Free GPU: launch on Kaggle in one command

```bash
export KAGGLE_API_TOKEN=<KGAT_…>        # kaggle.com → Settings → API
python3 scripts/kaggle_launch.py \
  --token <WORKER_TOKEN> --max-minutes 480 --watch
```

This bakes the worker into a **private, GPU-enabled, internet-on kernel** at
`kaggle.com/code/<you>/deyoung-worker` and pushes it. Kaggle boots a fresh
session that loops claim→render→deliver for up to `--max-minutes` (≈9h GPU
session cap). Budget: **~30 free GPU-hours/week** — re-run the command any
time for another session (it versions the same kernel).

Credentials compatibility: both the new `KGAT_…` access tokens (env
`KAGGLE_API_TOKEN`) and classic `~/.kaggle/kaggle.json` work.

## Owner's PC (PATI agent style)

Same script, no Kaggle account needed:

```bash
pip install torch diffusers transformers accelerate imageio imageio-ffmpeg  # once, GPU build
python3 workers/deyoung_worker.py --token <WORKER_TOKEN> --renderer auto --exit-idle
```

## Paid premium path

The Atlas Cloud (Kling 3.0, native lip-sync) and Evolink (Veo) integrations
become just another worker in this same plane when their credits are topped
up — premium/lip-sync jobs route to them, everything else stays free. Their
keys are currently **valid but empty (402)**; top up either to enable.

## Operational notes

- `WORKER_TOKEN` must be ≥16 chars; the worker API answers `503` when it is
  unset, so a misconfigured server can never accept anonymous renders.
- Delivered files are stored under `public/uploads/` (gitignored) and served
  through the Range-capable API route — identical behavior in dev and in the
  standalone production bundle. Railway's container filesystem is ephemeral:
  delivered videos live until the next deploy, same as the rest of the media
  pipeline. Point `resultUrl` at object storage later for permanence.
- Rotate `WORKER_TOKEN` and `KAGGLE_API_TOKEN` periodically; never paste
  either into chats — the launcher reads them from the environment only.
