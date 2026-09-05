"""Z.ai adapter - the FIRST Personal AI client of PATI, deliberately thin.

Z.ai (browser Personal AI) can integrate in three $0 ways:
1. Tool-calling: register the JSON produced by `tool_spec()` as a PATI tool so
   Z.ai can call pati_* tools during a conversation.
2. MCP: run `pati-mcp` (stdio MCP server) inside an MCP-capable client.
3. Plain API: any Z.ai plugin/extension can use PatiClient over HTTP.

None of these embed orchestration inside Z.ai: PATI plans, routes, executes.
"""
from __future__ import annotations

import json

from .base import PersonalAIAdapter, summarize_task_status


class ZAIAdapter(PersonalAIAdapter):
    name = "zai"

    def describe_capabilities(self) -> str:
        caps = self.client.get_capabilities()
        by_cat: dict[str, list[str]] = {}
        for c in caps:
            by_cat.setdefault(c["category"], []).append(c["capability_id"])
        lines = ["PATI capabilities (all free, $0):"]
        for cat, ids in sorted(by_cat.items()):
            lines.append(f"  {cat}: {', '.join(ids[:8])}{' ...' if len(ids) > 8 else ''}")
        return "\n".join(lines)

    def execute_objective(self, objective: str, **kw) -> dict:
        return self.client.submit_task(objective, **kw)

    def format_result(self, task: dict) -> str:
        status = task["status"]
        out = [f"PATI finished your request: {status}."]
        if task.get("error"):
            out.append(f"Problem: {task['error']}")
        arts = self.client.list_task_artifacts(task["id"]) if status == "COMPLETED" else []
        for a in arts:
            loc = a["location"] if a["storage"] == "local_reference" else f"artifact {a['id']}"
            out.append(f"  artifact: {a['name']} ({a['size']} bytes) -> {loc}")
        if not arts and status == "COMPLETED":
            out.append(summarize_task_status(task))
        return "\n".join(out)

    # ------------------------------------------------------------------
    def tool_spec(self) -> list[dict]:
        """OpenAI-style tool definitions a Z.ai tool-calling client can adopt.

        These map 1:1 onto SDK operations; execution always goes through PATI.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "pati_submit_objective",
                    "description": "Submit a high-level objective to PATI (files, video, image, voice, research, coding). Returns a task id.",
                    "parameters": {"type": "object", "properties": {
                        "objective": {"type": "string"},
                        "type": {"type": "string", "enum": [
                            "auto", "text_generation", "image_generation", "video_workflow",
                            "voice_generation", "speech_to_text", "music_generation", "research",
                            "document", "coding", "filesystem_organize"]},
                        "params": {"type": "object"}},
                        "required": ["objective"]},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "pati_get_task",
                    "description": "Get PATI task status, stages and results.",
                    "parameters": {"type": "object",
                                   "properties": {"task_id": {"type": "string"}},
                                   "required": ["task_id"}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "pati_list_workers",
                    "description": "List PATI workers (local agent, Kaggle GPU, containers) and their health.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "pati_system_status",
                    "description": "PATI system status incl. FREE_ONLY policy and quotas.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
        ]

    def handle_tool_call(self, name: str, args: dict) -> str:
        """Execute a Z.ai tool call against PATI and return text for the model."""
        if name == "pati_submit_objective":
            task = self.client.submit_task(args["objective"], task_type=args.get("type", "auto"),
                                           params=args.get("params") or {})
            return json.dumps({"task_id": task["id"], "status": task["status"],
                               "stages": [s["name"] for s in task["stages"]]})
        if name == "pati_get_task":
            task = self.client.get_task(args["task_id"])
            return self.format_result(task)
        if name == "pati_list_workers":
            return json.dumps(self.client.list_workers(), default=str)
        if name == "pati_system_status":
            return json.dumps(self.client.get_system_status(), default=str)
        raise KeyError(f"unknown tool: {name}")
