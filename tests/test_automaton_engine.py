"""
Tests for Automaton Engine: Thompson NFA, DFA Powerset Construction, Gas Meter, and Diagrams.
Zero external runtime dependencies.
"""

from __future__ import annotations

import json
from typing import Any, Dict

import pytest

from regex_droid_builder.automaton_engine import (
    AutomatonBuilder,
    AutomatonDFA,
    AutomatonGasMeter,
    GasMeterExecutionResult,
    ThompsonNFA,
    symbol_matches,
    to_mermaid_state_diagram,
)
from regex_droid_builder.cli import main
from regex_droid_builder.mcp_server import MCPServer


def test_symbol_matches_basic() -> None:
    assert symbol_matches("a", "a") is True
    assert symbol_matches("a", "b") is False
    assert symbol_matches(".", "x") is True
    assert symbol_matches(".", "\n") is False
    assert symbol_matches("\\d", "5") is True
    assert symbol_matches("\\d", "x") is False
    assert symbol_matches("\\D", "x") is True
    assert symbol_matches("\\D", "5") is False
    assert symbol_matches("\\w", "_") is True
    assert symbol_matches("\\w", "a") is True
    assert symbol_matches("\\w", "!") is False
    assert symbol_matches("\\s", " ") is True
    assert symbol_matches("\\s", "\t") is True
    assert symbol_matches("\\s", "a") is False


def test_symbol_matches_character_class() -> None:
    assert symbol_matches("[a-z]", "m") is True
    assert symbol_matches("[a-z]", "A") is False
    assert symbol_matches("[^0-9]", "a") is True
    assert symbol_matches("[^0-9]", "7") is False
    assert symbol_matches("[0-9a-fA-F]", "e") is True


def test_thompson_nfa_construction_primitives() -> None:
    builder = AutomatonBuilder()

    # Literal
    nfa_lit = builder.build_nfa("a")
    assert nfa_lit.total_states >= 2
    assert "a" in nfa_lit.symbols

    # Sequence
    nfa_seq = builder.build_nfa("abc")
    assert nfa_seq.total_states >= 4
    assert {"a", "b", "c"}.issubset(nfa_seq.symbols)

    # Alternation
    nfa_alt = builder.build_nfa("cat|dog")
    assert nfa_alt.total_states >= 8
    assert nfa_alt.states[nfa_alt.accept_state].is_accept is True

    # Kleene star
    nfa_star = builder.build_nfa("a*")
    assert nfa_star.total_states >= 4

    # Plus quantifier
    nfa_plus = builder.build_nfa("a+")
    assert nfa_plus.total_states >= 4


def test_dfa_powerset_construction() -> None:
    builder = AutomatonBuilder()
    nfa = builder.build_nfa("ab|ac")
    dfa = builder.convert_to_dfa(nfa)

    assert isinstance(dfa, AutomatonDFA)
    assert dfa.total_states >= 2
    assert dfa.start_state == 0
    assert any(st.is_accept for st in dfa.states.values())
    assert dfa.state_explosion_ratio >= 0.1


def test_automaton_gas_meter_match_and_mismatch() -> None:
    meter = AutomatonGasMeter(max_gas=10000)

    # Test match
    res_match = meter.trace_execution("abc", "abc")
    assert res_match.is_match is True
    assert res_match.gas_consumed > 0
    assert res_match.gas_exhausted is False
    assert res_match.verdict == "SAFE"
    assert len(res_match.execution_steps) >= 3

    # Test mismatch
    res_mismatch = meter.trace_execution("abc", "xyz")
    assert res_mismatch.is_match is False
    assert res_mismatch.gas_consumed > 0


def test_automaton_gas_meter_complex_pattern() -> None:
    meter = AutomatonGasMeter(max_gas=20000)
    res = meter.trace_execution(r"[\w]+@[\w]+\.[a-z]+", "user@domain.com")
    assert res.is_match is True
    assert res.gas_consumed > 5
    assert res.nfa_states_count > 0
    assert res.dfa_states_count > 0


def test_automaton_gas_meter_gas_exhaustion_limit() -> None:
    # Set a very low gas limit to verify safe termination
    tiny_meter = AutomatonGasMeter(max_gas=5)
    res = tiny_meter.trace_execution("a*", "aaaaaaaaaaaaaaa")
    assert res.gas_exhausted is True
    assert res.state_explosion_risk == "CRITICAL_EXPLOSION"
    assert "GAS_EXHAUSTED" in res.verdict


def test_mermaid_diagram_generation() -> None:
    builder = AutomatonBuilder()
    nfa = builder.build_nfa("a|b")
    dfa = builder.convert_to_dfa(nfa)

    diagram_nfa = to_mermaid_state_diagram(nfa)
    assert diagram_nfa.startswith("stateDiagram-v2")
    assert "[*] -->" in diagram_nfa

    diagram_dfa = to_mermaid_state_diagram(dfa)
    assert diagram_dfa.startswith("stateDiagram-v2")
    assert "--> [*]" in diagram_dfa


def test_mcp_automaton_tools() -> None:
    server = MCPServer()

    # regex_automaton_analysis
    res_auto = server.handle_tool_call("regex_automaton_analysis", {"pattern": "ab*c"})
    data_auto = json.loads(res_auto["content"][0]["text"])
    assert data_auto["pattern"] == "ab*c"
    assert data_auto["nfa_states_count"] > 0
    assert "mermaid_nfa" in data_auto
    assert "mermaid_dfa" in data_auto

    # regex_gas_meter
    res_gas = server.handle_tool_call(
        "regex_gas_meter",
        {"pattern": "abc", "input_text": "abc", "max_gas": 1000}
    )
    data_gas = json.loads(res_gas["content"][0]["text"])
    assert data_gas["is_match"] is True
    assert data_gas["gas_consumed"] > 0
    assert data_gas["verdict"] == "SAFE"


def test_cli_automaton_commands(capsys: pytest.CaptureFixture[str]) -> None:
    # CLI automaton --json
    code = main(["automaton", "a|b", "--json"])
    assert code == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["nfa_states_count"] > 0

    # CLI automaton --mermaid
    code_m = main(["automaton", "a|b", "--mermaid"])
    assert code_m == 0
    out_m = capsys.readouterr().out
    assert "stateDiagram-v2" in out_m

    # CLI gas-meter --json
    code_g = main(["gas-meter", "abc", "abc", "--json"])
    assert code_g == 0
    out_g = capsys.readouterr().out
    data_g = json.loads(out_g)
    assert data_g["is_match"] is True
