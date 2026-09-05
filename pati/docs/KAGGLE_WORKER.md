# KAGGLE_WORKER.md

## Role in PATI

Kaggle is a **free, legitimate, ephemeral batch-compute worker**
(FREE_WITH_LIMITS). It is NOT a permanent server and NOT the control plane.
PATI plans; Kaggle executes individual GPU jobs and returns artifacts.

## Verified facts (2026-09-02, see docs/RESEARCH_REPORT.md)

- Official free API: `kaggle kernels push|status|output|list` plus the
  Python/CLI client (Apache-2.0). The website is NOT scraped; automation
  stays inside the official API and its dynamic rate limits.
- Free GPU: roughly 30 hours/week (weekly maximum GPU usage policy), session
  caps ~12 h, kernels are ephemeral; outputs must be written to
  `/kaggle/working` and are retrieved via `kaggle kernels output`.
- Models: Kaggle Models hosts official open-weights models; attaching a
  model to a kernel keeps weights inside Kaggle's infrastructure (no license
  violation by PATI). Non-commercial-weight models (XTTS-v2, MusicGen) are
  flagged in the registry; Piper (MIT) is the commercial-safe TTS.

## Setup (owner, one time, $0)

1. Create a free Kaggle account.
2. Profile picture → Settings → API → **Create New Token**.
3. Save the token in ONE of the officially supported forms (checked in this
   order by the worker):

   - **New style (current Kaggle site):** the `KGAT_...` token string.
     Put it in the file `~/.kaggle/access_token` (one line, nothing else),
     or export it as the `KAGGLE_API_TOKEN` environment variable.
   - **Classic style:** the `kaggle.json` download
     (`{"username": ..., "key": ...}`) at `~/.kaggle/kaggle.json`.
     This style additionally lets PATI resolve your username locally
     (no network call) for kernel slugs.

   Windows PowerShell examples (run in PowerShell, not CMD):

   ```powershell
   # New-style token file (recommended when Kaggle gives you a KGAT_ token)
   New-Item -ItemType Directory -Force "$env:USERPROFILE\.kaggle" | Out-Null
   Set-Content -Path "$env:USERPROFILE\.kaggle\access_token" -Value "PASTE_NEW_TOKEN_HERE" -NoNewline
   # Optionally also set your username so kernel slugs resolve without a CLI call:
   setx KAGGLE_USERNAME "your-kaggle-username"
   ```

   Linux/macOS equivalent:

   ```bash
   mkdir -p ~/.kaggle && echo "PASTE_NEW_TOKEN_HERE" > ~/.kaggle/access_token && chmod 600 ~/.kaggle/access_token
   ```

4. `pip install pati[kaggle]`.
5. Register the worker through PATI (the control plane-side adapter runs
   where the credentials live):

```
KaggleWorker()             # reports available/unavailable honestly
kw.submit(job)             # pushes a generated kernel script
kw.status(job_id)          # polls kernel status
kw.artifacts(job_id)       # pulls /kaggle/working outputs
```

Without any token the worker reports unavailable and the router returns
`RESOURCE_UNAVAILABLE` for GPU capabilities — PATI never falls back to paid
compute. `register()` / `doctor` report which credential style was detected
(never the secret itself).

## Job protocol

`submit(job)` maps a PATI stage to a generated `pati_job.py` kernel script:

- text-family capabilities (text_generation, summarization,
  structured_output, reasoning, coding) → a transformers generate step using
  an open-weights instruct model (override with `PATI_KAGGLE_MODEL` or
  `params.model_sources` to attach a Kaggle-hosted model).
- image_generation → Stable Diffusion XL kernel (fp16).
- other modalities → explicit "capability not yet mapped" result (honest).
- `enable_internet` is opt-in per job (`params.enable_internet`).

Quota: the worker enforces a **local daily GPU-minute budget**
(default 240 min/day, configurable via `/admin/quotas/gpu_minutes_per_day`)
on top of Kaggle's weekly allowance. Budget exhaustion is a
RESOURCE_UNAVAILABLE condition, not an error to hide.

## Limitations (honest)

- Kernel queue latency (minutes), cold starts, 12 h session caps.
- Kaggle cannot be cancelled via API; PATI discards outputs instead.
- GPU availability (T4/P100) varies with demand.
- Results are pulled asynchronously; long jobs need deadline tuning
  (`PATI_STAGE_DEADLINE_S`).

## Tests

`tests/test_remote_worker_e2e.py` proves the identical pull-worker protocol
end to end over real HTTP with a deterministic simulated worker; the Kaggle
push adapter is exercised with its real code paths minus network
(`kaggle_available()` gating, kernel body/meta generation, quota budgeting).
