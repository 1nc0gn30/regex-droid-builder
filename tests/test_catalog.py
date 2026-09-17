"""Tests for preset pattern catalog."""

import re
import pytest
from regex_droid_builder.catalog import PRESETS, get_preset, list_presets


def test_presets_catalog_validity():
    assert len(PRESETS) >= 8
    for p in PRESETS.values():
        assert p.id
        assert p.name
        assert p.pattern
        compiled = re.compile(p.pattern)

        # Run test cases
        for tc in p.test_cases:
            match = bool(compiled.search(tc["input"]))
            assert match == tc["should_match"], f"Preset {p.id} failed on input '{tc['input']}' (expected {tc['should_match']}, got {match})"


def test_get_and_list_presets():
    p = get_preset("email")
    assert p.id == "email"

    p_def = get_preset("unknown_id")
    assert p_def.id == "email"

    all_p = list_presets()
    assert len(all_p) == len(PRESETS)
