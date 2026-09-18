"""
Tests for Formal Verifier: Hopcroft/Moore DFA State Minimization,
Regex Equivalence Checking, Subset Containment, and Shortest Counterexample Synthesis.
"""

from __future__ import annotations

import json
from regex_droid_builder.automaton_engine import AutomatonBuilder
from regex_droid_builder.cli import main
from regex_droid_builder.formal_verifier import (
    DFAEquivalenceVerifier,
    DFAStateMinimizer,
    RegexEquivalenceResult,
    compare_regex_patterns,
    minimize_dfa,
)
from regex_droid_builder.mcp_server import MCPServer


def test_dfa_minimization_preserves_language() -> None:
    builder = AutomatonBuilder()
    minimizer = DFAStateMinimizer()

    # Pattern with redundant branch structure
    pattern = r"a(b|c)|a(b|c)"
    nfa = builder.build_nfa(pattern)
    dfa_raw = builder.convert_to_dfa(nfa)
    dfa_min = minimizer.minimize(dfa_raw)

    assert dfa_min.total_states <= dfa_raw.total_states
    assert dfa_min.start_state in dfa_min.states

    # Verify acceptance of matching strings
    # Both "ab" and "ac" must be accepted by minimized DFA
    for word in ("ab", "ac"):
        curr = dfa_min.start_state
        for ch in word:
            curr = dfa_min.states[curr].transitions.get(ch)
            assert curr is not None
        assert dfa_min.states[curr].is_accept is True


def test_regex_exact_equivalence() -> None:
    # a(b|c) is equivalent to ab|ac
    res = compare_regex_patterns(r"a(b|c)", r"ab|ac")
    assert res.are_equivalent is True
    assert res.is_subset_a_in_b is True
    assert res.is_subset_b_in_a is True
    assert res.counterexample_a_not_b is None
    assert res.counterexample_b_not_a is None
    assert res.verdict == "EQUIVALENT"


def test_regex_subset_containment_and_counterexample() -> None:
    # a+ is a strict subset of a*
    # Empty string "" is in a* but not in a+
    res = compare_regex_patterns(r"a+", r"a*")
    assert res.are_equivalent is False
    assert res.is_subset_a_in_b is True  # a+ is subset of a*
    assert res.is_subset_b_in_a is False # a* is not subset of a+
    assert res.counterexample_a_not_b is None
    assert res.counterexample_b_not_a == ""
    assert res.verdict == "A_IS_SUBSET_OF_B"


def test_regex_disjoint_languages() -> None:
    # Pure 'a' characters vs pure 'b' characters (non-empty)
    res = compare_regex_patterns(r"^a+$", r"^b+$")
    assert res.are_equivalent is False
    assert res.are_disjoint is True
    assert res.shared_sample is None
    assert res.verdict == "DISJOINT"


def test_regex_counterexample_synthesis() -> None:
    # Pattern A accepts "foo" or "bar", Pattern B accepts "foo" or "baz"
    res = compare_regex_patterns(r"foo|bar", r"foo|baz")
    assert res.are_equivalent is False
    assert res.counterexample_a_not_b == "bar"
    assert res.counterexample_b_not_a == "baz"
    assert res.shared_sample == "foo"
    assert res.verdict == "OVERLAPPING_DISTINCT"


def test_mcp_compare_tool() -> None:
    server = MCPServer()
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "regex_compare_equivalence",
            "arguments": {
                "pattern_a": r"x(y|z)",
                "pattern_b": r"xy|xz",
            }
        }
    }
    resp_str = server.handle_request(json.dumps(req))
    assert resp_str is not None
    resp = json.loads(resp_str)
    assert "result" in resp
    text = resp["result"]["content"][0]["text"]
    data = json.loads(text)
    assert data["are_equivalent"] is True
    assert data["verdict"] == "EQUIVALENT"


def test_mcp_minimize_tool() -> None:
    server = MCPServer()
    req = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "regex_minimize_dfa",
            "arguments": {
                "pattern": r"(a|a)+",
            }
        }
    }
    resp_str = server.handle_request(json.dumps(req))
    assert resp_str is not None
    resp = json.loads(resp_str)
    assert "result" in resp
    text = resp["result"]["content"][0]["text"]
    data = json.loads(text)
    assert "minimized_dfa_states" in data
    assert data["minimized_dfa_states"] >= 1


def test_cli_compare_command(capsys) -> None:
    code = main(["compare", "a(b|c)", "ab|ac", "--json"])
    assert code == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["are_equivalent"] is True
    assert data["verdict"] == "EQUIVALENT"


def test_cli_minimize_command(capsys) -> None:
    code = main(["minimize", "a(b|c)", "--json"])
    assert code == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "minimized_dfa_states" in data
