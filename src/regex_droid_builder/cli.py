"""
Command-Line Interface for regex-droid-builder.
Zero external runtime dependencies.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any, List, Optional

from regex_droid_builder.ast_engine import explain_regex
from regex_droid_builder.automaton_engine import (
    AutomatonBuilder,
    AutomatonGasMeter,
    to_mermaid_state_diagram,
)
from regex_droid_builder.catalog import PRESETS, get_preset, list_presets
from regex_droid_builder.codegen import generate_code_snippets
from regex_droid_builder.mcp_server import run_mcp_server
from regex_droid_builder.redos_detector import ReDoSAnalyzer, ReDoSSeverity
from regex_droid_builder.ui_server import run_ui_server


class Colors:
    """ANSI terminal color helpers with automatic disabling."""
    def __init__(self, force_disable: bool = False) -> None:
        disabled = force_disable or "NO_COLOR" in os.environ or not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty()
        self.BLUE = "" if disabled else "\033[94m"
        self.GREEN = "" if disabled else "\033[92m"
        self.YELLOW = "" if disabled else "\033[93m"
        self.RED = "" if disabled else "\033[91m"
        self.CYAN = "" if disabled else "\033[96m"
        self.BOLD = "" if disabled else "\033[1m"
        self.DIM = "" if disabled else "\033[2m"
        self.RESET = "" if disabled else "\033[0m"


def build_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="regex-droid",
        description="Visual Regex AST Builder, ReDoS Vulnerability Detector & Multi-Language Code Generator",
    )
    parser.add_argument("-v", "--version", action="version", version="regex-droid-builder 0.1.0")

    base = argparse.ArgumentParser(add_help=False)
    base.add_argument("--no-color", action="store_true", help="Disable ANSI color output")
    base.add_argument("-f", "--flags", default="", help="Regex flags (e.g. 'i', 'm', 's')")

    sub = parser.add_subparsers(dest="command", help="Available subcommands")

    # explain
    p_exp = sub.add_parser("explain", parents=[base], help="Explain a regular expression in plain English")
    p_exp.add_argument("pattern", help="Regular expression pattern to explain")
    p_exp.add_argument("--json", action="store_true", help="Output AST as JSON")

    # audit / redos
    p_aud = sub.add_parser("audit", aliases=["redos"], parents=[base], help="Audit pattern for ReDoS vulnerabilities")
    p_aud.add_argument("pattern", help="Regular expression pattern to audit")
    p_aud.add_argument("--json", action="store_true", help="Output report as JSON")

    # test
    p_test = sub.add_parser("test", parents=[base], help="Test strings against a regular expression")
    p_test.add_argument("pattern", help="Regular expression pattern")
    p_test.add_argument("inputs", nargs="+", help="Input strings to test")
    p_test.add_argument("--json", action="store_true", help="Output results as JSON")

    # codegen
    p_code = sub.add_parser("codegen", parents=[base], help="Generate multi-language code snippets")
    p_code.add_argument("pattern", help="Regular expression pattern")
    p_code.add_argument("-l", "--lang", choices=["all", "python", "javascript", "rust", "go", "java", "csharp"], default="all")

    # presets
    p_pres = sub.add_parser("presets", parents=[base], help="List curated regex presets")
    p_pres.add_argument("--json", action="store_true", help="Output presets as JSON")

    # automaton / dfa
    p_auto = sub.add_parser("automaton", aliases=["dfa", "nfa"], parents=[base], help="Compile regex to Thompson NFA & DFA state machine")
    p_auto.add_argument("pattern", help="Regular expression pattern to compile")
    p_auto.add_argument("--mermaid", action="store_true", help="Print Mermaid stateDiagram-v2")
    p_auto.add_argument("--json", action="store_true", help="Output automaton report as JSON")

    # gas-meter
    p_gas = sub.add_parser("gas-meter", aliases=["gas"], parents=[base], help="Simulate input execution against regex automaton gas meter")
    p_gas.add_argument("pattern", help="Regular expression pattern")
    p_gas.add_argument("input_text", help="Input string to trace")
    p_gas.add_argument("--max-gas", type=int, default=50000, help="Maximum gas ceiling (default: 50000)")
    p_gas.add_argument("--json", action="store_true", help="Output execution trace as JSON")

    # serve
    p_serve = sub.add_parser("serve", parents=[base], help="Start Regex Droid Studio Web UI (Material 3 influenced)")
    p_serve.add_argument("--host", default="0.0.0.0", help="Host address (default: 0.0.0.0)")
    p_serve.add_argument("--port", type=int, default=8097, help="Port (default: 8097)")

    # mcp
    p_mcp = sub.add_parser("mcp", parents=[base], help="Run Model Context Protocol stdio server")

    # compare / equivalence
    p_comp = sub.add_parser("compare", aliases=["equiv", "diff"], parents=[base], help="Formally verify equivalence, subset containment, or find counterexamples between two regexes")
    p_comp.add_argument("pattern_a", help="First regular expression pattern")
    p_comp.add_argument("pattern_b", help="Second regular expression pattern")
    p_comp.add_argument("--max-depth", type=int, default=25, help="Maximum BFS search depth (default: 25)")
    p_comp.add_argument("--json", action="store_true", help="Output comparison result as JSON")

    # transpile
    p_trans = sub.add_parser("transpile", parents=[base], help="Transpile regex across language dialects (Python, PCRE, JS, Go, Rust, POSIX)")
    p_trans.add_argument("pattern", help="Regular expression pattern to transpile")
    p_trans.add_argument("--from", dest="from_dialect", default="python", help="Source dialect (python, pcre, javascript, go, rust, posix_ere)")
    p_trans.add_argument("--to", dest="to_dialect", default="javascript", help="Target dialect (python, pcre, javascript, go, rust, posix_ere)")
    p_trans.add_argument("--json", action="store_true", help="Output transpilation result as JSON")

    # minimize
    p_min = sub.add_parser("minimize", parents=[base], help="Minimize regex into canonical minimum-state DFA via Hopcroft/Moore partitioning")
    p_min.add_argument("pattern", help="Regular expression pattern to minimize")
    p_min.add_argument("--mermaid", action="store_true", help="Print Mermaid stateDiagram-v2 of minimal DFA")
    p_min.add_argument("--json", action="store_true", help="Output minimal DFA summary as JSON")

    # diagnostics / doctor
    p_doc = sub.add_parser("doctor", aliases=["diagnostics", "platform"], parents=[base], help="Run system diagnostics")

    # test-self
    p_tself = sub.add_parser("test-self", parents=[base], help="Run internal self-verification test runner")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """CLI execution entrypoint."""
    if argv is None:
        argv = sys.argv[1:]

    parser = build_parser()
    if not argv:
        parser.print_help()
        return 0

    args = parser.parse_args(argv)
    c = Colors(force_disable=getattr(args, "no_color", False))

    if args.command == "explain":
        steps = explain_regex(args.pattern, args.flags)
        if args.json:
            print(json.dumps({"pattern": args.pattern, "steps": steps}, indent=2))
        else:
            print(f"\n{c.BOLD}🤖 Regex Structure & Plain-English Explanation{c.RESET}")
            print(f"  Pattern: {c.CYAN}/{args.pattern}/{args.flags}{c.RESET}\n")
            for idx, step in enumerate(steps, 1):
                indent = "  " * step["depth"]
                val = f" ({step['value']})" if step["value"] else ""
                print(f"  {indent}{c.GREEN}#{idx}{c.RESET} {c.BOLD}{step['type']}{c.RESET}{val}: {step['explanation']}")
            print()
        return 0

    elif args.command in ("audit", "redos"):
        analyzer = ReDoSAnalyzer()
        report = analyzer.analyze(args.pattern, args.flags)
        if args.json:
            print(json.dumps(report.to_dict(), indent=2))
        else:
            print(f"\n{c.BOLD}🛡️ ReDoS Security Audit Report{c.RESET}")
            print(f"  Pattern: {c.CYAN}/{args.pattern}/{args.flags}{c.RESET}")

            sev_color = c.GREEN if report.severity == ReDoSSeverity.SAFE else (c.YELLOW if report.severity in (ReDoSSeverity.LOW, ReDoSSeverity.MEDIUM) else c.RED)
            print(f"  Severity: {sev_color}{report.severity.value}{c.RESET}")
            print(f"  Complexity: {c.BOLD}{report.complexity_order}{c.RESET}")
            print(f"  Description: {report.description}")
            if report.is_vulnerable:
                print(f"  {c.RED}Matched Subpattern: {report.matched_subpattern}{c.RESET}")
                print(f"  {c.YELLOW}Remediation: {report.remediation}{c.RESET}")
            print()
        return 0 if not report.is_vulnerable else 1

    elif args.command == "test":
        re_flags = 0
        if "i" in args.flags:
            re_flags |= re.IGNORECASE
        if "m" in args.flags:
            re_flags |= re.MULTILINE
        if "s" in args.flags:
            re_flags |= re.DOTALL

        try:
            compiled = re.compile(args.pattern, re_flags)
        except re.error as e:
            print(f"{c.RED}Error: Invalid regex: {str(e)}{c.RESET}")
            return 1

        results = []
        for s in args.inputs:
            m = compiled.search(s)
            results.append({
                "input": s,
                "is_match": bool(m),
                "matched_text": m.group(0) if m else None,
                "groups": m.groups() if m else []
            })

        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(f"\n{c.BOLD}🧪 Regex Match Results for /{args.pattern}/{args.flags}:{c.RESET}\n")
            for r in results:
                icon = f"{c.GREEN}✓ MATCH{c.RESET}" if r["is_match"] else f"{c.RED}✗ NO MATCH{c.RESET}"
                extra = f" (captured: '{r['matched_text']}')" if r["is_match"] else ""
                print(f"  [{icon}] \"{r['input']}\"{extra}")
            print()
        return 0

    elif args.command == "codegen":
        snippets = generate_code_snippets(args.pattern, args.flags)
        if args.lang == "all":
            for lang, code in snippets.items():
                print(f"\n{c.BOLD}--- {lang.upper()} ---{c.RESET}")
                print(code.strip())
        else:
            print(snippets.get(args.lang, "").strip())
        return 0

    elif args.command == "presets":
        if args.json:
            print(json.dumps(list_presets(), indent=2))
        else:
            print(f"\n{c.BOLD}🤖 Regex Droid Curated Presets Catalog{c.RESET}\n")
            for p in PRESETS.values():
                print(f"  {c.CYAN}{p.id:<14}{c.RESET} : {c.BOLD}{p.name}{c.RESET} ({c.DIM}{p.category}{c.RESET})")
                print(f"    Pattern: /{p.pattern}/{p.flags}")
                print(f"    {c.DIM}{p.explanation}{c.RESET}\n")
        return 0

    elif args.command in ("automaton", "dfa", "nfa"):
        builder = AutomatonBuilder()
        nfa = builder.build_nfa(args.pattern)
        dfa = builder.convert_to_dfa(nfa)
        mermaid_nfa = to_mermaid_state_diagram(nfa)
        mermaid_dfa = to_mermaid_state_diagram(dfa)

        if args.json:
            print(json.dumps({
                "pattern": args.pattern,
                "nfa_states_count": nfa.total_states,
                "dfa_states_count": dfa.total_states,
                "state_explosion_ratio": dfa.state_explosion_ratio,
                "is_state_explosion": dfa.is_state_explosion,
                "mermaid_nfa": mermaid_nfa,
                "mermaid_dfa": mermaid_dfa,
            }, indent=2))
        elif args.mermaid:
            print(f"\n{c.BOLD}--- Thompson NFA State Diagram ---{c.RESET}\n")
            print(mermaid_nfa)
            print(f"\n{c.BOLD}--- Powerset DFA State Diagram ---{c.RESET}\n")
            print(mermaid_dfa)
        else:
            print(f"\n{c.BOLD}🤖 Automaton Finite State Machine Analysis{c.RESET}")
            print(f"  Pattern             : /{args.pattern}/")
            print(f"  Thompson NFA States : {c.CYAN}{nfa.total_states}{c.RESET}")
            print(f"  Subset DFA States   : {c.CYAN}{dfa.total_states}{c.RESET}")
            print(f"  State Ratio (D/N)   : {dfa.state_explosion_ratio}x")
            expl_str = f"{c.RED}CRITICAL EXPLOSION{c.RESET}" if dfa.is_state_explosion else f"{c.GREEN}BOUNDED / SAFE{c.RESET}"
            print(f"  Explosion Risk      : {expl_str}\n")
        return 0

    elif args.command in ("gas-meter", "gas"):
        meter = AutomatonGasMeter(max_gas=args.max_gas)
        res = meter.trace_execution(args.pattern, args.input_text)
        if args.json:
            print(json.dumps(res.to_dict(), indent=2))
        else:
            print(f"\n{c.BOLD}⚡ Automaton Execution Gas Meter{c.RESET}")
            print(f"  Pattern       : /{res.pattern}/")
            print(f"  Input String  : \"{res.input_text}\" (len {len(res.input_text)})")
            match_str = f"{c.GREEN}MATCH{c.RESET}" if res.is_match else f"{c.RED}NO MATCH{c.RESET}"
            print(f"  Result        : {match_str}")
            print(f"  Gas Consumed  : {c.CYAN}{res.gas_consumed}{c.RESET} / {res.max_gas_limit}")
            risk_color = c.RED if "CRITICAL" in res.state_explosion_risk else (c.YELLOW if "MODERATE" in res.state_explosion_risk else c.GREEN)
            print(f"  Risk Profile  : {risk_color}{res.state_explosion_risk}{c.RESET}")
            print(f"  Verdict       : {res.verdict}\n")
        return 0

    elif args.command in ("compare", "equiv", "diff"):
        from regex_droid_builder.formal_verifier import compare_regex_patterns
        res = compare_regex_patterns(args.pattern_a, args.pattern_b, max_depth=args.max_depth)
        if args.json:
            print(json.dumps(res.to_dict(), indent=2))
        else:
            print(f"\n{c.BOLD}⚖️ Regex Formal Equivalence & Containment Verifier{c.RESET}")
            print(f"  Pattern A: {c.CYAN}/{res.pattern_a}/{c.RESET}")
            print(f"  Pattern B: {c.CYAN}/{res.pattern_b}/{c.RESET}")
            equiv_color = c.GREEN if res.are_equivalent else c.RED
            print(f"  Verdict  : {equiv_color}{res.verdict}{c.RESET}")
            print(f"  Equivalent: {equiv_color}{res.are_equivalent}{c.RESET}")
            print(f"  A ⊆ B    : {res.is_subset_a_in_b} | B ⊆ A: {res.is_subset_b_in_a} | Disjoint: {res.are_disjoint}")
            print(f"  DFA A States (min): {res.dfa_a_states_minimized} (orig: {res.dfa_a_states_original})")
            print(f"  DFA B States (min): {res.dfa_b_states_minimized} (orig: {res.dfa_b_states_original})")
            if res.counterexample_a_not_b is not None:
                print(f"  {c.RED}Counterexample (in A, not B):{c.RESET} \"{res.counterexample_a_not_b}\"")
            if res.counterexample_b_not_a is not None:
                print(f"  {c.RED}Counterexample (in B, not A):{c.RESET} \"{res.counterexample_b_not_a}\"")
            if res.shared_sample is not None:
                print(f"  {c.GREEN}Shared Match Sample        :{c.RESET} \"{res.shared_sample}\"")
            print()
        return 0

    elif args.command == "transpile":
        from regex_droid_builder.dialect_transpiler import transpile_regex
        res = transpile_regex(args.pattern, source_dialect=args.from_dialect, target_dialect=args.to_dialect)
        if args.json:
            print(json.dumps(res.to_dict(), indent=2))
        else:
            print(f"\n{c.BOLD}🔄 Regex Dialect Transpiler ({res.source_dialect} -> {res.target_dialect}){c.RESET}")
            print(f"  Source Pattern: {c.CYAN}/{res.source_pattern}/{c.RESET}")
            print(f"  Target Pattern: {c.GREEN}/{res.target_pattern}/{c.RESET}")
            lossless_str = f"{c.GREEN}YES{c.RESET}" if res.is_lossless else f"{c.RED}NO (Compatibility Warnings){c.RESET}"
            print(f"  Lossless      : {lossless_str}")
            if res.warnings:
                print(f"\n  {c.YELLOW}Compatibility Notes:{c.RESET}")
                for w in res.warnings:
                    sev_col = c.RED if w.severity == "UNSUPPORTED_ERROR" else c.YELLOW
                    print(f"    - {sev_col}[{w.severity}]{c.RESET} {w.feature}: {w.message}")
                    print(f"      {c.DIM}Remedy: {w.remediation}{c.RESET}")
            print(f"\n  {c.BOLD}Native Code Snippet ({res.target_dialect}):{c.RESET}")
            for line in res.code_snippet.split("\n"):
                print(f"    {line}")
            print()
        return 0

    elif args.command == "minimize":
        from regex_droid_builder.formal_verifier import minimize_dfa
        builder = AutomatonBuilder()
        nfa = builder.build_nfa(args.pattern)
        dfa_raw = builder.convert_to_dfa(nfa)
        dfa_min = minimize_dfa(dfa_raw)
        if args.json:
            print(json.dumps({
                "pattern": args.pattern,
                "original_dfa_states": dfa_raw.total_states,
                "minimized_dfa_states": dfa_min.total_states,
                "states_saved": dfa_raw.total_states - dfa_min.total_states,
            }, indent=2))
        elif args.mermaid:
            print(to_mermaid_state_diagram(dfa_min))
        else:
            print(f"\n{c.BOLD}📐 Hopcroft / Moore Canonical DFA Minimizer{c.RESET}")
            print(f"  Pattern             : /{args.pattern}/")
            print(f"  Original DFA States : {dfa_raw.total_states}")
            print(f"  Minimized DFA States: {c.GREEN}{dfa_min.total_states}{c.RESET}")
            print(f"  States Pruned/Merged: {c.CYAN}{dfa_raw.total_states - dfa_min.total_states}{c.RESET}\n")
        return 0

    elif args.command == "serve":
        server = run_ui_server(args.host, args.port)
        print(f"{c.GREEN}🤖 Regex Droid Studio UI running at:{c.RESET} http://{args.host}:{args.port}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")
        return 0

    elif args.command == "mcp":
        run_mcp_server()
        return 0

    elif args.command in ("doctor", "diagnostics", "platform"):
        print(f"\n{c.BOLD}🤖 Regex Droid Builder - System Diagnostics{c.RESET}")
        print(f"  Platform         : {sys.platform}")
        print(f"  Python Version   : {sys.version.split()[0]}")
        print(f"  Presets Loaded   : {len(PRESETS)}")
        print(f"  Zero Runtime Deps: {c.GREEN}YES (100% Python Standard Library){c.RESET}")
        print(f"  Status           : {c.GREEN}HEALTHY{c.RESET}\n")
        return 0

    elif args.command == "test-self":
        print(f"{c.BOLD}Running internal self-verification test runner...{c.RESET}")
        # Test basic parsing
        steps = explain_regex(r"^[\w.-]+@[\w.-]+\.[a-zA-Z]{2,}$")
        assert len(steps) > 3
        # Test redos detection
        analyzer = ReDoSAnalyzer()
        rep = analyzer.analyze(r"(a+)+$")
        assert rep.is_vulnerable is True
        print(f"{c.GREEN}✓ All internal checks passed!{c.RESET}")
        return 0

    return 0
