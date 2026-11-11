<p align="center">
  <img src="assets/hero-banner.svg" alt="Regex Droid Builder — Visual Regex AST Analyzer, Automaton Verifier & ReDoS Guard" width="100%" />
</p>

# Regex Droid Builder

**Zero-dependency Python 3.9+ regular expression AST synthesizer, Thompson NFA / subset DFA automaton compiler, Hopcroft DFA minimizer, formal equivalence verifier, ReDoS backtracking detector, dialect transpiler, and MCP server.**

- **Zoth Studio v2 Dossier**: [https://zoth.nullai.tech/tools/regex-droid-builder](https://zoth.nullai.tech/tools/regex-droid-builder)
- **Default Loopback Endpoint**: `http://127.0.0.1:8101`
- **Runtime Dependencies**: Zero external Python runtime packages (100% Python `stdlib`)
- **License**: MIT (100% free and open-source)

---

## Overview

`regex-droid-builder` parses regular expressions into structured abstract syntax trees (ASTs), compiles them into Thompson NFAs and deterministic DFAs, minimizes state machines via Hopcroft/Moore partition refinement, formally checks equivalence or subset containment between two patterns (returning shortest counterexample strings when unequal), detects catastrophic backtracking (ReDoS) hazards, and exports bindings across Python, JavaScript/TypeScript, Rust, Go, and PHP.

---

## Architecture

```text
src/regex_droid_builder/
├── ast_engine.py          # Recursive-descent regex AST parser, natural-language explainer & sample fuzzer
├── redos_guard.py         # Static & dynamic ReDoS star-height / overlapping alternation analyzer
├── automaton.py           # Thompson NFA construction, subset-construction DFA, Hopcroft minimization & gas meter
├── verifier.py            # Product-automaton BFS equivalence / subset verifier & counterexample generator
├── transpiler.py          # Cross-dialect transpiler (Python, PCRE, JavaScript, Go RE2, Rust regex, POSIX ERE)
├── codegen.py             # Multi-language code snippet emitter (Python, JS/TS, Rust, Go, PHP)
├── catalog.py             # Curated preset patterns with positive and negative test suites
├── mcp_server.py          # JSON-RPC 2.0 stdio MCP server exposing 11 regex analysis tools
├── ui_server.py           # Loopback HTTP API + browser workstation server (127.0.0.1:8101)
└── cli.py                 # Unified CLI entrypoint (`regex-droid` / `regexdroid`)
```

---

## Quickstart

```bash
git clone https://github.com/1nc0gn30/regex-droid-builder.git
cd regex-droid-builder
python3 -m pip install -e ".[dev]"

# Start the loopback web workstation on http://127.0.0.1:8101
regex-droid serve --host 127.0.0.1 --port 8101
```

Run directly from a source checkout without installing:

```bash
PYTHONPATH=src python3 -m regex_droid_builder.cli serve --port 8101
```

---

## CLI & MCP Usage

### CLI Subcommands

Installed entrypoints: `regex-droid`, `regexdroid`, and `regex-droid-builder`.

```bash
# View CLI help
regex-droid --help

# Explain a regex AST in plain English (or pass --json)
regex-droid explain "^[a-z0-9]+(?:-[a-z0-9]+)*$" --json

# Audit a pattern for ReDoS catastrophic backtracking risks
regex-droid audit "^(a+)+$" --json

# Test candidate strings against a pattern
regex-droid test "^\d{4}-\d{2}-\d{2}$" "2026-11-11" "11/11/2026" --json

# Compile to Thompson NFA + DFA and inspect state counts
regex-droid automaton "(ab|ac)+" --json

# Minimize into a canonical minimum-state DFA via Hopcroft partitioning
regex-droid minimize "(a|b)*abb" --json

# Formally prove whether two regexes accept the exact same language
regex-droid compare "(a|b)*" "(a*b*)*" --json

# Simulate execution cost against the automaton gas meter
regex-droid gas-meter "^[a-z0-9_]{3,16}$" "zoth_operator_01" --json

# Transpile across regex dialects (python, pcre, javascript, go, rust, posix)
regex-droid transpile "(?P<year>\d{4})-(?P<month>\d{2})" --from python --to javascript --json

# Generate ready-to-use host language bindings
regex-droid codegen "^[\w.+-]+@[\w-]+\.[\w.-]+$" --lang rust

# List curated regex presets
regex-droid presets --json

# Launch the stdio MCP server
regex-droid mcp
```

### ZothOS v3.4.0 CLI Integration

On ZothOS v3.4.0 workstations, `regex-droid` is available on `PATH` (`/usr/local/bin/regex-droid`):

```bash
regex-droid audit "^(a+)+$" --json
regex-droid web              # Starts http://127.0.0.1:8101
regex-droid desktop          # Launches the Electron workstation shell
```

### Model Context Protocol (MCP) Tools

```json
{
  "mcpServers": {
    "regex-droid-builder": {
      "command": "regex-droid",
      "args": ["mcp"]
    }
  }
}
```

| MCP Tool | Description |
| :--- | :--- |
| `regex_explain` | Parse a regex into an AST and return token-by-token plain-English explanations |
| `regex_analyze_redos` | Detect nested quantifiers, ambiguous alternations, and ReDoS attack strings |
| `regex_test` | Match test inputs with full span offsets and named/numbered capture groups |
| `regex_generate_code` | Emit code snippets for Python, JavaScript, Rust, Go, and PHP |
| `regex_presets` | Return curated regex presets with positive/negative test cases |
| `regex_automaton_analysis` | Build Thompson NFA and subset-construction DFA transition tables |
| `regex_gas_meter` | Trace input step-by-step with bounded gas metering |
| `regex_compare_equivalence` | Prove formal language equivalence/containment or return counterexamples |
| `regex_transpile_dialect` | Convert syntax and named capture conventions across regex engines |
| `regex_minimize_dfa` | Produce canonical minimal-state DFA via Hopcroft partition refinement |
| `regex_diagnostics` | Return host runtime and catalog health telemetry |

---

## HTTP API Reference

When running on `http://127.0.0.1:8101`:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health`, `/api/health` | Service status, uptime, and UTC timestamp |
| `GET` | `/api/presets` | Curated regex preset catalog |
| `GET` | `/api/diagnostics` | Runtime platform and preset count |
| `POST` | `/api/explain` | AST breakdown and human-readable explanation |
| `POST` | `/api/redos` | ReDoS vulnerability score, Complexity class, and remediation advice |
| `POST` | `/api/test` | Batch string match execution and capture group extraction |
| `POST` | `/api/samples` | Synthesize matching/non-matching sample strings from AST |
| `POST` | `/api/codegen` | Multi-language snippet generation |
| `POST` | `/api/automaton` | NFA/DFA state graph synthesis |
| `POST` | `/api/gas-meter` | Step-metered automaton execution trace |
| `POST` | `/api/compare` | Formal equivalence and counterexample search |
| `POST` | `/api/transpile` | Cross-dialect regex syntax conversion |
| `POST` | `/api/minimize` | Canonical Hopcroft DFA state minimization |

---

## Testing & Verification

```bash
# Run the full unit and formal-verification test suite
python3 -m pytest -q

# Run internal CLI self-check
regex-droid test-self

# Scan repository with gitleaks
gitleaks detect --source . --no-banner --redact
```

---

## Support

Regex Droid Builder is 100% free and open-source software. Optional community support is available via [Buy Us a Coffee (Stripe)](https://buy.stripe.com/3cIfZg27PdKo2D64Ocfw40X).

## License

MIT License — Copyright (c) 2026 [1nc0gn30](https://1nc0gn30.si) (`@1nc0gn30`) & [NullAI](https://nullai.tech). See [LICENSE](LICENSE) for full text.
