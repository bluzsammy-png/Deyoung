# LICENSE_POLICY — Licensing & Compliance

PATI is MIT-licensed, and so is everything it ships by default. Because PATI
orchestrates *other people's models and services*, this policy defines the
rules for every third-party component and how compliance is recorded.

## 1. PATI itself

- **License:** MIT. You may use, modify, and redistribute PATI, including
  commercially, with attribution and the license notice.
- **No patent bait, no CLA, no phone-home.** PATI makes zero network calls
  except those you configure (Kaggle, tunnels, connectors).

## 2. Third-party code dependencies

Rule: **runtime dependencies must be OSI-compatible and free.** Verified
against the registry (2026-09-02, see `docs/RESEARCH_REPORT.md`):

| Category | Components | Licenses |
|----------|------------|----------|
| Control plane | FastAPI, Uvicorn, Starlette, Pydantic | BSD/MIT/Apache-2.0 family |
| Data | SQLite (public domain), Python stdlib | PSF |
| HTTP client | httpx / requests | BSD |
| CLI | Typer/Click, Rich | MIT |
| Schema | jsonschema | MIT |
| Kaggle API | kaggle / requests | Apache-2.0 |

Procedure for adding a dependency mirrors FREE_FIRST_POLICY §5: verify
license → record in research report → implement → test. Copyleft runtime
dependencies (GPL into MIT code) are avoided not because GPL is bad but
because it constrains redistribution; build-time tools (tests, linters) may
be anything free.

## 3. Models (open weights)

Every model in `MODEL_REGISTRY.md` carries a license row. The policy sorts
acceptable licenses into three buckets:

| Bucket | Licenses | Usage rule in PATI |
|--------|----------|--------------------|
| **Permissive** | Apache-2.0, MIT, BSD | Personal + commercial use, redistribution OK. Preferred. |
| **Community/CopyLeft-OK** | Llama 3.2 Community, Qwen (Tongyi Qianwen), CC-BY-SA variants, GPL weights | Personal use always fine; commercial redistribution has conditions. PATI records the condition next to the model. |
| **Non-commercial (CC-BY-NC)** | Some research checkpoints | Register only with `personal_use_only: true`; never offered in any commercial context (see COMMERCIALIZATION.md). |

Hard rules for models:

1. **Weights are downloaded from official sources** (HF hub model page,
   project releases) — never from random mirrors.
2. **License name is stored in the registry entry**, not just in docs; the
   router can refuse a model by license class (e.g., in a commercial mode).
3. **Output ownership** follows the model license; PATI makes no additional
   claim and stamps provenance (model id + license) into job metadata so you
   always know what produced what.

## 4. External services

| Service | Terms angle | PATI stance |
|---------|-------------|-------------|
| Kaggle | GPU quota is a privilege, ~30 h/week; kernels must comply with Kaggle content rules | Respect the quota via local budget; no quota evasion, no multi-account tricks — that would violate terms and the spirit of FREE_FIRST |
| Cloudflare Tunnel | Free tier terms (no illegal content, reasonable use) | Personal remote access only |
| Google Drive API | OAuth consent scope minimization | `drive.file` scope only (files PATI created); scaffold in `pati_connectors/` |
| GitHub API | Rate limits on free tier | Token auth, conditional requests, backoff |

## 5. User content & artifacts

- Artifacts you create through PATI are **yours**. PATI stores them
  content-addressed on your disk and asserts no license over them.
- Provenance is preserved (which model/tool produced each artifact) because
  downstream licensing of *generated* content depends on it.
- The agent's audit log stays on your machine; it is a security record, not
  telemetry. Nothing is uploaded anywhere by default.

## 6. Compliance workflow (the "record it or it doesn't ship" rule)

```
new dependency/model/service
        │
        ▼
license + cost verified → row in docs/RESEARCH_REPORT.md
        │
        ▼
registry entry carries: license, cost=0, source URL, verification date
        │
        ▼
schema validation (cost ≤ 0) passes
        │
        ▼
ship, with a test pinning the registry entry
```

If a license of an existing component changes adversely, the component gets
flagged in the research report and (if required) removed in the next release
— the registry makes that a one-row edit, not an archaeology dig.

## 7. Attribution

PATI's UI/docs include an attribution section listing models and libraries
with their licenses — generated from the registries so it cannot drift from
reality. Redistribution requires keeping MIT notices for PATI's code and the
respective notices for bundled/registered components.
