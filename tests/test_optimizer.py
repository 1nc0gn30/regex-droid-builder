"""Unit tests for regex optimization and canonical simplification engine."""

import re
from regex_droid_builder import RegexOptimizationResult, optimize_regex


def test_optimize_quantifiers():
    # {0,1} -> ?, {1,} -> +, {0,} -> *, {1} -> ''
    raw = r"a{0,1}b{1,}c{0,}d{1}"
    res = optimize_regex(raw)

    assert isinstance(res, RegexOptimizationResult)
    assert res.optimized_pattern == r"a?b+c*d"
    assert res.characters_saved > 0
    assert len(res.transformations) >= 4


def test_optimize_character_classes():
    # [0-9] -> \d, [^0-9] -> \D, [a-zA-Z0-9_] -> \w
    raw = r"[0-9]+-[^0-9]+-[a-zA-Z0-9_]+"
    res = optimize_regex(raw)

    assert res.optimized_pattern == r"\d+-\D+-\w+"
    assert res.characters_saved > 0


def test_unbox_single_char_brackets():
    raw = r"[a][b][5]"
    res = optimize_regex(raw)
    assert res.optimized_pattern == "ab5"


def test_dedup_alternations():
    raw = r"(cat|dog|cat)"
    res = optimize_regex(raw)
    assert res.optimized_pattern == r"(cat|dog)"

    single = r"(apple|apple)"
    res_single = optimize_regex(single)
    assert res_single.optimized_pattern == "apple"


def test_semantic_equivalence():
    raw = r"[0-9]{1,}[a-zA-Z0-9_]{0,1}"
    res = optimize_regex(raw)

    # Both compiled patterns should match the same string
    orig_compiled = re.compile(raw)
    opt_compiled = re.compile(res.optimized_pattern)

    test_input = "123_abc"
    assert bool(orig_compiled.match(test_input)) == bool(opt_compiled.match(test_input))
