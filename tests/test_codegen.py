"""Tests for multi-language code generation."""

import pytest
from regex_droid_builder.codegen import generate_code_snippets


def test_codegen_all_languages():
    snippets = generate_code_snippets(r"^[\w.-]+@example\.com$", "i")
    assert "python" in snippets
    assert "javascript" in snippets
    assert "rust" in snippets
    assert "go" in snippets
    assert "java" in snippets
    assert "csharp" in snippets

    assert "re.IGNORECASE" in snippets["python"]
    assert "RegExp" in snippets["javascript"]
    assert "Regex::new" in snippets["rust"]
    assert "regexp.MustCompile" in snippets["go"]
