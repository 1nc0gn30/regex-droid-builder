"""Tests for FastMCP JSON-RPC 2.0 stdio server."""

import json
import pytest
from regex_droid_builder.mcp_server import MCPServer


def test_mcp_initialize():
    server = MCPServer()
    req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    res = json.loads(server.handle_request(req))
    assert res["id"] == 1
    assert res["result"]["serverInfo"]["name"] == "regex-droid-builder"


def test_mcp_tools_list():
    server = MCPServer()
    req = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    res = json.loads(server.handle_request(req))
    tool_names = [t["name"] for t in res["result"]["tools"]]
    assert "regex_explain" in tool_names
    assert "regex_analyze_redos" in tool_names
    assert "regex_test" in tool_names
    assert "regex_generate_code" in tool_names
    assert "regex_presets" in tool_names
    assert "regex_diagnostics" in tool_names


def test_mcp_tool_explain():
    server = MCPServer()
    req = json.dumps({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "regex_explain",
            "arguments": {"pattern": r"^[\w.-]+@[\w.-]+\.[a-zA-Z]{2,}$"}
        }
    })
    res = json.loads(server.handle_request(req))
    data = json.loads(res["result"]["content"][0]["text"])
    assert "explanation_steps" in data
    assert len(data["explanation_steps"]) > 0


def test_mcp_tool_analyze_redos():
    server = MCPServer()
    req = json.dumps({
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "regex_analyze_redos",
            "arguments": {"pattern": r"(a+)+$"}
        }
    })
    res = json.loads(server.handle_request(req))
    data = json.loads(res["result"]["content"][0]["text"])
    assert data["is_vulnerable"] is True
    assert data["severity"] == "CRITICAL_REDOS"


def test_mcp_tool_test():
    server = MCPServer()
    req = json.dumps({
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {
            "name": "regex_test",
            "arguments": {
                "pattern": r"^\d{3}-\d{4}$",
                "test_strings": ["123-4567", "invalid", "999-0000"]
            }
        }
    })
    res = json.loads(server.handle_request(req))
    data = json.loads(res["result"]["content"][0]["text"])
    assert data["total_tested"] == 3
    assert data["matches_count"] == 2


def test_mcp_tool_generate_code():
    server = MCPServer()
    req = json.dumps({
        "jsonrpc": "2.0",
        "id": 6,
        "method": "tools/call",
        "params": {
            "name": "regex_generate_code",
            "arguments": {"pattern": r"^[a-z]+$"}
        }
    })
    res = json.loads(server.handle_request(req))
    data = json.loads(res["result"]["content"][0]["text"])
    assert "python" in data["snippets"]
