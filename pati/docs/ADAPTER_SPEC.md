# ADAPTER_SPEC.md

Everything external sits behind an adapter. Adapters isolate PATI from
providers so no vendor becomes the foundation.

## Contract

An adapter (see `pati_connectors/base.py` and `adapters/template/`) declares
metadata and implements behavior:

- **metadata**: id, version, capabilities, license, free_status, cost (0),
  security profile, hardware/network requirements, last_verified.
- **configuration**: schema-validated config; least-privilege by default.
- **installation**: what the adapter needs, installed via audited ops.
- **health check**: cheap, honest probe.
- **execution**: normalized call interface; errors normalized to PATI codes
  (RESOURCE_UNAVAILABLE, SECURITY_VIOLATION, TRANSIENT...).
- **cleanup**: no leaked processes/files/credentials.

## Adapter families

| Family | Location | Examples |
|---|---|---|
| Personal AI clients | `pati/adapters/` | ZAIAdapter, GenericAdapter (MCP client = pati_mcp) |
| Workers | `pati_workers/` | Local Agent (pull), KaggleWorker (push), ContainerWorker |
| Connectors | `pati_connectors/` | GitHub, GDrive scaffold |
| Models | model registry + worker ops | kaggle-hosted, local (Ollama slot), builtin simulated |

## Rules

1. Adapters never contain orchestration logic.
2. Adapters never receive more privilege than their declared scopes.
3. Adapter failures are data, not crashes: they flow into stage errors,
   circuit breakers and (optionally) quarantine.
4. A provider with cost > 0 cannot be expressed as an adapter — the
   registries reject it (docs/FREE_FIRST_POLICY.md).
