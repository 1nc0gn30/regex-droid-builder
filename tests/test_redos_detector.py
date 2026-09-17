"""Tests for ReDoS Vulnerability & Catastrophic Backtracking Detector."""

import pytest
from regex_droid_builder.redos_detector import ReDoSAnalyzer, ReDoSSeverity


def test_safe_regex_audit(redos_analyzer):
    rep = redos_analyzer.analyze(r"^[a-zA-Z0-9_-]+$")
    assert rep.is_vulnerable is False
    assert rep.severity == ReDoSSeverity.SAFE
    assert rep.complexity_order == "O(N)"


def test_nested_quantifiers_detection(redos_analyzer):
    evil_patterns = [
        r"(a+)+$",
        r"([a-zA-Z]+)*",
        r"(\d+)+",
    ]
    for pattern in evil_patterns:
        rep = redos_analyzer.analyze(pattern)
        assert rep.is_vulnerable is True
        assert rep.severity in (ReDoSSeverity.CRITICAL, ReDoSSeverity.HIGH)
        assert "O(2^N)" in rep.complexity_order


def test_overlapping_alternation_detection(redos_analyzer):
    pattern = r"(\w|\d)+$"
    rep = redos_analyzer.analyze(pattern)
    assert rep.is_vulnerable is True
    assert "Overlapping Alternation" in (rep.vulnerability_type or "")


def test_empty_pattern_audit(redos_analyzer):
    rep = redos_analyzer.analyze("")
    assert rep.is_vulnerable is False
    assert rep.severity == ReDoSSeverity.SAFE
