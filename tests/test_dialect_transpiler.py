"""
Tests for Cross-Flavor Regex Dialect Transpiler.
"""

from __future__ import annotations

import json
from regex_droid_builder.cli import main
from regex_droid_builder.dialect_transpiler import (
    RegexDialectTranspiler,
    TranspilationResult,
    transpile_regex,
)
from regex_droid_builder.mcp_server import MCPServer


def test_python_to_javascript_named_groups() -> None:
    pattern = r"(?P<username>[a-zA-Z0-9_]+)@(?P<domain>[a-zA-Z0-9.-]+)"
    res = transpile_regex(pattern, source_dialect="python", target_dialect="javascript")

    assert isinstance(res, TranspilationResult)
    assert res.target_dialect == "javascript"
    assert "(?<username>" in res.target_pattern
    assert "(?<domain>" in res.target_pattern
    assert "(?P<" not in res.target_pattern
    assert res.is_lossless is True
    assert "const regex = /" in res.code_snippet


def test_javascript_to_python_named_groups() -> None:
    pattern = r"(?<year>\d{4})-(?<month>\d{2})-(?<day>\d{2})"
    res = transpile_regex(pattern, source_dialect="javascript", target_dialect="python")

    assert "(?P<year>" in res.target_pattern
    assert "(?P<month>" in res.target_pattern
    assert "(?P<day>" in res.target_pattern
    assert res.is_lossless is True
    assert "import re" in res.code_snippet


def test_transpile_to_go_detects_unsupported_lookarounds() -> None:
    pattern = r"\w+(?=\.json)"
    res = transpile_regex(pattern, source_dialect="python", target_dialect="go")

    assert res.is_lossless is False
    unsupported_warnings = [w for w in res.warnings if w.severity == "UNSUPPORTED_ERROR"]
    assert len(unsupported_warnings) > 0
    assert "Lookaround" in unsupported_warnings[0].feature


def test_transpile_to_rust_detects_unsupported_backreferences() -> None:
    pattern = r"<([a-z]+)>.*?</\1>"
    res = transpile_regex(pattern, source_dialect="pcre", target_dialect="rust")

    assert res.is_lossless is False
    unsupported_warnings = [w for w in res.warnings if w.severity == "UNSUPPORTED_ERROR"]
    assert len(unsupported_warnings) > 0
    assert "Backreferences" in unsupported_warnings[0].feature


def test_transpile_to_posix_ere_downgrades_named_and_non_capturing() -> None:
    pattern = r"(?P<id>[0-9]+)(?:-[a-z]+)?"
    res = transpile_regex(pattern, source_dialect="python", target_dialect="posix_ere")

    assert "(?P<" not in res.target_pattern
    assert "(?:" not in res.target_pattern
    assert "(" in res.target_pattern
    degraded = [w for w in res.warnings if w.severity == "DEGRADED_SYNTAX"]
    assert len(degraded) >= 2


def test_possessive_quantifier_transpilation() -> None:
    pattern = r'"[^"]*+"'
    res = transpile_regex(pattern, source_dialect="pcre", target_dialect="javascript")

    assert "*+" not in res.target_pattern
    assert "*" in res.target_pattern
    assert any("Possessive" in w.feature for w in res.warnings)


def test_mcp_transpile_tool() -> None:
    server = MCPServer()
    req = {
        "jsonrpc": "2.0",
        "id": 10,
        "method": "tools/call",
        "params": {
            "name": "regex_transpile_dialect",
            "arguments": {
                "pattern": r"(?P<key>\w+)=(?P<val>\w+)",
                "source_dialect": "python",
                "target_dialect": "javascript",
            }
        }
    }
    resp_str = server.handle_request(json.dumps(req))
    assert resp_str is not None
    resp = json.loads(resp_str)
    assert "result" in resp
    text = resp["result"]["content"][0]["text"]
    data = json.loads(text)
    assert data["target_dialect"] == "javascript"
    assert "(?<key>" in data["target_pattern"]


def test_cli_transpile_command(capsys) -> None:
    code = main(["transpile", r"(?P<tag>\w+)", "--from", "python", "--to", "javascript", "--json"])
    assert code == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["target_dialect"] == "javascript"
    assert "(?<tag>" in data["target_pattern"]
