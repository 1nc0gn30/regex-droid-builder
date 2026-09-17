"""
Model Context Protocol (MCP) Server for regex-droid-builder.
Conforms to MCP protocol version 2024-11-05 and JSON-RPC 2.0 over stdio.
Zero external runtime dependencies.
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any, Dict, List, Optional

from regex_droid_builder.ast_engine import RegexASTParser, explain_regex
from regex_droid_builder.catalog import PRESETS, get_preset, list_presets
from regex_droid_builder.codegen import generate_code_snippets
from regex_droid_builder.redos_detector import ReDoSAnalyzer

SERVER_NAME = "regex-droid-builder"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSION = "2024-11-05"


class MCPServer:
    """Model Context Protocol stdio server implementation."""

    def __init__(self) -> None:
        self.redos_analyzer = ReDoSAnalyzer()

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Return registered MCP tool schemas."""
        return [
            {
                "name": "regex_explain",
                "description": "Parse a regular expression into an Abstract Syntax Tree (AST) and generate a step-by-step plain English explanation.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "The regular expression pattern."
                        },
                        "flags": {
                            "type": "string",
                            "default": "",
                            "description": "Regex flags (e.g. 'i', 'm', 's')."
                        }
                    },
                    "required": ["pattern"]
                }
            },
            {
                "name": "regex_analyze_redos",
                "description": "Audit a regular expression for Catastrophic Backtracking and ReDoS vulnerabilities with complexity order (O(N), O(2^N)) and remediation guidance.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "The regex pattern to audit."
                        },
                        "flags": {
                            "type": "string",
                            "default": ""
                        }
                    },
                    "required": ["pattern"]
                }
            },
            {
                "name": "regex_test",
                "description": "Test multiple input strings against a regular expression and return match status, spans, and capture groups.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Regex pattern."
                        },
                        "flags": {
                            "type": "string",
                            "default": ""
                        },
                        "test_strings": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of strings to test against the pattern."
                        }
                    },
                    "required": ["pattern", "test_strings"]
                }
            },
            {
                "name": "regex_generate_code",
                "description": "Generate production-ready code snippets in Python, JavaScript/TypeScript, Rust, Go, Java, and C#.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Regex pattern."
                        },
                        "flags": {
                            "type": "string",
                            "default": ""
                        }
                    },
                    "required": ["pattern"]
                }
            },
            {
                "name": "regex_presets",
                "description": "List curated regex presets with descriptions, patterns, and verification test cases.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "regex_diagnostics",
                "description": "Run environment, platform, and regex engine diagnostics.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]

    def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool and format MCP result."""
        if tool_name == "regex_explain":
            pattern = arguments["pattern"]
            flags = arguments.get("flags", "")
            parser = RegexASTParser(pattern, flags)
            ast = parser.parse()
            breakdown = explain_regex(pattern, flags)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "pattern": pattern,
                            "flags": flags,
                            "ast": ast.to_dict(),
                            "explanation_steps": breakdown
                        }, indent=2)
                    }
                ]
            }

        elif tool_name == "regex_analyze_redos":
            pattern = arguments["pattern"]
            flags = arguments.get("flags", "")
            report = self.redos_analyzer.analyze(pattern, flags)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(report.to_dict(), indent=2)
                    }
                ]
            }

        elif tool_name == "regex_test":
            pattern = arguments["pattern"]
            flags = arguments.get("flags", "")
            test_strings = arguments.get("test_strings", [])

            re_flags = 0
            if "i" in flags:
                re_flags |= re.IGNORECASE
            if "m" in flags:
                re_flags |= re.MULTILINE
            if "s" in flags:
                re_flags |= re.DOTALL

            try:
                compiled = re.compile(pattern, re_flags)
            except re.error as e:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({"error": f"Invalid regex: {str(e)}"}, indent=2)
                        }
                    ]
                }

            results = []
            for s in test_strings:
                match = compiled.search(s)
                if match:
                    results.append({
                        "input": s,
                        "is_match": True,
                        "span": match.span(),
                        "matched_text": match.group(0),
                        "groups": match.groups(),
                        "group_dict": match.groupdict()
                    })
                else:
                    results.append({
                        "input": s,
                        "is_match": False,
                        "span": None,
                        "matched_text": None,
                        "groups": [],
                        "group_dict": {}
                    })

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "pattern": pattern,
                            "total_tested": len(test_strings),
                            "matches_count": sum(1 for r in results if r["is_match"]),
                            "results": results
                        }, indent=2)
                    }
                ]
            }

        elif tool_name == "regex_generate_code":
            pattern = arguments["pattern"]
            flags = arguments.get("flags", "")
            snippets = generate_code_snippets(pattern, flags)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "pattern": pattern,
                            "flags": flags,
                            "snippets": snippets
                        }, indent=2)
                    }
                ]
            }

        elif tool_name == "regex_presets":
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({"presets": list_presets()}, indent=2)
                    }
                ]
            }

        elif tool_name == "regex_diagnostics":
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "server": SERVER_NAME,
                            "version": SERVER_VERSION,
                            "protocol_version": PROTOCOL_VERSION,
                            "platform": sys.platform,
                            "python_version": sys.version,
                            "presets_catalog_size": len(PRESETS),
                            "zero_dependencies": True,
                            "status": "HEALTHY"
                        }, indent=2)
                    }
                ]
            }

        raise ValueError(f"Unknown tool: {tool_name}")

    def handle_request(self, request_str: str) -> Optional[str]:
        """Process JSON-RPC 2.0 request string and return formatted response."""
        try:
            req = json.loads(request_str)
        except Exception as e:
            return json.dumps({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {str(e)}"}
            })

        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if method == "initialize":
            return json.dumps({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION}
                }
            })

        elif method == "notifications/initialized":
            return None

        elif method == "ping":
            return json.dumps({"jsonrpc": "2.0", "id": req_id, "result": {}})

        elif method == "tools/list":
            return json.dumps({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": self.get_tool_definitions()}
            })

        elif method == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments", {})
            try:
                res = self.handle_tool_call(name, arguments)
                return json.dumps({"jsonrpc": "2.0", "id": req_id, "result": res})
            except Exception as e:
                return json.dumps({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32603, "message": str(e)}
                })

        return json.dumps({
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"}
        })

    def run_stdio(self) -> None:
        """Run stdio loop reading JSON-RPC requests."""
        for line in sys.stdin:
            line_str = line.strip()
            if not line_str:
                continue
            resp = self.handle_request(line_str)
            if resp:
                sys.stdout.write(resp + "\n")
                sys.stdout.flush()


def run_mcp_server() -> None:
    """Entrypoint to launch MCP stdio server."""
    server = MCPServer()
    server.run_stdio()
