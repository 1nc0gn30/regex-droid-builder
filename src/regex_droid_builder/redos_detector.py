"""
Static ReDoS (Regular Expression Denial of Service) Vulnerability & Catastrophic Backtracking Analyzer.
Zero external runtime dependencies (100% Python Standard Library).
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ReDoSSeverity(str, Enum):
    SAFE = "SAFE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL_REDOS"


@dataclass
class VulnerabilityReport:
    """Detailed ReDoS vulnerability report."""
    pattern: str
    is_vulnerable: bool
    severity: ReDoSSeverity
    vulnerability_type: Optional[str]
    description: str
    remediation: str
    matched_subpattern: Optional[str] = None
    complexity_order: str = "O(N)"  # O(N), O(N^2), O(2^N)
    test_metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern": self.pattern,
            "is_vulnerable": self.is_vulnerable,
            "severity": self.severity.value,
            "vulnerability_type": self.vulnerability_type,
            "complexity_order": self.complexity_order,
            "description": self.description,
            "remediation": self.remediation,
            "matched_subpattern": self.matched_subpattern,
            "test_metrics": self.test_metrics,
        }


# Known dangerous evil regex syntactic patterns
EVIL_PATTERNS = [
    (
        r"(\((?:[^()]*[+*][^()]*)\))[+*]",
        "Nested Quantifiers (Polynomial / Exponential Backtracking)",
        "O(2^N)",
        ReDoSSeverity.CRITICAL,
        "A quantified group contains inner quantifiers (e.g. `(a+)+` or `(x+)*`). When matching against failing input, backtracking branches explode exponentially.",
        "Flatten inner expressions or make the outer group atomic / non-overlapping (e.g. use possessive quantifiers or character class exclusions)."
    ),
    (
        r"\((?:[a-zA-Z0-9_\\w\\d]+)\|[a-zA-Z0-9_\\w\\d]+\)[+*]",
        "Overlapping Alternation inside Quantifier",
        "O(2^N)",
        ReDoSSeverity.HIGH,
        "Alternation options inside a repeated group can match the same characters (e.g. `(a|a)+` or `(\\w|\\d)+`), causing massive branch permutations on mismatch.",
        "Ensure alternation branches are mutually exclusive, or consolidate into a single character class."
    ),
    (
        r"\.\*.*\.\*",
        "Multiple Unanchored Greedy Wildcards",
        "O(N^2)",
        ReDoSSeverity.MEDIUM,
        "Multiple `.*` greedy wildcards in the same pattern create quadratic backtracking when scanning long multiline payloads.",
        "Replace greedy `.*` with negated character classes (e.g. `[^\\n]*` or `[^\"]*`) or non-greedy `.*?`."
    ),
]


class ReDoSAnalyzer:
    """Static and empirical ReDoS detector."""

    def __init__(self, timeout_seconds: float = 0.5) -> None:
        self.timeout_seconds = timeout_seconds

    def analyze(self, pattern: str, flags: str = "") -> VulnerabilityReport:
        """Analyze regular expression for catastrophic backtracking risks."""
        if not pattern:
            return VulnerabilityReport(
                pattern=pattern,
                is_vulnerable=False,
                severity=ReDoSSeverity.SAFE,
                vulnerability_type=None,
                description="Empty regex pattern.",
                remediation="N/A",
                complexity_order="O(1)"
            )

        # Step 1: Static Pattern Matching
        for regex_danger, vtype, complexity, severity, desc, remed in EVIL_PATTERNS:
            match = re.search(regex_danger, pattern)
            if match:
                return VulnerabilityReport(
                    pattern=pattern,
                    is_vulnerable=True,
                    severity=severity,
                    vulnerability_type=vtype,
                    complexity_order=complexity,
                    description=desc,
                    remediation=remed,
                    matched_subpattern=match.group(0),
                    test_metrics={"static_rule_matched": True}
                )

        # Step 2: Empirical Micro-benchmark test with synthetic non-matching string
        metrics = self._run_empirical_test(pattern)
        if metrics.get("time_exhausted", False) or metrics.get("exponential_growth", False):
            return VulnerabilityReport(
                pattern=pattern,
                is_vulnerable=True,
                severity=ReDoSSeverity.CRITICAL,
                vulnerability_type="Empirical Catastrophic Backtracking",
                complexity_order="O(2^N)",
                description="Empirical benchmark detected significant execution latency spikes on adversarial failing inputs.",
                remediation="Eliminate nested repetitions or avoid overlapping greedy loops.",
                test_metrics=metrics
            )

        return VulnerabilityReport(
            pattern=pattern,
            is_vulnerable=False,
            severity=ReDoSSeverity.SAFE,
            vulnerability_type=None,
            complexity_order="O(N)",
            description="No catastrophic backtracking vulnerabilities detected. Expression conforms to safe linear time matching.",
            remediation="No remediation required.",
            test_metrics=metrics
        )

    def _run_empirical_test(self, pattern: str) -> Dict[str, Any]:
        """Run safe latency tests against growing input lengths."""
        try:
            compiled = re.compile(pattern)
        except re.error:
            return {"error": "Invalid regex pattern"}

        lengths = [10, 18, 24]
        times = []

        for l in lengths:
            # Create adversarial non-matching suffix payload
            test_str = "a" * l + "!"
            t0 = time.perf_counter()
            try:
                compiled.search(test_str)
            except Exception:
                pass
            elapsed = time.perf_counter() - t0
            times.append(elapsed)

        is_exponential = False
        if len(times) == 3 and times[0] > 0:
            growth_ratio_1 = times[1] / max(times[0], 1e-6)
            growth_ratio_2 = times[2] / max(times[1], 1e-6)
            if growth_ratio_2 > 4.0 and times[2] > 0.05:
                is_exponential = True

        return {
            "lengths_tested": lengths,
            "timings_seconds": [round(t, 6) for t in times],
            "exponential_growth": is_exponential,
            "max_latency": round(max(times), 6) if times else 0.0
        }
