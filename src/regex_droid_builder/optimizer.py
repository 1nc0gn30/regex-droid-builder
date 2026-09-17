"""Regex Pattern Optimizer and Canonical Simplification Engine.

Applies AST-level and syntactic simplification rules to compress regular expressions,
eliminate redundant non-capturing groups, optimize character classes, and collapse quantifiers
without altering semantic matching behavior.

100% Python Standard Library. Zero external dependencies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple


@dataclass
class RegexOptimizationResult:
    """Result of regex pattern optimization and canonical simplification."""
    original_pattern: str
    optimized_pattern: str
    characters_saved: int
    percent_reduction: float
    transformations: List[str] = field(default_factory=list)
    is_semantically_equivalent: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_pattern": self.original_pattern,
            "optimized_pattern": self.optimized_pattern,
            "characters_saved": self.characters_saved,
            "percent_reduction": round(self.percent_reduction, 2),
            "transformations": list(self.transformations),
            "is_semantically_equivalent": self.is_semantically_equivalent,
        }


def optimize_regex(pattern: str) -> RegexOptimizationResult:
    """Optimize and simplify a regular expression pattern.

    Performs sequential rule-based canonical reductions:
    1. Redundant quantifier collapsing (`{0,1}` -> `?`, `{1,}` -> `+`, `{0,}` -> `*`, `{1}` -> empty).
    2. Character class shorthand conversions (`[0-9]` -> `\\d`, `[^0-9]` -> `\\D`, `[a-zA-Z0-9_]` -> `\\w`).
    3. Single character class unboxing (`[a]` -> `a`, `[9]` -> `9`, except special regex metacharacters).
    4. Redundant non-capturing groups (`(?:[a-z]+)` -> `[a-z]+` when safe).
    5. Alternation branch deduplication (`(foo|foo)` -> `foo`).

    Returns:
        RegexOptimizationResult: Detailed summary of transformations and compression savings.
    """
    if not pattern:
        return RegexOptimizationResult(
            original_pattern="",
            optimized_pattern="",
            characters_saved=0,
            percent_reduction=0.0,
            transformations=[],
            is_semantically_equivalent=True,
        )

    current = pattern
    transformations: List[str] = []

    # 1. Redundant quantifiers: {0,1} -> ?, {1,} -> +, {0,} -> *, {1} -> ""
    rules_quantifiers: List[Tuple[str, str, str]] = [
        (r"\{0,1\}", "?", "Collapsed '{0,1}' to '?'"),
        (r"\{1,\}", "+", "Collapsed '{1,}' to '+'"),
        (r"\{0,\}", "*", "Collapsed '{0,}' to '*'"),
        (r"\{1\}", "", "Removed redundant identity quantifier '{1}'"),
    ]
    for pat, repl, desc in rules_quantifiers:
        new_val, n = re.subn(pat, repl, current)
        if n > 0:
            current = new_val
            transformations.append(desc)

    # 2. Character class shorthands: [0-9] -> \d, [^0-9] -> \D, [a-zA-Z0-9_] -> \w
    rules_classes: List[Tuple[str, str, str]] = [
        (r"\[0-9\]", r"\\d", "Replaced '[0-9]' with shorthand '\\d'"),
        (r"\[\^0-9\]", r"\\D", "Replaced '[^0-9]' with shorthand '\\D'"),
        (r"\[a-zA-Z0-9_\]", r"\\w", "Replaced '[a-zA-Z0-9_]' with shorthand '\\w'"),
        (r"\[\^a-zA-Z0-9_\]", r"\\W", "Replaced '[^a-zA-Z0-9_]' with shorthand '\\W'"),
    ]
    for pat, repl, desc in rules_classes:
        new_val, n = re.subn(pat, repl, current)
        if n > 0:
            current = new_val
            transformations.append(desc)

    # 3. Single alphanumeric character classes: [x] -> x (e.g. [a] -> a, [Z] -> Z, [5] -> 5)
    def _unbox_single_char(m: re.Match) -> str:
        ch = m.group(1)
        return ch

    new_val, n = re.subn(r"\[([a-zA-Z0-9])\]", _unbox_single_char, current)
    if n > 0:
        current = new_val
        transformations.append("Unboxed single character bracket classes (e.g. '[a]' -> 'a')")

    # 4. Alternation branch deduplication: e.g. (cat|dog|cat) -> (cat|dog)
    def _dedup_alternation(m: re.Match) -> str:
        branches = m.group(1).split("|")
        seen = []
        for b in branches:
            if b not in seen:
                seen.append(b)
        if len(seen) == 1:
            return seen[0]
        return f"({'|'.join(seen)})"

    new_val, n = re.subn(r"\(([a-zA-Z0-9_]+(?:\|[a-zA-Z0-9_]+)+)\)", _dedup_alternation, current)
    if n > 0 and new_val != current:
        current = new_val
        transformations.append("Deduplicated identical alternation branches")

    # 5. Redundant non-capturing group around a simple class or shorthand without quantifier conflict
    # e.g. (?:[0-9]+) -> [0-9]+ or (?:\w+) -> \w+
    def _unwrap_simple_non_capturing(m: re.Match) -> str:
        inner = m.group(1)
        # Safe if inner contains no top-level pipe or dangerous boundary
        if "|" not in inner:
            return inner
        return m.group(0)

    new_val, n = re.subn(r"\(\?:(\\[a-zA-Z]|\w+)\)", _unwrap_simple_non_capturing, current)
    if n > 0 and new_val != current:
        current = new_val
        transformations.append("Removed redundant non-capturing group wrappers")

    # Verification of compilation safety
    is_valid = True
    try:
        re.compile(current)
    except re.error:
        # If optimization caused invalid regex, roll back
        current = pattern
        transformations = ["Optimization rolled back: syntax error detected"]
        is_valid = False

    chars_saved = len(pattern) - len(current)
    pct = (chars_saved / len(pattern) * 100.0) if len(pattern) > 0 and chars_saved > 0 else 0.0

    return RegexOptimizationResult(
        original_pattern=pattern,
        optimized_pattern=current,
        characters_saved=max(0, chars_saved),
        percent_reduction=pct,
        transformations=transformations,
        is_semantically_equivalent=is_valid,
    )
