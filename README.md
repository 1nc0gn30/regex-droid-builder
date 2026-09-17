# 🤖 Regex Droid Builder

[![CI](https://github.com/1nc0gn30/regex-droid-builder/actions/workflows/ci.yml/badge.svg)](https://github.com/1nc0gn30/regex-droid-builder/actions)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-0%20runtime-success.svg)](https://github.com/1nc0gn30/regex-droid-builder)
[![MCP Server](https://img.shields.io/badge/MCP-FastMCP%202024--11--05-blueviolet.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Visual Regular Expression AST Builder, Static ReDoS Catastrophic Backtracking Vulnerability Detector & Multi-Language Code Generator with Material 3 Web UI, Multi-OS CLI, FastMCP stdio server, and zero external runtime dependencies.**

---

## ✨ Features

- 🌳 **Regex AST & Natural Language Explainer**: Parses regular expressions into structured AST trees and generates step-by-step, plain-English explanations of literals, character classes, anchors, and quantifiers.
- 🛡️ **Static & Empirical ReDoS Defense**: Audits patterns for catastrophic exponential/polynomial backtracking risks (nested quantifiers like `(a+)+`, overlapping alternations inside loops, unanchored greedy wildcards) with complexity estimation (`O(N)`, `O(2^N)`) and remediation fixes.
- ⚡ **Multi-Language Code Generator**: Generates production-ready, type-safe snippet implementations in **Python (`re`)**, **JavaScript / TypeScript (`RegExp`)**, **Rust (`regex`)**, **Go (`regexp`)**, **Java**, and **C#**.
- 🎨 **Google Material 3 Light Mode Web UI**: Real-time regex analyzer, interactive multi-line test matrix runner, flag toggles, curated presets catalog, and 1-click code copy.
- 🚀 **Zero Third-Party Runtime Dependencies**: 100% Python Standard Library runtime (`re`, `http.server`, `urllib`, `time`, `json`, `dataclasses`, `argparse`).
- 🤖 **FastMCP Server Protocol**: Full Model Context Protocol (MCP) JSON-RPC 2.0 stdio server for Claude Desktop, Cursor, Cline, and autonomous AI coding agents.

---

## 🚀 Quick Start

### Installation
```bash
# Clone the repository
git clone https://github.com/1nc0gn30/regex-droid-builder.git
cd regex-droid-builder

# Install in editable mode
pip install -e .
```

---

## 💻 CLI Usage

```bash
# Explain regex pattern in plain English
regex-droid explain '^[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}$'

# Audit pattern for ReDoS vulnerabilities and catastrophic backtracking
regex-droid audit '(a+)+$'

# Test strings against a regular expression
regex-droid test '^https?:\/\/' 'https://google.com' 'ftp://server.org' 'http://localhost'

# Generate code in Python, JavaScript, Rust, Go, Java, and C#
regex-droid codegen '^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$' --lang python

# List curated regex presets
regex-droid presets

# Launch Google Material 3 Regex Studio Web UI
regex-droid serve --port 8097

# Start FastMCP stdio server for LLM agents
regex-droid mcp

# Run system diagnostics
regex-droid doctor
```

---

## 🤖 Model Context Protocol (MCP) Setup

Add `regex-droid-builder` to your Claude Desktop or Cursor configuration:

```json
{
  "mcpServers": {
    "regex-droid": {
      "command": "python3",
      "args": ["-m", "regex_droid_builder", "mcp"]
    }
  }
}
```

### Registered MCP Tools:
- `regex_explain`: Parse pattern and flags into plain English step-by-step AST explanation.
- `regex_analyze_redos`: Static & empirical ReDoS vulnerability audit with complexity estimation and remediation tips.
- `regex_test`: Execute multi-input test matrix against pattern with capture group extraction.
- `regex_generate_code`: Generate multi-language code snippets (Python, JS, Rust, Go, Java, C#).
- `regex_presets`: Query curated presets and test cases.
- `regex_diagnostics`: Platform and toolchain health check.

---

## 📐 Mathematical Foundations & ReDoS Complexity

### 1. Backtracking Complexity Classification

| Complexity Class | Growth Rate | Vulnerability Rating | Canonical Danger Pattern | Attack Vector Example |
| :--- | :--- | :--- | :--- | :--- |
| **Linear** | $\mathcal{O}(N)$ | **SAFE** | `^[a-zA-Z0-9]+$` | Standard token validation |
| **Polynomial** | $\mathcal{O}(N^2) \dots \mathcal{O}(N^k)$ | **MEDIUM / HIGH** | `.*=.*&` | Query parameter parser |
| **Exponential** | $\mathcal{O}(2^N)$ | **CRITICAL** | `(a+)+$`, `(a\|aa)+$` | Nested star/plus quantifiers |

### 2. Catastrophic Backtracking Mechanics
When an NFA engine attempts to match an input of length $N$ against nested quantifiers $E = (R_1^+)^+$, the number of possible parsing paths grows combinatorially according to the partition integer function $P(N) \sim 2^{N-1}$:

$$\text{Steps}(N) \ge 2^N$$

A single non-matching character at the end of a 30-byte string (e.g. `aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa!`) can trigger over $1{,}073{,}741{,}824$ recursive state transitions, causing complete thread freeze / CPU exhaustion.

---

## 🏛️ Architecture

```mermaid
flowchart TD
    subgraph CoreEngine["⚙️ Regex Droid Engine"]
        Parser["🌳 Recursive Descent AST Parser\n(Sequence, Alternation, Classes, Groups)"]
        ReDoS["🛡️ ReDoS Static & Fuzz Auditor\n(Evil-Regex Pattern Matcher)"]
        Fuzzer["⚡ Synthetic Sample Generator\n(Valid Matches + Edge-Case Fuzzing)"]
        CodeGen["💻 Polyglot Code Synthesizer\n(Python, JS, Rust, Go, Java, C#)"]
    end

    subgraph Interfaces["🖥️ Interfaces"]
        CLI["💻 CLI Entrypoint\n(regex-droid / python -m)"]
        MCP["🤖 FastMCP Stdio Server\n(Claude / Cursor / Cline)"]
        UI["🎨 Google Material 3 Studio\n(SVG Railroad Diagram & Live Matcher)"]
    end

    Parser --> ReDoS
    Parser --> Fuzzer
    Parser --> CodeGen
    ReDoS --> Interfaces
    Fuzzer --> Interfaces
    CodeGen --> Interfaces
```

---

## 🐍 Python SDK API Reference

```python
from regex_droid_builder.ast_engine import RegexASTParser, explain_regex, generate_test_samples
from regex_droid_builder.redos_detector import ReDoSAnalyzer
from regex_droid_builder.codegen import generate_code_snippets

# 1. Parse into AST & explain in natural language
pattern = r"^[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}$"
parser = RegexASTParser(pattern)
ast = parser.parse()
breakdown = explain_regex(pattern)
for step in breakdown[:3]:
    print(f"{step['type']}: {step['explanation']}")

# 2. Audit ReDoS vulnerability
analyzer = ReDoSAnalyzer()
report = analyzer.analyze("(a+)+$")
print(f"Vulnerable: {report.is_vulnerable} (Severity: {report.severity.value})")
print(f"Complexity: {report.complexity_order}")

# 3. Generate synthetic matching & non-matching test strings
samples = generate_test_samples(pattern, count=3)
print(f"Valid matches: {samples['matching']}")
print(f"Invalid non-matches: {samples['non_matching']}")

# 4. Generate multi-language code snippets
snippets = generate_code_snippets(pattern)
print(snippets["python"])
```

---

## 🧪 Running Tests

```bash
pytest -v
```

---

## 📜 License

MIT License © 2026 1nc0gn30

