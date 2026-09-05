# MODEL_REGISTRY.md

Source: `pati_api/registries.py::MODELS` + DB overrides. Exposed at
`GET /api/v1/models`; validated against `schemas/model.schema.json`
(which hard-codes `cost <= 0`).

Every entry carries the full master-prompt field set: ids/names/organization,
provider, modality, capabilities, license + license_url + source/repo/model
URLs, hardware/RAM/VRAM requirements, quantization options, context length,
languages, input/output types, latency estimate, quality/speed scores,
**cost (0) + free_status**, availability, worker_requirements, startup and
cold-start times, tool-calling/structured-output/vision/reasoning support
flags, commercial_use, license_restrictions, known_limitations,
benchmark_results, last_verified, status.

## Current entries (13)

| model_id | provider | modality | free_status | notes |
|---|---|---|---|---|
| pati-sim-text-v1 | builtin | text | FREE_FOREVER | deterministic, labeled simulated |
| pati-sim-image-v1 | builtin | image | FREE_FOREVER | simulated placeholder |
| pati-sim-video-v1 | builtin | video | FREE_FOREVER | simulated placeholder |
| pati-sim-audio-v1 | builtin | audio | FREE_FOREVER | simulated placeholder |
| qwen2.5-7b-instruct | kaggle-hosted | text | FREE_WITH_LIMITS | Apache-2.0 |
| llama-3.2-3b-instruct | kaggle-hosted | text | FREE_WITH_LIMITS | Llama community license |
| gemma-2-2b-it | kaggle-hosted | text | FREE_WITH_LIMITS | Gemma terms |
| sdxl-1.0 | kaggle-hosted | image | FREE_WITH_LIMITS | Open RAIL++-M |
| sd-1.5 | kaggle-hosted | image | FREE_WITH_LIMITS | Open RAIL-M |
| whisper-large-v3 | kaggle-hosted | audio | FREE_WITH_LIMITS | Apache-2.0 |
| xtts-v2 | kaggle-hosted | audio | FREE_WITH_LIMITS | **non-commercial** flagged |
| piper-tts | kaggle-hosted | audio | FREE_WITH_LIMITS | MIT (commercial-safe) |
| musicgen-small | kaggle-hosted | audio | FREE_WITH_LIMITS | CC-BY-NC flagged |

## Rules

- Simulated engines are honest: results carry `simulated: true` end to end.
- Non-commercial weights are usable for the owner's personal projects but
  flagged for the future SaaS path (Piper replaces XTTS commercially).
- Local providers (Ollama/llama.cpp, vLLM) attach through the same registry:
  add an entry with provider "local" and worker_requirements LOCAL_WORKER.
- `last_verified` dates drive re-verification (docs/RESEARCH_REPORT.md).
