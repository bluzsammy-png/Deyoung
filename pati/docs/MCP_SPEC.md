# MCP_SPEC.md

PATI ships a dependency-free MCP server (`pati_mcp/server.py`) speaking
JSON-RPC 2.0 over stdio, compatible with the Model Context Protocol (open
standard, Linux Foundation). Run it: `pati-mcp` with env `PATI_SERVER` and
`PATI_TOKEN` (a client token).

## Design rules

- **Safe tools only.** No shell, no credentials, no admin operations.
- Every tool maps 1:1 to a PATI API call; the MCP layer holds no logic.
- Results are returned as JSON text content blocks.

## Tools

| Tool | Input | Effect |
|---|---|---|
| pati_get_system_status | {} | health, policy, counts |
| pati_list_capabilities | {} | capability registry |
| pati_list_models | {} | free model registry |
| pati_list_tools | {} | tool registry |
| pati_list_workers | {} | worker fleet |
| pati_create_task | objective, type?, params? | submit objective |
| pati_get_task | task_id | status/stages/artifacts |
| pati_submit_research | query, mode? | research task |
| pati_get_artifact_meta | artifact_id | metadata only — never raw local bytes |

## Protocol notes

- `initialize` → protocolVersion 2024-11-05, capabilities.tools, serverInfo
  "pati-mcp".
- `tools/list` → the table above with JSON Schema inputSchema.
- `tools/call` → dispatch; unknown tool → -32602; upstream failure → -32000
  with the API error message.
- `ping` → {}.

## Admin exposure

Deliberately none. Token issuance, quota changes, connector credentials and
anything touching the filesystem are outside MCP. The MCP token is a normal
client token: revoke it and every MCP client loses access instantly.
