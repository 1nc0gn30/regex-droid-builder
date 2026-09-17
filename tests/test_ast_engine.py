"""Tests for Regex AST Parser and Natural Language Explainer."""

import pytest
from regex_droid_builder.ast_engine import (
    ASTNode,
    NodeType,
    RegexASTParser,
    RegexBuilder,
    explain_regex,
)


def test_ast_parser_email(email_parser):
    ast = email_parser.parse()
    assert ast.type == NodeType.ROOT
    assert len(ast.children) > 0
    d = ast.to_dict()
    assert "type" in d
    assert "children" in d


def test_ast_parser_alternation():
    parser = RegexASTParser(r"(cat|dog|fish)")
    ast = parser.parse()
    assert ast.type == NodeType.ROOT


def test_ast_parser_character_class():
    parser = RegexASTParser(r"[^0-9a-fA-F]")
    ast = parser.parse()
    assert ast.children[0].type == NodeType.CHARACTER_CLASS
    assert ast.children[0].metadata.get("negated") is True


def test_ast_parser_lookaround():
    parser = RegexASTParser(r"(?<=https:\/\/)[a-zA-Z0-9.-]+")
    ast = parser.parse()
    assert ast.type == NodeType.ROOT


def test_explain_regex():
    breakdown = explain_regex(r"^https?:\/\/(?:www\.)?google\.com$")
    assert len(breakdown) >= 4
    types = [b["type"] for b in breakdown]
    assert "ANCHOR" in types
    assert "LITERAL" in types or "GROUP" in types


def test_fluent_builder():
    builder = RegexBuilder()
    pattern = builder.start_of_line().word_characters(1).literally("@").email().end_of_line().build()
    assert pattern.startswith("^")
    assert pattern.endswith("$")
    assert r"\w+" in pattern


def test_generate_test_samples():
    from regex_droid_builder.ast_engine import generate_test_samples
    samples = generate_test_samples(r"^[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}$", count=3)
    assert len(samples["matching"]) > 0
    assert len(samples["non_matching"]) > 0
    # Test on literal/digit regex
    digit_samples = generate_test_samples(r"^\d{3}-\d{4}$", count=2)
    assert len(digit_samples["matching"]) > 0
    assert len(digit_samples["non_matching"]) > 0

