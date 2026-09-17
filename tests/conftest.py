"""Pytest configuration and fixtures for regex-droid-builder."""

import os
import sys
from pathlib import Path
import pytest

# Ensure src is in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from regex_droid_builder.ast_engine import RegexASTParser
from regex_droid_builder.redos_detector import ReDoSAnalyzer


@pytest.fixture
def email_parser() -> RegexASTParser:
    return RegexASTParser(r"^[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}$")


@pytest.fixture
def redos_analyzer() -> ReDoSAnalyzer:
    return ReDoSAnalyzer()
