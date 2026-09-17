"""
Automaton Engine: Thompson NFA, Subset Construction DFA, and State Machine Execution Gas Meter.
Zero external runtime dependencies (100% Python Standard Library).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple, Union

from .ast_engine import ASTNode, NodeType, RegexASTParser

EPSILON = "ε"


def symbol_matches(symbol: str, char: str) -> bool:
    """Check if a transition symbol matches an input character."""
    if symbol == EPSILON:
        return False
    if symbol == char:
        return True
    if symbol == ".":
        return char != "\n"
    if symbol == "\\d":
        return char.isdigit()
    if symbol == "\\D":
        return not char.isdigit()
    if symbol == "\\w":
        return char.isalnum() or char == "_"
    if symbol == "\\W":
        return not (char.isalnum() or char == "_")
    if symbol == "\\s":
        return char.isspace()
    if symbol == "\\S":
        return not char.isspace()
    if symbol.startswith("\\") and len(symbol) == 2:
        return char == symbol[1]

    # Character class [ ... ] or [^ ... ]
    if symbol.startswith("[") and symbol.endswith("]"):
        inner = symbol[1:-1]
        negated = False
        if inner.startswith("^"):
            negated = True
            inner = inner[1:]

        # Check ranges or individual characters
        idx = 0
        matched = False
        while idx < len(inner):
            if idx + 2 < len(inner) and inner[idx + 1] == "-":
                start_c = inner[idx]
                end_c = inner[idx + 2]
                if ord(start_c) <= ord(char) <= ord(end_c):
                    matched = True
                    break
                idx += 3
            else:
                c = inner[idx]
                if c == "\\" and idx + 1 < len(inner):
                    idx += 1
                    c = inner[idx]
                    if c == "d" and char.isdigit():
                        matched = True
                        break
                    elif c == "w" and (char.isalnum() or char == "_"):
                        matched = True
                        break
                    elif c == "s" and char.isspace():
                        matched = True
                        break
                    elif char == c:
                        matched = True
                        break
                elif char == c:
                    matched = True
                    break
                idx += 1

        return not matched if negated else matched

    return False


@dataclass
class NFAState:
    """A state in a Thompson NFA."""
    id: int
    is_accept: bool = False
    transitions: Dict[str, Set[int]] = field(default_factory=dict)

    def add_transition(self, symbol: str, to_state: int) -> None:
        if symbol not in self.transitions:
            self.transitions[symbol] = set()
        self.transitions[symbol].add(to_state)


@dataclass
class ThompsonNFA:
    """Thompson Non-Deterministic Finite Automaton."""
    start_state: int
    accept_state: int
    states: Dict[int, NFAState] = field(default_factory=dict)
    symbols: Set[str] = field(default_factory=set)

    @property
    def total_states(self) -> int:
        return len(self.states)

    def epsilon_closure(self, state_ids: Set[int]) -> Set[int]:
        """Compute epsilon-closure for a set of states."""
        closure = set(state_ids)
        stack = list(state_ids)

        while stack:
            curr = stack.pop()
            st = self.states.get(curr)
            if not st:
                continue
            for nxt in st.transitions.get(EPSILON, set()):
                if nxt not in closure:
                    closure.add(nxt)
                    stack.append(nxt)

        return closure


@dataclass
class DFAState:
    """A state in a Deterministic Finite Automaton."""
    id: int
    nfa_states: FrozenSet[int]
    is_accept: bool
    transitions: Dict[str, int] = field(default_factory=dict)


@dataclass
class AutomatonDFA:
    """Deterministic Finite Automaton compiled from NFA."""
    start_state: int
    states: Dict[int, DFAState] = field(default_factory=dict)
    alphabet: Set[str] = field(default_factory=set)
    state_explosion_ratio: float = 1.0
    is_state_explosion: bool = False

    @property
    def total_states(self) -> int:
        return len(self.states)


@dataclass
class GasMeterExecutionResult:
    """Result of running input through the automaton gas meter."""
    pattern: str
    input_text: str
    is_match: bool
    gas_consumed: int
    max_gas_limit: int
    gas_exhausted: bool
    nfa_states_count: int
    dfa_states_count: int
    state_explosion_risk: str
    execution_steps: List[Dict[str, Any]] = field(default_factory=list)
    verdict: str = "SAFE"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern": self.pattern,
            "input_text": self.input_text,
            "is_match": self.is_match,
            "gas_consumed": self.gas_consumed,
            "max_gas_limit": self.max_gas_limit,
            "gas_exhausted": self.gas_exhausted,
            "nfa_states_count": self.nfa_states_count,
            "dfa_states_count": self.dfa_states_count,
            "state_explosion_risk": self.state_explosion_risk,
            "execution_steps": self.execution_steps,
            "verdict": self.verdict,
        }


class AutomatonBuilder:
    """Builds Thompson NFAs and DFAs from Regex AST."""

    def __init__(self) -> None:
        self._next_state_id = 0

    def _new_state(self, is_accept: bool = False) -> NFAState:
        st = NFAState(id=self._next_state_id, is_accept=is_accept)
        self._next_state_id += 1
        return st

    def build_nfa(self, pattern: str) -> ThompsonNFA:
        """Compile a regex pattern into a Thompson NFA."""
        self._next_state_id = 0
        parser = RegexASTParser(pattern)
        ast_root = parser.parse()
        return self._build_from_ast(ast_root)

    def _build_from_ast(self, root: ASTNode) -> ThompsonNFA:
        """Build Thompson NFA from parsed AST node."""
        if root.type == NodeType.ROOT:
            if not root.children:
                s0 = self._new_state()
                s1 = self._new_state(is_accept=True)
                s0.add_transition(EPSILON, s1.id)
                return ThompsonNFA(start_state=s0.id, accept_state=s1.id, states={s0.id: s0, s1.id: s1})
            if len(root.children) == 1:
                return self._build_sub_nfa(root.children[0])
            return self._build_sequence(root.children)
        return self._build_sub_nfa(root)

    def _build_sub_nfa(self, node: ASTNode) -> ThompsonNFA:
        base_nfa: ThompsonNFA

        if node.type == NodeType.LITERAL:
            s0 = self._new_state()
            s1 = self._new_state(is_accept=True)
            val = node.value
            if not val:
                s0.add_transition(EPSILON, s1.id)
                symbols = set()
            elif val.startswith("\\") and len(val) == 2:
                # Escaped literal character (e.g. \., \*, \+)
                char = val[1]
                s0.add_transition(char, s1.id)
                symbols = {char}
            elif len(val) == 1:
                s0.add_transition(val, s1.id)
                symbols = {val}
            else:
                # Sequence of literal characters
                curr = s0
                for i, ch in enumerate(val):
                    nxt = s1 if i == len(val) - 1 else self._new_state()
                    curr.add_transition(ch, nxt.id)
                    curr = nxt
                symbols = set(val)
            base_nfa = ThompsonNFA(start_state=s0.id, accept_state=s1.id, states={s0.id: s0, s1.id: s1}, symbols=symbols)

        elif node.type == NodeType.CHARACTER_CLASS:
            s0 = self._new_state()
            s1 = self._new_state(is_accept=True)
            s0.add_transition(node.value, s1.id)
            base_nfa = ThompsonNFA(start_state=s0.id, accept_state=s1.id, states={s0.id: s0, s1.id: s1}, symbols={node.value})

        elif node.type == NodeType.ANCHOR:
            # For simplicity in NFA, treat anchors as epsilon transitions
            s0 = self._new_state()
            s1 = self._new_state(is_accept=True)
            s0.add_transition(EPSILON, s1.id)
            base_nfa = ThompsonNFA(start_state=s0.id, accept_state=s1.id, states={s0.id: s0, s1.id: s1})

        elif node.type == NodeType.SEQUENCE:
            base_nfa = self._build_sequence(node.children)

        elif node.type == NodeType.ALTERNATION:
            base_nfa = self._build_alternation(node.children)

        elif node.type == NodeType.GROUP:
            base_nfa = self._build_sequence(node.children) if node.children else self._empty_nfa()

        else:
            base_nfa = self._empty_nfa()

        # Apply quantifier if attached
        if node.quantifier:
            base_nfa = self._apply_quantifier(base_nfa, node.quantifier)

        return base_nfa

    def _empty_nfa(self) -> ThompsonNFA:
        s0 = self._new_state()
        s1 = self._new_state(is_accept=True)
        s0.add_transition(EPSILON, s1.id)
        return ThompsonNFA(start_state=s0.id, accept_state=s1.id, states={s0.id: s0, s1.id: s1})

    def _build_sequence(self, children: List[ASTNode]) -> ThompsonNFA:
        if not children:
            return self._empty_nfa()
        if len(children) == 1:
            return self._build_sub_nfa(children[0])

        nfas = [self._build_sub_nfa(child) for child in children]
        merged_states: Dict[int, NFAState] = {}
        merged_symbols: Set[str] = set()

        for i in range(len(nfas) - 1):
            curr_nfa = nfas[i]
            next_nfa = nfas[i + 1]
            merged_states.update(curr_nfa.states)
            merged_symbols.update(curr_nfa.symbols)
            # Link curr accept to next start
            curr_accept = merged_states[curr_nfa.accept_state]
            curr_accept.is_accept = False
            curr_accept.add_transition(EPSILON, next_nfa.start_state)

        last_nfa = nfas[-1]
        merged_states.update(last_nfa.states)
        merged_symbols.update(last_nfa.symbols)

        return ThompsonNFA(
            start_state=nfas[0].start_state,
            accept_state=last_nfa.accept_state,
            states=merged_states,
            symbols=merged_symbols,
        )

    def _build_alternation(self, branches: List[ASTNode]) -> ThompsonNFA:
        if not branches:
            return self._empty_nfa()
        if len(branches) == 1:
            return self._build_sub_nfa(branches[0])

        s_start = self._new_state()
        s_end = self._new_state(is_accept=True)
        merged_states: Dict[int, NFAState] = {s_start.id: s_start, s_end.id: s_end}
        merged_symbols: Set[str] = set()

        for branch in branches:
            b_nfa = self._build_sub_nfa(branch)
            merged_states.update(b_nfa.states)
            merged_symbols.update(b_nfa.symbols)

            s_start.add_transition(EPSILON, b_nfa.start_state)
            b_accept = merged_states[b_nfa.accept_state]
            b_accept.is_accept = False
            b_accept.add_transition(EPSILON, s_end.id)

        return ThompsonNFA(
            start_state=s_start.id,
            accept_state=s_end.id,
            states=merged_states,
            symbols=merged_symbols,
        )

    def _apply_quantifier(self, nfa: ThompsonNFA, q: str) -> ThompsonNFA:
        s_start = self._new_state()
        s_end = self._new_state(is_accept=True)
        states = dict(nfa.states)
        states[s_start.id] = s_start
        states[s_end.id] = s_end

        orig_accept = states[nfa.accept_state]
        orig_accept.is_accept = False

        if q in ("*", "*?"):
            s_start.add_transition(EPSILON, nfa.start_state)
            s_start.add_transition(EPSILON, s_end.id)
            orig_accept.add_transition(EPSILON, nfa.start_state)
            orig_accept.add_transition(EPSILON, s_end.id)
        elif q in ("+", "+?"):
            s_start.add_transition(EPSILON, nfa.start_state)
            orig_accept.add_transition(EPSILON, nfa.start_state)
            orig_accept.add_transition(EPSILON, s_end.id)
        elif q in ("?", "??"):
            s_start.add_transition(EPSILON, nfa.start_state)
            s_start.add_transition(EPSILON, s_end.id)
            orig_accept.add_transition(EPSILON, s_end.id)
        else:
            # Default fallback for bounded ranges {m,n}
            s_start.add_transition(EPSILON, nfa.start_state)
            orig_accept.add_transition(EPSILON, s_end.id)

        return ThompsonNFA(
            start_state=s_start.id,
            accept_state=s_end.id,
            states=states,
            symbols=nfa.symbols,
        )

    def convert_to_dfa(self, nfa: ThompsonNFA, max_states: int = 500) -> AutomatonDFA:
        """
        Convert Thompson NFA to DFA using powerset subset construction.
        Detects exponential state explosion.
        """
        initial_closure = frozenset(nfa.epsilon_closure({nfa.start_state}))
        dfa_states: Dict[int, DFAState] = {}
        unmarked: List[FrozenSet[int]] = [initial_closure]
        state_map: Dict[FrozenSet[int], int] = {initial_closure: 0}

        is_explosion = False
        symbols = [s for s in nfa.symbols if s != EPSILON]

        while unmarked:
            if len(dfa_states) >= max_states:
                is_explosion = True
                break

            curr_set = unmarked.pop(0)
            curr_id = state_map[curr_set]
            is_acc = any(nfa.states[sid].is_accept for sid in curr_set if sid in nfa.states)

            dfa_state = DFAState(id=curr_id, nfa_states=curr_set, is_accept=is_acc)
            dfa_states[curr_id] = dfa_state

            for sym in symbols:
                move_dest: Set[int] = set()
                for sid in curr_set:
                    st = nfa.states.get(sid)
                    if st and sym in st.transitions:
                        move_dest.update(st.transitions[sym])

                if not move_dest:
                    continue

                closure = frozenset(nfa.epsilon_closure(move_dest))
                if not closure:
                    continue

                if closure not in state_map:
                    if len(state_map) >= max_states:
                        is_explosion = True
                        break
                    next_id = len(state_map)
                    state_map[closure] = next_id
                    unmarked.append(closure)

                dfa_state.transitions[sym] = state_map[closure]

        ratio = (len(dfa_states) / max(1, nfa.total_states))
        if ratio > 3.0 or is_explosion:
            is_explosion = True

        return AutomatonDFA(
            start_state=0,
            states=dfa_states,
            alphabet=set(symbols),
            state_explosion_ratio=round(ratio, 2),
            is_state_explosion=is_explosion,
        )


class AutomatonGasMeter:
    """
    Executes an automaton over an input string while metering execution gas
    to detect ReDoS and runaway computational complexity.
    """

    def __init__(self, max_gas: int = 50000) -> None:
        self.max_gas = max_gas
        self.builder = AutomatonBuilder()

    def trace_execution(self, pattern: str, input_text: str) -> GasMeterExecutionResult:
        """
        Run the pattern against input_text using the NFA/DFA gas meter.
        Tracks state transitions step-by-step.
        """
        nfa = self.builder.build_nfa(pattern)
        dfa = self.builder.convert_to_dfa(nfa)

        gas_consumed = 0
        steps: List[Dict[str, Any]] = []
        gas_exhausted = False

        # Simulate NFA active states set for high fidelity tracking of branch multiplicity
        active_states = nfa.epsilon_closure({nfa.start_state})
        gas_consumed += len(active_states)

        steps.append({
            "step": 0,
            "char": "[START]",
            "active_state_count": len(active_states),
            "gas_step": len(active_states),
            "gas_total": gas_consumed,
        })

        is_match = False
        for pos, ch in enumerate(input_text):
            if gas_consumed >= self.max_gas:
                gas_exhausted = True
                break

            next_states: Set[int] = set()
            step_gas = 0

            # For every currently active state, test matching transitions
            for sid in active_states:
                st = nfa.states.get(sid)
                if not st:
                    continue
                for sym, targets in st.transitions.items():
                    step_gas += 1
                    if sym != EPSILON and symbol_matches(sym, ch):
                        next_states.update(targets)

            gas_consumed += step_gas
            closure = nfa.epsilon_closure(next_states)
            gas_consumed += len(closure)
            active_states = closure

            if len(steps) < 50:
                steps.append({
                    "step": pos + 1,
                    "char": ch,
                    "active_state_count": len(active_states),
                    "gas_step": step_gas + len(closure),
                    "gas_total": gas_consumed,
                })

            if not active_states:
                # Dead state
                break

        is_match = any(nfa.states[sid].is_accept for sid in active_states if sid in nfa.states)

        # Risk classification
        if gas_exhausted:
            risk = "CRITICAL_EXPLOSION"
            verdict = "GAS_EXHAUSTED_POTENTIAL_REDOS"
        elif dfa.is_state_explosion:
            risk = "HIGH_STATE_EXPLOSION"
            verdict = "DFA_STATE_EXPLOSION_WARNING"
        elif gas_consumed > len(input_text) * 20 and len(input_text) > 5:
            risk = "MODERATE_AMBIGUITY"
            verdict = "HIGH_BACKTRACKING_DENSITY"
        else:
            risk = "LOW"
            verdict = "SAFE"

        return GasMeterExecutionResult(
            pattern=pattern,
            input_text=input_text,
            is_match=is_match,
            gas_consumed=gas_consumed,
            max_gas_limit=self.max_gas,
            gas_exhausted=gas_exhausted,
            nfa_states_count=nfa.total_states,
            dfa_states_count=dfa.total_states,
            state_explosion_risk=risk,
            execution_steps=steps,
            verdict=verdict,
        )


def to_mermaid_state_diagram(nfa_or_dfa: Union[ThompsonNFA, AutomatonDFA], max_nodes: int = 25) -> str:
    """Generate Mermaid stateDiagram-v2 representation of the automaton."""
    lines = ["stateDiagram-v2"]

    if isinstance(nfa_or_dfa, ThompsonNFA):
        nfa = nfa_or_dfa
        lines.append(f"    [*] --> S{nfa.start_state}")
        count = 0
        for sid, st in nfa.states.items():
            if count >= max_nodes:
                lines.append(f"    S{sid} --> ... : [Truncated for brevity]")
                break
            for sym, targets in st.transitions.items():
                lbl = sym if sym != EPSILON else "ε"
                clean_lbl = lbl.replace('"', '\\"').replace(":", "colon")
                for tid in targets:
                    lines.append(f"    S{sid} --> S{tid} : {clean_lbl}")
            if st.is_accept:
                lines.append(f"    S{sid} --> [*]")
            count += 1

    elif isinstance(nfa_or_dfa, AutomatonDFA):
        dfa = nfa_or_dfa
        lines.append(f"    [*] --> D{dfa.start_state}")
        count = 0
        for sid, st in dfa.states.items():
            if count >= max_nodes:
                lines.append(f"    D{sid} --> ... : [Truncated]")
                break
            for sym, tid in st.transitions.items():
                clean_lbl = sym.replace('"', '\\"').replace(":", "colon")
                lines.append(f"    D{sid} --> D{tid} : {clean_lbl}")
            if st.is_accept:
                lines.append(f"    D{sid} --> [*]")
            count += 1

    return "\n".join(lines)
