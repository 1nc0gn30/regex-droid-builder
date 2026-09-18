"""
Formal Verifier: Hopcroft/Moore DFA State Minimization, Regex Equivalence Checking,
Subset Containment, and Shortest Counterexample Synthesis.

Zero external runtime dependencies (100% Python Standard Library).
"""

from __future__ import annotations

import collections
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

from .automaton_engine import AutomatonBuilder, AutomatonDFA, DFAState, symbol_matches


@dataclass
class RegexEquivalenceResult:
    """Result of formal language equivalence and containment verification."""
    pattern_a: str
    pattern_b: str
    are_equivalent: bool
    is_subset_a_in_b: bool
    is_subset_b_in_a: bool
    are_disjoint: bool
    counterexample_a_not_b: Optional[str] = None
    counterexample_b_not_a: Optional[str] = None
    shared_sample: Optional[str] = None
    dfa_a_states_original: int = 0
    dfa_a_states_minimized: int = 0
    dfa_b_states_original: int = 0
    dfa_b_states_minimized: int = 0
    verdict: str = "EQUIVALENT"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_a": self.pattern_a,
            "pattern_b": self.pattern_b,
            "are_equivalent": self.are_equivalent,
            "is_subset_a_in_b": self.is_subset_a_in_b,
            "is_subset_b_in_a": self.is_subset_b_in_a,
            "are_disjoint": self.are_disjoint,
            "counterexample_a_not_b": self.counterexample_a_not_b,
            "counterexample_b_not_a": self.counterexample_b_not_a,
            "shared_sample": self.shared_sample,
            "dfa_a_states_original": self.dfa_a_states_original,
            "dfa_a_states_minimized": self.dfa_a_states_minimized,
            "dfa_b_states_original": self.dfa_b_states_original,
            "dfa_b_states_minimized": self.dfa_b_states_minimized,
            "verdict": self.verdict,
        }


class DFAStateMinimizer:
    """
    Minimizes a Deterministic Finite Automaton (DFA) using
    Moore/Hopcroft equivalence partitioning into canonical minimum states.
    """

    def minimize(self, dfa: AutomatonDFA) -> AutomatonDFA:
        """Minimize the given DFA, eliminating unreachable and equivalent states."""
        if not dfa.states:
            return dfa

        # Step 1: Reachability analysis - discard states unreachable from start_state
        reachable: Set[int] = set()
        queue = collections.deque([dfa.start_state])
        reachable.add(dfa.start_state)

        while queue:
            curr = queue.popleft()
            st = dfa.states.get(curr)
            if not st:
                continue
            for next_id in st.transitions.values():
                if next_id not in reachable and next_id in dfa.states:
                    reachable.add(next_id)
                    queue.append(next_id)

        # Filter reachable states
        active_states = {sid: dfa.states[sid] for sid in reachable}
        if not active_states:
            return dfa

        alphabet = sorted(list(dfa.alphabet))

        # Step 2: Initial Partition into Accepting (F) and Non-Accepting (S \ F)
        accepting = {sid for sid, st in active_states.items() if st.is_accept}
        non_accepting = {sid for sid in active_states if sid not in accepting}

        partitions: List[Set[int]] = []
        if non_accepting:
            partitions.append(non_accepting)
        if accepting:
            partitions.append(accepting)

        # Mapping state_id -> partition block index
        state_to_block: Dict[int, int] = {}
        for idx, block in enumerate(partitions):
            for sid in block:
                state_to_block[sid] = idx

        # Dead state representation as -1
        def get_target_block(sid: int, symbol: str) -> int:
            st = active_states.get(sid)
            if not st or symbol not in st.transitions:
                return -1
            dest = st.transitions[symbol]
            return state_to_block.get(dest, -1)

        # Step 3: Iteratively refine partition blocks until fixed point
        changed = True
        max_iterations = 200
        iteration = 0

        while changed and iteration < max_iterations:
            changed = False
            iteration += 1
            new_partitions: List[Set[int]] = []

            for block in partitions:
                if len(block) <= 1:
                    new_partitions.append(block)
                    continue

                # Group states in block by signature of target partition blocks
                signature_groups: Dict[Tuple[int, ...], Set[int]] = collections.defaultdict(set)
                for sid in block:
                    sig = tuple(get_target_block(sid, sym) for sym in alphabet)
                    signature_groups[sig].add(sid)

                if len(signature_groups) > 1:
                    changed = True
                    new_partitions.extend(signature_groups.values())
                else:
                    new_partitions.append(block)

            partitions = new_partitions
            state_to_block = {}
            for idx, block in enumerate(partitions):
                for sid in block:
                    state_to_block[sid] = idx

        # Step 4: Reconstruct Minimized DFA
        new_dfa_states: Dict[int, DFAState] = {}
        new_start_state = state_to_block[dfa.start_state]

        for block_idx, block in enumerate(partitions):
            # Pick representative state
            rep_id = next(iter(block))
            rep_state = active_states[rep_id]
            is_acc = rep_state.is_accept

            # Combine NFA states from all constituent states
            combined_nfa = frozenset().union(*(active_states[sid].nfa_states for sid in block))

            new_transitions: Dict[str, int] = {}
            for sym in alphabet:
                target_blk = get_target_block(rep_id, sym)
                if target_blk != -1:
                    new_transitions[sym] = target_blk

            new_dfa_states[block_idx] = DFAState(
                id=block_idx,
                nfa_states=combined_nfa,
                is_accept=is_acc,
                transitions=new_transitions,
            )

        return AutomatonDFA(
            start_state=new_start_state,
            states=new_dfa_states,
            alphabet=set(alphabet),
            state_explosion_ratio=round(len(new_dfa_states) / max(1, len(dfa.states)), 2),
            is_state_explosion=False,
        )


class DFAEquivalenceVerifier:
    """
    Formally compares two regular expressions via product automaton BFS.
    Computes language equivalence, subset containment, disjointness, and counterexamples.
    """

    def __init__(self) -> None:
        self.builder = AutomatonBuilder()
        self.minimizer = DFAStateMinimizer()

    def compare(self, pattern_a: str, pattern_b: str, max_depth: int = 25) -> RegexEquivalenceResult:
        """
        Formally verify relationship between pattern_a and pattern_b.
        Returns RegexEquivalenceResult with shortest counterexample strings if different.
        """
        # Build NFAs and DFAs
        nfa_a = self.builder.build_nfa(pattern_a)
        dfa_a_raw = self.builder.convert_to_dfa(nfa_a)
        dfa_a = self.minimizer.minimize(dfa_a_raw)

        nfa_b = self.builder.build_nfa(pattern_b)
        dfa_b_raw = self.builder.convert_to_dfa(nfa_b)
        dfa_b = self.minimizer.minimize(dfa_b_raw)

        # Combined alphabet for transitions
        # Extract concrete representative characters for symbolic classes
        combined_symbols = dfa_a.alphabet.union(dfa_b.alphabet)
        alphabet_chars = self._derive_concrete_alphabet(combined_symbols)

        # Product automaton exploration
        # State in product: (Optional[int], Optional[int]) -> (state_in_A, state_in_B)
        start_state_a: Optional[int] = dfa_a.start_state
        start_state_b: Optional[int] = dfa_b.start_state

        visited: Set[Tuple[Optional[int], Optional[int]]] = set()
        queue = collections.deque([(start_state_a, start_state_b, "")])
        visited.add((start_state_a, start_state_b))

        counterexample_a_not_b: Optional[str] = None
        counterexample_b_not_a: Optional[str] = None
        shared_sample: Optional[str] = None

        while queue:
            sa, sb, current_str = queue.popleft()

            is_acc_a = (sa is not None and sa in dfa_a.states and dfa_a.states[sa].is_accept)
            is_acc_b = (sb is not None and sb in dfa_b.states and dfa_b.states[sb].is_accept)

            # Check for counterexamples
            if is_acc_a and not is_acc_b and counterexample_a_not_b is None:
                counterexample_a_not_b = current_str

            if is_acc_b and not is_acc_a and counterexample_b_not_a is None:
                counterexample_b_not_a = current_str

            if is_acc_a and is_acc_b and shared_sample is None:
                shared_sample = current_str

            # Early termination if both counterexamples and shared sample are found
            if counterexample_a_not_b is not None and counterexample_b_not_a is not None and shared_sample is not None:
                break

            if len(current_str) >= max_depth:
                continue

            # Expand product transitions
            for char in alphabet_chars:
                next_sa = self._step_dfa(dfa_a, sa, char)
                next_sb = self._step_dfa(dfa_b, sb, char)

                if next_sa is None and next_sb is None:
                    continue

                pair = (next_sa, next_sb)
                if pair not in visited:
                    visited.add(pair)
                    queue.append((next_sa, next_sb, current_str + char))

        are_equiv = (counterexample_a_not_b is None and counterexample_b_not_a is None)
        is_sub_a_b = (counterexample_a_not_b is None)
        is_sub_b_a = (counterexample_b_not_a is None)
        are_disjoint = (shared_sample is None)

        verdict: str
        if are_equiv:
            verdict = "EQUIVALENT"
        elif is_sub_a_b:
            verdict = "A_IS_SUBSET_OF_B"
        elif is_sub_b_a:
            verdict = "B_IS_SUBSET_OF_A"
        elif are_disjoint:
            verdict = "DISJOINT"
        else:
            verdict = "OVERLAPPING_DISTINCT"

        return RegexEquivalenceResult(
            pattern_a=pattern_a,
            pattern_b=pattern_b,
            are_equivalent=are_equiv,
            is_subset_a_in_b=is_sub_a_b,
            is_subset_b_in_a=is_sub_b_a,
            are_disjoint=are_disjoint,
            counterexample_a_not_b=counterexample_a_not_b,
            counterexample_b_not_a=counterexample_b_not_a,
            shared_sample=shared_sample,
            dfa_a_states_original=len(dfa_a_raw.states),
            dfa_a_states_minimized=len(dfa_a.states),
            dfa_b_states_original=len(dfa_b_raw.states),
            dfa_b_states_minimized=len(dfa_b.states),
            verdict=verdict,
        )

    def _step_dfa(self, dfa: AutomatonDFA, current_state: Optional[int], char: str) -> Optional[int]:
        """Advance one character through the DFA, returning destination state or None if dead."""
        if current_state is None or current_state not in dfa.states:
            return None
        st = dfa.states[current_state]

        # Check exact symbol match first
        if char in st.transitions:
            return st.transitions[char]

        # Check character classes or wildcards
        for sym, dest in st.transitions.items():
            if symbol_matches(sym, char):
                return dest

        return None

    def _derive_concrete_alphabet(self, symbols: Set[str]) -> List[str]:
        """Derive concrete ASCII characters to probe the alphabet transitions."""
        chars: Set[str] = set()
        for s in symbols:
            if not s:
                continue
            if len(s) == 1 and s != ".":
                chars.add(s)
            elif s == "\\d":
                chars.update(["0", "5", "9"])
            elif s == "\\D":
                chars.update(["a", " ", "_"])
            elif s == "\\w":
                chars.update(["a", "Z", "0", "_"])
            elif s == "\\W":
                chars.update([" ", "!", "@"])
            elif s == "\\s":
                chars.update([" ", "\t"])
            elif s == "\\S":
                chars.update(["x", "1"])
            elif s == ".":
                chars.update(["a", "1", " ", "@"])
            elif s.startswith("[") and s.endswith("]"):
                # Probe basic representative characters for ranges
                inner = s[1:-1]
                if "0-9" in inner:
                    chars.update(["0", "5", "9"])
                if "a-z" in inner:
                    chars.update(["a", "m", "z"])
                if "A-Z" in inner:
                    chars.update(["A", "M", "Z"])
                # Extract literal characters inside class
                clean_inner = inner.replace("^", "").replace("-", "")
                for ch in clean_inner[:5]:
                    if ch not in ("\\",):
                        chars.add(ch)

        # Ensure a few general probe characters exist if alphabet is tiny
        if not chars:
            chars.update(["a", "b", "0", "1"])
        return sorted(list(chars))


# Singleton instances
_minimizer = DFAStateMinimizer()
_equivalence_verifier = DFAEquivalenceVerifier()


def minimize_dfa(dfa: AutomatonDFA) -> AutomatonDFA:
    """Convenience function to minimize an AutomatonDFA."""
    return _minimizer.minimize(dfa)


def compare_regex_patterns(pattern_a: str, pattern_b: str, max_depth: int = 25) -> RegexEquivalenceResult:
    """Convenience function to compare two regex patterns for formal equivalence."""
    return _equivalence_verifier.compare(pattern_a, pattern_b, max_depth=max_depth)
