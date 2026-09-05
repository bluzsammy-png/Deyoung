"""PATI MCP server - safe tools only, stdio JSON-RPC 2.0 (zero dependencies).

Implements the relevant subset of the Model Context Protocol (open standard,
donated to the Linux Foundation) so MCP-capable AI clients can use PATI.
Administrative operations are NOT exposed over MCP. Credentials are never
exposed. Tools:

    pati_get_system_status      -> system health + FREE_ONLY policy
    pati_list_capabilities      -> capability registry
    pati_list_models            -> free model registry
    pati_list_tools             -> tool registry
    pati_list_workers           -> worker fleet status
    pati_create_task            -> submit an objective
    pati_get_task               -> task status/results
    pati_submit_research        -> research objective
    pati_get_artifact_meta      -> artifact metadata (never raw local bytes)

Environment: PATI_SERVER (default http://127.0.0.1:8000), PATI_TOKEN.
"""
from __future__ import annotations

import io
import json
import os
import sys

PROTOCOL_VERSION = "2024-11-05"


def _client():
    from pati import PatiClient
    from pati.errors import PATIError
    base = os.environ.get("PATI_SERVER", "http://127.0.0.1:8000")
    token = os.environ.get("PATI_TOKEN", "")
    if not token:
        raise RuntimeError("PATI_TOKEN not set; obtain a client token from the control plane")
    return PatiClient(base, token)


TOOLS = [
    {"name": "pati_get_system_status", "description": "PATI system status incl. FREE_ONLY policy",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "pati_list_capabilities", "description": "List PATI capabilities",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "pati_list_models", "description": "List free models (cost=0 enforced)",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "pati_list_tools", "description": "List PATI tools",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "pati_list_workers", "description": "List workers (local agent, Kaggle GPU, containers)",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "pati_create_task", "description": "Submit a high-level objective to PATI",
     "inputSchema": {"type": "object", "properties": {
         "objective": {"type": "string"}, "type": {"type": "string"},
         "params": {"type": "object"}}, "required": ["objective"]}},
    {"name": "pati_get_task", "description": "Get task status/stages/artifacts",
     "inputSchema": {"type": "object", "properties": {"task_id": {"type": "string"}},
                     "required": ["task_id"]}},
    {"name": "pati_submit_research", "description": "Submit a research objective",
     "inputSchema": {"type": "object", "properties": {"query": {"type": "string"},
                     "mode": {"type": "string"}}, "required": ["query"]}},
    {"name": "pati_get_artifact_meta", "description": "Artifact metadata (not bytes)",
     "inputSchema": {"type": "object", "properties": {"artifact_id": {"type": "string"}},
                     "required": ["artifact_id"]}},
]


def _dispatch_tool(name: str, args: dict) -> dict:
    pati = _client()
    if name == "pati_get_system_status":
        return pati.get_system_status()
    if name == "pati_list_capabilities":
        return {"capabilities": pati.get_capabilities()}
    if name == "pati_list_models":
        return {"models": pati.list_models()}
    if name == "pati_list_tools":
        return {"tools": pati.list_tools()}
    if name == "pati_list_workers":
        return {"workers": pati.list_workers()}
    if name == "pati_create_task":
        return pati.submit_task(args["objective"], task_type=args.get("type", "auto"),
                                params=args.get("params") or {})
    if name == "pati_get_task":
        return pati.get_task(args["task_id"])
    if name == "pati_submit_research":
        return pati.submit_research(args["query"], mode=args.get("mode", "local_corpus"))
    if name == "pati_get_artifact_meta":
        return pati.get_artifact(args["artifact_id"])
    raise KeyError(name)


def _reply(msg_id, result=None, error=None) -> dict:
    out = {"jsonrpc": "2.0", "id": msg_id}
    if error is not None:
        out["error"] = error
    else:
        out["result"] = result
    return out


def handle_message(msg: dict) -> dict | None:
    method = msg.get("method", "")
    msg_id = msg.get("id")
    try:
        if method == "initialize":
            return _reply(msg_id, {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "pati-mcp", "version": "1.0.0"}})
        if method == "notifications/initialized":
            return None
        if method == "tools/list":
            return _reply(msg_id, {"tools": TOOLS})
        if method == "tools/call":
            name = msg["params"]["name"]
            args = msg["params"].get("arguments") or {}
            result = _dispatch_tool(name, args)
            return _reply(msg_id, {"content": [
                {"type": "text", "text": json.dumps(result, indent=2, default=str)}]})
        if method == "ping":
            return _reply(msg_id, {})
        return _reply(msg_id, error={"code": -32601, "message": f"method not found: {method}"})
    except KeyError as e:
        return _reply(msg_id, error={"code": -32602, "message": f"unknown tool {e}"})
    except Exception as e:
        return _reply(msg_id, error={"code": -32000, "message": str(e)})


def serve(stdin=None, stdout=None) -> None:
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        reply = handle_message(msg)
        if reply is not None:
            stdout.write(json.dumps(reply) + "\n")
            stdout.flush()


def main() -> None:
    print("PATI MCP server (stdio). Set PATI_SERVER and PATI_TOKEN.", file=sys.stderr)
    serve()


if __name__ == "__main__":
    main()
