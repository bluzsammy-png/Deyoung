"""MCP server: initialize, tools/list, safe tool calls against the live API."""
from __future__ import annotations

import json
import os

import pytest


@pytest.fixture()
def mcp_env(server, monkeypatch):
    monkeypatch.setenv("PATI_SERVER", server["base_url"])
    monkeypatch.setenv("PATI_TOKEN", server["admin_token"])
    from pati_mcp import server as mcp
    return mcp


def test_initialize(mcp_env):
    reply = mcp_env.handle_message({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert reply["result"]["serverInfo"]["name"] == "pati-mcp"
    assert reply["result"]["protocolVersion"]


def test_tools_list_exposes_safe_tools_only(mcp_env):
    reply = mcp_env.handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    names = [t["name"] for t in reply["result"]["tools"]]
    assert "pati_create_task" in names and "pati_get_task" in names
    # no administrative or shell tools exist
    for banned in ("shell", "exec", "credentials", "ssh", "admin"):
        assert not any(banned in n for n in names)


def test_tool_call_roundtrip(mcp_env, admin):
    reply = mcp_env.handle_message({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                                    "params": {"name": "pati_list_workers", "arguments": {}}})
    assert "content" in reply["result"]
    payload = json.loads(reply["result"]["content"][0]["text"])
    assert "workers" in payload


def test_unknown_tool_error(mcp_env):
    reply = mcp_env.handle_message({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                                    "params": {"name": "pati_root_shell", "arguments": {}}})
    assert "error" in reply
