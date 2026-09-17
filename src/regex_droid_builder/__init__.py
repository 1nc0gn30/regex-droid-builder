"""
regex-droid-builder: Visual Regex AST Builder, ReDoS Vulnerability Detector & Code Generator.
Zero external runtime dependencies.
"""

from __future__ import annotations

from regex_droid_builder.ast_engine import (
    ASTNode,
    NodeType,
    RegexASTParser,
    RegexBuilder,
    explain_regex,
    generate_test_samples,
)
from regex_droid_builder.automaton_engine import (
    AutomatonBuilder,
    AutomatonDFA,
    AutomatonGasMeter,
    GasMeterExecutionResult,
    ThompsonNFA,
    to_mermaid_state_diagram,
)
from regex_droid_builder.catalog import RegexPreset, get_preset, list_presets
from regex_droid_builder.codegen import generate_code_snippets
from regex_droid_builder.mcp_server import MCPServer, run_mcp_server
from regex_droid_builder.optimizer import RegexOptimizationResult, optimize_regex
from regex_droid_builder.redos_detector import (
    ReDoSAnalyzer,
    ReDoSSeverity,
    VulnerabilityReport,
)

__version__ = "0.1.0"
__author__ = "1nc0gn30"

__all__ = [
    "ASTNode",
    "NodeType",
    "RegexASTParser",
    "RegexBuilder",
    "explain_regex",
    "generate_test_samples",
    "optimize_regex",
    "RegexOptimizationResult",
    "RegexPreset",
    "get_preset",
    "list_presets",
    "generate_code_snippets",
    "ReDoSAnalyzer",
    "ReDoSSeverity",
    "VulnerabilityReport",
    "AutomatonBuilder",
    "AutomatonDFA",
    "AutomatonGasMeter",
    "GasMeterExecutionResult",
    "ThompsonNFA",
    "to_mermaid_state_diagram",
    "MCPServer",
    "run_mcp_server",
]

